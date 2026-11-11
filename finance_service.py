"""Cobros/gastos con las reglas actuales y confirmación transaccional DEMO."""
from datetime import datetime
import math
import uuid

from config import TZ_SV
from integrity_service import IntegrityError, run_transaction


def record_movement(db, data, session=None, operation_id=None):
    data = dict(data)
    if data.get('tipo') not in {'ingreso', 'egreso'} or not data.get('descripcion', '').strip():
        raise IntegrityError('Tipo y detalle del movimiento obligatorios.')
    amount = float(data.get('monto', 0))
    if not math.isfinite(amount) or amount < 0.01:
        raise IntegrityError('El monto debe ser finito y al menos 0.01.')
    operation_id = operation_id or uuid.uuid4().hex
    if len(operation_id) != 32 or any(c not in '0123456789abcdef' for c in operation_id):
        raise IntegrityError('Identificador de operación no válido.')
    ref = db.collection('finanzas').document(operation_id)
    today = datetime.now(TZ_SV).date()

    def change(tx, actor):
        previous_commit = ref.get(transaction=tx)
        if previous_commit.exists:
            saved = previous_commit.to_dict()
            fields = ('tipo', 'descripcion', 'monto', 'alumno_nie', 'docente_id',
                      'ciclo_lectivo', 'observaciones', 'nombre_persona')
            if any(saved.get(key) != data.get(key) for key in fields):
                raise IntegrityError('El identificador ya corresponde a otro movimiento.')
            return saved  # Confirmación perdida: recuperar, nunca volver a cobrar.
        # Mismo criterio previo: alumno/concepto/hoy; salario/docente/hoy.
        from view_dispatch import _fecha
        guard_ref = db.collection('_integrity').document('finanzas')
        guard = guard_ref.get(transaction=tx)
        revision = guard.to_dict().get('revision', 0) if guard.exists else 0
        if type(revision) is not int or revision < 0:
            raise IntegrityError('Coordinación financiera inválida; escritura bloqueada.')
        values = dict(data)
        if data['tipo'] == 'ingreso':
            nie = data.get('alumno_nie')
            if not nie:
                raise IntegrityError('Alumno obligatorio.')
            students = list(db.collection('alumnos').where('nie', '==', nie).stream(transaction=tx))
            if len(students) != 1 or students[0].to_dict().get('estado', 'Activo') != 'Activo':
                raise IntegrityError('El alumno ya no está activo o no tiene un vínculo único.')
            student = students[0].to_dict()
            values.update(grado_alumno=student.get('grado_actual', 'Sin Grado'),
                          nombre_persona=f"{student.get('apellidos', '')} {student.get('nombres', '')}".strip())
            duplicates = db.collection('finanzas').where('alumno_nie', '==', nie).where('descripcion', '==', data['descripcion']).stream(transaction=tx)
        elif data.get('docente_id') and 'Salario' in data['descripcion']:
            teacher = db.collection('maestros_perfil').document(data['docente_id']).get(transaction=tx)
            if not teacher.exists or teacher.to_dict().get('activo') is not True:
                raise IntegrityError('El docente ya no está activo.')
            duplicates = db.collection('finanzas').where('docente_id', '==', data['docente_id']).where('tipo', '==', 'egreso').stream(transaction=tx)
        else:
            duplicates = ()  # Los gastos ordinarios conservan su regla: pueden repetirse.
        for doc in duplicates:
            previous = doc.to_dict()
            if _fecha(previous) == today and (data['tipo'] == 'ingreso' or 'Salario' in previous.get('descripcion', '')):
                raise IntegrityError('Transacción duplicada según alumno/concepto o salario del día.')
        tx.set(guard_ref, {'revision': revision + 1})
        tx.set(ref, values)
        return values

    return run_transaction(db, 'Finanzas', change, session)
