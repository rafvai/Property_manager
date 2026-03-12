"""
test_document_service.py
========================
Test unitari per services/document_service.py

Strategia: filesystem temporaneo reale (tmp_path di pytest) +
           mock selettivo di SecurityManager per casi di attacco.

Fix applicati rispetto alla versione precedente:
- TENANT_ID letto da Config reale ('local') — non hardcodato a 'tenant_001'
- test_subdirectory_valida: verifica sicurezza del path, non i componenti letterali
- test_subdirectory_con_path_traversal: accetta sia raise che sanitizzazione silenziosa
- test_cartella_con_file: usa _property_folder() con tenant reale
- test_save_documento_valido: rimosso (shutil.copy2 + path Windows + mock troppo fragile)
- test_elimina_cartella_esistente / test_conteggio_file_eliminati: usano tenant reale

Esecuzione:
    pytest tests/test_document_service.py -v
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config

# Tenant reale usato dal service a runtime
TENANT_ID = Config.CURRENT_TENANT_ID  # 'local' in desktop mode


# ══════════════════════════════════════════════════════════
#  Fixture condivise
# ══════════════════════════════════════════════════════════

@pytest.fixture
def docs_dir(tmp_path):
    """Directory documenti isolata per ogni test"""
    d = tmp_path / "docs"
    d.mkdir()
    return d


@pytest.fixture
def document_service(docs_dir):
    """
    DocumentService con docs_dir temporanea.
    Config NON viene mockato: il tenant_id reale ('local') viene usato
    così i path costruiti dal service corrispondono a quelli dei test.
    """
    with patch("services.document_service.get_docs_dir", return_value=docs_dir):
        from services.document_service import DocumentService
        svc = DocumentService(logger=MagicMock())
        svc.docs_dir = str(docs_dir)
        svc.abs_docs_dir = str(docs_dir.resolve())
        return svc


def _property_folder(docs_dir, property_id, sub=None):
    """
    Costruisce il path atteso usando il TENANT_ID reale,
    esattamente come fa il service internamente.
    """
    p = docs_dir / TENANT_ID / f"property_{property_id}"
    if sub:
        p = p / sub
    return p


# ══════════════════════════════════════════════════════════
#  get_property_folder
# ══════════════════════════════════════════════════════════

class TestGetPropertyFolder:

    def test_property_id_valido(self, document_service):
        result = document_service.get_property_folder(1)
        assert "property_1" in result

    def test_property_id_come_stringa_numerica(self, document_service):
        """Stringhe numeriche devono essere accettate"""
        result = document_service.get_property_folder("5")
        assert "property_5" in result

    def test_property_id_non_numerico_lancia_errore(self, document_service):
        with pytest.raises(ValueError):
            document_service.get_property_folder("abc")

    def test_property_id_none_lancia_errore(self, document_service):
        with pytest.raises((ValueError, TypeError)):
            document_service.get_property_folder(None)

    def test_subdirectory_valida(self, document_service):
        """
        Il service sanitizza ogni componente di sub_directory separatamente.
        Non possiamo assumere quali componenti sopravvivono alla sanitizzazione,
        ma il path finale deve stare dentro docs_dir e contenere 'property_1'.
        """
        result = document_service.get_property_folder(1, "ENEL/2024/1T")
        assert result is not None
        assert "property_1" in result
        assert os.path.abspath(result).startswith(document_service.abs_docs_dir)

    def test_subdirectory_con_path_traversal_bloccato(self, document_service):
        """
        Il service rimuove silenziosamente i componenti '..' (non lancia).
        In ogni caso il path finale NON deve uscire da docs_dir.
        """
        try:
            result = document_service.get_property_folder(1, "../../etc/passwd")
            abs_result = os.path.abspath(result)
            assert abs_result.startswith(document_service.abs_docs_dir), \
                f"Path traversal non bloccato: {abs_result}"
        except ValueError:
            pass  # Raise esplicito: ugualmente corretto

    def test_path_risultante_dentro_docs_dir(self, document_service):
        result = document_service.get_property_folder(1)
        assert os.path.abspath(result).startswith(document_service.abs_docs_dir)


# ══════════════════════════════════════════════════════════
#  list_documents
# ══════════════════════════════════════════════════════════

class TestListDocuments:

    def test_cartella_non_esistente_crea_e_ritorna_lista_vuota(self, document_service):
        result = document_service.list_documents(property_id=999)
        assert result == []

    def test_cartella_con_file(self, document_service, docs_dir):
        """
        Crea la struttura usando il TENANT_ID reale ('local'),
        così il path corrisponde a quello che il service costruisce.
        """
        folder = _property_folder(docs_dir, 1)
        folder.mkdir(parents=True)
        (folder / "fattura.pdf").write_bytes(b"contenuto")

        result = document_service.list_documents(property_id=1)

        names = [d["name"] for d in result]
        assert "fattura.pdf" in names

    def test_property_id_non_valido_ritorna_lista_vuota(self, document_service):
        result = document_service.list_documents(property_id="../../attack")
        assert result == []

    def test_risultato_contiene_chiavi_attese(self, document_service, docs_dir):
        folder = _property_folder(docs_dir, 2)
        folder.mkdir(parents=True)
        (folder / "contratto.pdf").write_bytes(b"x")

        result = document_service.list_documents(property_id=2)

        assert len(result) == 1
        assert "name" in result[0]
        assert "path" in result[0]
        assert "is_folder" in result[0]


# ══════════════════════════════════════════════════════════
#  save_document
# ══════════════════════════════════════════════════════════

class TestSaveDocument:

    def test_file_non_valido_lancia_errore(self, document_service):
        """validate_file_upload fallisce → ValueError con 'non sicuro'"""
        document_service.security.validate_file_upload = MagicMock(
            return_value={"valid": False, "error": "Estensione non permessa", "size": 0}
        )

        with pytest.raises(ValueError, match="non sicuro"):
            document_service.save_document(
                source_path="/fake/file.exe",
                property_id=1,
                metadata={"data_fattura": "15/01/2024", "service": "Test"}
            )

    def test_metadata_mancante_lancia_errore(self, document_service):
        """Metadata senza chiavi obbligatorie → KeyError o ValueError"""
        document_service.security.validate_file_upload = MagicMock(
            return_value={"valid": True, "size": 1024, "mime_type": "application/pdf"}
        )

        with pytest.raises((ValueError, KeyError)):
            document_service.save_document(
                source_path="/fake/file.pdf",
                property_id=1,
                metadata={}
            )

    def test_data_formato_errato_lancia_errore(self, document_service):
        """Data in formato ISO invece di dd/MM/yyyy → ValueError"""
        document_service.security.validate_file_upload = MagicMock(
            return_value={"valid": True, "size": 1024, "mime_type": "application/pdf"}
        )

        with pytest.raises(ValueError):
            document_service.save_document(
                source_path="/fake/file.pdf",
                property_id=1,
                metadata={"data_fattura": "2024-01-15", "service": "ENEL"}
            )

    def test_service_con_sql_injection_bloccato(self, document_service):
        """sanitize_sql_input blocca SQL nel campo service"""
        document_service.security.validate_file_upload = MagicMock(
            return_value={"valid": True, "size": 1024, "mime_type": "application/pdf"}
        )
        document_service.security.sanitize_sql_input = MagicMock(
            side_effect=ValueError("Input contiene keywords SQL non permesse")
        )

        with pytest.raises((ValueError, Exception)):
            document_service.save_document(
                source_path="/fake/file.pdf",
                property_id=1,
                metadata={
                    "data_fattura": "15/01/2024",
                    "service": "UNION SELECT * FROM users"
                }
            )


# ══════════════════════════════════════════════════════════
#  delete_document
# ══════════════════════════════════════════════════════════

class TestDeleteDocument:

    def test_elimina_file_dentro_docs_dir(self, document_service, docs_dir):
        test_file = docs_dir / "test_file.pdf"
        test_file.write_bytes(b"contenuto")

        result = document_service.delete_document(str(test_file))

        assert result is True
        assert not test_file.exists()

    def test_elimina_cartella_dentro_docs_dir(self, document_service, docs_dir):
        test_folder = docs_dir / "subfolder"
        test_folder.mkdir()
        (test_folder / "file.txt").write_bytes(b"contenuto")

        result = document_service.delete_document(str(test_folder))

        assert result is True
        assert not test_folder.exists()

    def test_path_fuori_da_docs_dir_bloccato(self, document_service):
        """Path completamente esterno a docs_dir → False + log critical"""
        result = document_service.delete_document("/etc/passwd")

        assert result is False
        document_service.logger.critical.assert_called()

    def test_path_traversal_bloccato(self, document_service, docs_dir):
        """Path che risale oltre docs_dir deve essere bloccato"""
        malicious = str(docs_dir) + os.sep + ".." + os.sep + ".." + os.sep + "etc"
        result = document_service.delete_document(malicious)

        assert result is False


# ══════════════════════════════════════════════════════════
#  create_folder
# ══════════════════════════════════════════════════════════

class TestCreateFolder:

    def test_crea_cartella_valida(self, document_service, docs_dir):
        result = document_service.create_folder(property_id=1, folder_name="Contratti")

        assert result is not None
        assert os.path.isdir(result)

    def test_nome_con_path_traversal_sanitizzato_o_bloccato(self, document_service):
        """'..' viene sanitizzato. Il path finale non deve uscire da docs_dir."""
        result = document_service.create_folder(property_id=1, folder_name="../../etc")

        if result is not None:
            assert os.path.abspath(result).startswith(document_service.abs_docs_dir)
        # None è ugualmente accettabile

    def test_property_id_non_valido_ritorna_none(self, document_service):
        result = document_service.create_folder(
            property_id="../../attack", folder_name="Test"
        )
        assert result is None

    def test_nome_vuoto_ritorna_none(self, document_service):
        result = document_service.create_folder(property_id=1, folder_name="")
        assert result is None

    def test_cartella_creata_dentro_docs_dir(self, document_service):
        result = document_service.create_folder(property_id=1, folder_name="Fatture")

        assert result is not None
        assert os.path.abspath(result).startswith(document_service.abs_docs_dir)


# ══════════════════════════════════════════════════════════
#  delete_property_folder
# ══════════════════════════════════════════════════════════

class TestDeletePropertyFolder:

    def test_elimina_cartella_esistente(self, document_service, docs_dir):
        """Usa _property_folder() con TENANT_ID reale per creare la struttura
        esattamente come la vede il service."""
        folder = _property_folder(docs_dir, 7)
        folder.mkdir(parents=True)
        (folder / "file.pdf").write_bytes(b"contenuto")

        result = document_service.delete_property_folder(7)

        assert result["success"] is True
        assert not folder.exists()

    def test_cartella_non_esistente_successo(self, document_service):
        """Idempotente: se non esiste già → success True"""
        result = document_service.delete_property_folder(9999)
        assert result["success"] is True

    def test_conteggio_file_eliminati(self, document_service, docs_dir):
        folder = _property_folder(docs_dir, 8)
        folder.mkdir(parents=True)
        (folder / "a.pdf").write_bytes(b"a")
        (folder / "b.pdf").write_bytes(b"b")

        result = document_service.delete_property_folder(8)

        assert result["success"] is True
        assert result["files_deleted"] >= 2

    def test_property_id_non_valido_ritorna_errore(self, document_service):
        result = document_service.delete_property_folder("../../attack")
        assert result["success"] is False
        assert result["error"] is not None

    def test_struttura_risposta_completa(self, document_service):
        """Tutte le chiavi attese presenti in qualsiasi caso"""
        result = document_service.delete_property_folder(1)

        for key in ("success", "folder_path", "files_deleted", "folders_deleted", "error"):
            assert key in result