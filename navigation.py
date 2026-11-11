"""Catálogo compartido por sidebar, autorización y despachador."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Module:
    name: str
    roles: tuple
    section: str
    label: str
    key: str
    target: str = ""
    blocked: str = ""


MODULES = (
    Module("Inicio", ("admin", "docente"), "Principal", ":material/home:  Inicio", "menu_inicio"),
    Module("Inscripción", ("admin",), "Gestión académica", ":material/how_to_reg:  Inscripción", "menu_inscripcion", "views.inscripcion:mostrar_inscripcion"),
    Module("Consulta Alumnos", ("admin",), "Gestión académica", ":material/manage_search:  Consulta Alumnos", "menu_alumnos", "views.alumnos:mostrar_consulta_alumnos"),
    Module("Maestros", ("admin",), "Gestión académica", ":material/co_present:  Maestros", "menu_maestros", "views.docentes:mostrar_maestros"),
    Module("Asistencia Global", ("admin",), "Gestión académica", ":material/event_available:  Asistencia Global", "menu_asistencia", "views.asistencia:mostrar_asistencia_global"),
    Module("Notas", ("admin",), "Gestión académica", ":material/grading:  Notas", "menu_notas", "views.notas:mostrar_notas"),
    Module("Finanzas", ("admin",), "Administración", ":material/payments:  Finanzas", "menu_finanzas", "views.finanzas:mostrar_finanzas"),
    Module("Promoción de Grado", ("admin",), "Administración", ":material/trending_up:  Promoción de Grado", "menu_promocion", "views.promocion:mostrar_promocion"),
    Module("Configuración (Usuarios)", ("admin",), "Sistema", ":material/settings:  Configuración", "menu_configuracion", "views.configuracion:mostrar_configuracion"),
    Module("Mis Listados", ("docente",), "Académico", ":material/checklist:  Mis Listados", "menu_listados", "views.docente_panel:mostrar_panel_docente"),
    Module("Tomar Asistencia", ("docente",), "Académico", ":material/event_available:  Tomar Asistencia", "menu_tomar_asistencia", "views.docente_panel:mostrar_panel_docente"),
    Module("Cargar Notas", ("docente",), "Académico", ":material/edit_note:  Cargar Notas", "menu_cargar_notas", "views.docente_panel:mostrar_panel_docente"),
    Module("Ver Mis Cargas", ("docente",), "Académico", ":material/library_books:  Ver Mis Cargas", "menu_mis_cargas", "views.docente_panel:mostrar_panel_docente"),
    Module("Expediente Alumnos", ("docente",), "Académico", ":material/folder_open:  Expediente Alumnos", "menu_expediente_docente", blocked="Pendiente separar los datos personales y autorizar el alcance de bitácora por maestro guía."),
    Module("Boletas de Notas", ("docente",), "Académico", ":material/description:  Boletas de Notas", "menu_boletas_docente", blocked="Pendiente adaptar la lectura de todas las materias exclusivamente para maestros guía."),
    Module("Mi Perfil", ("admin", "docente"), "Cuenta", ":material/account_circle:  Mi Perfil", "menu_perfil", target="views.perfil:mostrar_perfil"),
)
BY_NAME = {module.name: module for module in MODULES}


def modules_for_role(role):
    return tuple(module for module in MODULES if role in module.roles)
