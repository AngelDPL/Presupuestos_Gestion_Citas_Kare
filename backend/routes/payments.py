from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
from models import db, Payments, Clients, Businesses, Users, Admins
from decimal import Decimal
from datetime import datetime, date

# Crear el Blueprint
payments_bp = Blueprint('payments_api', __name__, url_prefix='/api/payments')


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
# GET - Obtener todos los pagos (requiere autenticación)
# ============================================================================

@payments_bp.route('', methods=['GET'])
@user_or_admin_required
def get_all_payments():
    """
    Obtiene todos los pagos
    GET /api/payments
    Headers: Authorization: Bearer {token}
    """
    try:
        payments = Payments.query.all()
        return jsonify([payment.serialize_payment() for payment in payments]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener pagos por cliente (requiere autenticación)
# ============================================================================

@payments_bp.route('/client/<int:client_id>', methods=['GET'])
@user_or_admin_required
def get_payments_by_client(client_id):
    """
    Obtiene todos los pagos de un cliente
    GET /api/payments/client/1
    Headers: Authorization: Bearer {token}
    """
    try:
        client = Clients.query.get(client_id)
        if not client:
            return jsonify({"error": "Cliente no encontrado"}), 404

        payments = Payments.query.filter_by(client_id=client_id).all()
        return jsonify([payment.serialize_payment() for payment in payments]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener pagos por negocio (requiere autenticación)
# ============================================================================

@payments_bp.route('/business/<int:business_id>', methods=['GET'])
@user_or_admin_required
def get_payments_by_business(business_id):
    """
    Obtiene todos los pagos de un negocio
    GET /api/payments/business/1
    Headers: Authorization: Bearer {token}
    """
    try:
        business = Businesses.query.get(business_id)
        if not business:
            return jsonify({"error": "Negocio no encontrado"}), 404

        # Obtener todos los clientes del negocio
        clients = Clients.query.filter_by(business_id=business_id).all()
        client_ids = [c.id for c in clients]

        payments = Payments.query.filter(Payments.client_id.in_(client_ids)).all()
        return jsonify([payment.serialize_payment() for payment in payments]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener un pago por ID (requiere autenticación)
# ============================================================================

@payments_bp.route('/<int:payment_id>', methods=['GET'])
@user_or_admin_required
def get_payment(payment_id):
    """
    Obtiene un pago específico por ID
    GET /api/payments/1
    Headers: Authorization: Bearer {token}
    """
    try:
        payment = Payments.query.get(payment_id)
        if not payment:
            return jsonify({"error": "Pago no encontrado"}), 404
        return jsonify(payment.serialize_payment()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# POST - Crear un nuevo pago (requiere autenticación)
# ============================================================================

@payments_bp.route('', methods=['POST'])
@user_or_admin_required
def create_payment():
    """
    Crea un nuevo pago
    POST /api/payments
    Headers: Authorization: Bearer {token}
    Body: {
        "client_id": 1,
        "payment_method": "card",
        "estimated_total": "150.00",
        "payments_made": "50.00",
        "payment_date": "2025-12-23"
    }
    """
    try:
        data = request.json

        if not data:
            return jsonify({"error": "El body no puede estar vacío"}), 400

        required_fields = ['client_id', 'payment_method', 'estimated_total']
        missing = [field for field in required_fields if field not in data]
        if missing:
            return jsonify({"error": f"Campos requeridos faltantes: {missing}"}), 400

        # Validar que el cliente existe
        client = Clients.query.get(data['client_id'])
        if not client or not client.is_active:
            return jsonify({"error": "Cliente no encontrado o inactivo"}), 404

        # Validar método de pago
        valid_methods = ['cash', 'card']
        if data['payment_method'] not in valid_methods:
            return jsonify({"error": f"Método de pago inválido. Debe ser: {valid_methods}"}), 400

        # Validar y convertir montos
        try:
            estimated_total = Decimal(str(data['estimated_total']))
            if estimated_total <= 0:
                return jsonify({"error": "El total estimado debe ser mayor a 0"}), 400
        except:
            return jsonify({"error": "El total estimado debe ser un número válido"}), 400

        payments_made = Decimal(str(data.get('payments_made', 0)))
        if payments_made < 0:
            return jsonify({"error": "Los pagos realizados no pueden ser negativos"}), 400

        if payments_made > estimated_total:
            return jsonify({"error": "Los pagos realizados no pueden exceder el total estimado"}), 400

        # Validar fecha de pago (opcional)
        payment_date = None
        if 'payment_date' in data:
            try:
                payment_date = datetime.fromisoformat(data['payment_date']).date()
            except:
                return jsonify({"error": "Formato de fecha inválido. Usa: YYYY-MM-DD"}), 400

        # Determinar estado automáticamente
        if payments_made == estimated_total:
            status = 'paid'
        else:
            status = 'pending'

        nuevo_payment = Payments(
            client_id=data['client_id'],
            payment_method=data['payment_method'],
            estimated_total=estimated_total,
            payments_made=payments_made,
            payment_date=payment_date,
            status=status
        )

        db.session.add(nuevo_payment)
        db.session.commit()

        return jsonify(nuevo_payment.serialize_payment()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PUT - Actualizar un pago (requiere autenticación)
# ============================================================================

@payments_bp.route('/<int:payment_id>', methods=['PUT'])
@user_or_admin_required
def update_payment(payment_id):
    """
    Actualiza un pago
    PUT /api/payments/1
    Headers: Authorization: Bearer {token}
    Body: {
        "payments_made": "100.00",
        "payment_method": "cash",
        "payment_date": "2025-12-23"
    }
    """
    try:
        payment = Payments.query.get(payment_id)
        if not payment:
            return jsonify({"error": "Pago no encontrado"}), 404

        data = request.json
        if not data:
            return jsonify({"error": "El body no puede estar vacío"}), 400

        # Actualizar método de pago
        if 'payment_method' in data:
            valid_methods = ['cash', 'card']
            if data['payment_method'] not in valid_methods:
                return jsonify({"error": f"Método de pago inválido. Debe ser: {valid_methods}"}), 400
            payment.payment_method = data['payment_method']

        # Actualizar pagos realizados
        if 'payments_made' in data:
            try:
                payments_made = Decimal(str(data['payments_made']))
                if payments_made < 0:
                    return jsonify({"error": "Los pagos realizados no pueden ser negativos"}), 400
                if payments_made > payment.estimated_total:
                    return jsonify({"error": "Los pagos realizados no pueden exceder el total estimado"}), 400
                payment.payments_made = payments_made
            except:
                return jsonify({"error": "Los pagos realizados deben ser un número válido"}), 400

        # Actualizar total estimado
        if 'estimated_total' in data:
            try:
                estimated_total = Decimal(str(data['estimated_total']))
                if estimated_total <= 0:
                    return jsonify({"error": "El total estimado debe ser mayor a 0"}), 400
                if payment.payments_made > estimated_total:
                    return jsonify({"error": "El total estimado no puede ser menor que los pagos realizados"}), 400
                payment.estimated_total = estimated_total
            except:
                return jsonify({"error": "El total estimado debe ser un número válido"}), 400

        # Actualizar fecha de pago
        if 'payment_date' in data:
            if data['payment_date'] is None:
                payment.payment_date = None
            else:
                try:
                    payment.payment_date = datetime.fromisoformat(data['payment_date']).date()
                except:
                    return jsonify({"error": "Formato de fecha inválido. Usa: YYYY-MM-DD"}), 400

        # Actualizar estado automáticamente
        if payment.payments_made == payment.estimated_total:
            payment.status = 'paid'
        else:
            payment.status = 'pending'

        db.session.commit()
        return jsonify(payment.serialize_payment()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# DELETE - Eliminar un pago (requiere autenticación admin)
# ============================================================================

@payments_bp.route('/<int:payment_id>', methods=['DELETE'])
@admin_required
def delete_payment(payment_id):
    """
    Elimina un pago
    DELETE /api/payments/1
    Headers: Authorization: Bearer {token}
    """
    try:
        payment = Payments.query.get(payment_id)
        if not payment:
            return jsonify({"error": "Pago no encontrado"}), 404

        db.session.delete(payment)
        db.session.commit()

        return jsonify({"message": "Pago eliminado correctamente"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener pagos por estado (requiere autenticación)
# ============================================================================

@payments_bp.route('/filter/status', methods=['GET'])
@user_or_admin_required
def filter_payments_by_status():
    """
    Filtra pagos por estado
    GET /api/payments/filter/status?status=pending
    Headers: Authorization: Bearer {token}
    """
    try:
        status = request.args.get('status')
        
        if not status:
            return jsonify({"error": "El parámetro 'status' es requerido"}), 400

        valid_statuses = ['pending', 'paid']
        if status not in valid_statuses:
            return jsonify({"error": f"Estado inválido. Debe ser: {valid_statuses}"}), 400

        payments = Payments.query.filter_by(status=status).all()
        return jsonify([payment.serialize_payment() for payment in payments]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener pagos por método (requiere autenticación)
# ============================================================================

@payments_bp.route('/filter/method', methods=['GET'])
@user_or_admin_required
def filter_payments_by_method():
    """
    Filtra pagos por método
    GET /api/payments/filter/method?method=card
    Headers: Authorization: Bearer {token}
    """
    try:
        method = request.args.get('method')
        
        if not method:
            return jsonify({"error": "El parámetro 'method' es requerido"}), 400

        valid_methods = ['cash', 'card']
        if method not in valid_methods:
            return jsonify({"error": f"Método inválido. Debe ser: {valid_methods}"}), 400

        payments = Payments.query.filter_by(payment_method=method).all()
        return jsonify([payment.serialize_payment() for payment in payments]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Obtener pagos pendientes (requiere autenticación)
# ============================================================================

@payments_bp.route('/pending', methods=['GET'])
@user_or_admin_required
def get_pending_payments():
    """
    Obtiene todos los pagos pendientes
    GET /api/payments/pending
    Headers: Authorization: Bearer {token}
    """
    try:
        payments = Payments.query.filter_by(status='pending').all()
        return jsonify([payment.serialize_payment() for payment in payments]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Estadísticas de pagos (requiere autenticación admin)
# ============================================================================

@payments_bp.route('/stats', methods=['GET'])
@admin_required
def get_payments_stats():
    """
    Obtiene estadísticas generales de pagos
    GET /api/payments/stats
    Headers: Authorization: Bearer {token}
    """
    try:
        all_payments = Payments.query.all()
        
        if not all_payments:
            return jsonify({
                "total_payments": 0,
                "pending_payments": 0,
                "paid_payments": 0,
                "total_estimated": "0.00",
                "total_collected": "0.00",
                "total_pending": "0.00",
                "collection_rate": 0.0,
                "cash_payments": 0,
                "card_payments": 0
            }), 200

        total_estimated = sum(p.estimated_total for p in all_payments)
        total_collected = sum(p.payments_made for p in all_payments)
        total_pending = total_estimated - total_collected

        stats = {
            "total_payments": len(all_payments),
            "pending_payments": sum(1 for p in all_payments if p.status == 'pending'),
            "paid_payments": sum(1 for p in all_payments if p.status == 'paid'),
            "total_estimated": str(total_estimated),
            "total_collected": str(total_collected),
            "total_pending": str(total_pending),
            "collection_rate": round((float(total_collected) / float(total_estimated) * 100) if total_estimated > 0 else 0, 2),
            "cash_payments": sum(1 for p in all_payments if p.payment_method == 'cash'),
            "card_payments": sum(1 for p in all_payments if p.payment_method == 'card')
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GET - Estadísticas de pagos por negocio (requiere autenticación)
# ============================================================================

@payments_bp.route('/business/<int:business_id>/stats', methods=['GET'])
@user_or_admin_required
def get_business_payments_stats(business_id):
    """
    Obtiene estadísticas de pagos de un negocio
    GET /api/payments/business/1/stats
    Headers: Authorization: Bearer {token}
    """
    try:
        business = Businesses.query.get(business_id)
        if not business:
            return jsonify({"error": "Negocio no encontrado"}), 404

        # Obtener todos los clientes del negocio
        clients = Clients.query.filter_by(business_id=business_id).all()
        client_ids = [c.id for c in clients]

        payments = Payments.query.filter(Payments.client_id.in_(client_ids)).all()

        if not payments:
            return jsonify({
                "business_id": business_id,
                "business_name": business.business_name,
                "total_payments": 0,
                "pending_payments": 0,
                "paid_payments": 0,
                "total_estimated": "0.00",
                "total_collected": "0.00",
                "total_pending": "0.00",
                "collection_rate": 0.0,
                "cash_payments": 0,
                "card_payments": 0
            }), 200

        total_estimated = sum(p.estimated_total for p in payments)
        total_collected = sum(p.payments_made for p in payments)
        total_pending = total_estimated - total_collected

        stats = {
            "business_id": business_id,
            "business_name": business.business_name,
            "total_payments": len(payments),
            "pending_payments": sum(1 for p in payments if p.status == 'pending'),
            "paid_payments": sum(1 for p in payments if p.status == 'paid'),
            "total_estimated": str(total_estimated),
            "total_collected": str(total_collected),
            "total_pending": str(total_pending),
            "collection_rate": round((float(total_collected) / float(total_estimated) * 100) if total_estimated > 0 else 0, 2),
            "cash_payments": sum(1 for p in payments if p.payment_method == 'cash'),
            "card_payments": sum(1 for p in payments if p.payment_method == 'card')
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# POST - Registrar abono a un pago (requiere autenticación)
# ============================================================================

@payments_bp.route('/<int:payment_id>/add-payment', methods=['POST'])
@user_or_admin_required
def add_payment_to_record(payment_id):
    """
    Registra un abono/pago adicional a un registro de pago
    POST /api/payments/1/add-payment
    Headers: Authorization: Bearer {token}
    Body: {
        "amount": "50.00",
        "payment_method": "cash",
        "payment_date": "2025-12-23"
    }
    """
    try:
        payment = Payments.query.get(payment_id)
        if not payment:
            return jsonify({"error": "Pago no encontrado"}), 404

        data = request.json
        if not data or 'amount' not in data:
            return jsonify({"error": "El 'amount' es requerido"}), 400

        # Validar cantidad
        try:
            amount = Decimal(str(data['amount']))
            if amount <= 0:
                return jsonify({"error": "El monto debe ser mayor a 0"}), 400
        except:
            return jsonify({"error": "El monto debe ser un número válido"}), 400

        # Calcular nuevo total de pagos
        new_total = payment.payments_made + amount
        if new_total > payment.estimated_total:
            return jsonify({"error": f"El monto excede el total. Máximo: {payment.estimated_total - payment.payments_made}"}), 400

        # Actualizar pagos
        payment.payments_made = new_total

        # Actualizar método de pago si viene
        if 'payment_method' in data:
            valid_methods = ['cash', 'card']
            if data['payment_method'] in valid_methods:
                payment.payment_method = data['payment_method']

        # Actualizar fecha de pago si viene
        if 'payment_date' in data:
            try:
                payment.payment_date = datetime.fromisoformat(data['payment_date']).date()
            except:
                return jsonify({"error": "Formato de fecha inválido. Usa: YYYY-MM-DD"}), 400

        # Actualizar estado automáticamente
        if payment.payments_made == payment.estimated_total:
            payment.status = 'paid'
        else:
            payment.status = 'pending'

        db.session.commit()

        return jsonify({
            "message": f"Abono de {amount} registrado correctamente",
            "payment": payment.serialize_payment()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500