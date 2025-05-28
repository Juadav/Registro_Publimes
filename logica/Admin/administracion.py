from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from datetime import datetime
from werkzeug.security import generate_password_hash
from modelo import (
    Rol,
    Usuario,
    UsuarioRol,
    db
)
from decoradores import requiere_login, requiere_rol

class GestorAdministracion:
    def __init__(self):
        self.bp = Blueprint('admin', __name__, url_prefix='/admin')
        self._registrar_rutas()
    
    def _registrar_rutas(self):
        # Rutas para usuarios
        self.bp.route('/usuarios', endpoint='gestion_usuarios')(self.gestion_usuarios)
        self.bp.route('/usuarios/nuevo', methods=['GET', 'POST'], endpoint='nuevo_usuario')(self.nuevo_usuario)
        self.bp.route('/usuarios/<int:id>/editar', methods=['GET', 'POST'], endpoint='editar_usuario')(self.editar_usuario)
        self.bp.route('/usuarios/<int:id>/eliminar', methods=['POST'], endpoint='eliminar_usuario')(self.eliminar_usuario)
        
        # Rutas para roles
        self.bp.route('/roles', endpoint='gestion_roles')(self.gestion_roles)
        self.bp.route('/roles/nuevo', methods=['GET', 'POST'], endpoint='nuevo_rol')(self.nuevo_rol)
        self.bp.route('/roles/<int:id>/editar', methods=['GET', 'POST'], endpoint='editar_rol')(self.editar_rol)
        self.bp.route('/roles/<int:id>/eliminar', methods=['POST'], endpoint='eliminar_rol')(self.eliminar_rol)

    # ============ MÉTODOS PARA USUARIOS ============
    @requiere_login
    @requiere_rol('Administrador General')
    def gestion_usuarios(self):
        """Lista todos los usuarios con paginación"""
        pagina = request.args.get('pagina', 1, type=int)
        usuarios = Usuario.query.order_by(
            Usuario.fecha_creacion.desc()
        ).paginate(page=pagina, per_page=10)
        return render_template('admin/usuarios.html', usuarios=usuarios)

    @requiere_login
    @requiere_rol('Administrador General')
    def nuevo_usuario(self):
        """Registra un nuevo usuario con validación de username"""
        if request.method == 'POST':
            form_data = self._validar_formulario_usuario()
            if form_data:
                try:
                    # Verificar si el nombre de usuario ya existe
                    if Usuario.query.filter_by(username=form_data['usuario']['username']).first():
                        flash('El nombre de usuario ya está en uso', 'danger')
                        return render_template('admin/AgregarAdmin/AgregarUsuario.html', 
                                             roles=Rol.query.all(), 
                                             error_username="El nombre de usuario ya está en uso")
                    
                    nuevo_usuario = Usuario(**form_data['usuario'])
                    db.session.add(nuevo_usuario)
                    db.session.flush()  # Para obtener el ID
                    
                    # Asignar roles
                    for rol_id in form_data['roles']:
                        usuario_rol = UsuarioRol(
                            idUsuario=nuevo_usuario.idUsuario,
                            idRol=rol_id
                        )
                        db.session.add(usuario_rol)
                    
                    db.session.commit()
                    flash('Usuario registrado exitosamente', 'success')
                    return redirect(url_for('admin.gestion_usuarios'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error al registrar: {str(e)}', 'danger')
            
        roles = Rol.query.all()
        return render_template('admin/AgregarAdmin/AgregarUsuario.html', roles=roles)

    def _validar_formulario_usuario(self):
        """Valida y procesa datos del formulario de usuario"""
        username = request.form.get('username')
        if Usuario.query.filter_by(username=username).first():
            return None
            
        password = request.form.get('password')
        if not password or len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'danger')
            return None
            
        return {
            'usuario': {
                'nombre': request.form.get('nombre'),
                'username': username,
                'password': generate_password_hash(password),
                'activo': True,
                'fecha_creacion': datetime.now()
            },
            'roles': [int(r) for r in request.form.getlist('roles')]
        }

    @requiere_login
    @requiere_rol('Administrador General')
    def editar_usuario(self, id):
        """Actualiza información de un usuario existente"""
        usuario = Usuario.query.get_or_404(id)
        
        if request.method == 'POST':
            try:
                # Actualizar datos básicos
                usuario.nombre = request.form.get('nombre')
                nuevo_password = request.form.get('password')
                if nuevo_password and len(nuevo_password) >= 6:
                    usuario.password = generate_password_hash(nuevo_password)
                elif nuevo_password:
                    flash('La contraseña debe tener al menos 6 caracteres', 'danger')
                    return redirect(url_for('admin.editar_usuario', id=id))
                
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
                
                db.session.commit()
                flash('Usuario actualizado exitosamente', 'success')
                return redirect(url_for('admin.gestion_usuarios'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar: {str(e)}', 'danger')
        
        roles = Rol.query.all()
        return render_template('admin/EditarAdmin/EditarUsuario.html', 
                            usuario=usuario, 
                            roles=roles)

    @requiere_login
    @requiere_rol('Administrador General')
    def eliminar_usuario(self, id):
        """Elimina un usuario si no es el admin principal"""
        usuario = Usuario.query.get_or_404(id)
        
        if usuario.username == 'admin':
            flash('No se puede eliminar el usuario admin', 'danger')
        else:
            try:
                # Eliminar primero las relaciones en UsuarioRol
                UsuarioRol.query.filter_by(idUsuario=id).delete()
                # Luego eliminar el usuario
                db.session.delete(usuario)
                db.session.commit()
                flash('Usuario eliminado exitosamente', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error al eliminar: {str(e)}', 'danger')
        
        return redirect(url_for('admin.gestion_usuarios'))

    # ============ MÉTODOS PARA ROLES ============
    @requiere_login
    @requiere_rol('Administrador General')
    def gestion_roles(self):
        """Lista todos los roles"""
        roles = Rol.query.order_by(Rol.idRol).all()
        return render_template('admin/roles.html', roles=roles)

    @requiere_login
    @requiere_rol('Administrador General')
    def nuevo_rol(self):
        """Crea un nuevo rol con validación de nombre"""
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            if Rol.query.filter_by(nombreRol=nombre).first():
                flash('El nombre de rol ya existe', 'danger')
            else:
                try:
                    nuevo_rol = Rol(
                        nombreRol=nombre,
                        descripcion=request.form.get('descripcion'),
                        fecha_creacion=datetime.now()
                    )
                    db.session.add(nuevo_rol)
                    db.session.commit()
                    flash('Rol creado exitosamente', 'success')
                    return redirect(url_for('admin.gestion_roles'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error al crear rol: {str(e)}', 'danger')
        
        return render_template('admin/AgregarAdmin/AgregarRol.html')

    @requiere_login
    @requiere_rol('Administrador General')
    def editar_rol(self, id):
        """Actualiza un rol existente"""
        rol = Rol.query.get_or_404(id)
        
        if request.method == 'POST':
            try:
                rol.nombreRol = request.form.get('nombre')
                rol.descripcion = request.form.get('descripcion')
                db.session.commit()
                flash('Rol actualizado exitosamente', 'success')
                return redirect(url_for('admin.gestion_roles'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar rol: {str(e)}', 'danger')
        
        return render_template('admin/EditarAdmin/EditarRol.html', rol=rol)

    @requiere_login
    @requiere_rol('Administrador General')
    def eliminar_rol(self, id):
        """Elimina un rol si no tiene usuarios asignados"""
        rol = Rol.query.get_or_404(id)
        
        if rol.idRol == 1:
            flash('No se puede eliminar este rol', 'danger')
        elif UsuarioRol.query.filter_by(idRol=id).count() > 0:
            flash('No se puede eliminar el rol porque tiene usuarios asignados', 'danger')
        else:
            try:
                db.session.delete(rol)
                db.session.commit()
                flash('Rol eliminado exitosamente', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error al eliminar rol: {str(e)}', 'danger')
        
        return redirect(url_for('admin.gestion_roles'))

# Instanciar y registrar el Blueprint
gestor_admin = GestorAdministracion()
bp_admin = gestor_admin.bp