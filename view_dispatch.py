"""Despacho autorizado y adaptación de contratos de las vistas existentes."""
from datetime import datetime
from importlib import import_module
import inspect

from academic_config import LISTA_GRADOS_NOTAS, LISTA_GRADOS_TODO, LISTA_MESES, MAPA_CURRICULAR
from auth import generar_hash
from authorization import AccessDenied, authorize
from config import CICLO_LECTIVO, TZ_SV
from firebase_service import subir_archivo
from navigation import BY_NAME
from teacher_store import TeacherStore
from utils import get_base64, redondear_mined


def obtener_fecha_hoy():
    return datetime.now(TZ_SV).date()


def obtener_hora_actual():
    return datetime.now(TZ_SV).strftime("%d/%m/%Y %H:%M")


def limpiar_nombre(nombre):
    return str(nombre or "").replace("*", "").replace("_", " ").strip()


def _fecha(data):
    value = data.get("fecha")
    if isinstance(value, datetime):
        return value.astimezone(TZ_SV).date() if value.tzinfo else value.date()
    if isinstance(value, str):
        return datetime.fromisoformat(value).date()
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, TZ_SV).date()
    if data.get("fecha_legible"):
        return datetime.strptime(data["fecha_legible"][:10], "%d/%m/%Y").date()
    raise AccessDenied("No se puede verificar la fecha del movimiento financiero.")


def render_module(db, module_name):
    principal = authorize(db, module_name)
    if module_name == "Inicio":
        from views.dashboard import mostrar_dashboard_admin, mostrar_dashboard_docente
        if principal.role == "admin":
            return mostrar_dashboard_admin(db=db, nombre_usuario=limpiar_nombre(principal.name))
        return mostrar_dashboard_docente(
            db=TeacherStore(db, principal, module_name), nombre_usuario=principal.name,
            limpiar_nombre=limpiar_nombre)

    def exists_duplicate(tabla, campo_id, id_valor, descripcion):
        authorize(db, module_name)
        if tabla != "finanzas":
            raise AccessDenied("Consulta de duplicados fuera de finanzas.")
        docs = db.collection(tabla).where(campo_id, "==", id_valor).where("descripcion", "==", descripcion).stream()
        return any(_fecha(doc.to_dict()) == obtener_fecha_hoy() for doc in docs)

    def duplicate_salary(docente_id, tipo_gasto):
        authorize(db, module_name)
        docs = db.collection("finanzas").where("docente_id", "==", docente_id).where("tipo", "==", "egreso").stream()
        return any(_fecha(doc.to_dict()) == obtener_fecha_hoy()
                   and "Salario" in doc.to_dict().get("descripcion", "")
                   and "Salario" in tipo_gasto for doc in docs)

    def blocked_reset(*args, **kwargs):
        raise AccessDenied("El borrado masivo permanece bloqueado en este bloque.")

    values = dict(
        db=db, lista_grados=LISTA_GRADOS_TODO, lista_grados_notas=LISTA_GRADOS_NOTAS,
        lista_meses=LISTA_MESES, mapa_curricular=MAPA_CURRICULAR,
        generar_hash=generar_hash, subir_archivo=subir_archivo,
        obtener_fecha_hoy=obtener_fecha_hoy, obtener_hora_actual=obtener_hora_actual,
        redondear_mined=redondear_mined, get_base64=get_base64,
        existe_duplicado=exists_duplicate, verificar_pago_duplicado_hoy=duplicate_salary,
        borrar_coleccion=blocked_reset, ciclo_origen=CICLO_LECTIVO,
        ciclo_destino=CICLO_LECTIVO + 1, opcion_seleccionada=module_name,
    )
    path, function_name = BY_NAME[module_name].target.split(":")
    function = getattr(import_module(path), function_name)
    kwargs = {name: values[name] for name in inspect.signature(function).parameters}
    return function(**kwargs)
