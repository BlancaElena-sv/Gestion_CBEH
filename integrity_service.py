"""Escrituras administrativas DEMO, con revalidación dentro de Firestore."""
from firebase_admin import firestore
import streamlit as st

from authorization import AccessDenied, authorize


class IntegrityError(ValueError):
    pass


def run_transaction(db, module, callback, session=None):
    # No hay fallback a escrituras directas si falta soporte transaccional.
    session = dict(st.session_state if session is None else session)
    principal = authorize(db, module, session)
    transaction = db.transaction()

    @firestore.transactional
    def execute(tx):
        actor = db.collection('usuarios').document(principal.user_id).get(transaction=tx)
        row = actor.to_dict() if actor.exists else {}
        if row.get('activo') is not True or row.get('rol') != 'admin':
            raise AccessDenied('El administrador ya no está autorizado para escribir.')
        return callback(tx, principal.user_id)

    return execute(transaction)


def mutate_user(db, user_id, action, values=None, session=None):
    """Una mutación de usuario y un cerrojo común, confirmados atómicamente.

    Todas las rutas de gestión de usuarios deben usar este protocolo. La consulta
    es la fuente de verdad; el documento guard no almacena un conteo de roles.
    """
    if not isinstance(user_id, str) or not user_id.strip() or '/' in user_id:
        raise IntegrityError('Usuario no válido.')
    if action not in {'save', 'deactivate', 'reactivate', 'delete'}:
        raise IntegrityError('Operación de usuario no válida.')
    values = dict(values or {})
    if action == 'save':
        if (set(values) != {'usuario', 'nombre', 'rol', 'password_hash'}
                or values['usuario'] != user_id or values['rol'] not in {'admin', 'docente'}
                or not values['nombre'].strip() or not values['password_hash']):
            raise IntegrityError('Datos de usuario no válidos.')
    elif action == 'deactivate':
        if set(values) != {'fecha_baja', 'baja_realizada_por'}:
            raise IntegrityError('Datos de baja no válidos.')
    elif values:
        raise IntegrityError('La operación no admite datos adicionales.')

    def change(tx, actor):
        if user_id == 'david' and (action in {'deactivate', 'delete'} or actor != 'david'):
            raise IntegrityError('El Super Admin está protegido.')
        if user_id == actor and action in {'deactivate', 'delete'}:
            raise IntegrityError('No puede desactivar ni eliminar su propio usuario.')
        guard_ref = db.collection('_integrity').document('administradores')
        guard = guard_ref.get(transaction=tx)
        revision = guard.to_dict().get('revision', 0) if guard.exists else 0
        if type(revision) is not int or revision < 0:
            raise IntegrityError('Cerrojo de administradores no válido; operación bloqueada.')
        ref = db.collection('usuarios').document(user_id)
        snapshot = ref.get(transaction=tx)
        current = snapshot.to_dict() if snapshot.exists else {}
        admins = list(db.collection('usuarios').where('rol', '==', 'admin')
                      .where('activo', '==', True).stream(transaction=tx))
        if action != 'save' and not snapshot.exists:
            raise IntegrityError('El usuario ya no existe.')
        if action == 'save':
            result = dict(current, **values)
            if not snapshot.exists:
                result['activo'] = True
        elif action == 'deactivate':
            result = dict(current, activo=False, **values)
        elif action == 'reactivate':
            if current.get('rol') not in {'admin', 'docente'}:
                raise IntegrityError('Rol desconocido; reactivación bloqueada.')
            result = dict(current, activo=True, fecha_baja=None, baja_realizada_por=None)
        else:
            result = {}
        remaining = sum(doc.id != user_id for doc in admins)
        remaining += int(result.get('rol') == 'admin' and result.get('activo') is True)
        if remaining < 1:
            raise IntegrityError('Debe conservarse al menos un administrador activo.')
        if action != 'delete' and result == current:
            return False
        # Lecturas completas antes de cualquier escritura.
        tx.set(guard_ref, {'revision': revision + 1})
        if action == 'delete':
            tx.delete(ref)
        else:
            tx.set(ref, result)
        return True

    return run_transaction(db, 'Configuración (Usuarios)', change, session)
