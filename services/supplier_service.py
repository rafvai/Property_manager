from database.models import Supplier, Property, SupplierDocument, SupplierReview
from database.connection import DatabaseConnection
from sqlalchemy import func, desc
from datetime import datetime


class SupplierService:
    """Gestisce le operazioni sui fornitori - Versione Completa"""

    def __init__(self, logger):
        self.logger = logger
        self.db = DatabaseConnection()

    def get_all(self, category=None, property_id=None, min_rating=None):
        """
        Recupera tutti i fornitori con filtri opzionali

        Args:
            category: Categoria opzionale
            property_id: ID proprietà opzionale
            min_rating: Rating minimo (1-5)

        Returns:
            Lista di fornitori con statistiche
        """
        session = self.db.get_session()
        try:
            query = session.query(
                Supplier,
                Property.name.label('property_name'),
                func.coalesce(func.avg(SupplierReview.rating), 0).label('avg_rating'),
                func.count(SupplierReview.id).label('review_count')
            ).outerjoin(
                Property, Supplier.property_id == Property.id
            ).outerjoin(
                SupplierReview, Supplier.id == SupplierReview.supplier_id
            )

            if category:
                query = query.filter(Supplier.category == category)

            if property_id:
                query = query.filter(Supplier.property_id == property_id)

            query = query.group_by(Supplier.id, Property.name)

            if min_rating:
                query = query.having(func.coalesce(func.avg(SupplierReview.rating), 0) >= min_rating)

            results = query.order_by(Supplier.name.asc()).all()

            suppliers = []
            for supplier, property_name, avg_rating, review_count in results:
                supplier_dict = supplier.to_dict()
                supplier_dict['property_name'] = property_name
                supplier_dict['avg_rating'] = round(avg_rating, 1) if avg_rating else 0
                supplier_dict['review_count'] = review_count
                suppliers.append(supplier_dict)

            return suppliers

        except Exception as e:
            self.logger.error(f"SupplierService: Errore recupero fornitori: {e}")
            return []
        finally:
            self.db.close_session(session)

    def get_by_id(self, supplier_id):
        """Recupera un fornitore con tutte le statistiche"""
        session = self.db.get_session()
        try:
            result = session.query(
                Supplier,
                Property.name.label('property_name'),
                func.coalesce(func.avg(SupplierReview.rating), 0).label('avg_rating'),
                func.count(SupplierReview.id).label('review_count')
            ).outerjoin(
                Property, Supplier.property_id == Property.id
            ).outerjoin(
                SupplierReview, Supplier.id == SupplierReview.supplier_id
            ).filter(
                Supplier.id == supplier_id
            ).group_by(Supplier.id, Property.name).first()

            if result:
                supplier, property_name, avg_rating, review_count = result
                supplier_dict = supplier.to_dict()
                supplier_dict['property_name'] = property_name
                supplier_dict['avg_rating'] = round(avg_rating, 1) if avg_rating else 0
                supplier_dict['review_count'] = review_count
                return supplier_dict
            return None

        except Exception as e:
            self.logger.error(f"SupplierService: Errore recupero fornitore: {e}")
            return None
        finally:
            self.db.close_session(session)

    def get_categories(self, property_id=None):
        """Recupera categorie uniche"""
        session = self.db.get_session()
        try:
            query = session.query(Supplier.category).distinct()

            if property_id:
                query = query.filter(Supplier.property_id == property_id)

            categories = query.order_by(Supplier.category.asc()).all()
            return [cat[0] for cat in categories]

        except Exception as e:
            self.logger.error(f"SupplierService: Errore recupero categorie: {e}")
            return []
        finally:
            self.db.close_session(session)

    def create(self, name, category, property_id=None, phone=None, email=None,
               address=None, notes=None, rating=None):
        """Crea un nuovo fornitore"""
        session = self.db.get_session()
        try:
            new_supplier = Supplier(
                property_id=property_id,
                name=name,
                category=category,
                phone=phone,
                email=email,
                address=address,
                notes=notes,
                rating=rating
            )
            session.add(new_supplier)
            session.commit()

            supplier_id = new_supplier.id
            self.logger.info(f"SupplierService: Fornitore creato: {supplier_id} - {name}")
            return supplier_id

        except Exception as e:
            session.rollback()
            self.logger.error(f"SupplierService: Errore creazione fornitore: {e}")
            return None
        finally:
            self.db.close_session(session)

    def update(self, supplier_id, **kwargs):
        """Aggiorna un fornitore"""
        session = self.db.get_session()
        try:
            supplier = session.query(Supplier).filter(
                Supplier.id == supplier_id
            ).first()

            if not supplier:
                return False

            allowed_fields = ['name', 'category', 'property_id', 'phone', 'email',
                              'address', 'notes', 'rating', 'last_service_date',
                              'total_spent', 'service_count']

            for field, value in kwargs.items():
                if field in allowed_fields:
                    setattr(supplier, field, value)

            session.commit()
            self.logger.info(f"SupplierService: Fornitore aggiornato: {supplier_id}")
            return True

        except Exception as e:
            session.rollback()
            self.logger.error(f"SupplierService: Errore aggiornamento fornitore: {e}")
            return False
        finally:
            self.db.close_session(session)

    def update_service_stats(self, supplier_id, service_date, amount):
        """
        Aggiorna statistiche dopo un servizio

        Args:
            supplier_id: ID fornitore
            service_date: Data servizio (yyyy-MM-dd)
            amount: Importo speso
        """
        session = self.db.get_session()
        try:
            supplier = session.query(Supplier).filter(
                Supplier.id == supplier_id
            ).first()

            if supplier:
                supplier.last_service_date = service_date
                supplier.total_spent = (supplier.total_spent or 0) + amount
                supplier.service_count = (supplier.service_count or 0) + 1
                session.commit()

                self.logger.info(f"SupplierService: Statistiche aggiornate per fornitore {supplier_id}")
                return True
            return False

        except Exception as e:
            session.rollback()
            self.logger.error(f"SupplierService: Errore aggiornamento statistiche: {e}")
            return False
        finally:
            self.db.close_session(session)

    def delete(self, supplier_id):
        """Elimina un fornitore e tutti i dati associati"""
        session = self.db.get_session()
        try:
            supplier = session.query(Supplier).filter(
                Supplier.id == supplier_id
            ).first()

            if not supplier:
                return False

            # Le reviews e documents vengono eliminati automaticamente (cascade)
            session.delete(supplier)
            session.commit()
            self.logger.info(f"SupplierService: Fornitore eliminato: {supplier_id}")
            return True

        except Exception as e:
            session.rollback()
            self.logger.error(f"SupplierService: Errore eliminazione fornitore: {e}")
            return False
        finally:
            self.db.close_session(session)

    def search(self, search_term, category=None, property_id=None):
        """Cerca fornitori per nome"""
        session = self.db.get_session()
        try:
            query = session.query(
                Supplier,
                Property.name.label('property_name'),
                func.coalesce(func.avg(SupplierReview.rating), 0).label('avg_rating'),
                func.count(SupplierReview.id).label('review_count')
            ).outerjoin(
                Property, Supplier.property_id == Property.id
            ).outerjoin(
                SupplierReview, Supplier.id == SupplierReview.supplier_id
            ).filter(
                Supplier.name.ilike(f"%{search_term}%")
            )

            if category:
                query = query.filter(Supplier.category == category)

            if property_id:
                query = query.filter(Supplier.property_id == property_id)

            query = query.group_by(Supplier.id, Property.name)
            results = query.order_by(Supplier.name.asc()).all()

            suppliers = []
            for supplier, property_name, avg_rating, review_count in results:
                supplier_dict = supplier.to_dict()
                supplier_dict['property_name'] = property_name
                supplier_dict['avg_rating'] = round(avg_rating, 1) if avg_rating else 0
                supplier_dict['review_count'] = review_count
                suppliers.append(supplier_dict)

            return suppliers

        except Exception as e:
            self.logger.error(f"SupplierService: Errore ricerca fornitori: {e}")
            return []
        finally:
            self.db.close_session(session)

    def get_stats(self, property_id=None):
        """Statistiche fornitori"""
        session = self.db.get_session()
        try:
            query_total = session.query(func.count(Supplier.id))
            query_categories = session.query(
                Supplier.category,
                func.count(Supplier.id).label('count')
            )

            if property_id:
                query_total = query_total.filter(Supplier.property_id == property_id)
                query_categories = query_categories.filter(Supplier.property_id == property_id)

            total = query_total.scalar()
            categories_count = query_categories.group_by(
                Supplier.category
            ).order_by(
                func.count(Supplier.id).desc()
            ).all()

            return {
                'total': total or 0,
                'by_category': [
                    {'category': cat, 'count': count}
                    for cat, count in categories_count
                ]
            }

        except Exception as e:
            self.logger.error(f"SupplierService: Errore statistiche fornitori: {e}")
            return {'total': 0, 'by_category': []}
        finally:
            self.db.close_session(session)

    def get_suggestions_for_transaction(self, category, property_id=None):
        """
        Suggerisce fornitori per una transazione

        Args:
            category: Categoria della transazione
            property_id: ID proprietà (opzionale)

        Returns:
            Lista di fornitori ordinati per rilevanza
        """
        session = self.db.get_session()
        try:
            query = session.query(
                Supplier,
                func.coalesce(func.avg(SupplierReview.rating), 0).label('avg_rating')
            ).outerjoin(
                SupplierReview, Supplier.id == SupplierReview.supplier_id
            ).filter(
                Supplier.category == category
            )

            if property_id:
                # Priorità: fornitori della stessa proprietà
                query = query.filter(Supplier.property_id == property_id)

            query = query.group_by(Supplier.id).order_by(
                desc('avg_rating'),  # Ordina per rating
                desc(Supplier.service_count),  # Poi per numero servizi
                desc(Supplier.last_service_date)  # Poi per data ultimo servizio
            )

            results = query.limit(5).all()  # Top 5 suggerimenti

            suppliers = []
            for supplier, avg_rating in results:
                supplier_dict = supplier.to_dict()
                supplier_dict['avg_rating'] = round(avg_rating, 1) if avg_rating else 0
                suppliers.append(supplier_dict)

            return suppliers

        except Exception as e:
            self.logger.error(f"SupplierService: Errore suggerimenti: {e}")
            return []
        finally:
            self.db.close_session(session)

    # === GESTIONE RECENSIONI ===

    def add_review(self, supplier_id, rating, title=None, comment=None, service_date=None):
        """Aggiunge una recensione"""
        session = self.db.get_session()
        try:
            review = SupplierReview(
                supplier_id=supplier_id,
                rating=rating,
                title=title,
                comment=comment,
                service_date=service_date
            )
            session.add(review)
            session.commit()

            self.logger.info(f"SupplierService: Recensione aggiunta per fornitore {supplier_id}")
            return review.id

        except Exception as e:
            session.rollback()
            self.logger.error(f"SupplierService: Errore aggiunta recensione: {e}")
            return None
        finally:
            self.db.close_session(session)

    def get_reviews(self, supplier_id):
        """Recupera tutte le recensioni di un fornitore"""
        session = self.db.get_session()
        try:
            reviews = session.query(SupplierReview).filter(
                SupplierReview.supplier_id == supplier_id
            ).order_by(desc(SupplierReview.created_at)).all()

            return [review.to_dict() for review in reviews]

        except Exception as e:
            self.logger.error(f"SupplierService: Errore recupero recensioni: {e}")
            return []
        finally:
            self.db.close_session(session)

    def delete_review(self, review_id):
        """Elimina una recensione"""
        session = self.db.get_session()
        try:
            review = session.query(SupplierReview).filter(
                SupplierReview.id == review_id
            ).first()

            if review:
                session.delete(review)
                session.commit()
                return True
            return False

        except Exception as e:
            session.rollback()
            self.logger.error(f"SupplierService: Errore eliminazione recensione: {e}")
            return False
        finally:
            self.db.close_session(session)

    # === GESTIONE DOCUMENTI ===

    def add_document(self, supplier_id, document_type, title, file_path, notes=None):
        """Aggiunge un documento al fornitore"""
        session = self.db.get_session()
        try:
            document = SupplierDocument(
                supplier_id=supplier_id,
                document_type=document_type,
                title=title,
                file_path=file_path,
                notes=notes
            )
            session.add(document)
            session.commit()

            self.logger.info(f"SupplierService: Documento aggiunto per fornitore {supplier_id}")
            return document.id

        except Exception as e:
            session.rollback()
            self.logger.error(f"SupplierService: Errore aggiunta documento: {e}")
            return None
        finally:
            self.db.close_session(session)

    def get_documents(self, supplier_id, document_type=None):
        """Recupera documenti di un fornitore"""
        session = self.db.get_session()
        try:
            query = session.query(SupplierDocument).filter(
                SupplierDocument.supplier_id == supplier_id
            )

            if document_type:
                query = query.filter(SupplierDocument.document_type == document_type)

            documents = query.order_by(desc(SupplierDocument.upload_date)).all()
            return [doc.to_dict() for doc in documents]

        except Exception as e:
            self.logger.error(f"SupplierService: Errore recupero documenti: {e}")
            return []
        finally:
            self.db.close_session(session)

    def delete_document(self, document_id):
        """Elimina un documento"""
        session = self.db.get_session()
        try:
            document = session.query(SupplierDocument).filter(
                SupplierDocument.id == document_id
            ).first()

            if document:
                session.delete(document)
                session.commit()
                return True
            return False

        except Exception as e:
            session.rollback()
            self.logger.error(f"SupplierService: Errore eliminazione documento: {e}")
            return False
        finally:
            self.db.close_session(session)