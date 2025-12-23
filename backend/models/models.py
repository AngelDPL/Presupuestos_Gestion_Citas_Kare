from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, Enum, ForeignKey, Numeric, DateTime, Date, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

db = SQLAlchemy()


class Admins(db.Model):
    """Tabla de administradores del sistema"""
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(Enum("Admin", name="role_admin"), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    def __init__(self, username: str, password: str, role: str = "Admin"):
        self.username = username
        self.role = role
        self.set_password(password)

    def set_password(self, password: str) -> None:
        """Encripta y almacena la contraseña"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifica que la contraseña sea correcta"""
        return check_password_hash(self.password_hash, password)

    def serialize_admins(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class Businesses(db.Model):
    """Tabla de negocios/empresas"""
    __tablename__ = "business"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_name: Mapped[str] = mapped_column(String(100), nullable=False)
    business_RIF: Mapped[str] = mapped_column(String(15), unique=True, nullable=False)
    business_CP: Mapped[str] = mapped_column(String(10), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    users: Mapped[List["Users"]] = relationship("Users", back_populates="business", cascade="all, delete-orphan")
    services: Mapped[List["Services"]] = relationship("Services", back_populates="business", cascade="all, delete-orphan")
    clients: Mapped[List["Clients"]] = relationship("Clients", back_populates="business", cascade="all, delete-orphan")
    appointments: Mapped[List["Appointments"]] = relationship("Appointments", back_populates="business", cascade="all, delete-orphan")
    calendar_events: Mapped[List["Calendar"]] = relationship("Calendar", back_populates="business", cascade="all, delete-orphan")

    def serialize_business(self) -> dict:
        return {
            "id": self.id,
            "name": self.business_name,
            "RIF": self.business_RIF,
            "CP": self.business_CP,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class Users(db.Model):
    """Tabla de usuarios/empleados del negocio"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    business_id: Mapped[int] = mapped_column(ForeignKey("business.id"), nullable=False)
    role: Mapped[str] = mapped_column(Enum("master", "manager", "employee", name="role_enum"), nullable=False)
    security_question: Mapped[str] = mapped_column(String(500), nullable=False)
    security_answer: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    business: Mapped["Businesses"] = relationship("Businesses", back_populates="users")
    appointments: Mapped[List["Appointments"]] = relationship("Appointments", back_populates="user", cascade="all, delete-orphan")

    def __init__(self, username: str, password: str, business_id: int, security_question: str, 
                 security_answer: str, role: str = "employee"):
        self.username = username
        self.business_id = business_id
        self.role = role
        self.security_question = security_question
        self.security_answer = security_answer
        self.set_password(password)

    def set_password(self, password: str) -> None:
        """Encripta y almacena la contraseña"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifica que la contraseña sea correcta"""
        return check_password_hash(self.password_hash, password)

    def serialize_user(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "business_id": self.business_id,
            "security_question": self.security_question,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class Services(db.Model):
    """Tabla de servicios que ofrece el negocio"""
    __tablename__ = "service"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("business.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(75), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    business: Mapped["Businesses"] = relationship("Businesses", back_populates="services")
    clients: Mapped[List["Clients"]] = relationship("Clients", secondary="client_service", back_populates="services")
    appointments: Mapped[List["Appointments"]] = relationship("Appointments", back_populates="service", cascade="all, delete-orphan")
    client_instances: Mapped[List["ClientService"]] = relationship("ClientService", back_populates="service", cascade="all, delete-orphan")

    def serialize_service(self) -> dict:
        return {
            "id": self.id,
            "business_id": self.business_id,
            "name": self.name,
            "description": self.description,
            "price": str(self.price),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class Clients(db.Model):
    """Tabla de clientes del negocio"""
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(75), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(15), nullable=False)
    client_id_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    client_dni: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    business_id: Mapped[int] = mapped_column(ForeignKey("business.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    business: Mapped["Businesses"] = relationship("Businesses", back_populates="clients")
    services: Mapped[List["Services"]] = relationship("Services", secondary="client_service", back_populates="clients")
    notes: Mapped[List["Notes"]] = relationship("Notes", back_populates="client", cascade="all, delete-orphan")
    payments: Mapped[List["Payments"]] = relationship("Payments", back_populates="client", cascade="all, delete-orphan")
    appointments: Mapped[List["Appointments"]] = relationship("Appointments", back_populates="client", cascade="all, delete-orphan")
    service_history: Mapped[List["ServiceHistory"]] = relationship("ServiceHistory", back_populates="client", cascade="all, delete-orphan")
    service_instances: Mapped[List["ClientService"]] = relationship("ClientService", back_populates="client", cascade="all, delete-orphan")

    def serialize_client(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
            "client_id_number": self.client_id_number,
            "client_dni": self.client_dni,
            "email": self.email,
            "business_id": self.business_id,
            "is_active": self.is_active,
            "services": [service.serialize_service() for service in self.services] if self.services else [],
            "notes": [note.serialize_note() for note in self.notes] if self.notes else [],
            "payments": [payment.serialize_payment() for payment in self.payments] if self.payments else [],
            "appointments": [appointment.serialize_appointment() for appointment in self.appointments] if self.appointments else [],
            "service_history": [history.serialize_history() for history in self.service_history] if self.service_history else [],
            "service_instances": [instance.serialize() for instance in self.service_instances] if self.service_instances else [],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class Notes(db.Model):
    """Tabla de notas/observaciones sobre clientes"""
    __tablename__ = "note"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    client: Mapped["Clients"] = relationship("Clients", back_populates="notes")
    service_history: Mapped[List["ServiceHistory"]] = relationship("ServiceHistory", back_populates="note")

    def serialize_note(self) -> dict:
        return {
            "id": self.id,
            "client_id": self.client_id,
            "client_name": self.client.name if self.client else None,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class Payments(db.Model):
    """Tabla de pagos de clientes"""
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint('payments_made <= estimated_total', name='check_payments_valid'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    payment_method: Mapped[str] = mapped_column(Enum("cash", "card", name="payment_method_enum"), nullable=False)
    estimated_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payments_made: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    payment_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(Enum("pending", "paid", name="status_enum"), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    client: Mapped["Clients"] = relationship("Clients", back_populates="payments")

    def serialize_payment(self) -> dict:
        pending = max(0, self.estimated_total - self.payments_made)
        return {
            "id": self.id,
            "client_id": self.client_id,
            "payment_method": self.payment_method,
            "estimated_total": str(self.estimated_total),
            "payments_made": str(self.payments_made),
            "pending_payments": str(pending),
            "payment_date": self.payment_date.isoformat() if self.payment_date else None,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class Appointments(db.Model):
    """Tabla de citas/reservas"""
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("service.id"), nullable=False)
    business_id: Mapped[int] = mapped_column(ForeignKey("business.id"), nullable=False)
    date_time: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(Enum("pending", "confirmed", "cancelled", "completed", name="appointment_status"), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["Users"] = relationship("Users", back_populates="appointments")
    client: Mapped["Clients"] = relationship("Clients", back_populates="appointments")
    service: Mapped["Services"] = relationship("Services", back_populates="appointments")
    calendar: Mapped[Optional["Calendar"]] = relationship("Calendar", back_populates="appointment", uselist=False)
    service_history: Mapped[List["ServiceHistory"]] = relationship("ServiceHistory", back_populates="appointment", cascade="all, delete-orphan")
    business: Mapped["Businesses"] = relationship("Businesses", back_populates="appointments")

    def serialize_appointment(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.username if self.user else None,
            "client_id": self.client_id,
            "client_name": self.client.name if self.client else None,
            "client_email": self.client.email if self.client else None,
            "service_id": self.service_id,
            "service_name": self.service.name if self.service else None,
            "client_services": [service.serialize_service() for service in self.client.services] if self.client and self.client.services else [],
            "date_time": self.date_time.isoformat(),
            "status": self.status,
            "calendar": self.calendar.serialize_calendar() if self.calendar else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class Calendar(db.Model):
    """Tabla de eventos de calendario (integración con Google Calendar)"""
    __tablename__ = "calendar"

    id: Mapped[int] = mapped_column(primary_key=True)
    start_date_time: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    end_date_time: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id"), nullable=False, unique=True)
    google_event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_sync: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    business_id: Mapped[Optional[int]] = mapped_column(ForeignKey("business.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    appointment: Mapped["Appointments"] = relationship("Appointments", back_populates="calendar")
    business: Mapped[Optional["Businesses"]] = relationship("Businesses", back_populates="calendar_events")

    def serialize_calendar(self) -> dict:
        return {
            "id": self.id,
            "start_date_time": self.start_date_time.isoformat(),
            "end_date_time": self.end_date_time.isoformat(),
            "appointment_id": self.appointment_id,
            "google_event_id": self.google_event_id,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class ServiceHistory(db.Model):
    """Tabla de historial de servicios realizados"""
    __tablename__ = "service_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id"), nullable=False)
    note_id: Mapped[Optional[int]] = mapped_column(ForeignKey("note.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    client: Mapped["Clients"] = relationship("Clients", back_populates="service_history")
    appointment: Mapped["Appointments"] = relationship("Appointments", back_populates="service_history")
    note: Mapped[Optional["Notes"]] = relationship("Notes", back_populates="service_history")

    def serialize_history(self) -> dict:
        return {
            "id": self.id,
            "client_id": self.client_id,
            "client_name": self.client.name if self.client else None,
            "appointment_id": self.appointment_id,
            "appointment_info": {
                "date_time": self.appointment.date_time.isoformat() if self.appointment else None,
                "service": self.appointment.service.name if self.appointment and self.appointment.service else None,
                "status": self.appointment.status if self.appointment else None
            },
            "note_id": self.note_id,
            "note_description": self.note.description if self.note else None,
            "created_at": self.created_at.isoformat()
        }


class ClientService(db.Model):
    """Tabla de relación entre clientes y servicios completados"""
    __tablename__ = "client_service"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("service.id"), index=True)
    completed: Mapped[bool] = mapped_column(default=False)
    completed_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    client: Mapped["Clients"] = relationship("Clients", back_populates="service_instances", overlaps="services,clients")
    service: Mapped["Services"] = relationship("Services", back_populates="client_instances", overlaps="clients,services")

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "client_id": self.client_id,
            "service_id": self.service_id,
            "service_name": self.service.name if self.service else None,
            "service_price": str(self.service.price) if self.service else None,
            "service_description": self.service.description if self.service else None,
            "completed": self.completed,
            "completed_date": self.completed_date.isoformat() if self.completed_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }