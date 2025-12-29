from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
from models import db, Services, Businesses, Users, Admins
from decimal import Decimal

# Crear el Blueprint
services_bp = Blueprint('services_api', __name__, url_prefix='/api/services')


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
# GET - Obtener todos los servicios (requiere autenticación)
# ============================================================================

@services_bp.route('', methods=['GET'])
@user_or_admin_required
def get_all_services():
    """
    Obtiene todos los servicios activos
    GET /api/services
    Headers: Authorization: Bearer {token}
    """
    try:
        services = Services.query.filter_by(is_active=True).all()
        return jsonify([service.serialize_service() for service in services]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener servicios por negocio (requiere autenticación)
# ============================================================================

@services_bp.route('/business/<int:business_id>', methods=['GET'])
@user_or_admin_required
def get_services_by_business(business_id):
    """
    Obtiene todos los servicios de un negocio específico
    GET /api/services/business/1
    Headers: Authorization: Bearer {token}
    """
    try:
        # Verificar que el negocio exista
        business = Businesses.query.get(business_id)
        if not business:
            return jsonify({"error": "Negocio no encontrado"}), 404

        services = Services.query.filter_by(business_id=business_id, is_active=True).all()
        return jsonify([service.serialize_service() for service in services]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener un servicio por ID (requiere autenticación)
# ============================================================================

@services_bp.route('/<int:service_id>', methods=['GET'])
@user_or_admin_required
def get_service(service_id):
    """
    Obtiene un servicio específico por ID
    GET /api/services/1
    Headers: Authorization: Bearer {token}
    """
    try:
        service = Services.query.get(service_id)
        if not service:
            return jsonify({"error": "Servicio no encontrado"}), 404
        return jsonify(service.serialize_service()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# POST - Crear un nuevo servicio (requiere autenticación admin o master)
# ============================================================================

@services_bp.route('', methods=['POST'])
@user_or_admin_required
def create_service():
    """
    Crea un nuevo servicio
    POST /api/services
    Headers: Authorization: Bearer {token}
    Body: {
        "business_id": 1,
        "name": "Corte de cabello",
        "description": "Corte clásico con navaja",
        "price": "15.99"
    }
    """
    try:
        data = request.json

        if not data:
            return jsonify({"error": "El body no puede estar vacío"}), 400

        required_fields = ['business_id', 'name', 'description', 'price']
        missing = [field for field in required_fields if field not in data]
        if missing:
            return jsonify({"error": f"Campos requeridos faltantes: {missing}"}), 400

        # Validar que el negocio exista
        business = Businesses.query.get(data['business_id'])
        if not business:
            return jsonify({"error": "El negocio no existe"}), 404

        # Validar que el precio sea un número válido
        try:
            price = Decimal(str(data['price']))
            if price < 0:
                return jsonify({"error": "El precio no puede ser negativo"}), 400
        except:
            return jsonify({"error": "El precio debe ser un número válido"}), 400

        nuevo_service = Services(
            business_id=data['business_id'],
            name=data['name'],
            description=data['description'],
            price=price
        )

        db.session.add(nuevo_service)
        db.session.commit()

        return jsonify(nuevo_service.serialize_service()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PUT - Actualizar un servicio (requiere autenticación)
# ============================================================================

@services_bp.route('/<int:service_id>', methods=['PUT'])
@user_or_admin_required
def update_service(service_id):
    """
    Actualiza un servicio
    PUT /api/services/1
    Headers: Authorization: Bearer {token}
    Body: {
        "name": "Corte premium",
        "description": "Corte personalizado con barba",
        "price": "25.99",
        "is_active": true
    }
    """
    try:
        service = Services.query.get(service_id)
        if not service:
            return jsonify({"error": "Servicio no encontrado"}), 404

        data = request.json
        if not data:
            return jsonify({"error": "El body no puede estar vacío"}), 400

        # Actualizar nombre
        if 'name' in data:
            service.name = data['name']

        # Actualizar descripción
        if 'description' in data:
            service.description = data['description']

        # Actualizar precio
        if 'price' in data:
            try:
                price = Decimal(str(data['price']))
                if price < 0:
                    return jsonify({"error": "El precio no puede ser negativo"}), 400
                service.price = price
            except:
                return jsonify({"error": "El precio debe ser un número válido"}), 400

        # Actualizar estado activo
        if 'is_active' in data:
            service.is_active = data['is_active']

        db.session.commit()
        return jsonify(service.serialize_service()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# DELETE - Eliminar un servicio (requiere autenticación)
# ============================================================================

@services_bp.route('/<int:service_id>', methods=['DELETE'])
@user_or_admin_required
def delete_service(service_id):
    """
    Elimina (soft delete) un servicio
    DELETE /api/services/1
    Headers: Authorization: Bearer {token}
    """
    try:
        service = Services.query.get(service_id)
        if not service:
            return jsonify({"error": "Servicio no encontrado"}), 404

        service.is_active = False
        db.session.commit()

        return jsonify({"message": "Servicio eliminado correctamente"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Buscar servicios por nombre (requiere autenticación)
# ============================================================================

@services_bp.route('/search/name', methods=['GET'])
@user_or_admin_required
def search_service_by_name():
    """
    Busca servicios por nombre (búsqueda parcial)
    GET /api/services/search/name?name=corte
    Headers: Authorization: Bearer {token}
    """
    try:
        name = request.args.get('name')
        
        if not name:
            return jsonify({"error": "El parámetro 'name' es requerido"}), 400

        services = Services.query.filter(
            Services.name.ilike(f'%{name}%'),
            Services.is_active == True
        ).all()
        
        if not services:
            return jsonify({"error": "Ningún servicio encontrado"}), 404

        return jsonify([service.serialize_service() for service in services]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener servicios por rango de precio (requiere autenticación)
# ============================================================================

@services_bp.route('/filter/price-range', methods=['GET'])
@user_or_admin_required
def filter_services_by_price():
    """
    Obtiene servicios dentro de un rango de precio
    GET /api/services/filter/price-range?min=10&max=50
    Headers: Authorization: Bearer {token}
    """
    try:
        min_price = request.args.get('min', type=float)
        max_price = request.args.get('max', type=float)
        
        if min_price is None or max_price is None:
            return jsonify({"error": "Parámetros 'min' y 'max' son requeridos"}), 400

        if min_price > max_price:
            return jsonify({"error": "El precio mínimo no puede ser mayor que el máximo"}), 400

        services = Services.query.filter(
            Services.price >= min_price,
            Services.price <= max_price,
            Services.is_active == True
        ).all()

        return jsonify([service.serialize_service() for service in services]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Estadísticas de servicios (requiere autenticación admin)
# ============================================================================

@services_bp.route('/stats', methods=['GET'])
@admin_required
def get_services_stats():
    """
    Obtiene estadísticas generales de servicios
    GET /api/services/stats
    Headers: Authorization: Bearer {token}
    """
    try:
        all_services = Services.query.all()
        active_services = Services.query.filter_by(is_active=True).all()
        
        if not all_services:
            return jsonify({
                "total_services": 0,
                "active_services": 0,
                "inactive_services": 0,
                "average_price": 0,
                "min_price": 0,
                "max_price": 0
            }), 200

        prices = [float(s.price) for s in active_services]
        
        stats = {
            "total_services": len(all_services),
            "active_services": len(active_services),
            "inactive_services": len(all_services) - len(active_services),
            "average_price": round(sum(prices) / len(prices), 2) if prices else 0,
            "min_price": round(min(prices), 2) if prices else 0,
            "max_price": round(max(prices), 2) if prices else 0
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Estadísticas de servicios por negocio (requiere autenticación)
# ============================================================================

@services_bp.route('/business/<int:business_id>/stats', methods=['GET'])
@user_or_admin_required
def get_business_services_stats(business_id):
    """
    Obtiene estadísticas de servicios de un negocio
    GET /api/services/business/1/stats
    Headers: Authorization: Bearer {token}
    """
    try:
        business = Businesses.query.get(business_id)
        if not business:
            return jsonify({"error": "Negocio no encontrado"}), 404

        all_services = Services.query.filter_by(business_id=business_id).all()
        active_services = Services.query.filter_by(business_id=business_id, is_active=True).all()

        if not all_services:
            return jsonify({
                "business_id": business_id,
                "business_name": business.business_name,
                "total_services": 0,
                "active_services": 0,
                "inactive_services": 0,
                "average_price": 0,
                "min_price": 0,
                "max_price": 0
            }), 200

        prices = [float(s.price) for s in active_services]

        stats = {
            "business_id": business_id,
            "business_name": business.business_name,
            "total_services": len(all_services),
            "active_services": len(active_services),
            "inactive_services": len(all_services) - len(active_services),
            "average_price": round(sum(prices) / len(prices), 2) if prices else 0,
            "min_price": round(min(prices), 2) if prices else 0,
            "max_price": round(max(prices), 2) if prices else 0
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500