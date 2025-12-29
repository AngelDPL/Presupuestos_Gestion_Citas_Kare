from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
from models import db, ClientService, Clients, Services, Businesses, Users, Admins
from datetime import datetime

# Crear el Blueprint
client_services_bp = Blueprint('client_services_api', __name__, url_prefix='/api/client-services')


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
# GET - Obtener todos los servicios de clientes (requiere autenticación)
# ============================================================================

@client_services_bp.route('', methods=['GET'])
@user_or_admin_required
def get_all_client_services():
    """
    Obtiene todos los servicios de clientes
    GET /api/client-services
    Headers: Authorization: Bearer {token}
    """
    try:
        client_services = ClientService.query.all()
        return jsonify([cs.serialize() for cs in client_services]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener servicios de un cliente específico (requiere autenticación)
# ============================================================================

@client_services_bp.route('/client/<int:client_id>', methods=['GET'])
@user_or_admin_required
def get_client_services(client_id):
    """
    Obtiene todos los servicios de un cliente específico
    GET /api/client-services/client/1
    Headers: Authorization: Bearer {token}
    """
    try:
        client = Clients.query.get(client_id)
        if not client:
            return jsonify({"error": "Cliente no encontrado"}), 404

        client_services = ClientService.query.filter_by(client_id=client_id).all()
        return jsonify([cs.serialize() for cs in client_services]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener servicios completados de un cliente (requiere autenticación)
# ============================================================================

@client_services_bp.route('/client/<int:client_id>/completed', methods=['GET'])
@user_or_admin_required
def get_client_completed_services(client_id):
    """
    Obtiene solo los servicios completados de un cliente
    GET /api/client-services/client/1/completed
    Headers: Authorization: Bearer {token}
    """
    try:
        client = Clients.query.get(client_id)
        if not client:
            return jsonify({"error": "Cliente no encontrado"}), 404

        client_services = ClientService.query.filter_by(
            client_id=client_id,
            completed=True
        ).all()
        return jsonify([cs.serialize() for cs in client_services]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener servicios pendientes de un cliente (requiere autenticación)
# ============================================================================

@client_services_bp.route('/client/<int:client_id>/pending', methods=['GET'])
@user_or_admin_required
def get_client_pending_services(client_id):
    """
    Obtiene solo los servicios pendientes de un cliente
    GET /api/client-services/client/1/pending
    Headers: Authorization: Bearer {token}
    """
    try:
        client = Clients.query.get(client_id)
        if not client:
            return jsonify({"error": "Cliente no encontrado"}), 404

        client_services = ClientService.query.filter_by(
            client_id=client_id,
            completed=False
        ).all()
        return jsonify([cs.serialize() for cs in client_services]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener un servicio de cliente por ID (requiere autenticación)
# ============================================================================

@client_services_bp.route('/<int:client_service_id>', methods=['GET'])
@user_or_admin_required
def get_client_service(client_service_id):
    """
    Obtiene un servicio de cliente específico por ID
    GET /api/client-services/1
    Headers: Authorization: Bearer {token}
    """
    try:
        client_service = ClientService.query.get(client_service_id)
        if not client_service:
            return jsonify({"error": "Servicio de cliente no encontrado"}), 404
        return jsonify(client_service.serialize()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# POST - Crear un nuevo servicio para un cliente (requiere autenticación)
# ============================================================================

@client_services_bp.route('', methods=['POST'])
@user_or_admin_required
def create_client_service():
    """
    Crea un nuevo servicio para un cliente
    POST /api/client-services
    Headers: Authorization: Bearer {token}
    Body: {
        "client_id": 1,
        "service_id": 1
    }
    """
    try:
        data = request.json

        if not data:
            return jsonify({"error": "El body no puede estar vacío"}), 400

        required_fields = ['client_id', 'service_id']
        missing = [field for field in required_fields if field not in data]
        if missing:
            return jsonify({"error": f"Campos requeridos faltantes: {missing}"}), 400

        # Validar que el cliente existe
        client = Clients.query.get(data['client_id'])
        if not client or not client.is_active:
            return jsonify({"error": "Cliente no encontrado o inactivo"}), 404

        # Validar que el servicio existe
        service = Services.query.get(data['service_id'])
        if not service or not service.is_active:
            return jsonify({"error": "Servicio no encontrado o inactivo"}), 404

        # Verificar que no exista ya esta combinación
        existing = ClientService.query.filter_by(
            client_id=data['client_id'],
            service_id=data['service_id'],
            completed=False
        ).first()

        if existing:
            return jsonify({"error": "Este cliente ya tiene este servicio pendiente"}), 409

        nuevo_client_service = ClientService(
            client_id=data['client_id'],
            service_id=data['service_id'],
            completed=False
        )

        db.session.add(nuevo_client_service)
        db.session.commit()

        return jsonify(nuevo_client_service.serialize()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PUT - Marcar servicio como completado (requiere autenticación)
# ============================================================================

@client_services_bp.route('/<int:client_service_id>/complete', methods=['PUT'])
@user_or_admin_required
def complete_client_service(client_service_id):
    """
    Marca un servicio de cliente como completado
    PUT /api/client-services/1/complete
    Headers: Authorization: Bearer {token}
    Body: {
        "completed_date": "2025-12-23"
    }
    """
    try:
        client_service = ClientService.query.get(client_service_id)
        if not client_service:
            return jsonify({"error": "Servicio de cliente no encontrado"}), 404

        data = request.json if request.json else {}

        # Marcar como completado
        client_service.completed = True

        # Actualizar fecha de completación
        if 'completed_date' in data:
            try:
                client_service.completed_date = datetime.fromisoformat(data['completed_date'])
            except:
                return jsonify({"error": "Formato de fecha inválido. Usa: YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS"}), 400
        else:
            # Si no viene fecha, usa la actual
            client_service.completed_date = datetime.now()

        db.session.commit()

        return jsonify({
            "message": "Servicio marcado como completado",
            "client_service": client_service.serialize()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PUT - Marcar servicio como pendiente (requiere autenticación)
# ============================================================================

@client_services_bp.route('/<int:client_service_id>/pending', methods=['PUT'])
@user_or_admin_required
def mark_pending_client_service(client_service_id):
    """
    Marca un servicio de cliente como pendiente (deshacer completado)
    PUT /api/client-services/1/pending
    Headers: Authorization: Bearer {token}
    """
    try:
        client_service = ClientService.query.get(client_service_id)
        if not client_service:
            return jsonify({"error": "Servicio de cliente no encontrado"}), 404

        client_service.completed = False
        client_service.completed_date = None

        db.session.commit()

        return jsonify({
            "message": "Servicio marcado como pendiente",
            "client_service": client_service.serialize()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# DELETE - Eliminar un servicio de cliente (requiere autenticación)
# ============================================================================

@client_services_bp.route('/<int:client_service_id>', methods=['DELETE'])
@user_or_admin_required
def delete_client_service(client_service_id):
    """
    Elimina un servicio de cliente
    DELETE /api/client-services/1
    Headers: Authorization: Bearer {token}
    """
    try:
        client_service = ClientService.query.get(client_service_id)
        if not client_service:
            return jsonify({"error": "Servicio de cliente no encontrado"}), 404

        db.session.delete(client_service)
        db.session.commit()

        return jsonify({"message": "Servicio de cliente eliminado correctamente"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Servicios por servicio (requiere autenticación admin)
# ============================================================================

@client_services_bp.route('/service/<int:service_id>', methods=['GET'])
@user_or_admin_required
def get_clients_by_service(service_id):
    """
    Obtiene todos los clientes que han contratado un servicio específico
    GET /api/client-services/service/1
    Headers: Authorization: Bearer {token}
    """
    try:
        service = Services.query.get(service_id)
        if not service:
            return jsonify({"error": "Servicio no encontrado"}), 404

        client_services = ClientService.query.filter_by(service_id=service_id).all()
        return jsonify([cs.serialize() for cs in client_services]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Estadísticas de servicios de un cliente (requiere autenticación)
# ============================================================================

@client_services_bp.route('/client/<int:client_id>/stats', methods=['GET'])
@user_or_admin_required
def get_client_services_stats(client_id):
    """
    Obtiene estadísticas de servicios de un cliente
    GET /api/client-services/client/1/stats
    Headers: Authorization: Bearer {token}
    """
    try:
        client = Clients.query.get(client_id)
        if not client:
            return jsonify({"error": "Cliente no encontrado"}), 404

        all_services = ClientService.query.filter_by(client_id=client_id).all()
        completed_services = ClientService.query.filter_by(client_id=client_id, completed=True).all()

        stats = {
            "client_id": client_id,
            "client_name": client.name,
            "total_services": len(all_services),
            "completed_services": len(completed_services),
            "pending_services": len(all_services) - len(completed_services),
            "completion_rate": round(
                (len(completed_services) / len(all_services) * 100) if all_services else 0,
                2
            ),
            "services": [cs.serialize() for cs in all_services]
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Estadísticas globales de ClientService (requiere autenticación admin)
# ============================================================================

@client_services_bp.route('/stats', methods=['GET'])
@admin_required
def get_global_client_services_stats():
    """
    Obtiene estadísticas globales de ClientService
    GET /api/client-services/stats
    Headers: Authorization: Bearer {token}
    """
    try:
        all_client_services = ClientService.query.all()
        completed = ClientService.query.filter_by(completed=True).all()

        if not all_client_services:
            return jsonify({
                "total_services": 0,
                "completed": 0,
                "pending": 0,
                "completion_rate": 0.0,
                "unique_clients": 0,
                "unique_services": 0
            }), 200

        unique_clients = len(set(cs.client_id for cs in all_client_services))
        unique_services = len(set(cs.service_id for cs in all_client_services))

        stats = {
            "total_services": len(all_client_services),
            "completed": len(completed),
            "pending": len(all_client_services) - len(completed),
            "completion_rate": round(
                (len(completed) / len(all_client_services) * 100) if all_client_services else 0,
                2
            ),
            "unique_clients": unique_clients,
            "unique_services": unique_services,
            "average_services_per_client": round(
                len(all_client_services) / unique_clients if unique_clients > 0 else 0,
                2
            )
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Estadísticas de un servicio (requiere autenticación)
# ============================================================================

@client_services_bp.route('/service/<int:service_id>/stats', methods=['GET'])
@user_or_admin_required
def get_service_stats(service_id):
    """
    Obtiene estadísticas de cuántos clientes han usado un servicio
    GET /api/client-services/service/1/stats
    Headers: Authorization: Bearer {token}
    """
    try:
        service = Services.query.get(service_id)
        if not service:
            return jsonify({"error": "Servicio no encontrado"}), 404

        all_records = ClientService.query.filter_by(service_id=service_id).all()
        completed = ClientService.query.filter_by(service_id=service_id, completed=True).all()

        stats = {
            "service_id": service_id,
            "service_name": service.name,
            "service_price": str(service.price),
            "total_clients": len(all_records),
            "completed_times": len(completed),
            "pending_times": len(all_records) - len(completed),
            "completion_rate": round(
                (len(completed) / len(all_records) * 100) if all_records else 0,
                2
            ),
            "total_revenue": str(service.price * len(completed))
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500