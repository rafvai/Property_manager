from database.models import Transaction
from database.connection import DatabaseConnection
from sqlalchemy import and_, func, cast, Integer
from datetime import datetime


class TransactionService:
    """Gestisce le operazioni sulle transazioni - ORM based"""

    def __init__(self, logger):
        self.logger = logger
        self.db = DatabaseConnection()

    def _parse_date_for_filter(self, date_field):
        """
        Converte formato dd/MM/yyyy in yyyy-MM-dd per confronto
        Usa funzioni SQLAlchemy compatibili con tutti i DB
        """
        # Estrai anno, mese, giorno dalla stringa dd/MM/yyyy
        year = func.substr(date_field, 7, 4)
        month = func.substr(date_field, 4, 2)
        day = func.substr(date_field, 1, 2)

        # Concatena in formato yyyy-MM-dd usando concat di SQLAlchemy
        return func.date(func.concat(year, '-', month, '-', day))

    def get_all(self, property_id=None, start_date=None, end_date=None):
        """Recupera tutte le transazioni con filtri opzionali"""
        session = self.db.get_session()
        try:
            query = session.query(Transaction)

            # Filtro per proprietà
            if property_id:
                query = query.filter(Transaction.property_id == property_id)

            # Filtro per date
            if start_date and end_date:
                parsed_date = self._parse_date_for_filter(Transaction.date)
                query = query.filter(
                    and_(
                        parsed_date >= start_date,
                        parsed_date <= end_date
                    )
                )

            # Ordina per data decrescente
            transactions = query.order_by(Transaction.date.desc()).all()

            return [trans.to_dict() for trans in transactions]

        except Exception as e:
            self.logger.error(f"TransactionService: Errore recupero transazioni: {e}")
            return []
        finally:
            self.db.close_session(session)

    def get_monthly_summary(self, year, property_id=None):
        """Recupera il riepilogo mensile per un anno"""
        session = self.db.get_session()
        try:
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"

            # Estrai mese dalla data dd/MM/yyyy
            month_expr = cast(func.substr(Transaction.date, 4, 2), Integer)

            # Query per raggruppare per mese e tipo
            query = session.query(
                month_expr.label('month'),
                Transaction.type,
                func.sum(Transaction.amount).label('total')
            )

            # Filtro per anno
            parsed_date = self._parse_date_for_filter(Transaction.date)
            query = query.filter(
                and_(
                    parsed_date >= start_date,
                    parsed_date <= end_date
                )
            )

            if property_id:
                query = query.filter(Transaction.property_id == property_id)

            results = query.group_by('month', Transaction.type).order_by('month').all()

            return results

        except Exception as e:
            self.logger.error(f"TransactionService: Errore riepilogo mensile: {e}")
            return []
        finally:
            self.db.close_session(session)

    def create(self, property_id, date, trans_type, amount, provider, service, supplier_id=None):
        """Crea una nuova transazione"""
        session = self.db.get_session()
        try:
            new_transaction = Transaction(
                property_id=property_id,
                date=date,
                type=trans_type,
                amount=amount,
                provider=provider,
                service=service
            )
            session.add(new_transaction)
            session.commit()

            transaction_id = new_transaction.id
            self.logger.info(f"TransactionService: Transazione creata: {transaction_id}")
            return transaction_id

        except Exception as e:
            session.rollback()
            self.logger.error(f"TransactionService: Errore creazione transazione: {e}")
            return None
        finally:
            self.db.close_session(session)

    def update(self, transaction_id, **kwargs):
        """Aggiorna una transazione"""
        session = self.db.get_session()
        try:
            transaction = session.query(Transaction).filter(
                Transaction.id == transaction_id
            ).first()

            if not transaction:
                return False

            # Campi aggiornabili
            allowed_fields = ['property_id', 'date', 'type', 'amount', 'provider', 'service']

            for field, value in kwargs.items():
                if field in allowed_fields and value is not None:
                    setattr(transaction, field, value)

            session.commit()
            self.logger.info(f"TransactionService: Transazione aggiornata: {transaction_id}")
            return True

        except Exception as e:
            session.rollback()
            self.logger.error(f"TransactionService: Errore aggiornamento: {e}")
            return False
        finally:
            self.db.close_session(session)

    def delete(self, transaction_id):
        """Elimina una transazione"""
        session = self.db.get_session()
        try:
            transaction = session.query(Transaction).filter(
                Transaction.id == transaction_id
            ).first()

            if not transaction:
                return False

            session.delete(transaction)
            session.commit()
            self.logger.info(f"TransactionService: Transazione eliminata: {transaction_id}")
            return True

        except Exception as e:
            session.rollback()
            self.logger.error(f"TransactionService: Errore eliminazione: {e}")
            return False
        finally:
            self.db.close_session(session)

    def get_balance(self, property_id=None, end_date=None):
        """Calcola il saldo totale"""
        session = self.db.get_session()
        try:
            # Query per entrate
            entrate_query = session.query(
                func.coalesce(func.sum(Transaction.amount), 0)
            ).filter(Transaction.type == 'Entrata')

            # Query per uscite
            uscite_query = session.query(
                func.coalesce(func.sum(Transaction.amount), 0)
            ).filter(Transaction.type == 'Uscita')

            # Filtro per proprietà
            if property_id:
                entrate_query = entrate_query.filter(Transaction.property_id == property_id)
                uscite_query = uscite_query.filter(Transaction.property_id == property_id)

            # Filtro per data fine
            if end_date:
                parsed_date = self._parse_date_for_filter(Transaction.date)
                date_filter = parsed_date <= end_date

                entrate_query = entrate_query.filter(date_filter)
                uscite_query = uscite_query.filter(date_filter)

            entrate = entrate_query.scalar() or 0
            uscite = uscite_query.scalar() or 0

            return entrate - uscite

        except Exception as e:
            self.logger.error(f"TransactionService: Errore calcolo saldo: {e}")
            return 0
        finally:
            self.db.close_session(session)

    def create_with_supplier(self, property_id, date, trans_type, amount,
                             provider, service, supplier_id=None):
        """
        Crea una nuova transazione con collegamento al fornitore

        Args:
            property_id: ID proprietà
            date: Data transazione (dd/MM/yyyy)
            trans_type: Tipo ('Entrata' o 'Uscita')
            amount: Importo
            provider: Nome fornitore
            service: Servizio/categoria
            supplier_id: ID fornitore (opzionale)

        Returns:
            ID transazione creata o None
        """
        session = self.db.get_session()
        try:
            new_transaction = Transaction(
                property_id=property_id,
                supplier_id=supplier_id,  # <- NUOVO campo
                date=date,
                type=trans_type,
                amount=amount,
                provider=provider,
                service=service
            )
            session.add(new_transaction)
            session.commit()

            transaction_id = new_transaction.id

            # AGGIORNA STATISTICHE FORNITORE se collegato
            if supplier_id and trans_type == 'Uscita':
                # Converti data da dd/MM/yyyy a yyyy-MM-dd
                try:
                    date_parts = date.split('/')
                    service_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"

                    # Importa SupplierService (oppure passa come parametro)
                    from services.supplier_service import SupplierService
                    supplier_service = SupplierService(self.logger)
                    supplier_service.update_service_stats(
                        supplier_id,
                        service_date,
                        amount
                    )
                except Exception as e:
                    self.logger.warning(f"Impossibile aggiornare stats fornitore: {e}")

            self.logger.info(f"TransactionService: Transazione creata: {transaction_id} (Fornitore: {supplier_id})")
            return transaction_id

        except Exception as e:
            session.rollback()
            self.logger.error(f"TransactionService: Errore creazione transazione: {e}")
            return None
        finally:
            self.db.close_session(session)

    # MODIFICA anche il metodo create esistente per supportare supplier_id:

    def create(self, property_id, date, trans_type, amount, provider, service, supplier_id=None):
        """
        Crea una nuova transazione (versione base con supporto supplier_id)
        """
        return self.create_with_supplier(
            property_id, date, trans_type, amount,
            provider, service, supplier_id
        )
