"""Promoción atómica por alumno; reglas existentes, sin atomicidad global."""
from dataclasses import dataclass
from integrity_service import IntegrityError, run_transaction

MAPA_PROMOCION = {'Kinder 4': 'Kinder 5',
 'Kinder 5': 'Preparatoria',
 'Preparatoria': 'Primer Grado',
 'Primer Grado': 'Segundo Grado',
 'Segundo Grado': 'Tercer Grado',
 'Tercer Grado': 'Cuarto Grado',
 'Cuarto Grado': 'Quinto Grado',
 'Quinto Grado': 'Sexto Grado',
 'Sexto Grado': 'Séptimo Grado',
 'Séptimo Grado': 'Octavo Grado',
 'Octavo Grado': 'Noveno Grado',
 'Noveno Grado': 'Graduado'}

@dataclass(frozen=True)
class PromotionResult:
    status: str
    reason: str = ''


def promotion_data(data, resultado, grado_origen, grado_destino, ciclo_origen,
                   ciclo_destino, fecha, usuario):
    """Mismos campos y decisiones del bloque anterior; solo construye el cambio."""
    historial = list(data.get('historial_academico', []))
    turno_actual = data.get('turno', 'Matutino')
    if resultado == 'No promovido':
        historial.append({
            'ciclo': ciclo_origen, 'grado': grado_origen,
            'resultado': 'No promovido', 'grado_destino': grado_origen,
            'ciclo_destino': ciclo_destino, 'turno_origen': turno_actual,
            'turno_destino': turno_actual, 'fecha': fecha, 'usuario': usuario,
        })
        return {
            'grado_anterior': grado_origen, 'grado_actual': grado_origen,
            'ciclo_lectivo': ciclo_destino, 'turno': turno_actual,
            'estado': 'Activo', 'activo': True, 'fecha_promocion': fecha,
            'promovido_por': usuario, 'resultado_cierre': 'No promovido',
            'historial_academico': historial,
        }
    if grado_destino == 'Graduado':
        historial.append({
            'ciclo': ciclo_origen, 'grado': grado_origen, 'resultado': 'Graduado',
            'fecha': fecha, 'usuario': usuario,
        })
        return {
            'estado': 'Graduado', 'activo': False, 'fecha_baja': fecha,
            'fecha_graduacion': fecha, 'motivo_baja': 'Graduación',
            'baja_realizada_por': usuario, 'ciclo_lectivo': ciclo_origen,
            'resultado_cierre': 'Graduado', 'historial_academico': historial,
        }
    nuevo_turno = 'Vespertino' if grado_origen == 'Cuarto Grado' else turno_actual
    historial.append({
        'ciclo': ciclo_origen, 'grado': grado_origen, 'resultado': 'Promovido',
        'grado_destino': grado_destino, 'ciclo_destino': ciclo_destino,
        'turno_origen': turno_actual, 'turno_destino': nuevo_turno,
        'fecha': fecha, 'usuario': usuario,
    })
    return {
        'grado_anterior': grado_origen, 'grado_actual': grado_destino,
        'ciclo_lectivo': ciclo_destino, 'turno': nuevo_turno,
        'estado': 'Activo', 'activo': True, 'fecha_promocion': fecha,
        'promovido_por': usuario, 'resultado_cierre': 'Promovido',
        'historial_academico': historial,
    }


def promote_student(db, document_id, result, grade, origin, destination, date, session=None):
    if result not in {'Promover', 'No promovido', 'No procesar'} or grade not in MAPA_PROMOCION:
        raise IntegrityError('Resultado o grado no válido.')
    if type(origin) is not int or type(destination) is not int or destination != origin + 1:
        raise IntegrityError('Los ciclos deben ser consecutivos.')
    if not isinstance(document_id, str) or not document_id or '/' in document_id:
        raise IntegrityError('Documento de alumno no válido.')

    def change(tx, actor):
        if result == 'No procesar':
            return PromotionResult('omitido', 'No procesar')
        ref = db.collection('alumnos').document(document_id)
        snapshot = ref.get(transaction=tx)
        if not snapshot.exists:
            return PromotionResult('rechazado', 'El alumno ya no existe.')
        data = snapshot.to_dict()
        history = data.get('historial_academico', [])
        if not isinstance(history, list) or any(not isinstance(row, dict) for row in history):
            raise IntegrityError('Historial no válido; requiere revisión sin sobrescribirlo.')
        if any(str(row.get('ciclo')) == str(origin) and row.get('resultado') in
               {'Promovido', 'No promovido', 'Graduado'} for row in history):
            return PromotionResult('rechazado', 'Ciclo ya procesado; no se repite.')
        if (str(data.get('ciclo_lectivo', origin)) != str(origin)
                or data.get('estado') != 'Activo' or data.get('grado_actual') != grade):
            return PromotionResult('rechazado', 'El grado, estado o ciclo cambió; recargue la selección.')
        # Nombre vigente, leído en la misma transacción, sin confiar en la sesión.
        user = db.collection('usuarios').document(actor).get(transaction=tx).to_dict()
        values = promotion_data(data, result, grade, MAPA_PROMOCION[grade], origin,
                                destination, date, user.get('nombre', 'Administrador'))
        tx.update(ref, values)
        status = 'no_promovido' if result == 'No promovido' else (
            'graduado' if MAPA_PROMOCION[grade] == 'Graduado' else 'promovido')
        return PromotionResult(status)

    return run_transaction(db, 'Promoción de Grado', change, session)
