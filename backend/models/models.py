from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, Enum, ForeignKey, Numeric, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Optional
from datetime import datetime

db = SQLAlchemy()

class Admins(db.Model):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[int] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(Enum("Admin", name:"role_admin", nullable=False))

    def __init__(self, username, password, role):
        self.username = username
        self.role = role
        self.set_password(password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password_hash(self, password):
        return check_password_hash(self.password_hash, password)
    
    def serialize_admins(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role
        }


class Businesses(db.Model):
    __tablename__ = "business"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_name: Mapped[str] = mapped_column(String(50), nullable=False)
    business_RIF: Mapped[str] = mapped_column(String(15), unique=True, nullable=False)
    business_CP: Mapped[str] = mapped_column(String(10), nullable=False)

    users = relationship("Users", back_populates="business")
    services = relationship("Services", back_populates="business")
    clients = relationship("Clients", back_populates="business")

    def serialize_business(self):
        return {
            "id": self.id,
            "name": self.business_name,
            "RIF": self.business_RIF,
            "CP": self.business_CP
        }


class Users(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    business_tax_id: Mapped[str] = mapped_column(
        ForeignKey("business.business_tax_id"), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("master", "manager", "employee", name="role_enum"), nullable=False)
    security_question: Mapped[str] = mapped_column(String(500), nullable=False)
    security_answer: Mapped[str] = mapped_column(String(500), nullable=False)

    business = relationship("Businesses", back_populates="users")
    appointments = relationship("Appointments", back_populates="user",
                                cascade="all, delete-orphan")

    def __init__(self, username, password, business_tax_id, security_question, security_answer, role="employee"):
        self.username = username
        self.business_tax_id = business_tax_id
        self.role = role
        self.security_question = security_question
        self.security_answer = security_answer
        self.set_password(password)