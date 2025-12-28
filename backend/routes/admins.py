from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from functools import wraps
from models import db, Admins

# Crear el Blueprint
admins_bp = Blueprint('admins', __name__, url_prefix='/api/admins')


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
            admin = Admins.query.get(current_user_id)
            
            if not admin or not admin.is_active:
                return jsonify({"error": "Acceso denegado: privilegios de administrador requeridos"}), 403
            
            return fn(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": f"Error de autenticación: {str(e)}"}), 401
    return wrapper


# ============================================================================
# POST - Crear el primer administrador (sin autenticación)
# ============================================================================

@admins_bp.route('/setup', methods=['POST'])
def setup_first_admin():
    """
    Crea el primer administrador del sistema (solo si no existe ninguno)
    POST /api/admins/setup
    Body: {
        "username": "admin",
        "password": "password123"
    }
    """
    try:
        # Verificar que no exista un admin previo
        if Admins.query.count() > 0:
            return jsonify({"error": "Ya existe un administrador configurado"}), 409

        data = request.json

        if not data:
            return jsonify({"error": "El body no puede estar vacío"}), 400

        if 'username' not in data or 'password' not in data:
            return jsonify({"error": "username y password son requeridos"}), 400

        # Crear el admin inicial
        nuevo_admin = Admins(
            username=data['username'],
            password=data['password'],
            role='Admin'
        )

        db.session.add(nuevo_admin)
        db.session.commit()

        return jsonify({
            "message": "Administrador creado exitosamente",
            "admin": nuevo_admin.serialize_admins()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# POST - Login de administrador (obtener token JWT)
# ============================================================================

@admins_bp.route('/login', methods=['POST'])
def login_admin():
    """
    Login de administrador - obtiene token JWT
    POST /api/admins/login
    Body: {
        "username": "juan",
        "password": "password123"
    }
    """
    try:
        data = request.json

        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "username y password son requeridos"}), 400

        admin = Admins.query.filter_by(username=data['username']).first()

        if not admin or not admin.check_password(data['password']):
            return jsonify({"error": "Username o contraseña incorrectos"}), 401

        if not admin.is_active:
            return jsonify({"error": "El administrador está inactivo"}), 403

        # Crear token JWT con el ID del admin
        access_token = create_access_token(identity=str(admin.id))

        return jsonify({
            "message": "Login exitoso",
            "access_token": access_token,
            "admin": admin.serialize_admins()
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener todos los administradores (requiere autenticación)
# ============================================================================

@admins_bp.route('', methods=['GET'])
@admin_required
def get_all_admins():
    """
    Obtiene todos los administradores activos
    GET /api/admins
    Headers: Authorization: Bearer {token}
    """
    try:
        admins = Admins.query.filter_by(is_active=True).all()
        return jsonify([admin.serialize_admins() for admin in admins]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener un administrador por ID (requiere autenticación)
# ============================================================================

@admins_bp.route('/<int:admin_id>', methods=['GET'])
@admin_required
def get_admin(admin_id):
    """
    Obtiene un administrador específico por ID
    GET /api/admins/1
    Headers: Authorization: Bearer {token}
    """
    try:
        admin = Admins.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Administrador no encontrado"}), 404
        return jsonify(admin.serialize_admins()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# POST - Crear un nuevo administrador (requiere autenticación)
# ============================================================================

@admins_bp.route('', methods=['POST'])
@admin_required
def create_admin():
    """
    Crea un nuevo administrador
    POST /api/admins
    Headers: Authorization: Bearer {token}
    Body: {
        "username": "nuevo_admin",
        "password": "password123",
        "role": "Admin"
    }
    """
    try:
        data = request.json

        if not data:
            return jsonify({"error": "El body no puede estar vacío"}), 400

        if 'username' not in data or 'password' not in data:
            return jsonify({"error": "username y password son requeridos"}), 400

        # Verificar que el username no exista
        if Admins.query.filter_by(username=data['username']).first():
            return jsonify({"error": "El username ya existe"}), 409

        nuevo_admin = Admins(
            username=data['username'],
            password=data['password'],
            role=data.get('role', 'Admin')
        )

        db.session.add(nuevo_admin)
        db.session.commit()

        return jsonify(nuevo_admin.serialize_admins()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PUT - Actualizar un administrador (requiere autenticación)
# ============================================================================

@admins_bp.route('/<int:admin_id>', methods=['PUT'])
@admin_required
def update_admin(admin_id):
    """
    Actualiza un administrador
    PUT /api/admins/1
    Headers: Authorization: Bearer {token}
    Body: {
        "username": "nuevo_username",
        "password": "nueva_password",
        "role": "Admin",
        "is_active": true
    }
    """
    try:
        admin = Admins.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Administrador no encontrado"}), 404

        data = request.json
        if not data:
            return jsonify({"error": "El body no puede estar vacío"}), 400

        if 'username' in data:
            existing = Admins.query.filter_by(username=data['username']).first()
            if existing and existing.id != admin_id:
                return jsonify({"error": "El username ya existe"}), 409
            admin.username = data['username']

        if 'password' in data:
            admin.set_password(data['password'])

        if 'role' in data:
            admin.role = data['role']

        if 'is_active' in data:
            admin.is_active = data['is_active']

        db.session.commit()
        return jsonify(admin.serialize_admins()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# DELETE - Eliminar un administrador (requiere autenticación)
# ============================================================================

@admins_bp.route('/<int:admin_id>', methods=['DELETE'])
@admin_required
def delete_admin(admin_id):
    """
    Elimina (soft delete) un administrador
    DELETE /api/admins/1
    Headers: Authorization: Bearer {token}
    """
    try:
        admin = Admins.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Administrador no encontrado"}), 404

        admin.is_active = False
        db.session.commit()

        return jsonify({"message": "Administrador eliminado correctamente"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500