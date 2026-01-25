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
    date = Column(String(20), nullable=False)  # Formato: dd/MM/yyyy
    type = Column(String(20), nullable=False)  # 'Entrata' o 'Uscita'
    amount = Column(Float, nullable=False)
    provider = Column(String(200), nullable=False)
    service = Column(String(200), nullable=False)

    # Relazione
    property = relationship("Property", back_populates="transactions")

    def to_dict(self):
        return {
            'id': self.id,
            'property_id': self.property_id,
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