from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
from models import db, Businesses, Admins

# Crear el Blueprint
businesses_bp = Blueprint('businesses', __name__, url_prefix='/api/businesses')



# DECORADOR PERSONALIZADO - Verificar que es Admin

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



# GET - Obtener todos los negocios (requiere autenticación)

@businesses_bp.route('', methods=['GET'])
@admin_required
def get_all_businesses():
    """
    Obtiene todos los negocios activos
    GET /api/businesses
    Headers: Authorization: Bearer {token}
    """
    try:
        businesses = Businesses.query.filter_by(is_active=True).all()
        return jsonify([biz.serialize_business() for biz in businesses]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# GET - Obtener un negocio por ID (requiere autenticación)

@businesses_bp.route('/<int:business_id>', methods=['GET'])
@admin_required
def get_business(business_id):
    """
    Obtiene un negocio específico por ID
    GET /api/businesses/1
    Headers: Authorization: Bearer {token}
    """
    try:
        business = Businesses.query.get(business_id)
        if not business:
            return jsonify({"error": "Negocio no encontrado"}), 404
        return jsonify(business.serialize_business()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# POST - Crear un nuevo negocio (requiere autenticación)

@businesses_bp.route('', methods=['POST'])
@admin_required
def create_business():
    """
    Crea un nuevo negocio
    POST /api/businesses
    Headers: Authorization: Bearer {token}
    Body: {
        "business_name": "Mi Barbería",
        "business_RIF": "J12345678",
        "business_CP": "1010"
    }
    """
    try:
        data = request.json

        if not data:
            return jsonify({"error": "El body no puede estar vacío"}), 400

        required_fields = ['business_name', 'business_RIF', 'business_CP']
        missing = [field for field in required_fields if field not in data]
        if missing:
            return jsonify({"error": f"Campos requeridos faltantes: {missing}"}), 400

        # Validar que el RIF no exista
        if Businesses.query.filter_by(business_RIF=data['business_RIF']).first():
            return jsonify({"error": "El RIF ya existe"}), 409

        nuevo_business = Businesses(
            business_name=data['business_name'],
            business_RIF=data['business_RIF'],
            business_CP=data['business_CP']
        )

        db.session.add(nuevo_business)
        db.session.commit()

        return jsonify(nuevo_business.serialize_business()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500



# PUT - Actualizar un negocio (requiere autenticación)

@businesses_bp.route('/<int:business_id>', methods=['PUT'])
@admin_required
def update_business(business_id):
    """
    Actualiza un negocio
    PUT /api/businesses/1
    Headers: Authorization: Bearer {token}
    Body: {
        "business_name": "Nuevo Nombre",
        "business_RIF": "J12345678",
        "business_CP": "2020",
        "is_active": true
    }
    """
    try:
        business = Businesses.query.get(business_id)
        if not business:
            return jsonify({"error": "Negocio no encontrado"}), 404

        data = request.json
        if not data:
            return jsonify({"error": "El body no puede estar vacío"}), 400

        # Actualizar nombre
        if 'business_name' in data:
            business.business_name = data['business_name']

        # Actualizar RIF
        if 'business_RIF' in data:
            existing = Businesses.query.filter_by(business_RIF=data['business_RIF']).first()
            if existing and existing.id != business_id:
                return jsonify({"error": "El RIF ya existe"}), 409
            business.business_RIF = data['business_RIF']

        # Actualizar código postal
        if 'business_CP' in data:
            business.business_CP = data['business_CP']

        # Actualizar estado activo
        if 'is_active' in data:
            business.is_active = data['is_active']

        db.session.commit()
        return jsonify(business.serialize_business()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500



# DELETE - Eliminar un negocio (requiere autenticación)

@businesses_bp.route('/<int:business_id>', methods=['DELETE'])
@admin_required
def delete_business(business_id):
    """
    Elimina (soft delete) un negocio
    DELETE /api/businesses/1
    Headers: Authorization: Bearer {token}
    """
    try:
        business = Businesses.query.get(business_id)
        if not business:
            return jsonify({"error": "Negocio no encontrado"}), 404

        # Soft delete: solo marcamos como inactivo
        business.is_active = False
        db.session.commit()

        return jsonify({"message": "Negocio eliminado correctamente"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500



# GET - Estadísticas de un negocio (requiere autenticación)

@businesses_bp.route('/<int:business_id>/stats', methods=['GET'])
@admin_required
def get_business_stats(business_id):
    """
    Obtiene estadísticas de un negocio
    GET /api/businesses/1/stats
    Headers: Authorization: Bearer {token}
    """
    try:
        business = Businesses.query.get(business_id)
        if not business:
            return jsonify({"error": "Negocio no encontrado"}), 404

        stats = {
            "business_id": business.id,
            "business_name": business.business_name,
            "total_users": len(business.users),
            "total_services": len(business.services),
            "total_clients": len(business.clients),
            "total_appointments": len(business.appointments),
            "active_users": sum(1 for u in business.users if u.is_active),
            "active_services": sum(1 for s in business.services if s.is_active),
            "active_clients": sum(1 for c in business.clients if c.is_active)
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500