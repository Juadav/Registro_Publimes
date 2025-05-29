from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import (
    StringField, 
    DateField, 
    SubmitField, 
    SelectField, 
    BooleanField
)
from wtforms.validators import (
    DataRequired, 
    Length, 
    Regexp, 
    ValidationError, 
    Optional
)
from datetime import datetime, timezone

# Importación de modelos
from modelo import (
    db,
    Celular,
    Chip,
    ChipEstado,
    CelularChip,
    ChipEstadoRelacion,
    Usuario
)

# Importación de decoradores personalizados
from decoradores import requiere_login, requiere_rol

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
        if field.data != self.original_imei:
            celular_existente = Celular.query.filter_by(imei=field.data).first()
            if celular_existente:
                raise ValidationError('Este IMEI ya está registrado. Debe ser único.')

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators=extra_validators):
            return False

        if not self.fecha_registro.data or not self.fecha_adquisicion.data:
            return False

        if self.fecha_adquisicion.data == self.fecha_registro.data:
            self.fecha_adquisicion.errors.append('La fecha de adquisición no puede ser igual a la fecha de registro')
            return False

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
                    fecha_registro=form.fecha_registro.data or datetime.now(timezone.utc).date()
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
# CONTROLADOR PARA CHIPS
# ==================================================
class ChipForm(FlaskForm):
    numero = StringField('Número', validators=[
        DataRequired(),
        Length(min=12, max=12, message='El número debe tener exactamente 12 dígitos'),
        Regexp('^593[0-9]{9}$', message='El número debe comenzar con 593 y tener 12 dígitos en total')
    ])
    iccid = StringField('ICCID', validators=[
        DataRequired(),
        Length(min=18, max=22, message='El ICCID debe tener entre 18 y 22 dígitos'),
        Regexp('^[0-9]+$', message='El ICCID solo debe contener números')
    ])
    operadora = SelectField('Operadora', choices=[
        ('', 'Seleccione operadora'),
        ('Claro', 'Claro'),
        ('Movistar', 'Movistar'),
        ('CNT', 'CNT'),
        ('Tuenti', 'Tuenti'),
    ], validators=[DataRequired()])
    tipo_linea = SelectField('Tipo de Línea', choices=[
        ('', 'Seleccione tipo'),
        ('Prepago', 'Prepago'),
        ('Postpago', 'Postpago'),
    ], validators=[DataRequired()])
    
    fecha_adquisicion = DateField('Fecha de Adquisición', validators=[DataRequired()])
    fecha_registro = DateField('Fecha de Registro', default=datetime.now, validators=[DataRequired()])
    fecha_activacion = DateField('Fecha de Activación', validators=[DataRequired()])
    
    submit = SubmitField('Guardar')

    def validate_numero(self, field):
        chip_existente = Chip.query.filter_by(numero=field.data).first()
        if chip_existente and (not hasattr(self, 'chip') or chip_existente.idChip != self.chip.idChip):
            raise ValidationError('Este número ya está registrado')

    def validate_iccid(self, field):
        chip_existente = Chip.query.filter_by(iccid=field.data).first()
        if chip_existente and (not hasattr(self, 'chip') or chip_existente.idChip != self.chip.idChip):
            raise ValidationError('Este ICCID ya está registrado')

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators=extra_validators):
            return False

        hoy = datetime.now(timezone.utc).date()
        
        if self.fecha_adquisicion.data > hoy:
            self.fecha_adquisicion.errors.append('La fecha de adquisición no puede ser futura')
            return False

        if self.fecha_registro.data > hoy:
            self.fecha_registro.errors.append('La fecha de registro no puede ser futura')
            return False

        if self.fecha_activacion.data > hoy:
            self.fecha_activacion.errors.append('La fecha de activación no puede ser futura')
            return False

        if self.fecha_adquisicion.data > self.fecha_registro.data:
            self.fecha_adquisicion.errors.append('La fecha de adquisición no puede ser posterior al registro')
            return False

        return True

class ControlChip:
    def __init__(self, bp):
        self.bp = bp
        self._registrar_rutas()

    def _registrar_rutas(self):
        self.bp.route('/chips', endpoint='chips_index')(self.index)
        self.bp.route('/chips/nuevo', methods=['GET', 'POST'], endpoint='chips_nuevo')(self.nuevo)
        self.bp.route('/chips/<int:id>/editar', methods=['GET', 'POST'], endpoint='chips_editar')(self.editar)
        self.bp.route('/chips/<int:id>/eliminar', methods=['POST'], endpoint='chips_eliminar')(self.eliminar)

    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def index(self):
        pagina = request.args.get('pagina', 1, type=int)
        busqueda = request.args.get('busqueda', '')
        
        query = Chip.query
        
        if busqueda:
            query = query.filter(
                (Chip.numero.contains(busqueda)) | 
                (Chip.iccid.contains(busqueda)) | 
                (Chip.operadora.contains(busqueda))
            )
            
        chips = query.order_by(
            Chip.fecha_registro.desc(), 
            Chip.operadora, 
            Chip.numero
        ).paginate(page=pagina, per_page=10)

        usuario_actual = Usuario.query.get(session['id_usuario'])
        return render_template('historial/Control_Historial/Control_Chip.html',
                            chips=chips,
                            busqueda=busqueda,
                            usuario_actual=usuario_actual)

    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def nuevo(self):
        usuario_actual = Usuario.query.get(session['id_usuario'])
        form = ChipForm()
        
        if form.validate_on_submit():
            try:
                chip = Chip(
                    numero=form.numero.data,
                    iccid=form.iccid.data,
                    operadora=form.operadora.data,
                    tipo_linea=form.tipo_linea.data,
                    fecha_adquisicion=form.fecha_adquisicion.data,
                    fecha_registro=form.fecha_registro.data,
                    fecha_activacion=form.fecha_activacion.data,
                )
                
                db.session.add(chip)
                db.session.commit()
                
                flash('Chip registrado exitosamente', 'success')
                return redirect(url_for('historial.chips_index'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error al registrar chip: {str(e)}', 'danger')

        return render_template('historial/Control_Historial/Agregar_ControlHistorial/Agregar_Chip.html',
                             form=form,
                             usuario_actual=usuario_actual)

    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def editar(self, id):
        usuario_actual = Usuario.query.get(session['id_usuario'])
        chip = Chip.query.get_or_404(id)
        form = ChipForm(obj=chip)
        form.chip = chip
        
        if form.validate_on_submit():
            try:
                chip.numero = form.numero.data
                chip.iccid = form.iccid.data
                chip.operadora = form.operadora.data
                chip.tipo_linea = form.tipo_linea.data
                chip.fecha_adquisicion = form.fecha_adquisicion.data
                chip.fecha_registro = form.fecha_registro.data
                chip.fecha_activacion = form.fecha_activacion.data
                
                db.session.commit()
                flash('Chip actualizado exitosamente', 'success')
                return redirect(url_for('historial.chips_index'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar chip: {str(e)}', 'danger')

        return render_template('historial/Control_Historial/Editar_ControlHistorial/Editar_Chip.html',
                             form=form,
                             chip=chip,
                             usuario_actual=usuario_actual)

    @requiere_login
    @requiere_rol('Administrador General')
    def eliminar(self, id):
        chip = Chip.query.get_or_404(id)
        try:
            if chip.celulares:
                flash('No se puede eliminar el chip porque está asignado a uno o más celulares', 'danger')
            else:
                db.session.delete(chip)
                db.session.commit()
                flash('Chip eliminado exitosamente', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar chip: {str(e)}', 'danger')
            
        return redirect(url_for('historial.chips_index'))

# ==================================================
# CONTROLADOR PARA ESTADOS DE CHIPS
# ==================================================
class EstadoForm(FlaskForm):
    nombre = StringField('Nombre del Estado', validators=[
        DataRequired(),
        Length(min=3, max=50)
    ])
    submit = SubmitField('Guardar')

class ControlEstado:
    def __init__(self, bp):
        self.bp = bp
        self._registrar_rutas()
    
    def _registrar_rutas(self):
        self.bp.route('/estados', endpoint='estados_index')(self.index)
        self.bp.route('/estados/nuevo', methods=['GET', 'POST'], endpoint='estados_nuevo')(self.nuevo)
        self.bp.route('/estados/<int:id>/editar', methods=['GET', 'POST'], endpoint='estados_editar')(self.editar)
        self.bp.route('/estados/<int:id>/eliminar', methods=['POST'], endpoint='estados_eliminar')(self.eliminar)

    @requiere_login
    @requiere_rol('Administrador General', 'Supervisor Historial')
    def index(self):
        estados = ChipEstado.query.order_by(ChipEstado.nombre).all()
        usuario_actual = Usuario.query.get(session['id_usuario'])
        return render_template('historial/Control_Historial/Control_Estado.html',
                            estados=estados,
                            usuario_actual=usuario_actual)

    @requiere_login
    @requiere_rol('Administrador General')
    def nuevo(self):
        usuario_actual = Usuario.query.get(session['id_usuario'])
        form = EstadoForm()
        
        if form.validate_on_submit():
            try:
                estado = ChipEstado(nombre=form.nombre.data)
                db.session.add(estado)
                db.session.commit()
                flash('Estado creado exitosamente', 'success')
                return redirect(url_for('historial.estados_index'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al crear estado: {str(e)}', 'danger')
        
        return render_template('historial/Control_Historial/Agregar_ControlHistorial/Agregar_Estado.html',
                            form=form,
                            usuario_actual=usuario_actual)

    @requiere_login
    @requiere_rol('Administrador General')
    def editar(self, id):
        usuario_actual = Usuario.query.get(session['id_usuario'])
        estado = ChipEstado.query.get_or_404(id)
        form = EstadoForm(obj=estado)
        
        if form.validate_on_submit():
            try:
                estado.nombre = form.nombre.data
                db.session.commit()
                flash('Estado actualizado exitosamente', 'success')
                return redirect(url_for('historial.estados_index'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar estado: {str(e)}', 'danger')
        
        return render_template('historial/Control_Historial/Editar_ControlHistorial/Editar_Estado.html',
                            form=form,
                            estado=estado,
                            usuario_actual=usuario_actual)

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