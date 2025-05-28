from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from modelo import Usuario
from decoradores import requiere_login
from flask import current_app

bp_login = Blueprint('login', __name__, template_folder='templates')

@bp_login.route('/', methods=['GET', 'POST'], endpoint='iniciar_sesion')
def iniciar_sesion():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        contrasena = request.form.get('contrasena')
        
        usuario_db = Usuario.query.filter_by(username=usuario).first()
        
        if usuario_db and check_password_hash(usuario_db.password, contrasena):
            session['id_usuario'] = usuario_db.idUsuario
            session['usuario'] = usuario_db.username
            session['nombre'] = usuario_db.nombre
            session['roles'] = [ur.rol.nombreRol for ur in usuario_db.roles]
            
            current_app.logger.info(f'Inicio de sesión exitoso para el usuario: {usuario}')
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('login.panel_control'))
        
        current_app.logger.warning(f'Intento de inicio de sesión fallido para el usuario: {usuario}')
        flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login/login.html')

@bp_login.route('/logout', endpoint='logout')
@requiere_login
def cerrar_sesion():
    usuario_actual = Usuario.query.get(session['id_usuario'])
    current_app.logger.info(f"Usuario {usuario_actual.username} cerró sesión")
    session.clear()
    flash('Ha cerrado sesión correctamente', 'info')
    return redirect(url_for('login.iniciar_sesion'))

@bp_login.route('/dashboard', endpoint='panel_control')
@requiere_login
def panel_control():
    from modelo import Campania, Celular, Chip
    
    usuario_actual = Usuario.query.get(session['id_usuario'])
    current_app.logger.info(f"Usuario {usuario_actual.username} accedió al panel de control")
    
    contexto = {
        'nombre': usuario_actual.nombre,
        'roles': session['roles']
    }
    
    if any(rol in ['Administrador General', 'Supervisor Operaciones'] for rol in session['roles']):
        contexto['total_campanias'] = Campania.query.count()
        contexto['campanias_pendientes'] = Campania.query.filter_by(estado='PENDIENTE').count()
    
    if any(rol in ['Administrador General', 'Supervisor Historial'] for rol in session['roles']):
        contexto['total_celulares'] = Celular.query.count()
        contexto['total_chips'] = Chip.query.count()
    
    return render_template('dashboard.html', **contexto)

@bp_login.route('/perfil', endpoint='ver_perfil')
@requiere_login
def ver_perfil():
    usuario = Usuario.query.get(session['id_usuario'])
    current_app.logger.info(f"Usuario {usuario.username} accedió a su perfil")
    return render_template('login/perfil.html', usuario=usuario)