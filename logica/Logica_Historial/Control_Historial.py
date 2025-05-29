from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from datetime import datetime
from modelo import db, Celular, Chip, ChipEstado, CelularChip, ChipEstadoRelacion, Usuario
from decoradores import requiere_login, requiere_rol
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp
from wtforms import ValidationError


# ==================================================
# CONTROLADOR PARA CELULARES
# ==================================================
class CelularForm(FlaskForm):
    imei = StringField('IMEI', validators=[
        DataRequired(),
        Length(min=15, max=15, message='El IMEI debe tener exactamente 15 dígitos'),
        Regexp('^[0-9]{15}$', message='El IMEI solo debe contener números')
    ])
    marca = StringField('Marca', validators=[DataRequired()])
    modelo = StringField('Modelo', validators=[DataRequired()])
    fecha_adquisicion = DateField('Fecha de Adquisición', validators=[DataRequired()])
    fecha_registro = DateField('Fecha de Registro', validators=[DataRequired()])
    submit = SubmitField('Guardar Celular')

    def __init__(self, *args, **kwargs):
        self.original_imei = kwargs.pop('original_imei', None)
        super(CelularForm, self).__init__(*args, **kwargs)

    def validate_imei(self, field):
        # Validar que el IMEI sea único
        if field.data != self.original_imei:  # Solo validar si cambió el IMEI
            celular_existente = Celular.query.filter_by(imei=field.data).first()
            if celular_existente:
                raise ValidationError('Este IMEI ya está registrado. Debe ser único.')

    def validate(self, extra_validators=None):
        # Validación base
        if not super().validate(extra_validators=extra_validators):
            return False

        # Validar que fecha_adquisicion no sea igual a fecha_registro
        if self.fecha_adquisicion.data == self.fecha_registro.data:
            self.fecha_adquisicion.errors.append('La fecha de adquisición no puede ser igual a la fecha de registro')
            return False

        # Validar que fecha_adquisicion no sea mayor a fecha_registro
        if self.fecha_adquisicion.data > self.fecha_registro.data:
            self.fecha_adquisicion.errors.append('La fecha de adquisición no puede ser posterior a la fecha de registro')
            return False

        return True

class ControlCelular:
    def __init__(self, bp):
        self.bp = bp
        self._registrar_rutas()
    
    def _registrar_rutas(self):
        self.bp.route('/celulares', endpoint='celulares_index')(self.index)
        self.bp.route('/celulares/nuevo', methods=['GET', 'POST'], endpoint='celulares_nuevo')(self.nuevo)
        self.bp.route('/celulares/<int:id>/editar', methods=['GET', 'POST'], endpoint='celulares_editar')(self.editar)
        self.bp.route('/celulares/<int:id>/eliminar', methods=['POST'], endpoint='celulares_eliminar')(self.eliminar)

    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def index(self):
        pagina = request.args.get('pagina', 1, type=int)
        celulares = Celular.query.order_by(
            Celular.fecha_registro.desc(), Celular.marca, Celular.modelo
        ).paginate(page=pagina, per_page=10)
        
        usuario_actual = Usuario.query.get(session['id_usuario'])
        return render_template('historial/Control_Historial/Control_Celular.html', 
                            celulares=celulares,
                            usuario_actual=usuario_actual)
    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def nuevo(self):
        usuario_actual = Usuario.query.get(session['id_usuario'])
        form = CelularForm()
        
        if form.validate_on_submit():
            try:
                # Verificar si el IMEI ya existe
                if Celular.query.filter_by(imei=form.imei.data).first():
                    flash('Este IMEI ya está registrado. Debe ser único.', 'danger')
                    return render_template('historial/Control_Historial/Agregar_ControlHistorial/Agregar_Celular.html',
                                        form=form,
                                        usuario_actual=usuario_actual)

                celular = Celular(
                    imei=form.imei.data,
                    marca=form.marca.data,
                    modelo=form.modelo.data,
                    fecha_adquisicion=form.fecha_adquisicion.data,
                    fecha_registro=form.fecha_registro.data or datetime.utcnow().date()
                )
                db.session.add(celular)
                db.session.commit()
                flash('Celular registrado exitosamente', 'success')
                return redirect(url_for('historial.celulares_index'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al registrar celular: {str(e)}', 'danger')
        
        return render_template('historial/Control_Historial/Agregar_ControlHistorial/Agregar_Celular.html',
                            form=form,
                            usuario_actual=usuario_actual)

    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def editar(self, id):
        usuario_actual = Usuario.query.get(session['id_usuario'])
        celular = Celular.query.get_or_404(id)
        form = CelularForm(obj=celular, original_imei=celular.imei)
        
        if form.validate_on_submit():
            try:
                # Verificar si el IMEI ya existe (solo si cambió)
                if form.imei.data != celular.imei and Celular.query.filter_by(imei=form.imei.data).first():
                    flash('Este IMEI ya está registrado. Debe ser único.', 'danger')
                    return render_template('historial/Control_Historial/Editar_ControlHistorial/Editar_Celular.html', 
                                        form=form,
                                        celular=celular,
                                        usuario_actual=usuario_actual)

                celular.imei = form.imei.data
                celular.marca = form.marca.data
                celular.modelo = form.modelo.data
                celular.fecha_adquisicion = form.fecha_adquisicion.data
                celular.fecha_registro = form.fecha_registro.data
                db.session.commit()
                flash('Celular actualizado exitosamente', 'success')
                return redirect(url_for('historial.celulares_index'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar celular: {str(e)}', 'danger')
        
        return render_template('historial/Control_Historial/Editar_ControlHistorial/Editar_Celular.html', 
                            form=form,
                            celular=celular,
                            usuario_actual=usuario_actual)

    @requiere_login
    @requiere_rol('Administrador General')
    def eliminar(self, id):
        celular = Celular.query.get_or_404(id)
        try:
            db.session.delete(celular)
            db.session.commit()
            flash('Celular eliminado exitosamente', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar celular: {str(e)}', 'danger')
        return redirect(url_for('historial.celulares_index'))

# ==================================================
# CONTROLADOR PARA CHIPS - VERSIÓN CORREGIDA
# ==================================================
class ControlChip:
    def __init__(self, bp):
        self.bp = bp
        self._registrar_rutas()
    
    def _registrar_rutas(self):
        # Rutas para Chips
        self.bp.route('/chips', endpoint='chips_index')(self.index)
        self.bp.route('/chips/nuevo', methods=['GET', 'POST'], endpoint='chips_nuevo')(self.nuevo)
        self.bp.route('/chips/<int:id>/editar', methods=['GET', 'POST'], endpoint='chips_editar')(self.editar)
        self.bp.route('/chips/<int:id>/eliminar', methods=['POST'], endpoint='chips_eliminar')(self.eliminar)
        self.bp.route('/chips/<int:id>/estado', methods=['GET', 'POST'], endpoint='chips_cambiar_estado')(self.cambiar_estado)

    # Listado de Chips
    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def index(self):
        pagina = request.args.get('pagina', 1, type=int)
        chips = Chip.query.join(ChipEstadoRelacion).join(ChipEstado)\
                 .order_by(Chip.operadora, Chip.numero)\
                 .paginate(page=pagina, per_page=10)
        
        usuario_actual = Usuario.query.get(session['id_usuario'])
        return render_template('historial/Control_Historial/Control_Chip.html', 
                            chips=chips,
                            usuario_actual=usuario_actual)

    # Validar formato del número (593 para Ecuador)
    def _validar_numero(self, numero):
        if not numero.startswith('593'):
            raise ValueError("El número debe comenzar con '593' (código de Ecuador)")
        if not numero[3:].isdigit() or len(numero) != 12:
            raise ValueError("El número debe contener 12 dígitos (incluyendo el 593)")
        return True

    # Nuevo Chip
    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def nuevo(self):
        usuario_actual = Usuario.query.get(session['id_usuario'])
        if request.method == 'POST':
            try:
                # Validar número
                numero = request.form['numero'].strip()
                self._validar_numero(numero)
                
                # Verificar si el número ya existe
                if Chip.query.filter_by(numero=numero).first():
                    raise ValueError("Este número de chip ya está registrado")
                
                # Crear chip
                chip = Chip(
                    numero=numero,
                    operadora=request.form['operadora'],
                    tipo_linea=request.form['tipo_linea'],
                    fecha_activacion=datetime.strptime(request.form['fecha_activacion'], '%Y-%m-%d'),
                    estado_actual='ACTIVO'  # Estado inicial
                )
                db.session.add(chip)
                db.session.flush()  # Para obtener el ID
                
                # Registrar estado inicial
                estado_inicial = ChipEstadoRelacion(
                    idChip=chip.idChip,
                    idEstado=1,  # Estado ACTIVO por defecto
                    fecha_cambio=datetime.now(),
                    observaciones='Estado inicial al registrar el chip'
                )
                db.session.add(estado_inicial)
                db.session.commit()
                
                flash('Chip registrado exitosamente', 'success')
                return redirect(url_for('historial.chips_index'))
            except ValueError as ve:
                db.session.rollback()
                flash(f'Error de validación: {str(ve)}', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Error al registrar chip: {str(e)}', 'danger')
        
        estados = ChipEstado.query.all()
        return render_template('historial/Control_Historial/Agregar_ControlHistorial/Agregar_Chip.html',
                            estados=estados,
                            usuario_actual=usuario_actual)

    # Editar Chip
    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def editar(self, id):
        usuario_actual = Usuario.query.get(session['id_usuario'])
        chip = Chip.query.get_or_404(id)
        
        if request.method == 'POST':
            try:
                # Validar número si ha cambiado
                nuevo_numero = request.form['numero'].strip()
                if nuevo_numero != chip.numero:
                    self._validar_numero(nuevo_numero)
                    if Chip.query.filter(Chip.numero == nuevo_numero, Chip.idChip != id).first():
                        raise ValueError("Este número de chip ya está registrado")
                
                # Actualizar datos
                chip.numero = nuevo_numero
                chip.operadora = request.form['operadora']
                chip.tipo_linea = request.form['tipo_linea']
                chip.fecha_activacion = datetime.strptime(request.form['fecha_activacion'], '%Y-%m-%d')
                
                db.session.commit()
                flash('Chip actualizado exitosamente', 'success')
                return redirect(url_for('historial.chips_index'))
            except ValueError as ve:
                db.session.rollback()
                flash(f'Error de validación: {str(ve)}', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar chip: {str(e)}', 'danger')
        
        return render_template('historial/Control_Historial/Editar_ControlHistorial/Editar_Chip.html',
                            chip=chip,
                            usuario_actual=usuario_actual)

    # Eliminar Chip
    @requiere_login
    @requiere_rol('Administrador General')
    def eliminar(self, id):
        chip = Chip.query.get_or_404(id)
        try:
            # Primero eliminar los estados relacionados
            ChipEstadoRelacion.query.filter_by(idChip=id).delete()
            # Luego eliminar el chip
            db.session.delete(chip)
            db.session.commit()
            flash('Chip eliminado exitosamente', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar chip: {str(e)}', 'danger')
        return redirect(url_for('historial.chips_index'))

    # Cambiar Estado de Chip
    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def cambiar_estado(self, id):
        usuario_actual = Usuario.query.get(session['id_usuario'])
        chip = Chip.query.get_or_404(id)
        
        if request.method == 'POST':
            try:
                id_estado = int(request.form['estado'])
                observaciones = request.form.get('observaciones', '').strip()
                
                # Verificar si el estado es diferente al actual
                estado_actual = ChipEstado.query.filter_by(nombre=chip.estado_actual).first()
                if estado_actual and estado_actual.idEstado == id_estado:
                    raise ValueError("El chip ya tiene este estado asignado")
                
                # Registrar nuevo estado
                nuevo_estado = ChipEstadoRelacion(
                    idChip=chip.idChip,
                    idEstado=id_estado,
                    fecha_cambio=datetime.now(),
                    observaciones=observaciones or f"Cambio de estado a {ChipEstado.query.get(id_estado).nombre}"
                )
                db.session.add(nuevo_estado)
                
                # Actualizar estado actual del chip
                chip.estado_actual = ChipEstado.query.get(id_estado).nombre
                db.session.commit()
                
                flash('Estado del chip actualizado exitosamente', 'success')
                return redirect(url_for('historial.chips_index'))
            except ValueError as ve:
                db.session.rollback()
                flash(f'Error de validación: {str(ve)}', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Error al cambiar estado: {str(e)}', 'danger')
        
        estados = ChipEstado.query.all()
        return render_template('historial/Control_Historial/Editar_ControlHistorial/Cambiar_Estado_Chip.html', 
                            chip=chip, 
                            estados=estados,
                            usuario_actual=usuario_actual)
# ==================================================
# CONTROLADOR PARA ESTADOS DE CHIPS
# ==================================================
class ControlEstado:
    def __init__(self, bp):
        self.bp = bp
        self._registrar_rutas()
    
    def _registrar_rutas(self):
        # Rutas para Estados
        self.bp.route('/estados', endpoint='estados_index')(self.index)
        self.bp.route('/estados/nuevo', methods=['GET', 'POST'], endpoint='estados_nuevo')(self.nuevo)
        self.bp.route('/estados/<int:id>/editar', methods=['GET', 'POST'], endpoint='estados_editar')(self.editar)
        self.bp.route('/estados/<int:id>/eliminar', methods=['POST'], endpoint='estados_eliminar')(self.eliminar)

    # Listado de Estados
    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def index(self):
        estados = ChipEstado.query.order_by(ChipEstado.nombre).all()
        usuario_actual = Usuario.query.get(session['id_usuario'])
        return render_template('historial/Control_Historial/Control_Estado.html',
                            estados=estados,
                            usuario_actual=usuario_actual)

    # Nuevo Estado
    @requiere_login
    @requiere_rol('Administrador General')
    def nuevo(self):
        usuario_actual = Usuario.query.get(session['id_usuario'])
        if request.method == 'POST':
            try:
                estado = ChipEstado(nombre=request.form['nombre'])
                db.session.add(estado)
                db.session.commit()
                flash('Estado creado exitosamente', 'success')
                return redirect(url_for('historial.estados_index'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al crear estado: {str(e)}', 'danger')
        return render_template('historial/Control_Historial/Agregar_ControlHistorial/Agregar_Estado.html',
                            usuario_actual=usuario_actual)

    # Editar Estado
    @requiere_login
    @requiere_rol('Administrador General')
    def editar(self, id):
        usuario_actual = Usuario.query.get(session['id_usuario'])
        estado = ChipEstado.query.get_or_404(id)
        if request.method == 'POST':
            try:
                estado.nombre = request.form['nombre']
                db.session.commit()
                flash('Estado actualizado exitosamente', 'success')
                return redirect(url_for('historial.estados_index'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar estado: {str(e)}', 'danger')
        return render_template('historial/Control_Historial/Editar_ControlHistorial/Editar_Estado.html',
                            estado=estado,
                            usuario_actual=usuario_actual)

    # Eliminar Estado
    @requiere_login
    @requiere_rol('Administrador General')
    def eliminar(self, id):
        estado = ChipEstado.query.get_or_404(id)
        try:
            if ChipEstadoRelacion.query.filter_by(idEstado=id).count() > 0:
                flash('No se puede eliminar el estado porque hay chips asociados', 'danger')
            else:
                db.session.delete(estado)
                db.session.commit()
                flash('Estado eliminado exitosamente', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar estado: {str(e)}', 'danger')
        return redirect(url_for('historial.estados_index'))


# ==================================================
# CONTROLADOR PRINCIPAL DE HISTORIAL
# ==================================================
class ControlHistorial:
    def __init__(self):
        self.bp = Blueprint('historial', __name__, url_prefix='/historial')
        self.control_celular = ControlCelular(self.bp)
        self.control_chip = ControlChip(self.bp)
        self.control_estado = ControlEstado(self.bp)
        
        self.bp.route('', endpoint='dashboard')(self.dashboard)

    # Dashboard de Historial
    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def dashboard(self):
        total_celulares = Celular.query.count()
        total_chips = Chip.query.count()
        estados_chips = db.session.query(
            ChipEstado.nombre,
            db.func.count(ChipEstadoRelacion.idChip)
        ).join(ChipEstadoRelacion).group_by(ChipEstado.nombre).all()
        
        usuario_actual = Usuario.query.get(session['id_usuario'])
        return render_template('historial/Control_Historial/dashboard.html',
                            total_celulares=total_celulares,
                            total_chips=total_chips,
                            estados_chips=estados_chips,
                            usuario_actual=usuario_actual)


# ==================================================
# INSTANCIA PRINCIPAL
# ==================================================
gestor_historial = ControlHistorial()
bp_historial = gestor_historial.bp