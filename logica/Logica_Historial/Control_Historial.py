from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from datetime import datetime
from modelo import Celular, db
from decoradores import requiere_login, requiere_rol

class ControlHistorial:
    def __init__(self):
        self.bp = Blueprint('control_historial', __name__, url_prefix='/control-historial')
        self._registrar_rutas()
    
    def _registrar_rutas(self):
        self.bp.route('', methods=['GET'])(self.control_celulares)
        self.bp.route('/nuevo', methods=['GET', 'POST'])(self.nuevo_celular)
        self.bp.route('/<int:id>/editar', methods=['GET', 'POST'])(self.editar_celular)

    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def control_celulares(self):
        """Muestra listado simplificado de celulares para auditoría"""
        celulares = Celular.query.order_by(Celular.idCelular.desc()).all()
        return render_template('historial/Control_Historial/Control_Celulares.html', 
                               celulares=celulares)

    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def nuevo_celular(self):
        """Registro básico para auditoría de celulares"""
        if request.method == 'POST':
            imei = request.form.get('imei')
            
            if not imei or len(imei) < 15:
                flash('IMEI inválido. Debe tener al menos 15 caracteres', 'danger')
            elif Celular.query.filter_by(imei=imei).first():
                flash('El IMEI ya está registrado', 'danger')
            else:
                try:
                    nuevo_cel = Celular(
                        imei=imei,
                        marca=request.form.get('marca', '').upper(),
                        modelo=request.form.get('modelo', '').upper(),
                        estado='DISPONIBLE',
                        fecha_adquisicion=None
                    )
                    db.session.add(nuevo_cel)
                    db.session.commit()
                    flash('Celular registrado en Control de Celulares', 'success')
                    return redirect(url_for('control_historial.control_celulares'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error al registrar: {str(e)}', 'danger')
        
        return render_template('historial/Agregar_Historial/nuevo_celular.html')

    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def editar_celular(self, id):
        """Edición básica de celulares para el control"""
        celular = Celular.query.get_or_404(id)
        
        if request.method == 'POST':
            try:
                nuevo_imei = request.form.get('imei')
                
                if nuevo_imei != celular.imei and Celular.query.filter_by(imei=nuevo_imei).first():
                    flash('El IMEI ya está registrado en otro dispositivo', 'danger')
                else:
                    celular.imei = nuevo_imei
                    celular.marca = request.form.get('marca', '').upper()
                    celular.modelo = request.form.get('modelo', '').upper()
                    
                    db.session.commit()
                    flash('Celular actualizado correctamente', 'success')
                    return redirect(url_for('control_historial.control_celulares'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar: {str(e)}', 'danger')
        
        return render_template('historial/Editar_Historial/editar_celular.html', celular=celular)

# Instanciar y registrar blueprint
control_historial = ControlHistorial()
bp_control_historial = control_historial.bp
