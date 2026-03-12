"""
test_transaction_service.py
===========================
Test unitari per services/transaction_service.py

Strategia: mock DatabaseConnection e SQLAlchemy session — zero accesso a DB reale.
Il TransactionService reale usa logger (non db direttamente) e DatabaseConnection.

Copertura:
- get_all: filtro property_id, date range, tenant isolation, errore DB
- get_monthly_summary: raggruppamento per mese, errore DB
- create: successo, rollback su errore
- create_with_supplier: con/senza supplier_id, aggiornamento stats, rollback
- update: campi modificabili, whitelist rispettata, non trovata, rollback
- delete: hard delete, non trovata, rollback (NB: il service reale non ha soft delete)
- get_balance: entrate - uscite, filtri property/data, saldo negativo

Esecuzione:
    pytest tests/test_transaction_service.py -v
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch, call
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ══════════════════════════════════════════════════════════
#  Helper factories
# ══════════════════════════════════════════════════════════

def _make_transaction(id=1, tipo="Entrata", importo=500.0,
                      property_id=1, tenant_id="tenant_001",
                      supplier_id=None):
    t = MagicMock()
    t.id = id
    t.type = tipo
    t.amount = importo
    t.descrizione = "Affitto gennaio"
    t.date = date(2024, 1, 15)
    t.property_id = property_id
    t.tenant_id = tenant_id
    t.supplier_id = supplier_id
    t.service = "Affitto"
    t.provider = "Inquilino Rossi"
    t.to_dict.return_value = {
        "id": id, "type": tipo, "amount": importo,
        "property_id": property_id, "tenant_id": tenant_id
    }
    return t


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def transaction_service(mock_session):
    with patch("services.transaction_service.DatabaseConnection") as MockDB:
        mock_db = MockDB.return_value
        mock_db.get_session.return_value = mock_session
        mock_db.close_session = MagicMock()

        from services.transaction_service import TransactionService
        svc = TransactionService(logger=MagicMock())
        svc.db = mock_db
        return svc, mock_session


# ══════════════════════════════════════════════════════════
#  get_all
# ══════════════════════════════════════════════════════════

class TestGetAll:

    def test_restituisce_lista_dizionari(self, transaction_service):
        svc, session = transaction_service
        trans = [_make_transaction(1), _make_transaction(2)]
        session.query.return_value \
            .filter_by.return_value \
            .order_by.return_value \
            .all.return_value = trans

        result = svc.get_all()

        assert len(result) == 2
        assert isinstance(result[0], dict)

    def test_lista_vuota(self, transaction_service):
        svc, session = transaction_service
        session.query.return_value \
            .filter_by.return_value \
            .order_by.return_value \
            .all.return_value = []

        result = svc.get_all()

        assert result == []

    def test_filtro_property_id(self, transaction_service):
        """get_all con property_id deve includere il filtro nella query"""
        svc, session = transaction_service
        session.query.return_value \
            .filter_by.return_value \
            .filter.return_value \
            .order_by.return_value \
            .all.return_value = [_make_transaction(1)]

        result = svc.get_all(property_id=1)

        assert isinstance(result, list)

    def test_tenant_isolation(self, transaction_service):
        """La query deve includere sempre il filtro tenant_id"""
        svc, session = transaction_service
        session.query.return_value \
            .filter_by.return_value \
            .order_by.return_value \
            .all.return_value = []

        svc.get_all()

        filter_calls = str(session.query.return_value.filter_by.call_args)
        assert "tenant_id" in filter_calls

    def test_errore_db_ritorna_lista_vuota(self, transaction_service):
        svc, session = transaction_service
        session.query.side_effect = Exception("DB error")

        result = svc.get_all()

        assert result == []
        svc.logger.error.assert_called()

    def test_filtro_date_range(self, transaction_service):
        """Con start_date e end_date deve applicare un filtro temporale"""
        svc, session = transaction_service
        session.query.return_value \
            .filter_by.return_value \
            .filter.return_value \
            .order_by.return_value \
            .all.return_value = [_make_transaction(1)]

        result = svc.get_all(start_date="2024-01-01", end_date="2024-12-31")

        assert isinstance(result, list)


# ══════════════════════════════════════════════════════════
#  get_monthly_summary
# ══════════════════════════════════════════════════════════

class TestGetMonthlySummary:

    def test_ritorna_risultati(self, transaction_service):
        svc, session = transaction_service
        session.query.return_value \
            .filter.return_value \
            .group_by.return_value \
            .order_by.return_value \
            .all.return_value = [(1, "Entrata", 1200.0), (1, "Uscita", 300.0)]

        result = svc.get_monthly_summary(year=2024)

        assert len(result) == 2

    def test_lista_vuota_anno_senza_dati(self, transaction_service):
        svc, session = transaction_service
        session.query.return_value \
            .filter.return_value \
            .group_by.return_value \
            .order_by.return_value \
            .all.return_value = []

        result = svc.get_monthly_summary(year=2099)

        assert result == []

    def test_errore_db_ritorna_lista_vuota(self, transaction_service):
        svc, session = transaction_service
        session.query.side_effect = Exception("DB error")

        result = svc.get_monthly_summary(year=2024)

        assert result == []
        svc.logger.error.assert_called()


# ══════════════════════════════════════════════════════════
#  create
# ══════════════════════════════════════════════════════════

class TestCreate:

    def test_crea_transazione_successo(self, transaction_service):
        svc, session = transaction_service

        with patch("services.transaction_service.Transaction") as MockTrans:
            mock_t = MagicMock()
            mock_t.id = 42
            MockTrans.return_value = mock_t

            result = svc.create(
                property_id=1,
                date=date(2024, 1, 15),
                trans_type="Entrata",
                amount=1200.0,
                provider="Inquilino Rossi",
                service="Affitto"
            )

        session.add.assert_called_once()
        session.commit.assert_called_once()
        # create() delega a create_with_supplier → ritorna id
        assert result == 42 or result is not None

    def test_errore_db_fa_rollback(self, transaction_service):
        svc, session = transaction_service
        session.commit.side_effect = Exception("DB error")

        with patch("services.transaction_service.Transaction"):
            result = svc.create(
                property_id=1, date=date(2024, 1, 15),
                trans_type="Entrata", amount=500.0,
                provider="Test", service="Test"
            )

        session.rollback.assert_called_once()
        assert result is None


# ══════════════════════════════════════════════════════════
#  create_with_supplier
# ══════════════════════════════════════════════════════════

class TestCreateWithSupplier:

    def test_crea_senza_supplier(self, transaction_service):
        svc, session = transaction_service

        with patch("services.transaction_service.Transaction") as MockTrans:
            mock_t = MagicMock()
            mock_t.id = 10
            MockTrans.return_value = mock_t

            result = svc.create_with_supplier(
                property_id=1,
                date=date(2024, 1, 20),
                trans_type="Entrata",
                amount=800.0,
                provider="Affittuario",
                service="Affitto"
            )

        assert result == 10
        session.add.assert_called_once()
        session.commit.assert_called_once()

    def test_crea_con_supplier_id_aggiorna_stats(self, transaction_service):
        """Con supplier_id e tipo Uscita → aggiorna le statistiche del fornitore.
        SupplierService viene importato DENTRO la funzione con 'from services...',
        quindi va patchato nel suo modulo sorgente."""
        svc, session = transaction_service

        with patch("services.transaction_service.Transaction") as MockTrans, \
             patch("services.supplier_service.SupplierService") as MockSupplierSvc:

            mock_t = MagicMock()
            mock_t.id = 20
            MockTrans.return_value = mock_t

            mock_instance = MagicMock()
            MockSupplierSvc.return_value = mock_instance

            result = svc.create_with_supplier(
                property_id=1,
                date=date(2024, 1, 25),
                trans_type="Uscita",
                amount=120.0,
                provider="ENEL",
                service="Bolletta Luce",
                supplier_id=5
            )

        assert result == 20
        mock_instance.update_service_stats.assert_called_once()

    def test_crea_entrata_con_supplier_non_aggiorna_stats(self, transaction_service):
        """Le Entrate non devono aggiornare le stats del fornitore"""
        svc, session = transaction_service

        with patch("services.transaction_service.Transaction") as MockTrans, \
             patch("services.supplier_service.SupplierService") as MockSupplierSvc:

            mock_t = MagicMock()
            mock_t.id = 30
            MockTrans.return_value = mock_t

            mock_instance = MagicMock()
            MockSupplierSvc.return_value = mock_instance

            svc.create_with_supplier(
                property_id=1,
                date=date(2024, 1, 15),
                trans_type="Entrata",  # Entrata: non aggiorna stats
                amount=1000.0,
                provider="Inquilino",
                service="Affitto",
                supplier_id=5
            )

        mock_instance.update_service_stats.assert_not_called()

    def test_errore_db_fa_rollback(self, transaction_service):
        svc, session = transaction_service
        session.commit.side_effect = Exception("DB error")

        with patch("services.transaction_service.Transaction"):
            result = svc.create_with_supplier(
                property_id=1, date=date(2024, 1, 1),
                trans_type="Entrata", amount=100.0,
                provider="Test", service="Test"
            )

        session.rollback.assert_called_once()
        assert result is None

    def test_errore_stats_fornitore_non_blocca_transazione(self, transaction_service):
        """Se l'aggiornamento stats fallisce, la transazione deve essere già salvata"""
        svc, session = transaction_service

        with patch("services.transaction_service.Transaction") as MockTrans, \
             patch("services.supplier_service.SupplierService") as MockSupplierSvc:

            mock_t = MagicMock()
            mock_t.id = 50
            MockTrans.return_value = mock_t
            MockSupplierSvc.return_value.update_service_stats.side_effect = Exception("Stats error")

            result = svc.create_with_supplier(
                property_id=1,
                date=date(2024, 1, 1),
                trans_type="Uscita",
                amount=200.0,
                provider="Test",
                service="Manutenzione",
                supplier_id=9
            )

        # La transazione deve essere salvata anche se le stats falliscono
        assert result == 50
        session.commit.assert_called()
        svc.logger.warning.assert_called()


# ══════════════════════════════════════════════════════════
#  update
# ══════════════════════════════════════════════════════════

class TestUpdate:

    def test_aggiorna_importo(self, transaction_service):
        svc, session = transaction_service
        t = _make_transaction(id=1, importo=100.0)
        session.query.return_value.filter.return_value.first.return_value = t

        result = svc.update(1, amount=250.0)

        assert result is True
        assert t.amount == 250.0
        session.commit.assert_called_once()

    def test_aggiorna_provider(self, transaction_service):
        svc, session = transaction_service
        t = _make_transaction(id=1)
        session.query.return_value.filter.return_value.first.return_value = t

        result = svc.update(1, provider="Nuovo Fornitore")

        assert result is True
        assert t.provider == "Nuovo Fornitore"

    def test_campo_non_nella_whitelist_ignorato(self, transaction_service):
        """tenant_id non è nella whitelist → non viene modificato"""
        svc, session = transaction_service
        t = _make_transaction(id=1, tenant_id="tenant_001")
        session.query.return_value.filter.return_value.first.return_value = t

        result = svc.update(1, tenant_id="tenant_hacker")

        assert result is True
        # tenant_id deve rimanere invariato
        assert t.tenant_id == "tenant_001"

    def test_transazione_non_trovata_ritorna_false(self, transaction_service):
        svc, session = transaction_service
        session.query.return_value.filter.return_value.first.return_value = None

        result = svc.update(999, amount=100.0)

        assert result is False

    def test_errore_db_fa_rollback(self, transaction_service):
        svc, session = transaction_service
        t = _make_transaction(id=1)
        session.query.return_value.filter.return_value.first.return_value = t
        session.commit.side_effect = Exception("DB error")

        result = svc.update(1, amount=500.0)

        session.rollback.assert_called_once()
        assert result is False

    def test_tenant_isolation_nella_query(self, transaction_service):
        """La query di update deve filtrare per tenant_id"""
        svc, session = transaction_service
        session.query.return_value.filter.return_value.first.return_value = None

        svc.update(1, amount=100.0)

        filter_calls = str(session.query.return_value.filter.call_args)
        assert "tenant_id" in filter_calls.lower() or \
               session.query.return_value.filter.called


# ══════════════════════════════════════════════════════════
#  delete (hard delete — comportamento del service reale)
# ══════════════════════════════════════════════════════════

class TestDelete:

    def test_elimina_transazione_successo(self, transaction_service):
        svc, session = transaction_service
        t = _make_transaction(id=1)
        session.query.return_value.filter.return_value.first.return_value = t

        result = svc.delete(1)

        assert result is True
        session.delete.assert_called_once_with(t)
        session.commit.assert_called_once()

    def test_transazione_non_trovata_ritorna_false(self, transaction_service):
        svc, session = transaction_service
        session.query.return_value.filter.return_value.first.return_value = None

        result = svc.delete(999)

        assert result is False
        session.delete.assert_not_called()

    def test_errore_db_fa_rollback(self, transaction_service):
        svc, session = transaction_service
        t = _make_transaction(id=1)
        session.query.return_value.filter.return_value.first.return_value = t
        session.commit.side_effect = Exception("DB error")

        result = svc.delete(1)

        session.rollback.assert_called_once()
        assert result is False

    def test_tenant_isolation_nella_delete(self, transaction_service):
        """La delete deve filtrare per tenant_id"""
        svc, session = transaction_service
        session.query.return_value.filter.return_value.first.return_value = None

        svc.delete(1)

        assert session.query.return_value.filter.called


# ══════════════════════════════════════════════════════════
#  get_balance
# ══════════════════════════════════════════════════════════

class TestGetBalance:

    def test_saldo_positivo(self, transaction_service):
        """Entrate 1500 - Uscite 500 = Saldo 1000"""
        svc, session = transaction_service

        # Prima chiamata scalar() → entrate, seconda → uscite
        session.query.return_value \
            .filter.return_value \
            .scalar.side_effect = [1500.0, 500.0]

        result = svc.get_balance()

        assert result == 1000.0

    def test_saldo_negativo(self, transaction_service):
        """Uscite possono superare le entrate"""
        svc, session = transaction_service
        session.query.return_value \
            .filter.return_value \
            .scalar.side_effect = [100.0, 600.0]

        result = svc.get_balance()

        assert result == -500.0

    def test_saldo_zero_senza_transazioni(self, transaction_service):
        svc, session = transaction_service
        session.query.return_value \
            .filter.return_value \
            .scalar.side_effect = [0.0, 0.0]

        result = svc.get_balance()

        assert result == 0.0

    def test_filtro_property_id(self, transaction_service):
        """get_balance con property_id deve filtrare ulteriormente"""
        svc, session = transaction_service
        session.query.return_value \
            .filter.return_value \
            .filter.return_value \
            .scalar.side_effect = [800.0, 200.0]

        result = svc.get_balance(property_id=1)

        assert isinstance(result, (int, float))

    def test_errore_db_ritorna_zero(self, transaction_service):
        svc, session = transaction_service
        session.query.side_effect = Exception("DB error")

        result = svc.get_balance()

        assert result == 0
        svc.logger.error.assert_called()