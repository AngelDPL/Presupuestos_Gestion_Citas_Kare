from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({"message": "¡Hola desde Flask!"})

@app.route('/api/usuarios', methods=['GET'])
def get_usuarios():
    usuarios = [
        {"id": 1, "nombre": "Juan", "email": "juan@example.com"},
        {"id": 2, "nombre": "María", "email": "maria@example.com"},
        {"id": 3, "nombre": "Pedro", "email": "pedro@example.com"}
    ]
    return jsonify(usuarios)

if __name__ == '__main__':
    app.run(debug=True, port=5000)