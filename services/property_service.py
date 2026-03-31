from database.models import Property
from database.connection import DatabaseConnection
from config import Config


class PropertyService:
    """Gestisce operazioni sulle proprietà - ORM based"""

    def __init__(self, logger):
        self.logger = logger
        self.db = DatabaseConnection()

    def get_all(self):
        """Recupera tutte le proprietà"""
        session = self.db.get_session()
        try:
            properties = session.query(Property).filter_by(tenant_id = Config.CURRENT_TENANT_ID).all()
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
            prop = session.query(Property).filter(Property.id == property_id, Property.tenant_id==Config.CURRENT_TENANT_ID).first()
            return prop.to_dict() if prop else None
        except Exception as e:
            self.logger.error(f"PropertyService: Errore recupero proprietà: {e}")
            return None
        finally:
            self.db.close_session(session)

    def create(self, name, address, managed_by=None,
               square_meters=None, energy_class=None):
        session = self.db.get_session()
        try:
            new_property = Property(
                name=name,
                tenant_id=Config.CURRENT_TENANT_ID,
                address=address,
                managed_by=managed_by,
                square_meters=square_meters,
                energy_class=energy_class,
            )
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

    def update(self, property_id, name=None, address=None,
               managed_by=None, square_meters=None, energy_class=None,
               _clear_managed_by=False, _clear_square_meters=False,
               _clear_energy_class=False):
        session = self.db.get_session()
        try:
            prop = session.query(Property).filter(
                Property.id == property_id,
                Property.tenant_id == Config.CURRENT_TENANT_ID
            ).first()
            if not prop:
                return False

            if name:          prop.name = name
            if address:       prop.address = address

            # I campi nullable ammettono anche il valore None esplicito
            if managed_by is not None:    prop.managed_by = managed_by
            if _clear_managed_by:         prop.managed_by = None
            if square_meters is not None: prop.square_meters = square_meters
            if _clear_square_meters:      prop.square_meters = None
            if energy_class is not None:  prop.energy_class = energy_class
            if _clear_energy_class:       prop.energy_class = None

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
            prop = session.query(Property).filter(Property.id == property_id, Property.tenant_id==Config.CURRENT_TENANT_ID).first()
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