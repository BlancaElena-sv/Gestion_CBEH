"""Mi Perfil: solo la cuenta de la sesión; sin roles ni campos administrativos."""
from datetime import datetime
from urllib.parse import urlparse, unquote

from firebase_admin import firestore
import streamlit as st

from auth import generar_hash, verificar_password
from authorization import AccessDenied, authorize
from config import TZ_SV
from firebase_demo_service import BUCKETS_PERMITIDOS
from integrity_service import IntegrityError


PUBLIC_FIELDS = ('nombre', 'rol', 'email', 'telefono', 'bio', 'foto_url', 'created_at',
                 'activo', 'tema', 'notificaciones_email')


def photo_url_allowed(url, user_id):
    parsed = urlparse(str(url or ''))
    parts = parsed.path.split('/')
    return (parsed.scheme == 'https' and parsed.netloc == 'firebasestorage.googleapis.com'
            and len(parts) == 6 and parts[:3] == ['', 'v0', 'b']
            and parts[3] in BUCKETS_PERMITIDOS and parts[4] == 'o'
            and unquote('/'.join(parts[5:])).startswith(f'perfiles/{user_id}/'))


def read_profile(db):
    principal = authorize(db, 'Mi Perfil')
    doc = db.collection('usuarios').document(principal.user_id).get()
    if not doc.exists:
        raise AccessDenied('La cuenta ya no existe.')
    return {key: value for key, value in doc.to_dict().items() if key in PUBLIC_FIELDS}


def save_profile(db, action, values=None, current_password=None, new_password=None, session=None):
    session = dict(st.session_state if session is None else session)
    principal = authorize(db, 'Mi Perfil', session)
    values = dict(values or {})
    if action == 'personal':
        if set(values) - {'nombre', 'email', 'telefono', 'bio', 'foto_url'} or not str(values.get('nombre', '')).strip():
            raise IntegrityError('El nombre es obligatorio y los campos administrativos están protegidos.')
        if 'foto_url' in values and not photo_url_allowed(values['foto_url'], principal.user_id):
            raise IntegrityError('La fotografía debe pertenecer a esta cuenta en Firebase DEMO.')
    elif action == 'preferences':
        if (set(values) != {'tema', 'notificaciones_email'}
                or values['tema'] not in {'claro', 'oscuro', 'automático'}
                or type(values['notificaciones_email']) is not bool):
            raise IntegrityError('Preferencias no válidas.')
    elif action == 'password':
        if values or not current_password or not new_password or len(new_password) < 6:
            raise IntegrityError('Complete la contraseña actual y una nueva de al menos 6 caracteres.')
    else:
        raise IntegrityError('Operación de perfil no válida.')
    # bcrypt se calcula una vez; el hash vigente se verifica de nuevo en cada reintento.
    new_hash = generar_hash(new_password) if action == 'password' else None

    @firestore.transactional
    def change(tx):
        ref = db.collection('usuarios').document(principal.user_id)
        doc = ref.get(transaction=tx)
        row = doc.to_dict() if doc.exists else {}
        if row.get('activo') is not True or row.get('rol') != principal.role:
            raise AccessDenied('La cuenta cambió o ya no está activa.')
        changes = dict(values)
        teacher_ref = None
        if principal.role == 'docente':
            # Vínculo original verificado, nunca el nombre/correo que se está editando.
            if row.get('id_docente'):
                if row['id_docente'] != principal.teacher_id:
                    raise AccessDenied('El vínculo docente cambió; recargue el perfil.')
                matches = [db.collection('maestros_perfil').document(principal.teacher_id).get(transaction=tx)]
            else:
                matches = list(db.collection('maestros_perfil').where('nombre', '==', row.get('nombre')).stream(transaction=tx))
            if (len(matches) != 1 or matches[0].id != principal.teacher_id
                    or not matches[0].exists or matches[0].to_dict().get('activo') is not True):
                raise AccessDenied('No existe un vínculo docente único y activo.')
            # Estabiliza la identidad legacy antes de permitir cambiar el nombre.
            changes['id_docente'] = principal.teacher_id
            teacher_ref = db.collection('maestros_perfil').document(principal.teacher_id)
        if action == 'password':
            if not verificar_password(current_password, row.get('password_hash')):
                raise IntegrityError('La contraseña actual es incorrecta.')
            changes['password_hash'] = new_hash
        changes['ultimo_acceso'] = datetime.now(TZ_SV).isoformat()
        tx.update(ref, changes)
        if teacher_ref is not None and 'foto_url' in changes:
            tx.update(teacher_ref, {'foto_url': changes['foto_url']})

    return change(db.transaction())
