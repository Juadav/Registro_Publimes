from extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash

class Rol(db.Model):
    __tablename__ = 'rol'
    idRol = db.Column(db.Integer, primary_key=True)
    nombreRol = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.String(200))
    usuarios = db.relationship('UsuarioRol', back_populates='rol')

class Usuario(db.Model):
    __tablename__ = 'usuario'
    idUsuario = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    roles = db.relationship('UsuarioRol', back_populates='usuario')
    clientes_asignados = db.relationship('Cliente', back_populates='operador_publimes')
    envios_realizados = db.relationship('EnvioCampania', back_populates='usuario')
    transferencias_supervisor = db.relationship('TransferenciaTelefono', foreign_keys='TransferenciaTelefono.idSupervisorHistorial', back_populates='supervisor_historial')
    transferencias_origen = db.relationship('TransferenciaTelefono', foreign_keys='TransferenciaTelefono.idOperadorPublimes', back_populates='operador_publimes')

class UsuarioRol(db.Model):
    __tablename__ = 'usuario_rol'
    idUsuario = db.Column(db.Integer, db.ForeignKey('usuario.idUsuario'), primary_key=True)
    idRol = db.Column(db.Integer, db.ForeignKey('rol.idRol'), primary_key=True)
    fecha_asignacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    usuario = db.relationship('Usuario', back_populates='roles')
    rol = db.relationship('Rol', back_populates='usuarios')

class Cliente(db.Model):
    __tablename__ = 'cliente'
    idCliente = db.Column(db.Integer, primary_key=True)
    nombreCliente = db.Column(db.String(100), nullable=False)
    contacto_principal = db.Column(db.String(100))
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(100))
    fecha_registro = db.Column(db.Date)
    activo = db.Column(db.Boolean, default=True)
    
    idOperadorPublimes = db.Column(db.Integer, db.ForeignKey('usuario.idUsuario'))
    operador_publimes = db.relationship('Usuario', back_populates='clientes_asignados')
    campanias = db.relationship('Campania', back_populates='cliente')

class Campania(db.Model):
    __tablename__ = 'campania'
    idCampania = db.Column(db.Integer, primary_key=True)
    idCliente = db.Column(db.Integer, db.ForeignKey('cliente.idCliente'))
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    tipo_envio = db.Column(db.String(50))
    tipo_contenido = db.Column(db.String(50))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), default='PENDIENTE')
    
    cliente = db.relationship('Cliente', back_populates='campanias')
    envios = db.relationship('EnvioCampania', back_populates='campania')

class EnvioCampania(db.Model):
    __tablename__ = 'envio_campania'
    idEnvio = db.Column(db.Integer, primary_key=True)
    idCampania = db.Column(db.Integer, db.ForeignKey('campania.idCampania'))
    idUsuario = db.Column(db.Integer, db.ForeignKey('usuario.idUsuario'))
    fecha_envio = db.Column(db.DateTime, default=datetime.utcnow)
    cantidad_programada = db.Column(db.Integer)
    estado = db.Column(db.String(20), default='PROGRAMADO')
    observaciones = db.Column(db.Text)
    
    campania = db.relationship('Campania', back_populates='envios')
    usuario = db.relationship('Usuario', back_populates='envios_realizados')
    detalles_chip = db.relationship('DetalleEnvioChip', back_populates='envio')
    resultados = db.relationship('ResultadoEnvio', back_populates='envio')

class DetalleEnvioChip(db.Model):
    __tablename__ = 'detalle_envio_chip'
    idDetalle = db.Column(db.Integer, primary_key=True)
    idEnvio = db.Column(db.Integer, db.ForeignKey('envio_campania.idEnvio'))
    idChip = db.Column(db.Integer, db.ForeignKey('chip.idChip'))
    cantidad_enviada = db.Column(db.Integer, default=0)
    cantidad_fallida = db.Column(db.Integer, default=0)
    fecha_inicio = db.Column(db.DateTime)
    fecha_fin = db.Column(db.DateTime)
    estado = db.Column(db.String(20), default='PENDIENTE')
    
    envio = db.relationship('EnvioCampania', back_populates='detalles_chip')
    chip = db.relationship('Chip', back_populates='envios')

class ResultadoEnvio(db.Model):
    __tablename__ = 'resultado_envio'
    idResultado = db.Column(db.Integer, primary_key=True)
    idEnvio = db.Column(db.Integer, db.ForeignKey('envio_campania.idEnvio'))
    idUsuario = db.Column(db.Integer, db.ForeignKey('usuario.idUsuario'))
    enviados = db.Column(db.Integer)
    fallidos = db.Column(db.Integer)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    envio = db.relationship('EnvioCampania', back_populates='resultados')
    usuario = db.relationship('Usuario')

class Celular(db.Model):
    __tablename__ = 'celular'
    idCelular = db.Column(db.Integer, primary_key=True)
    imei = db.Column(db.String(20), unique=True, nullable=False)
    marca = db.Column(db.String(50))
    modelo = db.Column(db.String(50))
    fecha_adquisicion = db.Column(db.Date)
    estado = db.Column(db.String(20), default='DISPONIBLE')
    
    chips = db.relationship('CelularChip', back_populates='celular')
    transferencias = db.relationship('TransferenciaTelefono', back_populates='celular')

class Chip(db.Model):
    __tablename__ = 'chip'
    idChip = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False)
    operadora = db.Column(db.String(50), nullable=False)
    tipo_linea = db.Column(db.String(50))
    fecha_activacion = db.Column(db.Date)
    estado_actual = db.Column(db.String(20), default='ACTIVO')
    
    celulares = db.relationship('CelularChip', back_populates='chip')
    estados = db.relationship('ChipEstadoRelacion', back_populates='chip')
    envios = db.relationship('DetalleEnvioChip', back_populates='chip')

class CelularChip(db.Model):
    __tablename__ = 'celular_chip'
    idCelular = db.Column(db.Integer, db.ForeignKey('celular.idCelular'), primary_key=True)
    idChip = db.Column(db.Integer, db.ForeignKey('chip.idChip'), primary_key=True)
    fecha_asignacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_remocion = db.Column(db.DateTime)
    usuario_asignacion = db.Column(db.Integer, db.ForeignKey('usuario.idUsuario'))
    
    celular = db.relationship('Celular', back_populates='chips')
    chip = db.relationship('Chip', back_populates='celulares')
    usuario = db.relationship('Usuario')

class ChipEstado(db.Model):
    __tablename__ = 'chip_estado'
    idEstado = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    
    chips = db.relationship('ChipEstadoRelacion', back_populates='estado')

class ChipEstadoRelacion(db.Model):
    __tablename__ = 'chip_estado_relacion'
    id = db.Column(db.Integer, primary_key=True)
    idChip = db.Column(db.Integer, db.ForeignKey('chip.idChip'), nullable=False)
    idEstado = db.Column(db.Integer, db.ForeignKey('chip_estado.idEstado'), nullable=False)
    fecha_adquisicion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_perdida = db.Column(db.DateTime)
    
    chip = db.relationship('Chip', back_populates='estados')
    estado = db.relationship('ChipEstado', back_populates='chips')

class TransferenciaTelefono(db.Model):
    __tablename__ = 'transferencia_telefono'
    idTransferencia = db.Column(db.Integer, primary_key=True)
    idCelular = db.Column(db.Integer, db.ForeignKey('celular.idCelular'))
    fecha_transferencia = db.Column(db.DateTime, default=datetime.utcnow)
    idSupervisorHistorial = db.Column(db.Integer, db.ForeignKey('usuario.idUsuario'))
    idOperadorPublimes = db.Column(db.Integer, db.ForeignKey('usuario.idUsuario'))
    
    celular = db.relationship('Celular', back_populates='transferencias')
    supervisor_historial = db.relationship('Usuario', foreign_keys=[idSupervisorHistorial], back_populates='transferencias_supervisor')
    operador_publimes = db.relationship('Usuario', foreign_keys=[idOperadorPublimes], back_populates='transferencias_origen')

def init_db(app):
    """Función para inicializar la base de datos"""
    with app.app_context():
        db.create_all()
        
        # Crear roles básicos si no existen
        if not Rol.query.first():
            roles = [
                Rol(nombreRol='Administrador General', descripcion='Acceso completo al sistema'),
                Rol(nombreRol='Supervisor Operaciones', descripcion='Supervisa operaciones de mensajería'),
                Rol(nombreRol='Operador Publimes', descripcion='Operador de campañas de mensajería'),
                Rol(nombreRol='Supervisor Historial', descripcion='Supervisa el historial de equipos'),
                Rol(nombreRol='Operador Historial', descripcion='Gestiona el historial de equipos')
            ]
            db.session.add_all(roles)
            db.session.commit()
        
        # Crear usuario admin si no existe
        if not Usuario.query.filter_by(username='admin').first():
            admin = Usuario(
                nombre='Administrador',
                username='admin',
                password=generate_password_hash('admin123'),
                activo=True
            )
            db.session.add(admin)
            db.session.commit()

            admin_rol = UsuarioRol(
                idUsuario=admin.idUsuario,
                idRol=1  # ID del Administrador General
            )
            db.session.add(admin_rol)
            db.session.commit()

        # Crear estados básicos de chips si no existen
        if not ChipEstado.query.first():
            estados = [
                ChipEstado(nombre='ACTIVO'),
                ChipEstado(nombre='INACTIVO'),
                ChipEstado(nombre='SUSPENDIDO'),
                ChipEstado(nombre='PERDIDO')
            ]
            db.session.add_all(estados)
            db.session.commit()