from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
from models import db, Appointments, Users, Clients, Services, Businesses, Admins
from datetime import datetime, timedelta

# Crear el Blueprint
appointments_bp = Blueprint('appointments', __name__, url_prefix='/api/appointments')


# ============================================================================
# DECORADOR PERSONALIZADO - Verificar que es Admin
# ============================================================================

def admin_required(fn):
    """Decorador que verifica que el usuario sea un Admin"""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        try:
            current_user_id = get_jwt_identity()
            admin = Admins.query.get(int(current_user_id))
            
            if not admin or not admin.is_active:
                return jsonify({"error": "Acceso denegado: privilegios de administrador requeridos"}), 403
            
            return fn(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": f"Error de autenticación: {str(e)}"}), 401
    return wrapper


def user_or_admin_required(fn):
    """Decorador que verifica que sea un User o Admin"""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        try:
            current_user_id = get_jwt_identity()
            user_id = int(current_user_id)
            
            # Verificar si es admin
            admin = Admins.query.get(user_id)
            if admin and admin.is_active:
                return fn(*args, **kwargs)
            
            # Verificar si es usuario
            user = Users.query.get(user_id)
            if user and user.is_active:
                return fn(*args, **kwargs)
            
            return jsonify({"error": "Acceso denegado: autenticación requerida"}), 403
        except Exception as e:
            return jsonify({"error": f"Error de autenticación: {str(e)}"}), 401
    return wrapper


# ============================================================================
# GET - Obtener todas las citas (requiere autenticación)
# ============================================================================

@appointments_bp.route('', methods=['GET'])
@user_or_admin_required
def get_all_appointments():
    """
    Obtiene todas las citas
    GET /api/appointments
    Headers: Authorization: Bearer {token}
    """
    try:
        appointments = Appointments.query.all()
        return jsonify([appt.serialize_appointment() for appt in appointments]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener citas por negocio (requiere autenticación)
# ============================================================================

@appointments_bp.route('/business/<int:business_id>', methods=['GET'])
@user_or_admin_required
def get_appointments_by_business(business_id):
    """
    Obtiene todas las citas de un negocio
    GET /api/appointments/business/1
    Headers: Authorization: Bearer {token}
    """
    try:
        business = Businesses.query.get(business_id)
        if not business:
            return jsonify({"error": "Negocio no encontrado"}), 404

        appointments = Appointments.query.filter_by(business_id=business_id).all()
        return jsonify([appt.serialize_appointment() for appt in appointments]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener citas por usuario/empleado (requiere autenticación)
# ============================================================================

@appointments_bp.route('/user/<int:user_id>', methods=['GET'])
@user_or_admin_required
def get_appointments_by_user(user_id):
    """
    Obtiene todas las citas de un usuario/empleado
    GET /api/appointments/user/1
    Headers: Authorization: Bearer {token}
    """
    try:
        user = Users.query.get(user_id)
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        appointments = Appointments.query.filter_by(user_id=user_id).all()
        return jsonify([appt.serialize_appointment() for appt in appointments]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener citas por cliente (requiere autenticación)
# ============================================================================

@appointments_bp.route('/client/<int:client_id>', methods=['GET'])
@user_or_admin_required
def get_appointments_by_client(client_id):
    """
    Obtiene todas las citas de un cliente
    GET /api/appointments/client/1
    Headers: Authorization: Bearer {token}
    """
    try:
        client = Clients.query.get(client_id)
        if not client:
            return jsonify({"error": "Cliente no encontrado"}), 404

        appointments = Appointments.query.filter_by(client_id=client_id).all()
        return jsonify([appt.serialize_appointment() for appt in appointments]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener una cita por ID (requiere autenticación)
# ============================================================================

@appointments_bp.route('/<int:appointment_id>', methods=['GET'])
@user_or_admin_required
def get_appointment(appointment_id):
    """
    Obtiene una cita específica por ID
    GET /api/appointments/1
    Headers: Authorization: Bearer {token}
    """
    try:
        appointment = Appointments.query.get(appointment_id)
        if not appointment:
            return jsonify({"error": "Cita no encontrada"}), 404
        return jsonify(appointment.serialize_appointment()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# POST - Crear una nueva cita (requiere autenticación)
# ============================================================================

@appointments_bp.route('', methods=['POST'])
@user_or_admin_required
def create_appointment():
    """
    Crea una nueva cita Y automáticamente crea el evento en el calendario
    POST /api/appointments
    Headers: Authorization: Bearer {token}
    Body (opción 1 - con IDs):
    {
        "user_id": 1,
        "client_id": 1,
        "service_id": 1,
        "business_id": 1,
        "date_time": "2025-12-25T14:30:00"
    }
    
    Body (opción 2 - con nombres):
    {
        "user_name": "Juan Pérez",
        "client_name": "María López",
        "service_name": "Corte de cabello",
        "business_id": 1,
        "date_time": "2025-12-25T14:30:00"
    }
    
    Body (opción 3 - mixto):
    {
        "user_id": 1,
        "client_name": "María López",
        "service_id": 1,
        "business_id": 1,
        "date_time": "2025-12-25T14:30:00"
    }
    """
    try:
        from models import Calendar
        
        data = request.json

        if not data:
            return jsonify({"error": "El body no puede estar vacío"}), 400

        # Validar que business_id y date_time siempre estén presentes
        if 'business_id' not in data or 'date_time' not in data:
            return jsonify({"error": "business_id y date_time son requeridos"}), 400

        # ============================================================
        # RESOLVER USER (por ID o por nombre)
        # ============================================================
        user = None
        if 'user_id' in data:
            user = Users.query.get(data['user_id'])
            if not user:
                return jsonify({"error": "Usuario (ID) no encontrado"}), 404
        elif 'user_name' in data:
            user = Users.query.filter_by(username=data['user_name']).first()
            if not user:
                return jsonify({"error": f"Usuario '{data['user_name']}' no encontrado"}), 404
        else:
            return jsonify({"error": "Debes proporcionar user_id o user_name"}), 400

        if not user.is_active:
            return jsonify({"error": "Usuario inactivo"}), 400

        # ============================================================
        # RESOLVER CLIENT (por ID o por nombre)
        # ============================================================
        client = None
        if 'client_id' in data:
            client = Clients.query.get(data['client_id'])
            if not client:
                return jsonify({"error": "Cliente (ID) no encontrado"}), 404
        elif 'client_name' in data:
            client = Clients.query.filter_by(name=data['client_name']).first()
            if not client:
                return jsonify({"error": f"Cliente '{data['client_name']}' no encontrado"}), 404
        else:
            return jsonify({"error": "Debes proporcionar client_id o client_name"}), 400

        if not client.is_active:
            return jsonify({"error": "Cliente inactivo"}), 400

        # ============================================================
        # RESOLVER SERVICE (por ID o por nombre)
        # ============================================================
        service = None
        if 'service_id' in data:
            service = Services.query.get(data['service_id'])
            if not service:
                return jsonify({"error": "Servicio (ID) no encontrado"}), 404
        elif 'service_name' in data:
            service = Services.query.filter_by(name=data['service_name']).first()
            if not service:
                return jsonify({"error": f"Servicio '{data['service_name']}' no encontrado"}), 404
        else:
            return jsonify({"error": "Debes proporcionar service_id o service_name"}), 400

        if not service.is_active:
            return jsonify({"error": "Servicio inactivo"}), 400

        # ============================================================
        # VALIDAR NEGOCIO
        # ============================================================
        business = Businesses.query.get(data['business_id'])
        if not business or not business.is_active:
            return jsonify({"error": "Negocio no encontrado o inactivo"}), 404

        # ============================================================
        # VALIDAR FECHA Y HORA
        # ============================================================
        try:
            date_time = datetime.fromisoformat(data['date_time'])
        except:
            return jsonify({"error": "Formato de fecha inválido. Usa: YYYY-MM-DDTHH:MM:SS"}), 400

        if date_time <= datetime.now():
            return jsonify({"error": "La cita debe ser en el futuro"}), 400

        # ============================================================
        # VERIFICAR CONFLICTO DE HORARIOS PARA EL USUARIO
        # ============================================================
        conflicting = Appointments.query.filter(
            Appointments.user_id == user.id,
            Appointments.date_time == date_time,
            Appointments.status.in_(['pending', 'confirmed'])
        ).first()

        if conflicting:
            return jsonify({"error": "El usuario ya tiene una cita en ese horario"}), 409

        # ============================================================
        # CREAR LA CITA
        # ============================================================
        nueva_appointment = Appointments(
            user_id=user.id,
            client_id=client.id,
            service_id=service.id,
            business_id=data['business_id'],
            date_time=date_time,
            status=data.get('status', 'pending')
        )

        db.session.add(nueva_appointment)
        db.session.flush()  # Obtener el ID sin hacer commit

        # ============================================================
        # CREAR AUTOMÁTICAMENTE EL EVENTO EN CALENDAR
        # ============================================================
        # Calcular duración del evento (1 hora por defecto)
        event_duration_hours = data.get('duration_hours', 1)
        end_date_time = date_time.replace(hour=date_time.hour + event_duration_hours)

        nuevo_calendar_event = Calendar(
            appointment_id=nueva_appointment.id,
            business_id=data['business_id'],
            start_date_time=date_time,
            end_date_time=end_date_time
        )

        db.session.add(nuevo_calendar_event)
        db.session.commit()

        return jsonify({
            "message": "Cita creada y evento de calendario generado automáticamente",
            "appointment": nueva_appointment.serialize_appointment(),
            "calendar_event": nuevo_calendar_event.serialize_calendar()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PUT - Actualizar una cita (requiere autenticación)
# ============================================================================

@appointments_bp.route('/<int:appointment_id>', methods=['PUT'])
@user_or_admin_required
def update_appointment(appointment_id):
    """
    Actualiza una cita
    PUT /api/appointments/1
    Headers: Authorization: Bearer {token}
    Body: {
        "date_time": "2025-12-25T15:00:00",
        "status": "confirmed"
    }
    """
    try:
        appointment = Appointments.query.get(appointment_id)
        if not appointment:
            return jsonify({"error": "Cita no encontrada"}), 404

        data = request.json
        if not data:
            return jsonify({"error": "El body no puede estar vacío"}), 400

        # Actualizar fecha y hora
        if 'date_time' in data:
            try:
                date_time = datetime.fromisoformat(data['date_time'])
            except:
                return jsonify({"error": "Formato de fecha inválido. Usa: YYYY-MM-DDTHH:MM:SS"}), 400

            if date_time <= datetime.now():
                return jsonify({"error": "La cita debe ser en el futuro"}), 400

            appointment.date_time = date_time

        # Actualizar estado
        if 'status' in data:
            valid_statuses = ['pending', 'confirmed', 'cancelled', 'completed']
            if data['status'] not in valid_statuses:
                return jsonify({"error": f"Estado inválido. Debe ser: {valid_statuses}"}), 400
            appointment.status = data['status']

        db.session.commit()
        return jsonify(appointment.serialize_appointment()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# DELETE - Cancelar una cita (requiere autenticación)
# ============================================================================

@appointments_bp.route('/<int:appointment_id>', methods=['DELETE'])
@user_or_admin_required
def delete_appointment(appointment_id):
    """
    Cancela una cita
    DELETE /api/appointments/1
    Headers: Authorization: Bearer {token}
    """
    try:
        appointment = Appointments.query.get(appointment_id)
        if not appointment:
            return jsonify({"error": "Cita no encontrada"}), 404

        appointment.status = 'cancelled'
        db.session.commit()

        return jsonify({"message": "Cita cancelada correctamente"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener citas por fecha (requiere autenticación)
# ============================================================================

@appointments_bp.route('/filter/date', methods=['GET'])
@user_or_admin_required
def filter_appointments_by_date():
    """
    Filtra citas por fecha
    GET /api/appointments/filter/date?date=2025-12-25
    Headers: Authorization: Bearer {token}
    """
    try:
        date_str = request.args.get('date')
        
        if not date_str:
            return jsonify({"error": "El parámetro 'date' es requerido"}), 400

        try:
            date = datetime.fromisoformat(date_str).date()
        except:
            return jsonify({"error": "Formato de fecha inválido. Usa: YYYY-MM-DD"}), 400

        appointments = Appointments.query.filter(
            db.func.date(Appointments.date_time) == date
        ).all()

        return jsonify([appt.serialize_appointment() for appt in appointments]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener citas por rango de fechas (requiere autenticación)
# ============================================================================

@appointments_bp.route('/filter/date-range', methods=['GET'])
@user_or_admin_required
def filter_appointments_by_date_range():
    """
    Filtra citas por rango de fechas
    GET /api/appointments/filter/date-range?start=2025-12-20&end=2025-12-31
    Headers: Authorization: Bearer {token}
    """
    try:
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        if not start_str or not end_str:
            return jsonify({"error": "Los parámetros 'start' y 'end' son requeridos"}), 400

        try:
            start_date = datetime.fromisoformat(start_str)
            end_date = datetime.fromisoformat(end_str)
        except:
            return jsonify({"error": "Formato de fecha inválido. Usa: YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS"}), 400

        if start_date > end_date:
            return jsonify({"error": "La fecha de inicio no puede ser mayor que la de fin"}), 400

        appointments = Appointments.query.filter(
            Appointments.date_time >= start_date,
            Appointments.date_time <= end_date
        ).all()

        return jsonify([appt.serialize_appointment() for appt in appointments]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener citas por estado (requiere autenticación)
# ============================================================================

@appointments_bp.route('/filter/status', methods=['GET'])
@user_or_admin_required
def filter_appointments_by_status():
    """
    Filtra citas por estado
    GET /api/appointments/filter/status?status=pending
    Headers: Authorization: Bearer {token}
    """
    try:
        status = request.args.get('status')
        
        if not status:
            return jsonify({"error": "El parámetro 'status' es requerido"}), 400

        valid_statuses = ['pending', 'confirmed', 'cancelled', 'completed']
        if status not in valid_statuses:
            return jsonify({"error": f"Estado inválido. Debe ser: {valid_statuses}"}), 400

        appointments = Appointments.query.filter_by(status=status).all()

        return jsonify([appt.serialize_appointment() for appt in appointments]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener citas próximas (requiere autenticación)
# ============================================================================

@appointments_bp.route('/upcoming', methods=['GET'])
@user_or_admin_required
def get_upcoming_appointments():
    """
    Obtiene las próximas citas (próximos 7 días por defecto)
    GET /api/appointments/upcoming?days=7
    Headers: Authorization: Bearer {token}
    """
    try:
        days = request.args.get('days', default=7, type=int)
        
        if days < 1:
            return jsonify({"error": "El parámetro 'days' debe ser mayor a 0"}), 400

        now = datetime.now()
        future_date = now + timedelta(days=days)

        appointments = Appointments.query.filter(
            Appointments.date_time >= now,
            Appointments.date_time <= future_date,
            Appointments.status.in_(['pending', 'confirmed'])
        ).order_by(Appointments.date_time.asc()).all()

        return jsonify([appt.serialize_appointment() for appt in appointments]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Estadísticas de citas (requiere autenticación admin)
# ============================================================================

@appointments_bp.route('/stats', methods=['GET'])
@admin_required
def get_appointments_stats():
    """
    Obtiene estadísticas generales de citas
    GET /api/appointments/stats
    Headers: Authorization: Bearer {token}
    """
    try:
        all_appointments = Appointments.query.all()
        
        stats = {
            "total_appointments": len(all_appointments),
            "pending": sum(1 for a in all_appointments if a.status == 'pending'),
            "confirmed": sum(1 for a in all_appointments if a.status == 'confirmed'),
            "completed": sum(1 for a in all_appointments if a.status == 'completed'),
            "cancelled": sum(1 for a in all_appointments if a.status == 'cancelled'),
            "completion_rate": round(
                (sum(1 for a in all_appointments if a.status == 'completed') / len(all_appointments) * 100)
                if all_appointments else 0,
                2
            )
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Estadísticas de citas por negocio (requiere autenticación)
# ============================================================================

@appointments_bp.route('/business/<int:business_id>/stats', methods=['GET'])
@user_or_admin_required
def get_business_appointments_stats(business_id):
    """
    Obtiene estadísticas de citas de un negocio
    GET /api/appointments/business/1/stats
    Headers: Authorization: Bearer {token}
    """
    try:
        business = Businesses.query.get(business_id)
        if not business:
            return jsonify({"error": "Negocio no encontrado"}), 404

        appointments = Appointments.query.filter_by(business_id=business_id).all()

        stats = {
            "business_id": business_id,
            "business_name": business.business_name,
            "total_appointments": len(appointments),
            "pending": sum(1 for a in appointments if a.status == 'pending'),
            "confirmed": sum(1 for a in appointments if a.status == 'confirmed'),
            "completed": sum(1 for a in appointments if a.status == 'completed'),
            "cancelled": sum(1 for a in appointments if a.status == 'cancelled'),
            "completion_rate": round(
                (sum(1 for a in appointments if a.status == 'completed') / len(appointments) * 100)
                if appointments else 0,
                2
            )
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500