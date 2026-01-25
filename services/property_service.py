from database.models import Property
from database.connection import DatabaseConnection


class PropertyService:
    """Gestisce operazioni sulle proprietà - ORM based"""

    def __init__(self, logger):
        self.logger = logger
        self.db = DatabaseConnection()

    def get_all(self):
        """Recupera tutte le proprietà"""
        session = self.db.get_session()
        try:
            properties = session.query(Property).all()
            return [prop.to_dict() for prop in properties]
        except Exception as e:
            self.logger.error(f"PropertyService: Errore recupero proprietà: {e}")
            return []
        finally:
            self.db.close_session(session)

    def get_by_id(self, property_id):
        """Recupera una proprietà per ID"""
        session = self.db.get_session()
        try:
            prop = session.query(Property).filter(Property.id == property_id).first()
            return prop.to_dict() if prop else None
        except Exception as e:
            self.logger.error(f"PropertyService: Errore recupero proprietà: {e}")
            return None
        finally:
            self.db.close_session(session)

    def create(self, name, address, owner):
        """Crea una nuova proprietà"""
        session = self.db.get_session()
        try:
            new_property = Property(name=name, address=address, owner=owner)
            session.add(new_property)
            session.commit()

            property_id = new_property.id
            self.logger.info(f"PropertyService: Proprietà creata: {property_id}")
            return property_id

        except Exception as e:
            session.rollback()
            self.logger.error(f"PropertyService: Errore creazione proprietà: {e}")
            return None
        finally:
            self.db.close_session(session)

    def update(self, property_id, name=None, address=None, owner=None):
        """Aggiorna una proprietà esistente"""
        session = self.db.get_session()
        try:
            prop = session.query(Property).filter(Property.id == property_id).first()
            if not prop:
                return False

            if name:
                prop.name = name
            if address:
                prop.address = address
            if owner:
                prop.owner = owner

            session.commit()
            self.logger.info(f"PropertyService: Proprietà aggiornata: {property_id}")
            return True

        except Exception as e:
            session.rollback()
            self.logger.error(f"PropertyService: Errore aggiornamento: {e}")
            return False
        finally:
            self.db.close_session(session)

    def delete(self, property_id):
        """Elimina una proprietà (CASCADE elimina anche transactions/deadlines)"""
        session = self.db.get_session()
        try:
            prop = session.query(Property).filter(Property.id == property_id).first()
            if not prop:
                return False

            session.delete(prop)
            session.commit()
            self.logger.info(f"PropertyService: Proprietà eliminata: {property_id}")
            return True

        except Exception as e:
            session.rollback()
            self.logger.error(f"PropertyService: Errore eliminazione: {e}")
            return False
        finally:
            self.db.close_session(session)