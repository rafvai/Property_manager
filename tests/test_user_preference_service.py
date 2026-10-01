"""
test_user_preference_service.py
===============================
Test unitari per services/user_preference_service.py (stato onboarding).

Strategia: mock DatabaseConnection e SQLAlchemy session, come negli altri test.

Esecuzione:
    pytest tests/test_user_preference_service.py -v
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def service(mock_session):
    with patch("services.user_preference_service.DatabaseConnection") as MockDB:
        MockDB.return_value.get_session.return_value = mock_session
        MockDB.return_value.close_session = MagicMock()
        from services.user_preference_service import UserPreferenceService
        yield UserPreferenceService(MagicMock())


def _riga_trovata(mock_session, valore):
    riga = MagicMock()
    riga.value = valore
    mock_session.query.return_value.filter_by.return_value.first.return_value = riga
    return riga


class TestOnboarding:

    def test_default_non_completato(self, service, mock_session):
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        assert service.is_onboarding_completed() is False

    def test_completato_se_valore_1(self, service, mock_session):
        _riga_trovata(mock_session, "1")
        assert service.is_onboarding_completed() is True

    def test_non_completato_se_valore_0(self, service, mock_session):
        _riga_trovata(mock_session, "0")
        assert service.is_onboarding_completed() is False

    def test_set_crea_riga_e_committa(self, service, mock_session):
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        assert service.set_onboarding_completed() is True
        nuova_riga = mock_session.add.call_args[0][0]
        assert nuova_riga.key == "onboarding_completed"
        assert nuova_riga.value == "1"
        mock_session.commit.assert_called_once()

    def test_set_aggiorna_riga_esistente(self, service, mock_session):
        riga = _riga_trovata(mock_session, "0")
        assert service.set_onboarding_completed() is True
        assert riga.value == "1"
        mock_session.add.assert_not_called()

    def test_set_falso_riporta_a_zero(self, service, mock_session):
        riga = _riga_trovata(mock_session, "1")
        assert service.set_onboarding_completed(False) is True
        assert riga.value == "0"

    def test_set_invalida_cache(self, service, mock_session):
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        assert service.is_onboarding_completed() is False
        _riga_trovata(mock_session, "1")
        # Senza set() la cache restituirebbe ancora il vecchio valore
        service.set_onboarding_completed()
        assert service.is_onboarding_completed() is True

    def test_errore_db_ritorna_default(self, service, mock_session):
        mock_session.query.side_effect = Exception("db non raggiungibile")
        assert service.is_onboarding_completed() is False
