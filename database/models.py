from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text, Date, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Property(Base):
    __tablename__ = 'properties'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    address = Column(String(500), nullable=False)
    managed_by = Column(String(200), nullable=True)
    square_meters = Column(Float, nullable=True)
    energy_class = Column(String(10), nullable=True)

    transactions = relationship("Transaction", back_populates="property", cascade="all, delete-orphan")
    deadlines = relationship("Deadline", back_populates="property", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id':             self.id,
            'tenant_id':      self.tenant_id,
            'name':           self.name,
            'address':        self.address,
            'managed_by':     self.managed_by,
            'square_meters':  self.square_meters,
            'energy_class':   self.energy_class,
        }


class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=False)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=True)
    date = Column(Date, nullable=False, index=True)
    type = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    provider = Column(String(200), nullable=False)
    service = Column(String(200), nullable=False)

    property = relationship("Property", back_populates="transactions")
    supplier = relationship("Supplier")

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'property_id': self.property_id,
            'supplier_id': self.supplier_id,
            'date': self.date.isoformat() if self.date else None,
            'type': self.type,
            'amount': self.amount,
            'provider': self.provider,
            'service': self.service
        }


class Deadline(Base):
    __tablename__ = 'deadlines'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(Date, nullable=False, index=True)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    property = relationship("Property", back_populates="deadlines")

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'property_id': self.property_id,
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'completed': self.completed,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Supplier(Base):
    __tablename__ = 'suppliers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=True)
    name = Column(String(200), nullable=False)
    category = Column(String(200), nullable=False)
    phone = Column(String(50), nullable=True)
    email = Column(String(200), nullable=True)
    address = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)
    last_service_date = Column(Date, nullable=True)
    total_spent = Column(Float, default=0.0)
    service_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    property = relationship("Property", backref="suppliers")
    documents = relationship("SupplierDocument", back_populates="supplier", cascade="all, delete-orphan")
    reviews = relationship("SupplierReview", back_populates="supplier", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'property_id': self.property_id,
            'name': self.name,
            'category': self.category,
            'phone': self.phone,
            'email': self.email,
            'address': self.address,
            'notes': self.notes,
            'rating': self.rating,
            'last_service_date': self.last_service_date.isoformat() if self.last_service_date else None,
            'total_spent': self.total_spent,
            'service_count': self.service_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class SupplierDocument(Base):
    __tablename__ = 'supplier_documents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=False)
    document_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    file_path = Column(String(500), nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    supplier = relationship("Supplier", back_populates="documents")

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'supplier_id': self.supplier_id,
            'document_type': self.document_type,
            'title': self.title,
            'file_path': self.file_path,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'notes': self.notes
        }


class SupplierReview(Base):
    __tablename__ = 'supplier_reviews'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=False)
    rating = Column(Integer, nullable=False)
    title = Column(String(200), nullable=True)
    comment = Column(Text, nullable=True)
    service_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="reviews")

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'supplier_id': self.supplier_id,
            'rating': self.rating,
            'title': self.title,
            'comment': self.comment,
            'service_date': self.service_date.isoformat() if self.service_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class UserPreference(Base):
    __tablename__ = 'user_preferences'

    id         = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id  = Column(String(64), nullable=False, index=True)
    key        = Column(String(100), nullable=False)
    value      = Column(String(500), nullable=True)
    currency   = Column(String(5), nullable=False, default="€")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'key', name='uq_preference_tenant_key'),
    )