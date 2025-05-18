from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
from extensions import db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mensajeria.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar db con app
db.init_app(app)

# Importar modelos después de inicializar db
from models import (
    Rol, Usuario, UsuarioRol, 
    Cliente, Campania, EnvioCampania,
    DetalleEnvioChip, ResultadoEnvio,
    Celular, Chip, CelularChip,
    ChipEstado, ChipEstadoRelacion,
    TransferenciaTelefono
)

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

def init_db():
    with app.app_context():
        db.create_all()
        
        # Insertar roles básicos
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
                password=generate_password_hash('admin123')
            )
            db.session.add(admin)
            db.session.commit()

            admin_rol = UsuarioRol(
                idUsuario=admin.idUsuario,
                idRol=1  # ID del Administrador General
            )
            db.session.add(admin_rol)
            db.session.commit()

        # Insertar estados básicos del chip
        if not ChipEstado.query.first():
            estados = [
                ChipEstado(nombre='ACTIVO'),
                ChipEstado(nombre='INACTIVO'),
                ChipEstado(nombre='SUSPENDIDO'),
                ChipEstado(nombre='PERDIDO')
            ]
            db.session.add_all(estados)
            db.session.commit()

# =============================================
# DECORATORS AND HELPER FUNCTIONS
# =============================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor inicie sesión para acceder a esta página', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Por favor inicie sesión para acceder a esta página', 'danger')
                return redirect(url_for('login'))
            
            user = db.session.get(Usuario, session['user_id'])
            user_roles = [ur.rol.nombreRol for ur in user.roles]
            
            if not any(role in user_roles for role in roles):
                flash('No tiene permisos para acceder a esta página', 'danger')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

# =============================================
# APPLICATION ROUTES
# =============================================

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = Usuario.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.idUsuario
            session['username'] = user.username
            session['nombre'] = user.nombre
            session['roles'] = [ur.rol.nombreRol for ur in user.roles]
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login/login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Ha cerrado sesión correctamente', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = db.session.get(Usuario, session['user_id'])
    user_roles = [ur.rol.nombreRol for ur in user.roles]
    
    context = {
        'nombre': user.nombre,
        'roles': user_roles
    }
    
    if 'Administrador General' in user_roles or 'Supervisor Operaciones' in user_roles:
        context['total_campanias'] = Campania.query.count()
        context['campanias_pendientes'] = Campania.query.filter_by(estado='PENDIENTE').count()
    
    if 'Administrador General' in user_roles or 'Supervisor Historial' in user_roles:
        context['total_celulares'] = Celular.query.count()
        context['total_chips'] = Chip.query.count()
    
    return render_template('dashboard.html', **context)
# =============================================
# RUTAS PARA GESTIÓN DE USUARIOS Y ROLES (Solo Admin)
# =============================================

@app.route('/admin/usuarios')
@login_required
@role_required('Administrador General')
def gestion_usuarios():
    usuarios = Usuario.query.all()
    roles = Rol.query.all()
    return render_template('admin/usuarios.html', usuarios=usuarios, roles=roles)

@app.route('/admin/usuarios/nuevo', methods=['GET', 'POST'])
@login_required
@role_required('Administrador General')
def nuevo_usuario():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        username = request.form.get('username')
        password = request.form.get('password')
        roles_seleccionados = request.form.getlist('roles')
        
        # Validar que el usuario no exista
        if Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe', 'danger')
            return redirect(url_for('nuevo_usuario'))
        
        nuevo_usuario = Usuario(
            nombre=nombre,
            username=username,
            password=generate_password_hash(password)
        )
        
        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            
            # Asignar roles
            for rol_id in roles_seleccionados:
                usuario_rol = UsuarioRol(
                    idUsuario=nuevo_usuario.idUsuario,
                    idRol=rol_id
                )
                db.session.add(usuario_rol)
            
            db.session.commit()
            flash('Usuario creado con éxito', 'success')
            return redirect(url_for('gestion_usuarios'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear usuario: {str(e)}', 'danger')
    
    roles = Rol.query.all()
    return render_template('admin/nuevo_usuario.html', roles=roles)

@app.route('/admin/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('Administrador General')
def editar_usuario(id):
    usuario = db.session.get(Usuario, id)
    if not usuario:
        flash('Usuario no encontrado', 'danger')
        return redirect(url_for('gestion_usuarios'))
    
    if request.method == 'POST':
        usuario.nombre = request.form.get('nombre')
        nuevo_password = request.form.get('password')
        
        if nuevo_password:
            usuario.password = generate_password_hash(nuevo_password)
        
        # Actualizar roles
        roles_seleccionados = [int(r) for r in request.form.getlist('roles')]
        roles_actuales = [ur.idRol for ur in usuario.roles]
        
        # Eliminar roles no seleccionados
        for rol in usuario.roles:
            if rol.idRol not in roles_seleccionados:
                db.session.delete(rol)
        
        # Agregar nuevos roles
        for rol_id in roles_seleccionados:
            if rol_id not in roles_actuales:
                usuario_rol = UsuarioRol(
                    idUsuario=usuario.idUsuario,
                    idRol=rol_id
                )
                db.session.add(usuario_rol)
        
        try:
            db.session.commit()
            flash('Usuario actualizado con éxito', 'success')
            return redirect(url_for('gestion_usuarios'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar usuario: {str(e)}', 'danger')
    
    roles = Rol.query.all()
    return render_template('admin/editar_usuario.html', usuario=usuario, roles=roles)

@app.route('/admin/usuarios/eliminar/<int:id>', methods=['POST'])
@login_required
@role_required('Administrador General')
def eliminar_usuario(id):
    usuario = db.session.get(Usuario, id)
    if not usuario:
        flash('Usuario no encontrado', 'danger')
        return redirect(url_for('gestion_usuarios'))
    
    if usuario.username == 'admin':
        flash('No se puede eliminar el usuario admin', 'danger')
        return redirect(url_for('gestion_usuarios'))
    
    try:
        # Eliminar relaciones de roles primero
        UsuarioRol.query.filter_by(idUsuario=id).delete()
        db.session.delete(usuario)
        db.session.commit()
        flash('Usuario eliminado con éxito', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar usuario: {str(e)}', 'danger')
    
    return redirect(url_for('gestion_usuarios'))

@app.route('/admin/roles')
@login_required
@role_required('Administrador General')
def gestion_roles():
    roles = Rol.query.all()
    return render_template('admin/roles.html', roles=roles)

@app.route('/admin/roles/nuevo', methods=['GET', 'POST'])
@login_required
@role_required('Administrador General')
def nuevo_rol():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        
        if Rol.query.filter_by(nombreRol=nombre).first():
            flash('El rol ya existe', 'danger')
            return redirect(url_for('nuevo_rol'))
        
        nuevo_rol = Rol(
            nombreRol=nombre,
            descripcion=descripcion
        )
        
        try:
            db.session.add(nuevo_rol)
            db.session.commit()
            flash('Rol creado con éxito', 'success')
            return redirect(url_for('gestion_roles'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear rol: {str(e)}', 'danger')
    
    return render_template('admin/nuevo_rol.html')

@app.route('/admin/roles/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('Administrador General')
def editar_rol(id):
    rol = db.session.get(Rol, id)
    if not rol:
        flash('Rol no encontrado', 'danger')
        return redirect(url_for('gestion_roles'))
    
    if request.method == 'POST':
        rol.nombreRol = request.form.get('nombre')
        rol.descripcion = request.form.get('descripcion')
        
        try:
            db.session.commit()
            flash('Rol actualizado con éxito', 'success')
            return redirect(url_for('gestion_roles'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar rol: {str(e)}', 'danger')
    
    return render_template('admin/editar_rol.html', rol=rol)

@app.route('/admin/roles/eliminar/<int:id>', methods=['POST'])
@login_required
@role_required('Administrador General')
def eliminar_rol(id):
    rol = db.session.get(Rol, id)
    if not rol:
        flash('Rol no encontrado', 'danger')
        return redirect(url_for('gestion_roles'))
    
    if rol.idRol == 1:  # No permitir eliminar el rol de Administrador General
        flash('No se puede eliminar este rol', 'danger')
        return redirect(url_for('gestion_roles'))
    
    try:
        # Verificar si hay usuarios con este rol
        if UsuarioRol.query.filter_by(idRol=id).count() > 0:
            flash('No se puede eliminar el rol porque tiene usuarios asignados', 'danger')
            return redirect(url_for('gestion_roles'))
        
        db.session.delete(rol)
        db.session.commit()
        flash('Rol eliminado con éxito', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar rol: {str(e)}', 'danger')
    
    return redirect(url_for('gestion_roles'))
# =============================================
# RUTAS PARA GESTIÓN DE CELULARES (CRUD)
# =============================================

@app.route('/celulares')
@login_required
@role_required('Administrador General', 'Supervisor Historial', 'Operador Historial')
def gestion_celulares():
    celulares = Celular.query.all()
    return render_template('historial/gestor_celulares.html', celulares=celulares)

@app.route('/celulares/nuevo', methods=['GET', 'POST'])
@login_required
@role_required('Administrador General', 'Supervisor Historial')
def nuevo_celular():
    if request.method == 'POST':
        imei = request.form.get('imei')
        marca = request.form.get('marca')
        modelo = request.form.get('modelo')
        fecha_adquisicion = request.form.get('fecha_adquisicion')
        estado = request.form.get('estado', 'DISPONIBLE')
        
        # Validar que el IMEI no exista
        if Celular.query.filter_by(imei=imei).first():
            flash('El IMEI ya está registrado', 'danger')
            return redirect(url_for('nuevo_celular'))
        
        nuevo_celular = Celular(
            imei=imei,
            marca=marca,
            modelo=modelo,
            fecha_adquisicion=datetime.strptime(fecha_adquisicion, '%Y-%m-%d') if fecha_adquisicion else None,
            estado=estado
        )
        
        try:
            db.session.add(nuevo_celular)
            db.session.commit()
            flash('Celular registrado con éxito', 'success')
            return redirect(url_for('gestion_celulares'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar celular: {str(e)}', 'danger')
    
    return render_template('historial/nuevo_celular.html')

@app.route('/celulares/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('Administrador General', 'Supervisor Historial')
def editar_celular(id):
    celular = db.session.get(Celular, id)
    if not celular:
        flash('Celular no encontrado', 'danger')
        return redirect(url_for('gestion_celulares'))
    
    if request.method == 'POST':
        celular.imei = request.form.get('imei')
        celular.marca = request.form.get('marca')
        celular.modelo = request.form.get('modelo')
        celular.estado = request.form.get('estado')
        fecha_adquisicion = request.form.get('fecha_adquisicion')
        celular.fecha_adquisicion = datetime.strptime(fecha_adquisicion, '%Y-%m-%d') if fecha_adquisicion else None
        
        try:
            db.session.commit()
            flash('Celular actualizado con éxito', 'success')
            return redirect(url_for('gestion_celulares'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar celular: {str(e)}', 'danger')
    
    return render_template('historial/editar_celular.html', celular=celular)

@app.route('/celulares/eliminar/<int:id>', methods=['POST'])
@login_required
@role_required('Administrador General', 'Supervisor Historial')
def eliminar_celular(id):
    celular = db.session.get(Celular, id)
    if not celular:
        flash('Celular no encontrado', 'danger')
        return redirect(url_for('gestion_celulares'))
    
    try:
        # Verificar si el celular tiene chips asociados
        if celular.chips:
            flash('No se puede eliminar el celular porque tiene chips asociados', 'danger')
            return redirect(url_for('gestion_celulares'))
        
        db.session.delete(celular)
        db.session.commit()
        flash('Celular eliminado con éxito', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar celular: {str(e)}', 'danger')
    
    return redirect(url_for('gestion_celulares'))

# =============================================
# RUTAS PARA GESTIÓN DE CHIPS (CRUD)
# =============================================

@app.route('/chips')
@login_required
@role_required('Administrador General', 'Supervisor Historial', 'Operador Historial')
def gestion_chips():
    chips = Chip.query.all()
    estados = ChipEstado.query.all()
    return render_template('historial/gestor_chips.html', chips=chips, estados=estados)

@app.route('/chips/nuevo', methods=['GET', 'POST'])
@login_required
@role_required('Administrador General', 'Supervisor Historial')
def nuevo_chip():
    if request.method == 'POST':
        numero = request.form.get('numero')
        operadora = request.form.get('operadora')
        tipo_linea = request.form.get('tipo_linea')
        fecha_activacion = request.form.get('fecha_activacion')
        estado_actual = request.form.get('estado_actual')
        
        # Validar que el número no exista
        if Chip.query.filter_by(numero=numero).first():
            flash('El número de chip ya está registrado', 'danger')
            return redirect(url_for('nuevo_chip'))
        
        nuevo_chip = Chip(
            numero=numero,
            operadora=operadora,
            tipo_linea=tipo_linea,
            fecha_activacion=datetime.strptime(fecha_activacion, '%Y-%m-%d') if fecha_activacion else None,
            estado_actual=estado_actual
        )
        
        try:
            db.session.add(nuevo_chip)
            db.session.commit()
            
            # Registrar el estado inicial del chip
            estado = ChipEstado.query.filter_by(nombre=estado_actual).first()
            if estado:
                estado_chip = ChipEstadoRelacion(
                    idChip=nuevo_chip.idChip,
                    idEstado=estado.idEstado,
                    fecha_adquisicion=datetime.utcnow()
                )
                db.session.add(estado_chip)
                db.session.commit()
            
            flash('Chip registrado con éxito', 'success')
            return redirect(url_for('gestion_chips'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar chip: {str(e)}', 'danger')
    
    estados = ChipEstado.query.all()
    return render_template('historial/nuevo_chip.html', estados=estados)

@app.route('/chips/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('Administrador General', 'Supervisor Historial')
def editar_chip(id):
    chip = db.session.get(Chip, id)
    if not chip:
        flash('Chip no encontrado', 'danger')
        return redirect(url_for('gestion_chips'))
    
    if request.method == 'POST':
        chip.numero = request.form.get('numero')
        chip.operadora = request.form.get('operadora')
        chip.tipo_linea = request.form.get('tipo_linea')
        nuevo_estado = request.form.get('estado_actual')
        fecha_activacion = request.form.get('fecha_activacion')
        chip.fecha_activacion = datetime.strptime(fecha_activacion, '%Y-%m-%d') if fecha_activacion else None
        
        try:
            # Verificar si el estado actual ha cambiado
            if chip.estado_actual != nuevo_estado:
                # Actualizar el estado actual
                chip.estado_actual = nuevo_estado
                
                # Registrar el nuevo estado
                estado = ChipEstado.query.filter_by(nombre=nuevo_estado).first()
                if estado:
                    estado_chip = ChipEstadoRelacion(
                        idChip=id,
                        idEstado=estado.idEstado,
                        fecha_adquisicion=datetime.utcnow()
                    )
                    db.session.add(estado_chip)
            
            db.session.commit()
            flash('Chip actualizado con éxito', 'success')
            return redirect(url_for('gestion_chips'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar chip: {str(e)}', 'danger')
    
    estados = ChipEstado.query.all()
    return render_template('historial/editar_chip.html', chip=chip, estados=estados)

@app.route('/chips/eliminar/<int:id>', methods=['POST'])
@login_required
@role_required('Administrador General', 'Supervisor Historial')
def eliminar_chip(id):
    chip = db.session.get(Chip, id)
    if not chip:
        flash('Chip no encontrado', 'danger')
        return redirect(url_for('gestion_chips'))
    
    try:
        # Verificar si el chip está asignado a un celular
        if chip.celulares:
            flash('No se puede eliminar el chip porque está asignado a un celular', 'danger')
            return redirect(url_for('gestion_chips'))
        
        # Eliminar los estados asociados al chip
        ChipEstadoRelacion.query.filter_by(idChip=id).delete()
        
        db.session.delete(chip)
        db.session.commit()
        flash('Chip eliminado con éxito', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar chip: {str(e)}', 'danger')
    
    return redirect(url_for('gestion_chips'))

# =============================================
# RUTAS PARA ASIGNACIÓN DE CHIPS A CELULARES
# =============================================

@app.route('/celulares/<int:id_celular>/chips', methods=['GET', 'POST'])
@login_required
@role_required('Administrador General', 'Supervisor Historial', 'Operador Historial')
def gestion_chips_celular(id_celular):
    celular = db.session.get(Celular, id_celular)
    if not celular:
        flash('Celular no encontrado', 'danger')
        return redirect(url_for('gestion_celulares'))
    
    if request.method == 'POST':
        id_chip = request.form.get('id_chip')
        
        # Verificar que el chip no esté ya asignado a otro celular
        asignacion_existente = CelularChip.query.filter_by(idChip=id_chip, fecha_remocion=None).first()
        if asignacion_existente:
            flash('Este chip ya está asignado a otro celular', 'danger')
            return redirect(url_for('gestion_chips_celular', id_celular=id_celular))
        
        # Verificar que el celular no tenga más de 2 chips asignados
        chips_activos = CelularChip.query.filter_by(idCelular=id_celular, fecha_remocion=None).count()
        if chips_activos >= 2:
            flash('No se pueden asignar más de 2 chips a un celular', 'danger')
            return redirect(url_for('gestion_chips_celular', id_celular=id_celular))
        
        nueva_asignacion = CelularChip(
            idCelular=id_celular,
            idChip=id_chip,
            usuario_asignacion=session['user_id']
        )
        
        try:
            db.session.add(nueva_asignacion)
            db.session.commit()
            flash('Chip asignado con éxito', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al asignar chip: {str(e)}', 'danger')
        
        return redirect(url_for('gestion_chips_celular', id_celular=id_celular))
    
    # Obtener chips disponibles (no asignados actualmente)
    chips_asignados = [cc.idChip for cc in celular.chips if cc.fecha_remocion is None]
    chips_disponibles = Chip.query.filter(~Chip.idChip.in_(chips_asignados)).all()
    
    return render_template('historial/gestion_chips_celular.html', 
                         celular=celular, 
                         chips_disponibles=chips_disponibles)

@app.route('/celulares/<int:id_celular>/remover-chip/<int:id_chip>', methods=['POST'])
@login_required
@role_required('Administrador General', 'Supervisor Historial')
def remover_chip_celular(id_celular, id_chip):
    asignacion = CelularChip.query.filter_by(
        idCelular=id_celular, 
        idChip=id_chip,
        fecha_remocion=None
    ).first()
    
    if not asignacion:
        flash('Asignación no encontrada', 'danger')
        return redirect(url_for('gestion_chips_celular', id_celular=id_celular))
    
    asignacion.fecha_remocion = datetime.utcnow()
    
    try:
        db.session.commit()
        flash('Chip removido del celular con éxito', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al remover chip: {str(e)}', 'danger')
    
    return redirect(url_for('gestion_chips_celular', id_celular=id_celular))

# =============================================
# RUTAS PARA GESTIÓN DE ESTADOS DE CHIPS
# =============================================

@app.route('/estados-chips')
@login_required
@role_required('Administrador General', 'Supervisor Historial')
def gestion_estados_chips():
    estados = ChipEstado.query.all()
    return render_template('historial/gestor_estados.html', estados=estados)

@app.route('/historial-estado-chip/<int:id_chip>')
@login_required
@role_required('Administrador General', 'Supervisor Historial', 'Operador Historial')
def historial_estado_chip(id_chip):
    chip = db.session.get(Chip, id_chip)
    if not chip:
        flash('Chip no encontrado', 'danger')
        return redirect(url_for('gestion_chips'))
    
    historial = ChipEstadoRelacion.query.filter_by(idChip=id_chip).order_by(ChipEstadoRelacion.fecha_adquisicion.desc()).all()
    return render_template('historial/historial_estado_chip.html', chip=chip, historial=historial)

# =============================================
# EJECUCIÓN DE LA APLICACIÓN
# =============================================
if __name__ == '__main__':
    init_db()
    app.run(
        host='0.0.0.0',  # Accesible desde otras máquinas
        port=5005,       # Puerto personalizado
        debug=True,      # Debug activado (solo desarrollo)
        threaded=True    # Maneja múltiples peticiones
    )