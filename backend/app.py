from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from dotenv import load_dotenv
import os

from models import db, Admins, Businesses, Users, Clients, Services, Appointments, Payments, ClientService, Calendar, Notes
from routes.admins import admins_bp
from routes.businesses import businesses_bp
from routes.users import users_bp
from routes.clients import clients_bp
from routes.services import services_bp
from routes.appointments import appointments_bp
from routes.payments import payments_bp
from routes.client_services import client_services_bp
from routes.calendar import calendar_bp

load_dotenv()

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///kare.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'tu-clave-secreta-cambiar-en-produccion')

db.init_app(app)
jwt = JWTManager(app)
CORS(app)

with app.app_context():
    db.create_all()

# ============================================================================
# FLASK-ADMIN SETUP
# ============================================================================

class AdminModelView(ModelView):
    """Clase personalizada para ModelView con protección"""
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('admin.index'))


# Crear instancia de Admin
admin = Admin(
    app,
    name='Kare - Panel de Administración'
)

# Registrar modelos en Flask-Admin
admin.add_view(AdminModelView(Admins, db.session, name='Administradores'))
admin.add_view(AdminModelView(Businesses, db.session, name='Negocios'))
admin.add_view(AdminModelView(Users, db.session, name='Empleados'))
admin.add_view(AdminModelView(Clients, db.session, name='Clientes'))
admin.add_view(AdminModelView(Services, db.session, name='Servicios'))
admin.add_view(AdminModelView(Appointments, db.session, name='Citas'))
admin.add_view(AdminModelView(Payments, db.session, name='Pagos'))
admin.add_view(AdminModelView(ClientService, db.session, name='Servicios de Clientes'))
admin.add_view(AdminModelView(Calendar, db.session, name='Calendario'))
admin.add_view(AdminModelView(Notes, db.session, name='Notas'))

# ============================================================================
# BLUEPRINTS - RUTAS API
# ============================================================================

app.register_blueprint(admins_bp)
app.register_blueprint(businesses_bp)
app.register_blueprint(users_bp)
app.register_blueprint(clients_bp)
app.register_blueprint(services_bp)
app.register_blueprint(appointments_bp)
app.register_blueprint(payments_bp)
app.register_blueprint(client_services_bp)
app.register_blueprint(calendar_bp)

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health():
    return {"status": "ok"}, 200

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    app.run(debug=True, port=5000)