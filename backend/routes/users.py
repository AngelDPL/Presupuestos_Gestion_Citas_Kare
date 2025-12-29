from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
from models import db, Users, Businesses, Admins

# Crear el Blueprint
users_bp = Blueprint('users_api', __name__, url_prefix='/api/users')


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
# GET - Obtener todos los usuarios (requiere autenticación admin)
# ============================================================================

@users_bp.route('', methods=['GET'])
@admin_required
def get_all_users():
    """
    Obtiene todos los usuarios activos
    GET /api/users
    Headers: Authorization: Bearer {token}
    """
    try:
        users = Users.query.filter_by(is_active=True).all()
        return jsonify([user.serialize_user() for user in users]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener usuarios por negocio (requiere autenticación admin)
# ============================================================================

@users_bp.route('/business/<int:business_id>', methods=['GET'])
@admin_required
def get_users_by_business(business_id):
    """
    Obtiene todos los usuarios de un negocio específico
    GET /api/users/business/1
    Headers: Authorization: Bearer {token}
    """
    try:
        # Verificar que el negocio exista
        business = Businesses.query.get(business_id)
        if not business:
            return jsonify({"error": "Negocio no encontrado"}), 404

        users = Users.query.filter_by(business_id=business_id, is_active=True).all()
        return jsonify([user.serialize_user() for user in users]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener un usuario por ID (requiere autenticación)
# ============================================================================

@users_bp.route('/<int:user_id>', methods=['GET'])
@user_or_admin_required
def get_user(user_id):
    """
    Obtiene un usuario específico por ID
    GET /api/users/1
    Headers: Authorization: Bearer {token}
    """
    try:
        user = Users.query.get(user_id)
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404
        return jsonify(user.serialize_user()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# POST - Crear un nuevo usuario (requiere autenticación admin)
# ============================================================================

@users_bp.route('', methods=['POST'])
@admin_required
def create_user():
    """
    Crea un nuevo usuario/empleado
    POST /api/users
    Headers: Authorization: Bearer {token}
    Body: {
        "username": "juan_perez",
        "password": "password123",
        "business_id": 1,
        "role": "employee",
        "security_question": "¿Cuál es tu color favorito?",
        "security_answer": "azul"
    }
    """
    try:
        data = request.json

        if not data:
            return jsonify({"error": "El body no puede estar vacío"}), 400

        required_fields = ['username', 'password', 'business_id', 'role', 'security_question', 'security_answer']
        missing = [field for field in required_fields if field not in data]
        if missing:
            return jsonify({"error": f"Campos requeridos faltantes: {missing}"}), 400

        # Validar que el username no exista
        if Users.query.filter_by(username=data['username']).first():
            return jsonify({"error": "El username ya existe"}), 409

        # Validar que el negocio exista
        business = Businesses.query.get(data['business_id'])
        if not business:
            return jsonify({"error": "El negocio no existe"}), 404

        # Validar rol válido
        valid_roles = ['master', 'manager', 'employee']
        if data['role'] not in valid_roles:
            return jsonify({"error": f"Rol inválido. Debe ser: {valid_roles}"}), 400

        # Verificar que no exista un master si role es master
        if data['role'] == 'master':
            existing_master = Users.query.filter_by(business_id=data['business_id'], role='master').first()
            if existing_master:
                return jsonify({"error": "Este negocio ya tiene un usuario master asignado"}), 409

        nuevo_user = Users(
            username=data['username'],
            password=data['password'],
            business_id=data['business_id'],
            role=data['role'],
            security_question=data['security_question'],
            security_answer=data['security_answer']
        )

        db.session.add(nuevo_user)
        db.session.commit()

        return jsonify(nuevo_user.serialize_user()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PUT - Actualizar un usuario (requiere autenticación)
# ============================================================================

@users_bp.route('/<int:user_id>', methods=['PUT'])
@user_or_admin_required
def update_user(user_id):
    """
    Actualiza un usuario
    PUT /api/users/1
    Headers: Authorization: Bearer {token}
    Body: {
        "username": "nuevo_username",
        "password": "nueva_password",
        "role": "manager",
        "security_question": "¿Tu nombre?",
        "security_answer": "Juan",
        "is_active": true
    }
    """
    try:
        user = Users.query.get(user_id)
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        data = request.json
        if not data:
            return jsonify({"error": "El body no puede estar vacío"}), 400

        # Actualizar username
        if 'username' in data:
            existing = Users.query.filter_by(username=data['username']).first()
            if existing and existing.id != user_id:
                return jsonify({"error": "El username ya existe"}), 409
            user.username = data['username']

        # Actualizar contraseña
        if 'password' in data:
            user.set_password(data['password'])

        # Actualizar rol
        if 'role' in data:
            valid_roles = ['master', 'manager', 'employee']
            if data['role'] not in valid_roles:
                return jsonify({"error": f"Rol inválido. Debe ser: {valid_roles}"}), 400
            
            # Si cambia a master, verificar que no exista otro
            if data['role'] == 'master' and user.role != 'master':
                existing_master = Users.query.filter_by(business_id=user.business_id, role='master').first()
                if existing_master:
                    return jsonify({"error": "Este negocio ya tiene un usuario master asignado"}), 409
            
            user.role = data['role']

        # Actualizar pregunta de seguridad
        if 'security_question' in data:
            user.security_question = data['security_question']

        # Actualizar respuesta de seguridad
        if 'security_answer' in data:
            user.security_answer = data['security_answer']

        # Actualizar estado activo
        if 'is_active' in data:
            user.is_active = data['is_active']

        db.session.commit()
        return jsonify(user.serialize_user()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# DELETE - Eliminar un usuario (requiere autenticación admin)
# ============================================================================

@users_bp.route('/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """
    Elimina (soft delete) un usuario
    DELETE /api/users/1
    Headers: Authorization: Bearer {token}
    """
    try:
        user = Users.query.get(user_id)
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        user.is_active = False
        db.session.commit()

        return jsonify({"message": "Usuario eliminado correctamente"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# POST - Login de usuario
# ============================================================================

@users_bp.route('/login', methods=['POST'])
def login_user():
    """
    Login de usuario - obtiene token JWT
    POST /api/users/login
    Body: {
        "username": "juan_perez",
        "password": "password123"
    }
    """
    try:
        data = request.json

        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "username y password son requeridos"}), 400

        user = Users.query.filter_by(username=data['username']).first()

        if not user or not user.check_password(data['password']):
            return jsonify({"error": "Username o contraseña incorrectos"}), 401

        if not user.is_active:
            return jsonify({"error": "El usuario está inactivo"}), 403

        # Crear token JWT con el ID del usuario
        from flask_jwt_extended import create_access_token
        access_token = create_access_token(identity=str(user.id))

        return jsonify({
            "message": "Login exitoso",
            "access_token": access_token,
            "user": user.serialize_user()
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# POST - Verificar respuesta de seguridad (para recuperación de contraseña)
# ============================================================================

@users_bp.route('/verify-security/<int:user_id>', methods=['POST'])
def verify_security_answer(user_id):
    """
    Verifica la respuesta de seguridad de un usuario
    POST /api/users/verify-security/1
    Body: {
        "security_answer": "azul"
    }
    """
    try:
        user = Users.query.get(user_id)
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        data = request.json
        if not data or 'security_answer' not in data:
            return jsonify({"error": "security_answer es requerido"}), 400

        # Comparar respuestas (case-insensitive)
        if data['security_answer'].lower() == user.security_answer.lower():
            return jsonify({
                "message": "Respuesta correcta",
                "verified": True,
                "security_question": user.security_question
            }), 200
        else:
            return jsonify({
                "message": "Respuesta incorrecta",
                "verified": False
            }), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PUT - Cambiar contraseña (requiere autenticación)
# ============================================================================

@users_bp.route('/<int:user_id>/change-password', methods=['PUT'])
@user_or_admin_required
def change_password(user_id):
    """
    Cambia la contraseña de un usuario
    PUT /api/users/1/change-password
    Headers: Authorization: Bearer {token}
    Body: {
        "old_password": "password123",
        "new_password": "newpassword123"
    }
    """
    try:
        user = Users.query.get(user_id)
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        data = request.json
        if not data or 'old_password' not in data or 'new_password' not in data:
            return jsonify({"error": "old_password y new_password son requeridos"}), 400

        # Verificar contraseña antigua
        if not user.check_password(data['old_password']):
            return jsonify({"error": "La contraseña antigua es incorrecta"}), 401

        # Establecer nueva contraseña
        user.set_password(data['new_password'])
        db.session.commit()

        return jsonify({
            "message": "Contraseña cambiada correctamente",
            "user": user.serialize_user()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500