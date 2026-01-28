from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Property(Base):
    __tablename__ = 'properties'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    address = Column(String(500), nullable=False)
    owner = Column(String(200), nullable=False)

    # Relazioni
    transactions = relationship("Transaction", back_populates="property", cascade="all, delete-orphan")
    deadlines = relationship("Deadline", back_populates="property", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'owner': self.owner
        }


class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=False)

    # AGGIUNGI QUESTO CAMPO:
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=True)

    date = Column(String(20), nullable=False)
    type = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    provider = Column(String(200), nullable=False)
    service = Column(String(200), nullable=False)

    # Relazioni
    property = relationship("Property", back_populates="transactions")

    # AGGIUNGI QUESTA RELAZIONE:
    supplier = relationship("Supplier")

    def to_dict(self):
        return {
            'id': self.id,
            'property_id': self.property_id,
            'supplier_id': self.supplier_id,  # <- AGGIUNGI
            'date': self.date,
            'type': self.type,
            'amount': self.amount,
            'provider': self.provider,
            'service': self.service
        }


class Deadline(Base):
    __tablename__ = 'deadlines'

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(String(20), nullable=False)  # Formato: yyyy-MM-dd
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relazione
    property = relationship("Property", back_populates="deadlines")

    def to_dict(self):
        return {
            'id': self.id,
            'property_id': self.property_id,
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date,
            'completed': self.completed,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Supplier(Base):
    __tablename__ = 'suppliers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=True)
    name = Column(String(200), nullable=False)
    category = Column(String(200), nullable=False)
    phone = Column(String(50), nullable=True)
    email = Column(String(200), nullable=True)
    address = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)

    # NUOVI CAMPI per le 4 funzionalità
    rating = Column(Integer, nullable=True)  # Valutazione 1-5 stelle
    last_service_date = Column(String(20), nullable=True)  # Formato: yyyy-MM-dd
    total_spent = Column(Float, default=0.0)  # Totale speso con questo fornitore
    service_count = Column(Integer, default=0)  # Numero di servizi utilizzati

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    property = relationship("Property", backref="suppliers")

    # AGGIUNGI QUESTE DUE RELAZIONI:
    documents = relationship("SupplierDocument", back_populates="supplier", cascade="all, delete-orphan")
    reviews = relationship("SupplierReview", back_populates="supplier", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'property_id': self.property_id,
            'name': self.name,
            'category': self.category,
            'phone': self.phone,
            'email': self.email,
            'address': self.address,
            'notes': self.notes,
            'rating': self.rating,
            'last_service_date': self.last_service_date,
            'total_spent': self.total_spent,
            'service_count': self.service_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class SupplierDocument(Base):
    """Documenti associati a un fornitore (contratti, preventivi, fatture)"""
    __tablename__ = 'supplier_documents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=False)
    document_type = Column(String(50), nullable=False)  # 'contratto', 'preventivo', 'fattura', 'altro'
    title = Column(String(200), nullable=False)
    file_path = Column(String(500), nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    # Relazione
    supplier = relationship("Supplier", back_populates="documents")

    def to_dict(self):
        return {
            'id': self.id,
            'supplier_id': self.supplier_id,
            'document_type': self.document_type,
            'title': self.title,
            'file_path': self.file_path,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'notes': self.notes
        }

class SupplierReview(Base):
    """Recensioni/valutazioni dei fornitori"""
    __tablename__ = 'supplier_reviews'

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 stelle
    title = Column(String(200), nullable=True)
    comment = Column(Text, nullable=True)
    service_date = Column(String(20), nullable=True)  # Data del servizio recensito
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relazione
    supplier = relationship("Supplier", back_populates="reviews")

    def to_dict(self):
        return {
            'id': self.id,
            'supplier_id': self.supplier_id,
            'rating': self.rating,
            'title': self.title,
            'comment': self.comment,
            'service_date': self.service_date,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }