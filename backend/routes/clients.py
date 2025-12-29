from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
from models import db, Clients, Businesses, Users, Admins

# Crear el Blueprint
clients_bp = Blueprint('clients_api', __name__, url_prefix='/api/clients')


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
# GET - Obtener todos los clientes (requiere autenticación)
# ============================================================================

@clients_bp.route('', methods=['GET'])
@user_or_admin_required
def get_all_clients():
    """
    Obtiene todos los clientes activos
    GET /api/clients
    Headers: Authorization: Bearer {token}
    """
    try:
        clients = Clients.query.filter_by(is_active=True).all()
        return jsonify([client.serialize_client() for client in clients]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener clientes por negocio (requiere autenticación)
# ============================================================================

@clients_bp.route('/business/<int:business_id>', methods=['GET'])
@user_or_admin_required
def get_clients_by_business(business_id):
    """
    Obtiene todos los clientes de un negocio específico
    GET /api/clients/business/1
    Headers: Authorization: Bearer {token}
    """
    try:
        # Verificar que el negocio exista
        business = Businesses.query.get(business_id)
        if not business:
            return jsonify({"error": "Negocio no encontrado"}), 404

        clients = Clients.query.filter_by(business_id=business_id, is_active=True).all()
        return jsonify([client.serialize_client() for client in clients]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener un cliente por ID (requiere autenticación)
# ============================================================================

@clients_bp.route('/<int:client_id>', methods=['GET'])
@user_or_admin_required
def get_client(client_id):
    """
    Obtiene un cliente específico por ID
    GET /api/clients/1
    Headers: Authorization: Bearer {token}
    """
    try:
        client = Clients.query.get(client_id)
        if not client:
            return jsonify({"error": "Cliente no encontrado"}), 404
        return jsonify(client.serialize_client()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# POST - Crear un nuevo cliente (requiere autenticación)
# ============================================================================

@clients_bp.route('', methods=['POST'])
@user_or_admin_required
def create_client():
    """
    Crea un nuevo cliente
    POST /api/clients
    Headers: Authorization: Bearer {token}
    Body: {
        "name": "Juan Pérez",
        "phone": "+34612345678",
        "client_dni": "12345678A",
        "email": "juan@example.com",
        "business_id": 1,
        "address": "Calle Principal 123, Madrid"
    }
    """
    try:
        data = request.json

        if not data:
            return jsonify({"error": "El body no puede estar vacío"}), 400

        required_fields = ['name', 'phone', 'client_dni', 'email', 'business_id']
        missing = [field for field in required_fields if field not in data]
        if missing:
            return jsonify({"error": f"Campos requeridos faltantes: {missing}"}), 400

        # Validar que el negocio exista
        business = Businesses.query.get(data['business_id'])
        if not business:
            return jsonify({"error": "El negocio no existe"}), 404

        # Validar que el email no exista
        if Clients.query.filter_by(email=data['email']).first():
            return jsonify({"error": "El email ya existe"}), 409

        # Validar que el DNI no exista
        if Clients.query.filter_by(client_dni=data['client_dni']).first():
            return jsonify({"error": "El DNI ya existe"}), 409

        # Generar ID secuencial automático (CLI-001, CLI-002, etc.)
        last_client = Clients.query.filter_by(business_id=data['business_id']).order_by(
            Clients.id.desc()
        ).first()
        
        if last_client:
            # Extraer el número del último ID y sumarle 1
            last_number = int(last_client.client_id_number.split('-')[1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        client_id_number = f"CLI-{new_number:03d}"  # CLI-001, CLI-002, etc.

        nuevo_client = Clients(
            name=data['name'],
            phone=data['phone'],
            client_id_number=client_id_number,
            client_dni=data['client_dni'],
            email=data['email'],
            business_id=data['business_id'],
            address=data.get('address')
        )

        db.session.add(nuevo_client)
        db.session.commit()

        return jsonify(nuevo_client.serialize_client()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PUT - Actualizar un cliente (requiere autenticación)
# ============================================================================

@clients_bp.route('/<int:client_id>', methods=['PUT'])
@user_or_admin_required
def update_client(client_id):
    """
    Actualiza un cliente
    PUT /api/clients/1
    Headers: Authorization: Bearer {token}
    Body: {
        "name": "Nuevo Nombre",
        "phone": "+34612345678",
        "email": "nuevo@example.com",
        "address": "Nueva dirección",
        "is_active": true
    }
    """
    try:
        client = Clients.query.get(client_id)
        if not client:
            return jsonify({"error": "Cliente no encontrado"}), 404

        data = request.json
        if not data:
            return jsonify({"error": "El body no puede estar vacío"}), 400

        # Actualizar nombre
        if 'name' in data:
            client.name = data['name']

        # Actualizar teléfono
        if 'phone' in data:
            client.phone = data['phone']

        # Actualizar dirección
        if 'address' in data:
            client.address = data['address']

        # Actualizar email
        if 'email' in data:
            existing = Clients.query.filter_by(email=data['email']).first()
            if existing and existing.id != client_id:
                return jsonify({"error": "El email ya existe"}), 409
            client.email = data['email']

        # Actualizar estado activo
        if 'is_active' in data:
            client.is_active = data['is_active']

        db.session.commit()
        return jsonify(client.serialize_client()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# DELETE - Eliminar un cliente (requiere autenticación)
# ============================================================================

@clients_bp.route('/<int:client_id>', methods=['DELETE'])
@user_or_admin_required
def delete_client(client_id):
    """
    Elimina (soft delete) un cliente
    DELETE /api/clients/1
    Headers: Authorization: Bearer {token}
    """
    try:
        client = Clients.query.get(client_id)
        if not client:
            return jsonify({"error": "Cliente no encontrado"}), 404

        client.is_active = False
        db.session.commit()

        return jsonify({"message": "Cliente eliminado correctamente"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Buscar cliente por email (requiere autenticación)
# ============================================================================

@clients_bp.route('/search/email', methods=['GET'])
@user_or_admin_required
def search_client_by_email():
    """
    Busca un cliente por email
    GET /api/clients/search/email?email=juan@example.com
    Headers: Authorization: Bearer {token}
    """
    try:
        email = request.args.get('email')
        
        if not email:
            return jsonify({"error": "El parámetro 'email' es requerido"}), 400

        client = Clients.query.filter_by(email=email, is_active=True).first()
        
        if not client:
            return jsonify({"error": "Cliente no encontrado"}), 404

        return jsonify(client.serialize_client()), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Buscar cliente por ID del cliente (requiere autenticación)
# ============================================================================

@clients_bp.route('/search/dni', methods=['GET'])
@user_or_admin_required
def search_client_by_dni():
    """
    Busca un cliente por su DNI
    GET /api/clients/search/dni?dni=12345678A
    Headers: Authorization: Bearer {token}
    """
    try:
        dni = request.args.get('dni')
        
        if not dni:
            return jsonify({"error": "El parámetro 'dni' es requerido"}), 400

        client = Clients.query.filter_by(client_dni=dni, is_active=True).first()
        
        if not client:
            return jsonify({"error": "Cliente no encontrado"}), 404

        return jsonify(client.serialize_client()), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener estadísticas de un cliente (requiere autenticación)
# ============================================================================

@clients_bp.route('/<int:client_id>/stats', methods=['GET'])
@user_or_admin_required
def get_client_stats(client_id):
    """
    Obtiene estadísticas de un cliente
    GET /api/clients/1/stats
    Headers: Authorization: Bearer {token}
    """
    try:
        client = Clients.query.get(client_id)
        if not client:
            return jsonify({"error": "Cliente no encontrado"}), 404

        stats = {
            "client_id": client.id,
            "client_name": client.name,
            "email": client.email,
            "total_appointments": len(client.appointments),
            "completed_appointments": sum(1 for a in client.appointments if a.status == 'completed'),
            "pending_appointments": sum(1 for a in client.appointments if a.status == 'pending'),
            "confirmed_appointments": sum(1 for a in client.appointments if a.status == 'confirmed'),
            "cancelled_appointments": sum(1 for a in client.appointments if a.status == 'cancelled'),
            "total_services": len(client.services),
            "completed_services": sum(1 for s in client.service_instances if s.completed),
            "pending_services": sum(1 for s in client.service_instances if not s.completed),
            "total_payments": len(client.payments),
            "total_notes": len(client.notes),
            "created_at": client.created_at.isoformat()
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# POST - Añadir nota a cliente (requiere autenticación)
# ============================================================================

@clients_bp.route('/<int:client_id>/notes', methods=['POST'])
@user_or_admin_required
def add_note_to_client(client_id):
    """
    Añade una nota a un cliente
    POST /api/clients/1/notes
    Headers: Authorization: Bearer {token}
    Body: {
        "description": "Cliente alérgico a ciertos productos"
    }
    """
    try:
        from models import Notes
        
        client = Clients.query.get(client_id)
        if not client:
            return jsonify({"error": "Cliente no encontrado"}), 404

        data = request.json
        if not data or 'description' not in data:
            return jsonify({"error": "description es requerido"}), 400

        nueva_nota = Notes(
            client_id=client_id,
            description=data['description']
        )

        db.session.add(nueva_nota)
        db.session.commit()

        return jsonify(nueva_nota.serialize_note()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener notas de cliente (requiere autenticación)
# ============================================================================

@clients_bp.route('/<int:client_id>/notes', methods=['GET'])
@user_or_admin_required
def get_client_notes(client_id):
    """
    Obtiene todas las notas de un cliente
    GET /api/clients/1/notes
    Headers: Authorization: Bearer {token}
    """
    try:
        from models import Notes
        
        client = Clients.query.get(client_id)
        if not client:
            return jsonify({"error": "Cliente no encontrado"}), 404

        notes = Notes.query.filter_by(client_id=client_id).all()
        return jsonify([note.serialize_note() for note in notes]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500