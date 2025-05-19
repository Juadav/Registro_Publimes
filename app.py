from flask import Flask
from modelo import init_db
from extensions import db
from logica.login import bp_login
from logica.administracion import bp_admin
from logica.historial import bp_historial
from datetime import datetime

app = Flask(__name__)

# Configuración de la app
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mensajeria.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize db with app
db.init_app(app)

# Context processor para pasar el año actual a las plantillas
@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

# Inicializar la base de datos con la app
init_db(app)

# Registrar los Blueprints
app.register_blueprint(bp_login)
app.register_blueprint(bp_admin, url_prefix='/admin')
app.register_blueprint(bp_historial)

# Iniciar el servidor
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5005,
        debug=True,
        threaded=True
    )