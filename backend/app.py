from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os

from models import db
from routes.admins import admins_bp
from routes.businesses import businesses_bp
from routes.users import users_bp
from routes.clients import clients_bp

load_dotenv()

app = Flask(__name__)

# Configuración
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')

# Inicializar extensiones
db.init_app(app)
jwt = JWTManager(app)
CORS(app)

# Crear tablas
with app.app_context():
    db.create_all()

# Registrar blueprints
app.register_blueprint(admins_bp)
app.register_blueprint(businesses_bp)
app.register_blueprint(users_bp)
app.register_blueprint(clients_bp)

@app.route('/api/health', methods=['GET'])
def health():
    return {"status": "ok"}, 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)