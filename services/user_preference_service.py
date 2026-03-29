from database.models import UserPreference
from database.connection import DatabaseConnection
from config import Config


class UserPreferenceService:
    """
    Gestisce le preferenze utente persistite nel DB.
    Interfaccia chiave/valore con default garantiti.
    """

    DEFAULTS = {
        "deadline_warning_days": "7",
        "currency": "€",
    }

    def __init__(self, logger):
        self.logger = logger
        self.db = DatabaseConnection()

    # ── lettura ──────────────────────────────────────────────

    def get(self, key: str) -> str:
        """Ritorna il valore della preferenza o il default se non esiste."""
        session = self.db.get_session()
        try:
            row = session.query(UserPreference).filter_by(
                tenant_id=Config.CURRENT_TENANT_ID,
                key=key
            ).first()
            return row.value if row else self.DEFAULTS.get(key, "")
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
        """Upsert della preferenza."""
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
        return self.get("currency")

    def set_currency(self, symbol: str) -> bool:
        if symbol not in ["€", "$", "£"]:
            return False
        return self.set("currency", symbol)