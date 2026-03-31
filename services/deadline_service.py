from database.models import Deadline
from database.connection import DatabaseConnection
from datetime import datetime, date, timedelta
from config import Config


class DeadlineService:
    """Gestisce le operazioni sulle scadenze - ORM based"""

    def __init__(self, logger):
        self.logger = logger
        self.db = DatabaseConnection()

    # ──────────────────────────────────────────────────────────────
    #  LETTURA
    # ──────────────────────────────────────────────────────────────

    def get_by_month(self, year: int, month: int) -> dict:
        """
        Carica tutte le scadenze di un mese specifico in una sola query SQL.
        Ritorna dict {date_str: [deadline_dict, ...]} pronto per il calendario.
        """
        session = self.db.get_session()
        try:
            first_day = date(year, month, 1)
            if month == 12:
                last_day = date(year + 1, 1, 1)
            else:
                last_day = date(year, month + 1, 1)

            deadlines = session.query(Deadline).filter(
                Deadline.tenant_id == Config.CURRENT_TENANT_ID,
                Deadline.completed == False,
                Deadline.due_date >= first_day,
                Deadline.due_date <  last_day,
            ).order_by(Deadline.due_date.asc(), Deadline.title.asc()).all()

            result = {}
            for d in deadlines:
                due     = d.due_date
                due_str = due if isinstance(due, str) else due.isoformat()
                result.setdefault(due_str, []).append(d.to_dict())

            return result

        except Exception as e:
            self.logger.error(f"DeadlineService: Errore get_by_month {year}/{month}: {e}")
            return {}
        finally:
            self.db.close_session(session)

    def get_all(self, property_id=None, include_completed=False):
        """Recupera tutte le scadenze con filtri opzionali"""
        session = self.db.get_session()
        try:
            query = session.query(Deadline).filter_by(
                tenant_id=Config.CURRENT_TENANT_ID
            )
            if property_id:
                query = query.filter(Deadline.property_id == property_id)
            if not include_completed:
                query = query.filter(Deadline.completed == False)

            deadlines = query.order_by(Deadline.due_date.asc()).all()
            return [d.to_dict() for d in deadlines]

        except Exception as e:
            self.logger.error(f"DeadlineService: Errore recupero scadenze: {e}")
            return []
        finally:
            self.db.close_session(session)

    def get_next_deadline(self, property_id=None):
        """Recupera la prossima scadenza non completata (da oggi in poi)."""
        session = self.db.get_session()
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            query = session.query(Deadline).filter(
                Deadline.completed  == False,
                Deadline.tenant_id  == Config.CURRENT_TENANT_ID,
                Deadline.due_date   >= today,
            )
            if property_id:
                query = query.filter(Deadline.property_id == property_id)

            deadline = query.order_by(Deadline.due_date.asc()).first()
            return deadline.to_dict() if deadline else None

        except Exception as e:
            self.logger.error(
                f"DeadlineService: Errore recupero prossima scadenza: {e}"
            )
            return None
        finally:
            self.db.close_session(session)

    def get_upcoming(self, warning_days: int = 7, property_id=None) -> list:
        """
        Restituisce le scadenze non completate che cadono entro i prossimi
        `warning_days` giorni (incluso oggi).

        Usato per determinare se mostrare badge o notifiche di avviso.

        Args:
            warning_days: Finestra di preavviso in giorni (letto da UserPreferenceService)
            property_id:  Filtra per proprietà (opzionale)

        Returns:
            Lista di deadline_dict ordinate per data crescente
        """
        session = self.db.get_session()
        try:
            today    = date.today()
            deadline_limit = today + timedelta(days=warning_days)

            query = session.query(Deadline).filter(
                Deadline.tenant_id == Config.CURRENT_TENANT_ID,
                Deadline.completed == False,
                Deadline.due_date  >= today,
                Deadline.due_date  <= deadline_limit,
            )
            if property_id:
                query = query.filter(Deadline.property_id == property_id)

            deadlines = query.order_by(Deadline.due_date.asc()).all()
            return [d.to_dict() for d in deadlines]

        except Exception as e:
            self.logger.error(f"DeadlineService: Errore get_upcoming: {e}")
            return []
        finally:
            self.db.close_session(session)

    def get_overdue(self, property_id=None) -> list:
        """
        Restituisce le scadenze non completate già scadute (due_date < oggi).

        Args:
            property_id: Filtra per proprietà (opzionale)

        Returns:
            Lista di deadline_dict ordinate per data crescente
        """
        session = self.db.get_session()
        try:
            today = date.today()
            query = session.query(Deadline).filter(
                Deadline.tenant_id == Config.CURRENT_TENANT_ID,
                Deadline.completed == False,
                Deadline.due_date  <  today,
            )
            if property_id:
                query = query.filter(Deadline.property_id == property_id)

            deadlines = query.order_by(Deadline.due_date.asc()).all()
            return [d.to_dict() for d in deadlines]

        except Exception as e:
            self.logger.error(f"DeadlineService: Errore get_overdue: {e}")
            return []
        finally:
            self.db.close_session(session)

    def get_by_date(self, date_str):
        """Recupera scadenze per una data specifica (formato: YYYY-MM-DD)"""
        session = self.db.get_session()
        try:
            deadlines = session.query(Deadline).filter(
                Deadline.due_date  == date_str,
                Deadline.tenant_id == Config.CURRENT_TENANT_ID,
            ).order_by(Deadline.title.asc()).all()
            return [d.to_dict() for d in deadlines]

        except Exception as e:
            self.logger.error(
                f"DeadlineService: Errore recupero scadenze per data: {e}"
            )
            return []
        finally:
            self.db.close_session(session)

    # ──────────────────────────────────────────────────────────────
    #  SCRITTURA
    # ──────────────────────────────────────────────────────────────

    def create(self, title, due_date, description=None, property_id=None):
        """Crea una nuova scadenza"""
        session = self.db.get_session()
        try:
            new_deadline = Deadline(
                property_id=property_id,
                tenant_id  =Config.CURRENT_TENANT_ID,
                title      =title,
                description=description,
                due_date   =due_date,
                completed  =False,
            )
            session.add(new_deadline)
            session.commit()
            self.logger.info(f"DeadlineService: Scadenza creata: {new_deadline.id}")
            return new_deadline.id

        except Exception as e:
            session.rollback()
            self.logger.error(f"DeadlineService: Errore creazione scadenza: {e}")
            return None
        finally:
            self.db.close_session(session)

    def update(self, deadline_id, **kwargs):
        """Aggiorna una scadenza"""
        session = self.db.get_session()
        try:
            deadline = session.query(Deadline).filter(
                Deadline.id        == deadline_id,
                Deadline.tenant_id == Config.CURRENT_TENANT_ID,
            ).first()

            if not deadline:
                return False

            allowed_fields = ['title', 'description', 'due_date',
                              'completed', 'property_id']
            for field, value in kwargs.items():
                if field in allowed_fields and value is not None:
                    setattr(deadline, field, value)

            session.commit()
            self.logger.info(f"DeadlineService: Scadenza aggiornata: {deadline_id}")
            return True

        except Exception as e:
            session.rollback()
            self.logger.error(
                f"DeadlineService: Errore aggiornamento scadenza: {e}"
            )
            return False
        finally:
            self.db.close_session(session)

    def mark_completed(self, deadline_id):
        """Segna una scadenza come completata"""
        return self.update(deadline_id, completed=True)

    def delete(self, deadline_id):
        """Elimina una scadenza"""
        session = self.db.get_session()
        try:
            deadline = session.query(Deadline).filter(
                Deadline.id        == deadline_id,
                Deadline.tenant_id == Config.CURRENT_TENANT_ID,
            ).first()

            if not deadline:
                return False

            session.delete(deadline)
            session.commit()
            self.logger.info(f"DeadlineService: Scadenza eliminata: {deadline_id}")
            return True

        except Exception as e:
            session.rollback()
            self.logger.error(
                f"DeadlineService: Errore eliminazione scadenza: {e}"
            )
            return False
        finally:
            self.db.close_session(session)