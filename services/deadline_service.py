from database.models import Deadline
from database.connection import DatabaseConnection
from datetime import datetime


class DeadlineService:
    """Gestisce le operazioni sulle scadenze - ORM based"""

    def __init__(self, logger):
        self.logger = logger
        self.db = DatabaseConnection()

    def get_all(self, property_id=None, include_completed=False):
        """Recupera tutte le scadenze con filtri opzionali"""
        session = self.db.get_session()
        try:
            query = session.query(Deadline)

            # Filtro per proprietà
            if property_id:
                query = query.filter(Deadline.property_id == property_id)

            # Filtro per completate
            if not include_completed:
                query = query.filter(Deadline.completed == False)

            # Ordina per data scadenza
            deadlines = query.order_by(Deadline.due_date.asc()).all()

            return [deadline.to_dict() for deadline in deadlines]

        except Exception as e:
            self.logger.error(f"DeadlineService: Errore recupero scadenze: {e}")
            return []
        finally:
            self.db.close_session(session)

    def get_next_deadline(self, property_id=None):
        """Recupera la prossima scadenza non completata"""
        session = self.db.get_session()
        try:
            query = session.query(Deadline).filter(
                Deadline.completed == False
            )

            if property_id:
                query = query.filter(Deadline.property_id == property_id)

            # Solo scadenze future o di oggi
            today = datetime.now().strftime('%Y-%m-%d')
            query = query.filter(Deadline.due_date >= today)

            # Prima scadenza
            deadline = query.order_by(Deadline.due_date.asc()).first()

            return deadline.to_dict() if deadline else None

        except Exception as e:
            self.logger.error(f"DeadlineService: Errore recupero prossima scadenza: {e}")
            return None
        finally:
            self.db.close_session(session)

    def get_by_date(self, date_str):
        """Recupera scadenze per una data specifica (formato: YYYY-MM-DD)"""
        session = self.db.get_session()
        try:
            deadlines = session.query(Deadline).filter(
                Deadline.due_date == date_str
            ).order_by(Deadline.title.asc()).all()

            return [deadline.to_dict() for deadline in deadlines]

        except Exception as e:
            self.logger.error(f"DeadlineService: Errore recupero scadenze per data: {e}")
            return []
        finally:
            self.db.close_session(session)

    def create(self, title, due_date, description=None, property_id=None):
        """Crea una nuova scadenza"""
        session = self.db.get_session()
        try:
            new_deadline = Deadline(
                property_id=property_id,
                title=title,
                description=description,
                due_date=due_date,
                completed=False
            )
            session.add(new_deadline)
            session.commit()

            deadline_id = new_deadline.id
            self.logger.info(f"DeadlineService: Scadenza creata: {deadline_id}")
            return deadline_id

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
                Deadline.id == deadline_id
            ).first()

            if not deadline:
                return False

            # Campi aggiornabili
            allowed_fields = ['title', 'description', 'due_date', 'completed', 'property_id']

            for field, value in kwargs.items():
                if field in allowed_fields and value is not None:
                    setattr(deadline, field, value)

            session.commit()
            self.logger.info(f"DeadlineService: Scadenza aggiornata: {deadline_id}")
            return True

        except Exception as e:
            session.rollback()
            self.logger.error(f"DeadlineService: Errore aggiornamento scadenza: {e}")
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
                Deadline.id == deadline_id
            ).first()

            if not deadline:
                return False

            session.delete(deadline)
            session.commit()
            self.logger.info(f"DeadlineService: Scadenza eliminata: {deadline_id}")
            return True

        except Exception as e:
            session.rollback()
            self.logger.error(f"DeadlineService: Errore eliminazione scadenza: {e}")
            return False
        finally:
            self.db.close_session(session)