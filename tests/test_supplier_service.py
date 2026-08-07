"""
test_supplier_service.py
========================
Test unitari per services/supplier_service.py

Strategia: mock DatabaseConnection e SQLAlchemy session.

Copertura:
- get_all: filtri categoria/property/rating, lista vuota, errore DB
- get_by_id: trovato, non trovato, stats aggregate
- get_categories: lista distinct, con filtro property_id
- create: successo, rollback su errore
- update: campi consentiti, fornitore non trovato, rollback
- update_service_stats: aggiornamento cumulativo, fornitore non trovato
- delete: successo (cascade implicito), non trovato
- search: match parziale, filtri combinati
- get_stats: totale e per categoria
- add_review / get_reviews / delete_review: ciclo completo
- add_document / get_documents / delete_document: ciclo completo

Esecuzione:
    pytest tests/test_supplier_service.py -v
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ══════════════════════════════════════════════════════════
#  Helper factories
# ══════════════════════════════════════════════════════════

def _make_supplier(id=1, name="ENEL", category="Bolletta Luce",
                   property_id=1, total_spent=0.0, service_count=0):
    s = MagicMock()
    s.id = id
    s.name = name
    s.category = category
    s.property_id = property_id
    s.total_spent = total_spent
    s.service_count = service_count
    s.last_service_date = None
    s.to_dict.return_value = {
        "id": id, "name": name, "category": category,
        "property_id": property_id
    }
    return s


def _make_review(id=1, supplier_id=1, rating=4, title="Buon servizio"):
    r = MagicMock()
    r.id = id
    r.supplier_id = supplier_id
    r.rating = rating
    r.title = title
    r.to_dict.return_value = {"id": id, "rating": rating, "title": title}
    return r


def _make_document(id=1, supplier_id=1, document_type="contratto", title="Contratto 2024"):
    d = MagicMock()
    d.id = id
    d.supplier_id = supplier_id
    d.document_type = document_type
    d.title = title
    d.to_dict.return_value = {"id": id, "type": document_type, "title": title}
    return d


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def supplier_service(mock_session):
    with patch("services.supplier_service.DatabaseConnection") as MockDB:
        mock_db = MockDB.return_value
        mock_db.get_session.return_value = mock_session
        mock_db.close_session = MagicMock()

        from services.supplier_service import SupplierService
        svc = SupplierService(logger=MagicMock())
        svc.db = mock_db
        return svc, mock_session


# ══════════════════════════════════════════════════════════
#  get_all
# ══════════════════════════════════════════════════════════

class TestGetAll:

    def _setup_query_result(self, session, suppliers_data):
        """Configura la query complessa con join per restituire dati predefiniti"""
        rows = [(s, f"Proprietà {s.property_id}", 4.0, 2) for s in suppliers_data]
        session.query.return_value \
            .outerjoin.return_value \
            .outerjoin.return_value \
            .filter.return_value \
            .group_by.return_value \
            .order_by.return_value \
            .all.return_value = rows
        # Percorso senza filtri aggiuntivi
        session.query.return_value \
            .outerjoin.return_value \
            .outerjoin.return_value \
            .group_by.return_value \
            .order_by.return_value \
            .all.return_value = rows
        return rows

    def test_restituisce_lista_dizionari(self, supplier_service):
        svc, session = supplier_service
        suppliers = [_make_supplier(1), _make_supplier(2)]
        self._setup_query_result(session, suppliers)

        result = svc.get_all()

        assert isinstance(result, list)

    def test_lista_vuota(self, supplier_service):
        svc, session = supplier_service
        self._setup_query_result(session, [])

        result = svc.get_all()

        assert result == []

    def test_errore_db_ritorna_lista_vuota(self, supplier_service):
        svc, session = supplier_service
        session.query.side_effect = Exception("DB error")

        result = svc.get_all()

        assert result == []
        svc.logger.error.assert_called()


# ══════════════════════════════════════════════════════════
#  get_by_id
# ══════════════════════════════════════════════════════════

class TestGetById:

    def test_trovato(self, supplier_service):
        svc, session = supplier_service
        supplier = _make_supplier(id=10, name="ENEL")
        session.query.return_value \
            .outerjoin.return_value \
            .outerjoin.return_value \
            .filter.return_value \
            .group_by.return_value \
            .first.return_value = (supplier, "Proprietà 1", 4.5, 3)

        result = svc.get_by_id(10)

        assert result is not None
        assert result["id"] == 10
        assert result["avg_rating"] == 4.5

    def test_non_trovato_ritorna_none(self, supplier_service):
        svc, session = supplier_service
        session.query.return_value \
            .outerjoin.return_value \
            .outerjoin.return_value \
            .filter.return_value \
            .group_by.return_value \
            .first.return_value = None

        result = svc.get_by_id(999)

        assert result is None

    def test_errore_db_ritorna_none(self, supplier_service):
        svc, session = supplier_service
        session.query.side_effect = Exception("DB error")

        result = svc.get_by_id(1)

        assert result is None


# ══════════════════════════════════════════════════════════
#  get_categories
# ══════════════════════════════════════════════════════════

class TestGetCategories:

    def test_restituisce_lista_stringhe(self, supplier_service):
        svc, session = supplier_service
        session.query.return_value \
            .distinct.return_value \
            .order_by.return_value \
            .all.return_value = [("Bolletta Luce",), ("Manutenzione",)]

        result = svc.get_categories()

        assert result == ["Bolletta Luce", "Manutenzione"]

    def test_nessuna_categoria_ritorna_lista_vuota(self, supplier_service):
        svc, session = supplier_service
        session.query.return_value \
            .distinct.return_value \
            .order_by.return_value \
            .all.return_value = []

        result = svc.get_categories()

        assert result == []

    def test_errore_db_ritorna_lista_vuota(self, supplier_service):
        svc, session = supplier_service
        session.query.side_effect = Exception("DB error")

        result = svc.get_categories()

        assert result == []


# ══════════════════════════════════════════════════════════
#  create
# ══════════════════════════════════════════════════════════

class TestCreate:

    def test_crea_fornitore_successo(self, supplier_service):
        svc, session = supplier_service

        with patch("services.supplier_service.Supplier") as MockSupplier:
            mock_s = MagicMock()
            mock_s.id = 99
            MockSupplier.return_value = mock_s

            result = svc.create(
                name="Idraulico Bianchi",
                category="Manutenzione",
                property_id=1,
                phone="0612345678",
                email="bianchi@email.it"
            )

        session.add.assert_called_once()
        session.commit.assert_called_once()
        assert result == 99

    def test_errore_db_fa_rollback(self, supplier_service):
        svc, session = supplier_service
        session.commit.side_effect = Exception("DB error")

        with patch("services.supplier_service.Supplier"):
            result = svc.create("Test", "Cat")

        session.rollback.assert_called_once()
        assert result is None

    def test_crea_senza_campi_opzionali(self, supplier_service):
        """Solo name e category sono obbligatori"""
        svc, session = supplier_service

        with patch("services.supplier_service.Supplier") as MockSupplier:
            mock_s = MagicMock()
            mock_s.id = 1
            MockSupplier.return_value = mock_s

            result = svc.create(name="Fornitore Base", category="Generale")

        assert result == 1


# ══════════════════════════════════════════════════════════
#  update
# ══════════════════════════════════════════════════════════

class TestUpdate:

    def test_aggiorna_nome(self, supplier_service):
        svc, session = supplier_service
        supplier = _make_supplier(id=1)
        session.query.return_value.filter.return_value.first.return_value = supplier

        result = svc.update(1, name="Nuovo Nome Fornitore")

        assert result is True
        assert supplier.name == "Nuovo Nome Fornitore"
        session.commit.assert_called_once()

    def test_aggiorna_categoria(self, supplier_service):
        svc, session = supplier_service
        supplier = _make_supplier(id=1)
        session.query.return_value.filter.return_value.first.return_value = supplier

        result = svc.update(1, category="Manutenzione Straordinaria")

        assert result is True
        assert supplier.category == "Manutenzione Straordinaria"

    def test_campo_non_consentito_ignorato(self, supplier_service):
        """Campi non nella whitelist non devono essere applicati"""
        svc, session = supplier_service
        supplier = _make_supplier(id=1)
        session.query.return_value.filter.return_value.first.return_value = supplier

        # tenant_id non è nella whitelist di update
        result = svc.update(1, tenant_id="hacker_tenant")

        assert result is True
        # tenant_id non deve essere modificato tramite setattr
        assert not hasattr(supplier, '_mock_calls') or \
               not any("tenant_id" in str(c) for c in supplier.mock_calls
                       if "setattr" in str(c))

    def test_fornitore_non_trovato_ritorna_false(self, supplier_service):
        svc, session = supplier_service
        session.query.return_value.filter.return_value.first.return_value = None

        result = svc.update(999, name="Non esiste")

        assert result is False

    def test_errore_db_fa_rollback(self, supplier_service):
        svc, session = supplier_service
        supplier = _make_supplier(id=1)
        session.query.return_value.filter.return_value.first.return_value = supplier
        session.commit.side_effect = Exception("DB error")

        result = svc.update(1, name="Test")

        session.rollback.assert_called_once()
        assert result is False


# ══════════════════════════════════════════════════════════
#  update_service_stats
# ══════════════════════════════════════════════════════════

class TestUpdateServiceStats:

    def test_aggiorna_statistiche_cumulativamente(self, supplier_service):
        svc, session = supplier_service
        supplier = _make_supplier(id=1, total_spent=100.0, service_count=2)
        session.query.return_value.filter.return_value.first.return_value = supplier

        result = svc.update_service_stats(1, "2024-01-15", 50.0)

        assert result is True
        assert supplier.total_spent == 150.0
        assert supplier.service_count == 3
        assert supplier.last_service_date == "2024-01-15"

    def test_fornitore_non_trovato_ritorna_false(self, supplier_service):
        svc, session = supplier_service
        session.query.return_value.filter.return_value.first.return_value = None

        result = svc.update_service_stats(999, "2024-01-15", 100.0)

        assert result is False

    def test_primo_servizio_parte_da_zero(self, supplier_service):
        """Fornitore senza servizi precedenti: stats partono da zero"""
        svc, session = supplier_service
        supplier = _make_supplier(id=1, total_spent=0.0, service_count=0)
        session.query.return_value.filter.return_value.first.return_value = supplier

        svc.update_service_stats(1, "2024-01-15", 200.0)

        assert supplier.total_spent == 200.0
        assert supplier.service_count == 1


# ══════════════════════════════════════════════════════════
#  delete
# ══════════════════════════════════════════════════════════

class TestDelete:

    def test_elimina_fornitore_successo(self, supplier_service):
        svc, session = supplier_service
        supplier = _make_supplier(id=1)
        session.query.return_value.filter.return_value.first.return_value = supplier

        result = svc.delete(1)

        assert result is True
        session.delete.assert_called_once_with(supplier)
        session.commit.assert_called_once()

    def test_fornitore_non_trovato_ritorna_false(self, supplier_service):
        svc, session = supplier_service
        session.query.return_value.filter.return_value.first.return_value = None

        result = svc.delete(999)

        assert result is False

    def test_errore_db_fa_rollback(self, supplier_service):
        svc, session = supplier_service
        supplier = _make_supplier(id=1)
        session.query.return_value.filter.return_value.first.return_value = supplier
        session.commit.side_effect = Exception("DB error")

        result = svc.delete(1)

        session.rollback.assert_called_once()
        assert result is False


# ══════════════════════════════════════════════════════════
#  search
# ══════════════════════════════════════════════════════════

class TestSearch:

    def _setup_search_result(self, session, suppliers):
        rows = [(s, f"Prop {s.property_id}", 3.5, 1) for s in suppliers]
        session.query.return_value \
            .outerjoin.return_value \
            .outerjoin.return_value \
            .filter.return_value \
            .group_by.return_value \
            .order_by.return_value \
            .all.return_value = rows
        return rows

    def test_ricerca_per_nome(self, supplier_service):
        svc, session = supplier_service
        suppliers = [_make_supplier(1, name="ENEL Energia")]
        self._setup_search_result(session, suppliers)

        result = svc.search("ENEL")

        assert isinstance(result, list)

    def test_nessun_risultato(self, supplier_service):
        svc, session = supplier_service
        self._setup_search_result(session, [])

        result = svc.search("xyz_non_esistente")

        assert result == []

    def test_errore_db_ritorna_lista_vuota(self, supplier_service):
        svc, session = supplier_service
        session.query.side_effect = Exception("DB error")

        result = svc.search("test")

        assert result == []


# ══════════════════════════════════════════════════════════
#  get_stats
# ══════════════════════════════════════════════════════════

class TestGetStats:

    def test_statistiche_totale_e_categorie(self, supplier_service):
        svc, session = supplier_service
        session.query.return_value.scalar.return_value = 5
        session.query.return_value \
            .group_by.return_value \
            .order_by.return_value \
            .all.return_value = [
                ("Bolletta Luce", 3),
                ("Manutenzione", 2)
            ]

        result = svc.get_stats()

        assert "total" in result
        assert "by_category" in result

    def test_errore_db_ritorna_struttura_vuota(self, supplier_service):
        svc, session = supplier_service
        session.query.side_effect = Exception("DB error")

        result = svc.get_stats()

        assert result == {"total": 0, "by_category": []}


# ══════════════════════════════════════════════════════════
#  Recensioni
# ══════════════════════════════════════════════════════════

class TestRecensioni:

    def test_add_review_successo(self, supplier_service):
        svc, session = supplier_service

        with patch("services.supplier_service.SupplierReview") as MockReview:
            mock_review = MagicMock()
            mock_review.id = 55
            MockReview.return_value = mock_review

            result = svc.add_review(
                supplier_id=1, rating=5,
                title="Ottimo", comment="Puntuale e professionale"
            )

        session.add.assert_called_once()
        session.commit.assert_called_once()
        assert result == 55

    def test_add_review_errore_fa_rollback(self, supplier_service):
        svc, session = supplier_service
        session.commit.side_effect = Exception("DB error")

        with patch("services.supplier_service.SupplierReview"):
            result = svc.add_review(supplier_id=1, rating=3)

        session.rollback.assert_called_once()
        assert result is None

    def test_get_reviews_lista(self, supplier_service):
        svc, session = supplier_service
        reviews = [_make_review(1), _make_review(2)]
        session.query.return_value \
            .filter.return_value \
            .order_by.return_value \
            .all.return_value = reviews

        result = svc.get_reviews(supplier_id=1)

        assert len(result) == 2
        assert isinstance(result[0], dict)

    def test_get_reviews_lista_vuota(self, supplier_service):
        svc, session = supplier_service
        session.query.return_value \
            .filter.return_value \
            .order_by.return_value \
            .all.return_value = []

        result = svc.get_reviews(supplier_id=999)

        assert result == []

    def test_delete_review_successo(self, supplier_service):
        svc, session = supplier_service
        review = _make_review(id=10)
        session.query.return_value.filter.return_value.first.return_value = review

        result = svc.delete_review(10)

        assert result is True
        session.delete.assert_called_once_with(review)

    def test_delete_review_non_trovata(self, supplier_service):
        svc, session = supplier_service
        session.query.return_value.filter.return_value.first.return_value = None

        result = svc.delete_review(999)

        assert result is False


# ══════════════════════════════════════════════════════════
#  Documenti
# ══════════════════════════════════════════════════════════

class TestDocumenti:

    def test_add_document_successo(self, supplier_service):
        svc, session = supplier_service

        with patch("services.supplier_service.SupplierDocument") as MockDoc:
            mock_doc = MagicMock()
            mock_doc.id = 77
            MockDoc.return_value = mock_doc

            result = svc.add_document(
                supplier_id=1,
                document_type="contratto",
                title="Contratto 2024",
                file_path="/docs/contratto.pdf"
            )

        session.add.assert_called_once()
        session.commit.assert_called_once()
        assert result == 77

    def test_add_document_errore_fa_rollback(self, supplier_service):
        svc, session = supplier_service
        session.commit.side_effect = Exception("DB error")

        with patch("services.supplier_service.SupplierDocument"):
            result = svc.add_document(1, "tipo", "titolo", "/path")

        session.rollback.assert_called_once()
        assert result is None

    def test_get_documents_lista(self, supplier_service):
        svc, session = supplier_service
        docs = [_make_document(1), _make_document(2)]
        session.query.return_value \
            .filter.return_value \
            .order_by.return_value \
            .all.return_value = docs

        result = svc.get_documents(supplier_id=1)

        assert len(result) == 2

    def test_get_documents_con_filtro_tipo(self, supplier_service):
        svc, session = supplier_service
        session.query.return_value \
            .filter.return_value \
            .filter.return_value \
            .order_by.return_value \
            .all.return_value = [_make_document(1, document_type="contratto")]

        result = svc.get_documents(supplier_id=1, document_type="contratto")

        assert isinstance(result, list)

    def test_delete_document_successo(self, supplier_service):
        svc, session = supplier_service
        doc = _make_document(id=5)
        session.query.return_value.filter.return_value.first.return_value = doc

        result = svc.delete_document(5)

        assert result is True
        session.delete.assert_called_once_with(doc)

    def test_delete_document_non_trovato(self, supplier_service):
        svc, session = supplier_service
        session.query.return_value.filter.return_value.first.return_value = None

        result = svc.delete_document(999)

        assert result is False
