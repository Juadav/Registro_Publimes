from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from datetime import datetime
from modelo import (
    Celular,
    Chip,
    CelularChip,
    ChipEstado,
    ChipEstadoRelacion,
    db
)
from decoradores import requiere_login, requiere_rol

class GestorHistorial:
    def __init__(self):
        self.bp = Blueprint('historial', __name__, url_prefix='/historial')
        self._registrar_rutas()
    
    def _registrar_rutas(self):
        # Rutas para celulares
        self.bp.route('/celulares')(self.gestion_celulares)
        self.bp.route('/celulares/nuevo', methods=['GET', 'POST'])(self.nuevo_celular)
        self.bp.route('/celulares/<int:id>/editar', methods=['GET', 'POST'])(self.editar_celular)
        self.bp.route('/celulares/<int:id>/eliminar', methods=['POST'])(self.eliminar_celular)
        
        # Rutas para chips
        self.bp.route('/chips')(self.gestion_chips)
        self.bp.route('/chips/nuevo', methods=['GET', 'POST'])(self.nuevo_chip)
        self.bp.route('/chips/<int:id>/editar', methods=['GET', 'POST'])(self.editar_chip)
        self.bp.route('/chips/<int:id>/eliminar', methods=['POST'])(self.eliminar_chip)
        
        # Rutas para asignación
        self.bp.route('/celulares/<int:id_celular>/asignar-chip', methods=['GET', 'POST'])(self.asignar_chip)
        self.bp.route('/celulares/<int:id_celular>/remover-chip/<int:id_chip>', methods=['POST'])(self.remover_chip)
        
        # Rutas para estados
        self.bp.route('/estados-chips')(self.gestion_estados)
        self.bp.route('/historial-estado-chip/<int:id_chip>')(self.historial_estado_chip)

    # ============ MÉTODOS PARA CELULARES ============
    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial', 'Operador Historial')
    def gestion_celulares(self):
        """Lista todos los celulares con paginación"""
        pagina = request.args.get('pagina', 1, type=int)
        celulares = Celular.query.order_by(
            Celular.fecha_adquisicion.desc()
        ).paginate(page=pagina, per_page=10)
        return render_template('historial/gestor_celulares.html', celulares=celulares)

    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def nuevo_celular(self):
        """Registra un nuevo celular con validación de IMEI"""
        if request.method == 'POST':
            form_data = self._validar_formulario_celular()
            if form_data:
                try:
                    nuevo_cel = Celular(**form_data)
                    db.session.add(nuevo_cel)
                    db.session.commit()
                    flash('Celular registrado exitosamente', 'success')
                    return redirect(url_for('historial.gestion_celulares'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error al registrar: {str(e)}', 'danger')
        return render_template('historial/nuevo_celular.html')

    def _validar_formulario_celular(self):
        """Valida y procesa datos del formulario de celular"""
        imei = request.form.get('imei')
        if Celular.query.filter_by(imei=imei).first():
            flash('IMEI ya registrado', 'danger')
            return None
            
        return {
            'imei': imei,
            'marca': request.form.get('marca'),
            'modelo': request.form.get('modelo'),
            'fecha_adquisicion': datetime.strptime(
                request.form.get('fecha_adquisicion'), 
                '%Y-%m-%d'
            ) if request.form.get('fecha_adquisicion') else None,
            'estado': request.form.get('estado', 'DISPONIBLE'),
            'usuario_registro': session['id_usuario']
        }

    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def editar_celular(self, id):
        """Actualiza información de un celular existente"""
        celular = Celular.query.get_or_404(id)
        
        if request.method == 'POST':
            try:
                celular.imei = request.form.get('imei')
                celular.marca = request.form.get('marca')
                celular.modelo = request.form.get('modelo')
                celular.estado = request.form.get('estado')
                celular.fecha_adquisicion = datetime.strptime(
                    request.form.get('fecha_adquisicion'), 
                    '%Y-%m-%d'
                ) if request.form.get('fecha_adquisicion') else None
                celular.ultima_actualizacion = datetime.utcnow()
                celular.usuario_actualizacion = session['id_usuario']
                
                db.session.commit()
                flash('Celular actualizado', 'success')
                return redirect(url_for('historial.gestion_celulares'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar: {str(e)}', 'danger')
        
        return render_template('historial/editar_celular.html', celular=celular)

    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def eliminar_celular(self, id):
        """Elimina un celular si no tiene chips asociados"""
        celular = Celular.query.get_or_404(id)
        
        if celular.chips_activos:
            flash('No se puede eliminar: tiene chips asociados', 'danger')
        else:
            try:
                db.session.delete(celular)
                db.session.commit()
                flash('Celular eliminado', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error al eliminar: {str(e)}', 'danger')
        
        return redirect(url_for('historial.gestion_celulares'))

    # ============ MÉTODOS PARA CHIPS ============
    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial', 'Operador Historial')
    def gestion_chips(self):
        """Lista chips con filtros y paginación"""
        estado = request.args.get('estado')
        pagina = request.args.get('pagina', 1, type=int)
        
        query = Chip.query
        if estado:
            query = query.filter_by(estado_actual=estado)
            
        chips = query.order_by(
            Chip.fecha_activacion.desc()
        ).paginate(page=pagina, per_page=10)
        
        estados = ChipEstado.query.all()
        return render_template('historial/gestor_chips.html', 
                             chips=chips, 
                             estados=estados,
                             estado_filtro=estado)

    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def nuevo_chip(self):
        """Registra un nuevo chip con su estado inicial"""
        if request.method == 'POST':
            form_data = self._validar_formulario_chip()
            if form_data:
                try:
                    nuevo_chip = Chip(**form_data['chip'])
                    db.session.add(nuevo_chip)
                    db.session.flush()  # Para obtener el ID
                    
                    if form_data['estado']:
                        estado_rel = ChipEstadoRelacion(
                            idChip=nuevo_chip.idChip,
                            idEstado=form_data['estado'].idEstado,
                            fecha_adquisicion=datetime.utcnow(),
                            usuario_registro=session['id_usuario']
                        )
                        db.session.add(estado_rel)
                    
                    db.session.commit()
                    flash('Chip registrado exitosamente', 'success')
                    return redirect(url_for('historial.gestion_chips'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error al registrar: {str(e)}', 'danger')
        
        estados = ChipEstado.query.all()
        return render_template('historial/nuevo_chip.html', estados=estados)

    def _validar_formulario_chip(self):
        """Valida y procesa datos del formulario de chip"""
        numero = request.form.get('numero')
        if Chip.query.filter_by(numero=numero).first():
            flash('Número de chip ya registrado', 'danger')
            return None
            
        estado = ChipEstado.query.filter_by(
            nombre=request.form.get('estado_actual')
        ).first()
        
        return {
            'chip': {
                'numero': numero,
                'operadora': request.form.get('operadora'),
                'tipo_linea': request.form.get('tipo_linea'),
                'fecha_activacion': datetime.strptime(
                    request.form.get('fecha_activacion'), 
                    '%Y-%m-%d'
                ) if request.form.get('fecha_activacion') else None,
                'estado_actual': request.form.get('estado_actual'),
                'usuario_registro': session['id_usuario']
            },
            'estado': estado
        }

    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def editar_chip(self, id):
        """Edita la información de un chip existente"""
        chip = Chip.query.get_or_404(id)
        estados = ChipEstado.query.all()

        if request.method == 'POST':
            try:
                chip.numero = request.form.get('numero')
                chip.operadora = request.form.get('operadora')
                chip.tipo_linea = request.form.get('tipo_linea')
                nuevo_estado = request.form.get('estado_actual')
                
                # Actualizar estado si cambió
                if chip.estado_actual != nuevo_estado:
                    chip.estado_actual = nuevo_estado
                    nuevo_estado_rel = ChipEstadoRelacion(
                        idChip=chip.idChip,
                        idEstado=ChipEstado.query.filter_by(nombre=nuevo_estado).first().idEstado,
                        fecha_adquisicion=datetime.utcnow(),
                        usuario_registro=session['id_usuario']
                    )
                    db.session.add(nuevo_estado_rel)
                
                db.session.commit()
                flash('Chip actualizado correctamente', 'success')
                return redirect(url_for('historial.gestion_chips'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar chip: {str(e)}', 'danger')

        return render_template('historial/editar_chip.html', 
                            chip=chip, 
                            estados=estados)

    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def eliminar_chip(self, id):
        """Elimina un chip si no está asignado a un celular"""
        chip = Chip.query.get_or_404(id)
        
        if chip.celulares_activos:
            flash('No se puede eliminar: el chip está asignado a un celular', 'danger')
        else:
            try:
                # Eliminar estados asociados primero
                ChipEstadoRelacion.query.filter_by(idChip=id).delete()
                db.session.delete(chip)
                db.session.commit()
                flash('Chip eliminado correctamente', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error al eliminar chip: {str(e)}', 'danger')
        
        return redirect(url_for('historial.gestion_chips'))

    # ============ MÉTODOS PARA ASIGNACIÓN ============
    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial', 'Operador Historial')
    def asignar_chip(self, id_celular):
        """Asigna un chip disponible a un celular"""
        celular = Celular.query.get_or_404(id_celular)
        
        if request.method == 'POST':
            id_chip = request.form.get('id_chip')
            
            if not self._validar_asignacion(celular, id_chip):
                return redirect(url_for('historial.asignar_chip', id_celular=id_celular))
            
            try:
                nueva_asignacion = CelularChip(
                    idCelular=id_celular,
                    idChip=id_chip,
                    usuario_asignacion=session['id_usuario']
                )
                db.session.add(nueva_asignacion)
                db.session.commit()
                flash('Chip asignado exitosamente', 'success')
                return redirect(url_for('historial.ver_celular', id=id_celular))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al asignar: {str(e)}', 'danger')
        
        chips_disponibles = self._obtener_chips_disponibles(celular)
        return render_template('historial/asignar_chip.html',
                            celular=celular,
                            chips=chips_disponibles)

    def _validar_asignacion(self, celular, id_chip):
        """Realiza validaciones para asignación de chips"""
        if CelularChip.query.filter_by(idChip=id_chip, fecha_remocion=None).first():
            flash('Chip ya asignado a otro celular', 'danger')
            return False
            
        if CelularChip.query.filter_by(idCelular=celular.idCelular, fecha_remocion=None).count() >= 2:
            flash('Límite de 2 chips por celular', 'danger')
            return False
            
        return True

    def _obtener_chips_disponibles(self, celular):
        """Obtiene chips no asignados actualmente"""
        asignados = [cc.idChip for cc in celular.chips if cc.fecha_remocion is None]
        return Chip.query.filter(
            ~Chip.idChip.in_(asignados),
            Chip.estado_actual == 'ACTIVO'
        ).all()

    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def remover_chip(self, id_celular, id_chip):
        """Remueve un chip de un celular"""
        asignacion = CelularChip.query.filter_by(
            idCelular=id_celular,
            idChip=id_chip,
            fecha_remocion=None
        ).first_or_404()
        
        try:
            asignacion.fecha_remocion = datetime.utcnow()
            db.session.commit()
            flash('Chip removido exitosamente', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al remover: {str(e)}', 'danger')
        
        return redirect(url_for('historial.ver_celular', id=id_celular))

    # ============ MÉTODOS PARA ESTADOS ============
    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def gestion_estados(self):
        """Muestra todos los estados disponibles"""
        estados = ChipEstado.query.all()
        return render_template('historial/gestor_estados.html', estados=estados)

    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial', 'Operador Historial')
    def historial_estado_chip(self, id_chip):
        """Muestra el historial de estados de un chip"""
        chip = Chip.query.get_or_404(id_chip)
        historial = ChipEstadoRelacion.query.filter_by(
            idChip=id_chip
        ).order_by(
            ChipEstadoRelacion.fecha_adquisicion.desc()
        ).all()
        
        return render_template('historial/historial_estado_chip.html',
                            chip=chip,
                            historial=historial)

# Instanciar y registrar el Blueprint
gestor_historial = GestorHistorial()
bp_historial = gestor_historial.bp