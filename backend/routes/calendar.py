from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
from models import db, Calendar, Appointments, Businesses, Users, Admins
from datetime import datetime
import requests

# Crear el Blueprint
calendar_bp = Blueprint('calendar', __name__, url_prefix='/api/calendar')


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
# GET - Obtener todos los eventos de calendario (requiere autenticación)
# ============================================================================

@calendar_bp.route('', methods=['GET'])
@user_or_admin_required
def get_all_calendar_events():
    """
    Obtiene todos los eventos del calendario
    GET /api/calendar
    Headers: Authorization: Bearer {token}
    """
    try:
        events = Calendar.query.all()
        return jsonify([event.serialize_calendar() for event in events]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener eventos de calendario por negocio (requiere autenticación)
# ============================================================================

@calendar_bp.route('/business/<int:business_id>', methods=['GET'])
@user_or_admin_required
def get_calendar_events_by_business(business_id):
    """
    Obtiene todos los eventos del calendario de un negocio
    GET /api/calendar/business/1
    Headers: Authorization: Bearer {token}
    """
    try:
        business = Businesses.query.get(business_id)
        if not business:
            return jsonify({"error": "Negocio no encontrado"}), 404

        events = Calendar.query.filter_by(business_id=business_id).all()
        return jsonify([event.serialize_calendar() for event in events]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener evento de calendario por cita (requiere autenticación)
# ============================================================================

@calendar_bp.route('/appointment/<int:appointment_id>', methods=['GET'])
@user_or_admin_required
def get_calendar_event_by_appointment(appointment_id):
    """
    Obtiene el evento del calendario asociado a una cita
    GET /api/calendar/appointment/1
    Headers: Authorization: Bearer {token}
    """
    try:
        appointment = Appointments.query.get(appointment_id)
        if not appointment:
            return jsonify({"error": "Cita no encontrada"}), 404

        event = Calendar.query.filter_by(appointment_id=appointment_id).first()
        if not event:
            return jsonify({"error": "Evento de calendario no encontrado para esta cita"}), 404

        return jsonify(event.serialize_calendar()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener un evento de calendario por ID (requiere autenticación)
# ============================================================================

@calendar_bp.route('/<int:event_id>', methods=['GET'])
@user_or_admin_required
def get_calendar_event(event_id):
    """
    Obtiene un evento de calendario específico por ID
    GET /api/calendar/1
    Headers: Authorization: Bearer {token}
    """
    try:
        event = Calendar.query.get(event_id)
        if not event:
            return jsonify({"error": "Evento de calendario no encontrado"}), 404
        return jsonify(event.serialize_calendar()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# POST - Crear un evento de calendario (requiere autenticación)
# ============================================================================

@calendar_bp.route('', methods=['POST'])
@user_or_admin_required
def create_calendar_event():
    """
    Crea un nuevo evento de calendario
    POST /api/calendar
    Headers: Authorization: Bearer {token}
    Body: {
        "appointment_id": 1,
        "business_id": 1,
        "start_date_time": "2025-12-25T14:30:00",
        "end_date_time": "2025-12-25T15:30:00"
    }
    """
    try:
        data = request.json

        if not data:
            return jsonify({"error": "El body no puede estar vacío"}), 400

        required_fields = ['appointment_id', 'start_date_time', 'end_date_time']
        missing = [field for field in required_fields if field not in data]
        if missing:
            return jsonify({"error": f"Campos requeridos faltantes: {missing}"}), 400

        # Validar que la cita existe
        appointment = Appointments.query.get(data['appointment_id'])
        if not appointment:
            return jsonify({"error": "Cita no encontrada"}), 404

        # Validar que no exista ya un evento para esta cita
        existing_event = Calendar.query.filter_by(appointment_id=data['appointment_id']).first()
        if existing_event:
            return jsonify({"error": "Ya existe un evento de calendario para esta cita"}), 409

        # Validar fechas
        try:
            start_date_time = datetime.fromisoformat(data['start_date_time'])
            end_date_time = datetime.fromisoformat(data['end_date_time'])
        except:
            return jsonify({"error": "Formato de fecha inválido. Usa: YYYY-MM-DDTHH:MM:SS"}), 400

        if start_date_time >= end_date_time:
            return jsonify({"error": "La fecha de inicio debe ser anterior a la de fin"}), 400

        nuevo_event = Calendar(
            appointment_id=data['appointment_id'],
            business_id=data.get('business_id', appointment.business_id),
            start_date_time=start_date_time,
            end_date_time=end_date_time,
            google_event_id=data.get('google_event_id'),
            last_sync=datetime.now() if data.get('google_event_id') else None
        )

        db.session.add(nuevo_event)
        db.session.commit()

        return jsonify(nuevo_event.serialize_calendar()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PUT - Actualizar un evento de calendario (requiere autenticación)
# ============================================================================

@calendar_bp.route('/<int:event_id>', methods=['PUT'])
@user_or_admin_required
def update_calendar_event(event_id):
    """
    Actualiza un evento de calendario
    PUT /api/calendar/1
    Headers: Authorization: Bearer {token}
    Body: {
        "start_date_time": "2025-12-25T15:00:00",
        "end_date_time": "2025-12-25T16:00:00"
    }
    """
    try:
        event = Calendar.query.get(event_id)
        if not event:
            return jsonify({"error": "Evento de calendario no encontrado"}), 404

        data = request.json
        if not data:
            return jsonify({"error": "El body no puede estar vacío"}), 400

        # Actualizar fechas
        if 'start_date_time' in data or 'end_date_time' in data:
            start = data.get('start_date_time', event.start_date_time.isoformat())
            end = data.get('end_date_time', event.end_date_time.isoformat())

            try:
                start_date_time = datetime.fromisoformat(start) if isinstance(start, str) else start
                end_date_time = datetime.fromisoformat(end) if isinstance(end, str) else end
            except:
                return jsonify({"error": "Formato de fecha inválido. Usa: YYYY-MM-DDTHH:MM:SS"}), 400

            if start_date_time >= end_date_time:
                return jsonify({"error": "La fecha de inicio debe ser anterior a la de fin"}), 400

            event.start_date_time = start_date_time
            event.end_date_time = end_date_time

        # Actualizar Google Event ID
        if 'google_event_id' in data:
            event.google_event_id = data['google_event_id']
            event.last_sync = datetime.now()

        db.session.commit()
        return jsonify(event.serialize_calendar()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# DELETE - Eliminar un evento de calendario (requiere autenticación)
# ============================================================================

@calendar_bp.route('/<int:event_id>', methods=['DELETE'])
@user_or_admin_required
def delete_calendar_event(event_id):
    """
    Elimina un evento de calendario
    DELETE /api/calendar/1
    Headers: Authorization: Bearer {token}
    """
    try:
        event = Calendar.query.get(event_id)
        if not event:
            return jsonify({"error": "Evento de calendario no encontrado"}), 404

        db.session.delete(event)
        db.session.commit()

        return jsonify({"message": "Evento de calendario eliminado correctamente"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# POST - Sincronizar evento con Google Calendar (requiere autenticación)
# ============================================================================

@calendar_bp.route('/<int:event_id>/sync-google', methods=['POST'])
@user_or_admin_required
def sync_event_with_google(event_id):
    """
    Sincroniza un evento con Google Calendar
    POST /api/calendar/1/sync-google
    Headers: Authorization: Bearer {token}
    Body: {
        "access_token": "google_access_token",
        "calendar_id": "calendar_id@gmail.com"
    }
    
    Nota: Requiere credenciales de Google OAuth2
    """
    try:
        event = Calendar.query.get(event_id)
        if not event:
            return jsonify({"error": "Evento de calendario no encontrado"}), 404

        data = request.json
        if not data or 'access_token' not in data:
            return jsonify({"error": "access_token es requerido"}), 400

        access_token = data['access_token']
        calendar_id = data.get('calendar_id', 'primary')

        # Preparar datos del evento para Google Calendar
        google_event = {
            "summary": f"Cita - {event.appointment.client.name}",
            "description": f"Servicio: {event.appointment.service.name}\nCliente: {event.appointment.client.name}",
            "start": {
                "dateTime": event.start_date_time.isoformat(),
                "timeZone": "America/Caracas"
            },
            "end": {
                "dateTime": event.end_date_time.isoformat(),
                "timeZone": "America/Caracas"
            }
        }

        # Si ya existe Google Event ID, actualizar
        if event.google_event_id:
            url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event.google_event_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            response = requests.put(url, json=google_event, headers=headers)
            
            if response.status_code != 200:
                return jsonify({"error": f"Error actualizando en Google Calendar: {response.text}"}), 400
            
            result = response.json()
            event.last_sync = datetime.now()
            db.session.commit()

            return jsonify({
                "message": "Evento sincronizado con Google Calendar",
                "google_event_id": result.get('id'),
                "google_event_url": result.get('htmlLink'),
                "calendar_event": event.serialize_calendar()
            }), 200

        else:
            # Crear nuevo evento en Google Calendar
            url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            response = requests.post(url, json=google_event, headers=headers)

            if response.status_code != 200:
                return jsonify({"error": f"Error creando en Google Calendar: {response.text}"}), 400

            result = response.json()
            event.google_event_id = result.get('id')
            event.last_sync = datetime.now()
            db.session.commit()

            return jsonify({
                "message": "Evento creado y sincronizado con Google Calendar",
                "google_event_id": result.get('id'),
                "google_event_url": result.get('htmlLink'),
                "calendar_event": event.serialize_calendar()
            }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener eventos por rango de fechas (requiere autenticación)
# ============================================================================

@calendar_bp.route('/filter/date-range', methods=['GET'])
@user_or_admin_required
def filter_calendar_events_by_date():
    """
    Filtra eventos de calendario por rango de fechas
    GET /api/calendar/filter/date-range?start=2025-12-20&end=2025-12-31
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

        events = Calendar.query.filter(
            Calendar.start_date_time >= start_date,
            Calendar.end_date_time <= end_date
        ).all()

        return jsonify([event.serialize_calendar() for event in events]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener eventos sincronizados (requiere autenticación)
# ============================================================================

@calendar_bp.route('/synced', methods=['GET'])
@user_or_admin_required
def get_synced_events():
    """
    Obtiene todos los eventos sincronizados con Google Calendar
    GET /api/calendar/synced
    Headers: Authorization: Bearer {token}
    """
    try:
        events = Calendar.query.filter(Calendar.google_event_id.isnot(None)).all()
        return jsonify([event.serialize_calendar() for event in events]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Estadísticas de calendario (requiere autenticación admin)
# ============================================================================

@calendar_bp.route('/stats', methods=['GET'])
@admin_required
def get_calendar_stats():
    """
    Obtiene estadísticas del calendario
    GET /api/calendar/stats
    Headers: Authorization: Bearer {token}
    """
    try:
        all_events = Calendar.query.all()
        synced_events = Calendar.query.filter(Calendar.google_event_id.isnot(None)).all()

        stats = {
            "total_events": len(all_events),
            "synced_events": len(synced_events),
            "unsync_events": len(all_events) - len(synced_events),
            "sync_percentage": round(
                (len(synced_events) / len(all_events) * 100) if all_events else 0,
                2
            ),
            "last_sync": max(
                (e.last_sync.isoformat() for e in synced_events if e.last_sync),
                default=None
            )
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Estadísticas de calendario por negocio (requiere autenticación)
# ============================================================================

@calendar_bp.route('/business/<int:business_id>/stats', methods=['GET'])
@user_or_admin_required
def get_business_calendar_stats(business_id):
    """
    Obtiene estadísticas del calendario de un negocio
    GET /api/calendar/business/1/stats
    Headers: Authorization: Bearer {token}
    """
    try:
        business = Businesses.query.get(business_id)
        if not business:
            return jsonify({"error": "Negocio no encontrado"}), 404

        all_events = Calendar.query.filter_by(business_id=business_id).all()
        synced_events = Calendar.query.filter_by(business_id=business_id).filter(
            Calendar.google_event_id.isnot(None)
        ).all()

        stats = {
            "business_id": business_id,
            "business_name": business.business_name,
            "total_events": len(all_events),
            "synced_events": len(synced_events),
            "unsync_events": len(all_events) - len(synced_events),
            "sync_percentage": round(
                (len(synced_events) / len(all_events) * 100) if all_events else 0,
                2
            )
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500