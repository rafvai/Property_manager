from database.models import UserPreference
from database.connection import DatabaseConnection
from config import Config


class UserPreferenceService:
    """
    Gestisce le preferenze utente persistite nel DB.
    Interfaccia chiave/valore con default garantiti.
    Usa una cache in-memory per evitare query ripetute su valori
    letti frequentemente (es. valuta) durante il ciclo di vita dell'app.
    """

    DEFAULTS = {
        "deadline_warning_days": "7",
        "currency": "€",
    }

    def __init__(self, logger):
        self.logger = logger
        self.db = DatabaseConnection()
        # Cache in-memory: viene invalidata ad ogni set()
        self._cache: dict = {}

    # ── lettura ──────────────────────────────────────────────

    def get(self, key: str) -> str:
        """
        Ritorna il valore della preferenza.
        Controlla prima la cache in-memory, poi il DB, poi i default.
        """
        if key in self._cache:
            return self._cache[key]

        session = self.db.get_session()
        try:
            row = session.query(UserPreference).filter_by(
                tenant_id=Config.CURRENT_TENANT_ID,
                key=key
            ).first()
            value = row.value if row else self.DEFAULTS.get(key, "")
            self._cache[key] = value
            return value
        except Exception as e:
            self.logger.error(f"UserPreferenceService: get({key}): {e}")
            return self.DEFAULTS.get(key, "")
        finally:
            self.db.close_session(session)

    def get_int(self, key: str) -> int:
        try:
            return int(self.get(key))
        except (ValueError, TypeError):
            try:
                return int(self.DEFAULTS.get(key, "0"))
            except ValueError:
                return 0

    # ── scrittura ─────────────────────────────────────────────

    def set(self, key: str, value: str) -> bool:
        """Upsert della preferenza e invalidazione cache."""
        session = self.db.get_session()
        try:
            row = session.query(UserPreference).filter_by(
                tenant_id=Config.CURRENT_TENANT_ID,
                key=key
            ).first()
            if row:
                row.value = str(value)
            else:
                session.add(UserPreference(
                    tenant_id=Config.CURRENT_TENANT_ID,
                    key=key,
                    value=str(value)
                ))
            session.commit()
            # Invalida la cache per questa chiave
            self._cache.pop(key, None)
            self.logger.info(f"UserPreferenceService: set({key}={value}) OK")
            return True
        except Exception as e:
            session.rollback()
            self.logger.error(f"UserPreferenceService: set({key}={value}): {e}")
            return False
        finally:
            self.db.close_session(session)

    # ── helper tipizzati ──────────────────────────────────────

    def get_deadline_warning_days(self) -> int:
        return self.get_int("deadline_warning_days")

    def set_deadline_warning_days(self, days: int) -> bool:
        if days not in [1, 3, 7, 14, 30]:
            return False
        return self.set("deadline_warning_days", str(days))

    def get_currency(self) -> str:
        """Ritorna il simbolo valuta scelto dall'utente (default: €)."""
        return self.get("currency")

    def set_currency(self, symbol: str) -> bool:
        """Salva la valuta nel DB e notifica la cache."""
        if symbol not in ["€", "$", "£"]:
            return False
        return self.set("currency", symbol)