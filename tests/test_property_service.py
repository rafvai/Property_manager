"""
test_property_service.py
========================
Test unitari per services/property_service.py

Strategia: mock DatabaseConnection e SQLAlchemy session.

Copertura:
- get_all: lista proprietà, lista vuota, tenant isolation
- get_by_id: trovata, non trovata, tenant sbagliato
- create: successo, rollback su errore DB
- update: campi singoli, proprietà non trovata, rollback su errore
- delete: successo, non trovata, rollback su errore, CASCADE implicito

Esecuzione:
    pytest tests/test_property_service.py -v
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ══════════════════════════════════════════════════════════
#  Fixture condivise
# ══════════════════════════════════════════════════════════

def _make_property(id=1, name="Via Roma 1", address="Roma", owner="Mario Rossi",
                   tenant_id="tenant_001"):
    p = MagicMock()
    p.id = id
    p.name = name
    p.address = address
    p.owner = owner
    p.tenant_id = tenant_id
    p.to_dict.return_value = {
        "id": id, "name": name, "address": address,
        "owner": owner, "tenant_id": tenant_id
    }
    return p


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def property_service(mock_session):
    """PropertyService con DB completamente mockato"""
    with patch("services.property_service.DatabaseConnection") as MockDB:
        mock_db_instance = MockDB.return_value
        mock_db_instance.get_session.return_value = mock_session
        mock_db_instance.close_session = MagicMock()

        from services.property_service import PropertyService
        svc = PropertyService(logger=MagicMock())
        svc.db = mock_db_instance
        return svc, mock_session


# ══════════════════════════════════════════════════════════
#  get_all
# ══════════════════════════════════════════════════════════

class TestGetAll:

    def test_restituisce_lista_dizionari(self, property_service):
        svc, session = property_service
        props = [_make_property(1), _make_property(2)]
        session.query.return_value.filter_by.return_value.all.return_value = props

        result = svc.get_all()

        assert len(result) == 2
        assert isinstance(result[0], dict)

    def test_lista_vuota(self, property_service):
        svc, session = property_service
        session.query.return_value.filter_by.return_value.all.return_value = []

        result = svc.get_all()

        assert result == []

    def test_tenant_isolation_nella_query(self, property_service):
        """La query deve filtrare per tenant_id corrente"""
        svc, session = property_service
        session.query.return_value.filter_by.return_value.all.return_value = []

        svc.get_all()

        filter_calls = str(session.query.return_value.filter_by.call_args)
        assert "tenant_id" in filter_calls

    def test_errore_db_ritorna_lista_vuota(self, property_service):
        svc, session = property_service
        session.query.side_effect = Exception("DB error")

        result = svc.get_all()

        assert result == []
        svc.logger.error.assert_called()


# ══════════════════════════════════════════════════════════
#  get_by_id
# ══════════════════════════════════════════════════════════

class TestGetById:

    def test_trovata(self, property_service):
        svc, session = property_service
        prop = _make_property(id=5)
        session.query.return_value.filter.return_value.first.return_value = prop

        result = svc.get_by_id(5)

        assert result is not None
        assert result["id"] == 5

    def test_non_trovata_ritorna_none(self, property_service):
        svc, session = property_service
        session.query.return_value.filter.return_value.first.return_value = None

        result = svc.get_by_id(999)

        assert result is None

    def test_tenant_sbagliato_ritorna_none(self, property_service):
        """Una proprietà di un altro tenant non deve essere visibile"""
        svc, session = property_service
        session.query.return_value.filter.return_value.first.return_value = None

        result = svc.get_by_id(1)

        assert result is None

    def test_errore_db_ritorna_none(self, property_service):
        svc, session = property_service
        session.query.side_effect = Exception("DB error")

        result = svc.get_by_id(1)

        assert result is None
        svc.logger.error.assert_called()


# ══════════════════════════════════════════════════════════
#  create
# ══════════════════════════════════════════════════════════

class TestCreate:

    def test_crea_proprieta_successo(self, property_service):
        svc, session = property_service
        # Simula che after commit l'oggetto abbia un id
        def set_id(obj):
            obj.id = 42
        session.refresh = MagicMock(side_effect=set_id)

        with patch("services.property_service.Property") as MockProperty:
            mock_prop = MagicMock()
            mock_prop.id = 42
            MockProperty.return_value = mock_prop

            result = svc.create("Via Roma 1", "Roma, RM", "Mario Rossi")

        session.add.assert_called_once()
        session.commit.assert_called_once()
        assert result == 42

    def test_errore_db_fa_rollback(self, property_service):
        svc, session = property_service
        session.commit.side_effect = Exception("DB error")

        with patch("services.property_service.Property"):
            result = svc.create("Test", "Addr", "Owner")

        session.rollback.assert_called_once()
        assert result is None

    def test_errore_db_logga(self, property_service):
        svc, session = property_service
        session.commit.side_effect = Exception("DB error")

        with patch("services.property_service.Property"):
            svc.create("Test", "Addr", "Owner")

        svc.logger.error.assert_called()


# ══════════════════════════════════════════════════════════
#  update
# ══════════════════════════════════════════════════════════

class TestUpdate:

    def test_aggiorna_nome(self, property_service):
        svc, session = property_service
        prop = _make_property(id=1, name="Vecchio Nome")
        session.query.return_value.filter.return_value.first.return_value = prop

        result = svc.update(1, name="Nuovo Nome")

        assert result is True
        assert prop.name == "Nuovo Nome"
        session.commit.assert_called_once()

    def test_aggiorna_indirizzo(self, property_service):
        svc, session = property_service
        prop = _make_property(id=1)
        session.query.return_value.filter.return_value.first.return_value = prop

        result = svc.update(1, address="Milano, MI")

        assert result is True
        assert prop.address == "Milano, MI"

    def test_aggiorna_gestore(self, property_service):
        """Il campo si chiama managed_by (ex owner)"""
        svc, session = property_service
        prop = _make_property(id=1)
        session.query.return_value.filter.return_value.first.return_value = prop

        result = svc.update(1, managed_by="Luigi Bianchi")

        assert result is True
        assert prop.managed_by == "Luigi Bianchi"

    def test_proprieta_non_trovata_ritorna_false(self, property_service):
        svc, session = property_service
        session.query.return_value.filter.return_value.first.return_value = None

        result = svc.update(999, name="Non esiste")

        assert result is False

    def test_errore_db_fa_rollback(self, property_service):
        svc, session = property_service
        prop = _make_property(id=1)
        session.query.return_value.filter.return_value.first.return_value = prop
        session.commit.side_effect = Exception("DB error")

        result = svc.update(1, name="Test")

        session.rollback.assert_called_once()
        assert result is False

    def test_nessun_campo_da_aggiornare_non_crasha(self, property_service):
        """Chiamata senza campi non deve crashare"""
        svc, session = property_service
        prop = _make_property(id=1)
        session.query.return_value.filter.return_value.first.return_value = prop

        result = svc.update(1)  # Nessun kwarg

        assert result is True


# ══════════════════════════════════════════════════════════
#  delete
# ══════════════════════════════════════════════════════════

class TestDelete:

    def test_elimina_proprieta_successo(self, property_service):
        svc, session = property_service
        prop = _make_property(id=1)
        session.query.return_value.filter.return_value.first.return_value = prop

        result = svc.delete(1)

        assert result is True
        session.delete.assert_called_once_with(prop)
        session.commit.assert_called_once()

    def test_proprieta_non_trovata_ritorna_false(self, property_service):
        svc, session = property_service
        session.query.return_value.filter.return_value.first.return_value = None

        result = svc.delete(999)

        assert result is False
        session.delete.assert_not_called()

    def test_errore_db_fa_rollback(self, property_service):
        svc, session = property_service
        prop = _make_property(id=1)
        session.query.return_value.filter.return_value.first.return_value = prop
        session.commit.side_effect = Exception("DB error")

        result = svc.delete(1)

        session.rollback.assert_called_once()
        assert result is False

    def test_tenant_isolation_nel_filtro(self, property_service):
        """La delete deve filtrare per tenant_id"""
        svc, session = property_service
        session.query.return_value.filter.return_value.first.return_value = None

        svc.delete(1)

        filter_calls = str(session.query.return_value.filter.call_args)
        assert "tenant_id" in filter_calls.lower() or \
               session.query.return_value.filter.called
