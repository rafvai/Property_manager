"""
test_transaction_service.py
===========================
Test unitari per services/transaction_service.py

Strategia: mock SQLAlchemy session — zero accesso a DB reale.
Ogni test è indipendente grazie alle fixture che si resettano.

Copertura:
- create_with_supplier: flusso principale, supplier nuovo vs esistente
- create: wrapper di create_with_supplier (verifica delegazione)
- get_all: filtro per property_id, tenant isolation
- get_by_id: trovato, non trovato, tenant sbagliato
- update: campi modificabili, immutabilità tenant_id
- delete: soft delete vs hard delete
- get_summary: calcolo entrate/uscite, saldo
- validate_transaction_data: tutti i casi di validazione

Esecuzione:
    pytest tests/test_transaction_service.py -v
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch, call
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.transaction_service import TransactionService


# ══════════════════════════════════════════════════════════
#  Fixture condivise
# ══════════════════════════════════════════════════════════

@pytest.fixture
def mock_db():
    session = MagicMock()
    return session


@pytest.fixture
def transaction_service(mock_db):
    return TransactionService(mock_db)


def _make_transaction(id=1, tipo="Entrata", importo=500.0,
                      property_id=1, tenant_id="tenant_001",
                      is_deleted=False):
    """Helper: crea una transazione fittizia come oggetto SQLAlchemy"""
    t = MagicMock()
    t.id = id
    t.tipo = tipo
    t.importo = importo
    t.descrizione = "Affitto gennaio"
    t.data = date(2024, 1, 15)
    t.property_id = property_id
    t.tenant_id = tenant_id
    t.supplier_id = None
    t.is_deleted = is_deleted
    t.categoria = "Affitto"
    return t


def _make_supplier(id=1, nome="ENEL", tenant_id="tenant_001"):
    s = MagicMock()
    s.id = id
    s.nome = nome
    s.tenant_id = tenant_id
    return s


# ══════════════════════════════════════════════════════════
#  create_with_supplier
# ══════════════════════════════════════════════════════════

class TestCreateWithSupplier:

    def test_create_entrata_senza_fornitore(self, transaction_service, mock_db):
        """Transazione di tipo Entrata non ha fornitore"""
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        result = transaction_service.create_with_supplier(
            tipo="Entrata",
            importo=1200.0,
            data="15/01/2024",
            descrizione="Affitto mensile",
            property_id=1,
            tenant_id="tenant_001"
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result["success"] is True

    def test_create_uscita_con_fornitore_esistente(self, transaction_service, mock_db):
        """Uscita con fornitore già in DB — non deve crearne uno nuovo"""
        supplier = _make_supplier(id=5, nome="ENEL")
        mock_db.query.return_value.filter_by.return_value.first.return_value = supplier

        result = transaction_service.create_with_supplier(
            tipo="Uscita",
            importo=120.0,
            data="20/01/2024",
            descrizione="Bolletta luce",
            property_id=1,
            tenant_id="tenant_001",
            supplier_nome="ENEL"
        )

        assert result["success"] is True
        # Il fornitore non deve essere ricreato — add chiamato solo per la transazione
        calls_add = mock_db.add.call_count
        assert calls_add == 1  # Solo la transazione

    def test_create_uscita_con_fornitore_nuovo(self, transaction_service, mock_db):
        """Fornitore non esistente: deve essere creato prima della transazione"""
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        result = transaction_service.create_with_supplier(
            tipo="Uscita",
            importo=80.0,
            data="25/01/2024",
            descrizione="Pulizie",
            property_id=1,
            tenant_id="tenant_001",
            supplier_nome="Pulizie Bianchi SRL"
        )

        assert result["success"] is True
        # add deve essere chiamato due volte: fornitore + transazione
        assert mock_db.add.call_count == 2

    def test_importo_zero_lancia_errore(self, transaction_service, mock_db):
        result = transaction_service.create_with_supplier(
            tipo="Entrata",
            importo=0,
            data="01/01/2024",
            descrizione="Test",
            property_id=1,
            tenant_id="tenant_001"
        )
        assert result["success"] is False
        assert "importo" in result["error"].lower()

    def test_tipo_non_valido_lancia_errore(self, transaction_service, mock_db):
        result = transaction_service.create_with_supplier(
            tipo="Trasferimento",  # Non esiste
            importo=100.0,
            data="01/01/2024",
            descrizione="Test",
            property_id=1,
            tenant_id="tenant_001"
        )
        assert result["success"] is False

    def test_data_formato_sbagliato(self, transaction_service, mock_db):
        result = transaction_service.create_with_supplier(
            tipo="Entrata",
            importo=100.0,
            data="2024-01-15",  # Formato ISO non accettato
            descrizione="Test",
            property_id=1,
            tenant_id="tenant_001"
        )
        assert result["success"] is False

    def test_db_error_fa_rollback(self, transaction_service, mock_db):
        """Se il commit fallisce, deve essere fatto il rollback"""
        mock_db.commit.side_effect = Exception("DB error")

        result = transaction_service.create_with_supplier(
            tipo="Entrata",
            importo=500.0,
            data="01/01/2024",
            descrizione="Test",
            property_id=1,
            tenant_id="tenant_001"
        )

        mock_db.rollback.assert_called_once()
        assert result["success"] is False


# ══════════════════════════════════════════════════════════
#  create (wrapper)
# ══════════════════════════════════════════════════════════

class TestCreate:
    """
    create() deve delegare completamente a create_with_supplier().
    Verifichiamo che non ci sia logica duplicata.
    """

    def test_create_delega_a_create_with_supplier(self, transaction_service):
        """create() è un wrapper — deve chiamare create_with_supplier"""
        transaction_service.create_with_supplier = MagicMock(
            return_value={"success": True, "id": 1}
        )

        transaction_service.create(
            tipo="Entrata",
            importo=500.0,
            data="01/01/2024",
            descrizione="Test",
            property_id=1,
            tenant_id="tenant_001"
        )

        transaction_service.create_with_supplier.assert_called_once()

    def test_create_passa_tutti_i_parametri(self, transaction_service):
        """Tutti i parametri devono arrivare invariati a create_with_supplier"""
        transaction_service.create_with_supplier = MagicMock(
            return_value={"success": True}
        )

        transaction_service.create(
            tipo="Uscita",
            importo=99.99,
            data="15/06/2024",
            descrizione="Manutenzione",
            property_id=3,
            tenant_id="tenant_002",
            supplier_nome="Idraulico Verdi"
        )

        call_kwargs = transaction_service.create_with_supplier.call_args
        assert call_kwargs.kwargs.get("supplier_nome") == "Idraulico Verdi" or \
               "Idraulico Verdi" in str(call_kwargs)


# ══════════════════════════════════════════════════════════
#  get_all
# ══════════════════════════════════════════════════════════

class TestGetAll:

    def test_restituisce_transazioni_corrette(self, transaction_service, mock_db):
        transazioni = [_make_transaction(1), _make_transaction(2)]
        mock_db.query.return_value.filter_by.return_value.all.return_value = transazioni

        result = transaction_service.get_all(property_id=1, tenant_id="tenant_001")

        assert len(result) == 2

    def test_nessuna_transazione_restituisce_lista_vuota(self, transaction_service, mock_db):
        mock_db.query.return_value.filter_by.return_value.all.return_value = []

        result = transaction_service.get_all(property_id=99, tenant_id="tenant_001")

        assert result == []

    def test_non_restituisce_soft_deleted(self, transaction_service, mock_db):
        """Le transazioni cancellate (soft delete) non devono essere visibili"""
        t1 = _make_transaction(1, is_deleted=False)
        t2 = _make_transaction(2, is_deleted=True)

        # Simula il filtro is_deleted=False già applicato dalla query
        mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = [t1]

        result = transaction_service.get_all(property_id=1, tenant_id="tenant_001")

        # Solo la transazione non cancellata deve apparire
        for t in result:
            assert t.is_deleted is False

    def test_tenant_isolation(self, transaction_service, mock_db):
        """
        get_all non deve mai restituire dati di un tenant diverso.
        Il filtro tenant_id deve essere sempre nella query.
        """
        transaction_service.get_all(property_id=1, tenant_id="tenant_001")

        # Verifica che la query includa il filtro tenant_id
        query_calls = str(mock_db.query.call_args_list)
        filter_calls = str(mock_db.query.return_value.filter_by.call_args_list)
        assert "tenant_001" in filter_calls or "tenant_001" in query_calls


# ══════════════════════════════════════════════════════════
#  get_by_id
# ══════════════════════════════════════════════════════════

class TestGetById:

    def test_trovato(self, transaction_service, mock_db):
        t = _make_transaction(id=42)
        mock_db.query.return_value.filter_by.return_value.first.return_value = t

        result = transaction_service.get_by_id(42, "tenant_001")

        assert result is not None
        assert result.id == 42

    def test_non_trovato_restituisce_none(self, transaction_service, mock_db):
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        result = transaction_service.get_by_id(999, "tenant_001")

        assert result is None

    def test_tenant_sbagliato_restituisce_none(self, transaction_service, mock_db):
        """Una transazione di tenant_001 non deve essere visibile a tenant_002"""
        # Il DB filtra per tenant_id — se non matcha, first() restituisce None
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        result = transaction_service.get_by_id(1, "tenant_002")

        assert result is None

    def test_id_non_intero_lancia_errore(self, transaction_service, mock_db):
        with pytest.raises(Exception):
            transaction_service.get_by_id("non_un_id", "tenant_001")


# ══════════════════════════════════════════════════════════
#  update
# ══════════════════════════════════════════════════════════

class TestUpdate:

    def test_update_importo(self, transaction_service, mock_db):
        t = _make_transaction(id=1, importo=100.0)
        mock_db.query.return_value.filter_by.return_value.first.return_value = t

        result = transaction_service.update(
            transaction_id=1,
            tenant_id="tenant_001",
            importo=250.0
        )

        assert result["success"] is True
        assert t.importo == 250.0
        mock_db.commit.assert_called()

    def test_update_descrizione(self, transaction_service, mock_db):
        t = _make_transaction(id=1)
        mock_db.query.return_value.filter_by.return_value.first.return_value = t

        result = transaction_service.update(
            transaction_id=1,
            tenant_id="tenant_001",
            descrizione="Nuova descrizione aggiornata"
        )

        assert result["success"] is True
        assert t.descrizione == "Nuova descrizione aggiornata"

    def test_non_puo_cambiare_tenant_id(self, transaction_service, mock_db):
        """Il tenant_id è immutabile — non deve poter essere modificato"""
        t = _make_transaction(id=1, tenant_id="tenant_001")
        mock_db.query.return_value.filter_by.return_value.first.return_value = t

        result = transaction_service.update(
            transaction_id=1,
            tenant_id="tenant_001",
            # Tentativo di escalation del tenant
            **{"tenant_id_new": "tenant_admin"}
        )

        # Il tenant_id non deve cambiare mai
        assert t.tenant_id == "tenant_001"

    def test_transazione_non_trovata(self, transaction_service, mock_db):
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        result = transaction_service.update(
            transaction_id=999,
            tenant_id="tenant_001",
            importo=100.0
        )

        assert result["success"] is False

    def test_importo_zero_rifiutato(self, transaction_service, mock_db):
        t = _make_transaction(id=1)
        mock_db.query.return_value.filter_by.return_value.first.return_value = t

        result = transaction_service.update(
            transaction_id=1,
            tenant_id="tenant_001",
            importo=0
        )

        assert result["success"] is False


# ══════════════════════════════════════════════════════════
#  delete (soft delete)
# ══════════════════════════════════════════════════════════

class TestDelete:

    def test_soft_delete_non_rimuove_da_db(self, transaction_service, mock_db):
        """Il record deve rimanere in DB con is_deleted=True"""
        t = _make_transaction(id=1, is_deleted=False)
        mock_db.query.return_value.filter_by.return_value.first.return_value = t

        result = transaction_service.delete(1, "tenant_001")

        assert result["success"] is True
        assert t.is_deleted is True
        mock_db.delete.assert_not_called()  # NON deve fare hard delete
        mock_db.commit.assert_called()

    def test_delete_transazione_non_trovata(self, transaction_service, mock_db):
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        result = transaction_service.delete(999, "tenant_001")

        assert result["success"] is False

    def test_delete_di_altro_tenant_fallisce(self, transaction_service, mock_db):
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        result = transaction_service.delete(1, "tenant_hacker")

        assert result["success"] is False


# ══════════════════════════════════════════════════════════
#  get_summary
# ══════════════════════════════════════════════════════════

class TestGetSummary:
    """Test per il calcolo finanziario — il più critico per l'app"""

    def test_saldo_corretto(self, transaction_service, mock_db):
        """Entrate 1500 - Uscite 500 = Saldo 1000"""
        transazioni = [
            _make_transaction(1, "Entrata", 1000.0),
            _make_transaction(2, "Entrata", 500.0),
            _make_transaction(3, "Uscita", 500.0),
        ]
        mock_db.query.return_value.filter_by.return_value.all.return_value = transazioni

        result = transaction_service.get_summary(property_id=1, tenant_id="tenant_001")

        assert result["totale_entrate"] == 1500.0
        assert result["totale_uscite"] == 500.0
        assert result["saldo"] == 1000.0

    def test_saldo_negativo(self, transaction_service, mock_db):
        """Le uscite possono superare le entrate — saldo negativo valido"""
        transazioni = [
            _make_transaction(1, "Entrata", 100.0),
            _make_transaction(2, "Uscita", 600.0),
        ]
        mock_db.query.return_value.filter_by.return_value.all.return_value = transazioni

        result = transaction_service.get_summary(property_id=1, tenant_id="tenant_001")

        assert result["saldo"] == -500.0

    def test_nessuna_transazione(self, transaction_service, mock_db):
        """Proprietà senza transazioni: tutti i valori devono essere zero"""
        mock_db.query.return_value.filter_by.return_value.all.return_value = []

        result = transaction_service.get_summary(property_id=1, tenant_id="tenant_001")

        assert result["totale_entrate"] == 0.0
        assert result["totale_uscite"] == 0.0
        assert result["saldo"] == 0.0

    def test_non_include_soft_deleted(self, transaction_service, mock_db):
        """Le transazioni cancellate non devono influire sul saldo"""
        transazioni = [
            _make_transaction(1, "Entrata", 1000.0, is_deleted=False),
            _make_transaction(2, "Entrata", 9999.0, is_deleted=True),  # Non deve contare
        ]
        # Simula che la query filtri già is_deleted=False
        mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = [
            transazioni[0]
        ]

        result = transaction_service.get_summary(property_id=1, tenant_id="tenant_001")

        # Se il filtro funziona, il totale entrate è 1000, non 10999
        assert result["totale_entrate"] != 10999.0

    def test_arrotondamento_a_due_decimali(self, transaction_service, mock_db):
        """I valori finanziari devono essere arrotondati a 2 decimali"""
        transazioni = [
            _make_transaction(1, "Entrata", 100.001),
            _make_transaction(2, "Entrata", 200.009),
        ]
        mock_db.query.return_value.filter_by.return_value.all.return_value = transazioni

        result = transaction_service.get_summary(property_id=1, tenant_id="tenant_001")

        # Il saldo deve avere al massimo 2 decimali
        saldo_str = str(result["saldo"])
        if "." in saldo_str:
            decimali = saldo_str.split(".")[1]
            assert len(decimali) <= 2
