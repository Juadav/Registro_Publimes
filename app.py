import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from modelo import init_db
from extensions import db
from logica.Login.login import bp_login
from logica.Admin.administracion import bp_admin
from datetime import datetime
import os

app = Flask(__name__)

# Configuración de la app
app.config['SECRET_KEY'] = 'atarazana'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mensajeria.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración del logging
if not os.path.exists('logs'):
    os.mkdir('logs')

# Crear un handler que rote los archivos de log, manteniendo 3 archivos de backup de 10MB cada uno
file_handler = RotatingFileHandler('logs/publimes.log', maxBytes=10240, backupCount=3)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)

app.logger.setLevel(logging.INFO)
app.logger.info('Inicio de la aplicación Publimes')

# Inicializar base de datos
db.init_app(app)

# Context processor para el año actual en las plantillas
@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

# Inicializar la base de datos
init_db(app)

# Registrar Blueprints
app.register_blueprint(bp_login)
app.register_blueprint(bp_admin, url_prefix='/admin')



# Iniciar el servidor
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5005,
        debug=True,
        threaded=True
    )