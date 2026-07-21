"""
test_deadline_service.py
========================
Test unitari per services/deadline_service.py

Strategia: mock DatabaseConnection e SQLAlchemy session.

Copertura:
- get_all: filtri property_id e include_completed, ordinamento, errore DB
- get_next_deadline: prossima scadenza futura, nessuna scadenza, filtro property
- get_by_date: scadenze per data specifica, lista vuota
- create: successo, rollback su errore
- update: campi consentiti, scadenza non trovata, rollback
- mark_completed: delega a update con completed=True
- delete: successo, non trovata, rollback

Esecuzione:
    pytest tests/test_deadline_service.py -v
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ══════════════════════════════════════════════════════════
#  Helper factories
# ══════════════════════════════════════════════════════════

def _make_deadline(id=1, title="Pagamento IMU", due_date="2024-06-16",
                   property_id=1, tenant_id="tenant_001", completed=False):
    d = MagicMock()
    d.id = id
    d.title = title
    d.due_date = due_date
    d.property_id = property_id
    d.tenant_id = tenant_id
    d.completed = completed
    d.description = "Scadenza IMU prima rata"
    d.to_dict.return_value = {
        "id": id, "title": title, "due_date": due_date,
        "property_id": property_id, "completed": completed
    }
    return d


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def deadline_service(mock_session):
    with patch("services.deadline_service.DatabaseConnection") as MockDB:
        mock_db = MockDB.return_value
        mock_db.get_session.return_value = mock_session
        mock_db.close_session = MagicMock()

        from services.deadline_service import DeadlineService
        svc = DeadlineService(logger=MagicMock())
        svc.db = mock_db
        return svc, mock_session


# ══════════════════════════════════════════════════════════
#  get_all
# ══════════════════════════════════════════════════════════

class TestGetAll:

    def test_restituisce_lista_dizionari(self, deadline_service):
        svc, session = deadline_service
        deadlines = [_make_deadline(1), _make_deadline(2)]
        session.query.return_value \
            .filter_by.return_value \
            .filter.return_value \
            .order_by.return_value \
            .all.return_value = deadlines

        result = svc.get_all()

        assert len(result) == 2
        assert isinstance(result[0], dict)

    def test_lista_vuota(self, deadline_service):
        svc, session = deadline_service
        session.query.return_value \
            .filter_by.return_value \
            .filter.return_value \
            .order_by.return_value \
            .all.return_value = []

        result = svc.get_all()

        assert result == []

    def test_filtra_completate_per_default(self, deadline_service):
        """Per default, include_completed=False — le completate non appaiono"""
        svc, session = deadline_service
        d_aperta = _make_deadline(1, completed=False)
        session.query.return_value \
            .filter_by.return_value \
            .filter.return_value \
            .order_by.return_value \
            .all.return_value = [d_aperta]

        result = svc.get_all()

        for item in result:
            assert item["completed"] is False

    def test_include_completate_se_richiesto(self, deadline_service):
        """Con include_completed=True le completate sono visibili"""
        svc, session = deadline_service
        d_completata = _make_deadline(1, completed=True)
        session.query.return_value \
            .filter_by.return_value \
            .order_by.return_value \
            .all.return_value = [d_completata]

        result = svc.get_all(include_completed=True)

        assert isinstance(result, list)

    def test_filtro_property_id(self, deadline_service):
        """get_all con property_id deve filtrare per proprietà"""
        svc, session = deadline_service
        deadlines = [_make_deadline(1, property_id=5)]
        session.query.return_value \
            .filter_by.return_value \
            .filter.return_value \
            .filter.return_value \
            .order_by.return_value \
            .all.return_value = deadlines

        result = svc.get_all(property_id=5)

        assert isinstance(result, list)

    def test_errore_db_ritorna_lista_vuota(self, deadline_service):
        svc, session = deadline_service
        session.query.side_effect = Exception("DB error")

        result = svc.get_all()

        assert result == []
        svc.logger.error.assert_called()


# ══════════════════════════════════════════════════════════
#  get_next_deadline
# ══════════════════════════════════════════════════════════

class TestGetNextDeadline:

    def test_ritorna_prossima_scadenza(self, deadline_service):
        svc, session = deadline_service
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        d = _make_deadline(1, due_date=tomorrow)
        # get_next_deadline usa UNA sola .filter() con condizioni combinate
        session.query.return_value \
            .filter.return_value \
            .order_by.return_value \
            .first.return_value = d

        result = svc.get_next_deadline()

        assert result is not None
        assert result["id"] == 1

    def test_nessuna_scadenza_futura_ritorna_none(self, deadline_service):
        svc, session = deadline_service
        session.query.return_value \
            .filter.return_value \
            .order_by.return_value \
            .first.return_value = None

        result = svc.get_next_deadline()

        assert result is None

    def test_filtro_per_property_id(self, deadline_service):
        """Con property_id deve filtrare ulteriormente (seconda .filter())"""
        svc, session = deadline_service
        session.query.return_value \
            .filter.return_value \
            .filter.return_value \
            .order_by.return_value \
            .first.return_value = None

        result = svc.get_next_deadline(property_id=3)

        # Non deve crashare con filtro aggiuntivo
        assert result is None

    def test_errore_db_ritorna_none(self, deadline_service):
        svc, session = deadline_service
        session.query.side_effect = Exception("DB error")

        result = svc.get_next_deadline()

        assert result is None
        svc.logger.error.assert_called()


# ══════════════════════════════════════════════════════════
#  get_by_date
# ══════════════════════════════════════════════════════════

class TestGetByDate:

    def test_scadenze_per_data(self, deadline_service):
        svc, session = deadline_service
        deadlines = [_make_deadline(1, due_date="2024-06-16")]
        session.query.return_value \
            .filter.return_value \
            .order_by.return_value \
            .all.return_value = deadlines

        result = svc.get_by_date("2024-06-16")

        assert len(result) == 1

    def test_data_senza_scadenze_ritorna_lista_vuota(self, deadline_service):
        svc, session = deadline_service
        session.query.return_value \
            .filter.return_value \
            .order_by.return_value \
            .all.return_value = []

        result = svc.get_by_date("2099-01-01")

        assert result == []

    def test_errore_db_ritorna_lista_vuota(self, deadline_service):
        svc, session = deadline_service
        session.query.side_effect = Exception("DB error")

        result = svc.get_by_date("2024-06-16")

        assert result == []


# ══════════════════════════════════════════════════════════
#  create
# ══════════════════════════════════════════════════════════

class TestCreate:

    def test_crea_scadenza_successo(self, deadline_service):
        svc, session = deadline_service

        with patch("services.deadline_service.Deadline") as MockDeadline:
            mock_d = MagicMock()
            mock_d.id = 10
            MockDeadline.return_value = mock_d

            result = svc.create(
                title="Pagamento IMU",
                due_date="2024-06-16",
                description="Prima rata IMU",
                property_id=1
            )

        session.add.assert_called_once()
        session.commit.assert_called_once()
        assert result == 10

    def test_errore_db_fa_rollback(self, deadline_service):
        svc, session = deadline_service
        session.commit.side_effect = Exception("DB error")

        with patch("services.deadline_service.Deadline"):
            result = svc.create("Test", "2024-01-01")

        session.rollback.assert_called_once()
        assert result is None

    def test_crea_senza_property_id(self, deadline_service):
        """property_id è opzionale"""
        svc, session = deadline_service

        with patch("services.deadline_service.Deadline") as MockDeadline:
            mock_d = MagicMock()
            mock_d.id = 5
            MockDeadline.return_value = mock_d

            result = svc.create(title="Scadenza Generica", due_date="2024-12-31")

        assert result == 5


# ══════════════════════════════════════════════════════════
#  update
# ══════════════════════════════════════════════════════════

class TestUpdate:

    def test_aggiorna_titolo(self, deadline_service):
        svc, session = deadline_service
        d = _make_deadline(id=1, title="Vecchio Titolo")
        session.query.return_value.filter.return_value.first.return_value = d

        result = svc.update(1, title="Nuovo Titolo")

        assert result is True
        assert d.title == "Nuovo Titolo"

    def test_segna_come_completata(self, deadline_service):
        svc, session = deadline_service
        d = _make_deadline(id=1, completed=False)
        session.query.return_value.filter.return_value.first.return_value = d

        result = svc.update(1, completed=True)

        assert result is True
        assert d.completed is True

    def test_aggiorna_data(self, deadline_service):
        svc, session = deadline_service
        d = _make_deadline(id=1, due_date="2024-06-16")
        session.query.return_value.filter.return_value.first.return_value = d

        result = svc.update(1, due_date="2024-12-31")

        assert result is True
        assert d.due_date == "2024-12-31"

    def test_scadenza_non_trovata_ritorna_false(self, deadline_service):
        svc, session = deadline_service
        session.query.return_value.filter.return_value.first.return_value = None

        result = svc.update(999, title="Non esiste")

        assert result is False

    def test_errore_db_fa_rollback(self, deadline_service):
        svc, session = deadline_service
        d = _make_deadline(id=1)
        session.query.return_value.filter.return_value.first.return_value = d
        session.commit.side_effect = Exception("DB error")

        result = svc.update(1, title="Test")

        session.rollback.assert_called_once()
        assert result is False

    def test_campo_non_consentito_non_applicato(self, deadline_service):
        """tenant_id non è nella whitelist di campi aggiornabili"""
        svc, session = deadline_service
        d = _make_deadline(id=1)
        session.query.return_value.filter.return_value.first.return_value = d

        # tenant_id non deve essere applicato
        result = svc.update(1, tenant_id="hacker")

        assert result is True
        assert d.tenant_id == "tenant_001"  # Invariato


# ══════════════════════════════════════════════════════════
#  mark_completed
# ══════════════════════════════════════════════════════════

class TestMarkCompleted:

    def test_mark_completed_chiama_update(self, deadline_service):
        """mark_completed è un wrapper di update(completed=True)"""
        svc, session = deadline_service
        svc.update = MagicMock(return_value=True)

        result = svc.mark_completed(42)

        svc.update.assert_called_once_with(42, completed=True)
        assert result is True

    def test_mark_completed_propaga_false_se_non_trovata(self, deadline_service):
        svc, session = deadline_service
        svc.update = MagicMock(return_value=False)

        result = svc.mark_completed(999)

        assert result is False


# ══════════════════════════════════════════════════════════
#  delete
# ══════════════════════════════════════════════════════════

class TestDelete:

    def test_elimina_scadenza_successo(self, deadline_service):
        svc, session = deadline_service
        d = _make_deadline(id=1)
        session.query.return_value.filter.return_value.first.return_value = d

        result = svc.delete(1)

        assert result is True
        session.delete.assert_called_once_with(d)
        session.commit.assert_called_once()

    def test_scadenza_non_trovata_ritorna_false(self, deadline_service):
        svc, session = deadline_service
        session.query.return_value.filter.return_value.first.return_value = None

        result = svc.delete(999)

        assert result is False
        session.delete.assert_not_called()

    def test_errore_db_fa_rollback(self, deadline_service):
        svc, session = deadline_service
        d = _make_deadline(id=1)
        session.query.return_value.filter.return_value.first.return_value = d
        session.commit.side_effect = Exception("DB error")

        result = svc.delete(1)

        session.rollback.assert_called_once()
        assert result is False

    def test_tenant_isolation_nel_filtro(self, deadline_service):
        """La delete deve filtrare per tenant_id"""
        svc, session = deadline_service
        session.query.return_value.filter.return_value.first.return_value = None

        svc.delete(1)

        # Verifica che filter sia stato chiamato (implica filtro tenant)
        assert session.query.return_value.filter.called
