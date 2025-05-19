from functools import wraps
from flask import flash, redirect, url_for, session, abort
from modelo import Usuario

def requiere_login(f):
    """Decorador para verificar sesión activa"""
    @wraps(f)
    def decorador(*args, **kwargs):
        if 'id_usuario' not in session:
            flash('Debe iniciar sesión para acceder a esta página', 'danger')
            return redirect(url_for('login.iniciar_sesion'))
        return f(*args, **kwargs)
    return decorador

def requiere_rol(*roles_permitidos):
    """Decorador para validar roles de usuario"""
    def decorador(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Primero verifica si está logueado
            if 'id_usuario' not in session:
                flash('Autenticación requerida', 'warning')
                return redirect(url_for('login.iniciar_sesion'))
            
            # Obtiene el usuario actual
            usuario_actual = Usuario.query.get(session['id_usuario'])
            
            # Verifica si tiene alguno de los roles requeridos
            roles_usuario = {ur.rol.nombreRol for ur in usuario_actual.roles}
            if not roles_usuario.intersection(roles_permitidos):
                flash('No tiene permisos suficientes para esta acción', 'danger')
                return redirect(url_for('login.panel_control'))
            
            return f(*args, **kwargs)
        return wrapper
    return decorador

def requiere_permiso(permiso_necesario):
    """Decorador para validar permisos específicos (extensible)"""
    def decorador(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Implementación básica - puede extenderse
            if not verificar_permiso(session.get('id_usuario'), permiso_necesario):
                flash('Permiso denegado', 'danger')
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorador

# Función de apoyo (puede moverse a un servicio aparte)
def verificar_permiso(id_usuario, permiso):
    """Lógica para verificar permisos específicos"""
    # Implementación básica - consulta a la base de datos
    usuario = Usuario.query.get(id_usuario)
    if not usuario:
        return False
        
    # Aquí iría la lógica real de verificación de permisos
    # Por ahora solo verifica si es admin
    return any(rol.nombreRol == 'Administrador General' for rol in usuario.roles)