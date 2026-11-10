"""Autorización de servidor. Sin caché de usuarios ni permisos académicos."""
from dataclasses import dataclass
from functools import wraps
import inspect

import streamlit as st
from config import CICLO_LECTIVO
from navigation import BY_NAME


class AccessDenied(PermissionError):
    pass


@dataclass(frozen=True)
class Principal:
    user_id: str
    role: str
    name: str
    teacher_id: str = ""
    assignments: frozenset = frozenset()
    guide_grades: frozenset = frozenset()

    @property
    def grades(self):
        return frozenset(grade for grade, _ in self.assignments)


def authorize(db, module_name, session=None):
    session = st.session_state if session is None else session
    module = BY_NAME.get(module_name)
    if (db is None or db.project != "edumanager-demo" or not module
            or session.get("logged_in") is not True
            or not isinstance(session.get("user_id"), str)
            or not session["user_id"].strip()):
        raise AccessDenied("Sesión o conexión DEMO no válida.")
    try:
        user_doc = db.collection("usuarios").document(session["user_id"]).get()
        user = user_doc.to_dict() if user_doc.exists else None
        if (not user or user.get("activo") is not True
                or user.get("rol") not in module.roles
                or user.get("rol") != session.get("user_role")):
            raise AccessDenied("Usuario inactivo o sin permiso para este módulo.")
        if module.blocked:
            raise AccessDenied(module.blocked)
        if user["rol"] == "admin":
            return Principal(session["user_id"], "admin", user.get("nombre", session["user_id"]))
        # Preferir vínculo explícito. Legacy: solo nombre exacto, único e inequívoco.
        teacher_id = user.get("id_docente")
        if teacher_id:
            docs = [db.collection("maestros_perfil").document(teacher_id).get()]
        elif user.get("nombre"):
            docs = list(db.collection("maestros_perfil").where("nombre", "==", user["nombre"]).stream())
        else:
            docs = []
        if len(docs) != 1 or not docs[0].exists:
            raise AccessDenied("No existe un vínculo docente único y verificable.")
        profile = docs[0].to_dict()
        if profile.get("activo") is not True or not profile.get("nombre"):
            raise AccessDenied("Perfil docente no activo.")
        teacher_id = docs[0].id
        assignments, guides = set(), set()
        for doc in db.collection("carga_academica").where("id_docente", "==", teacher_id).stream():
            row = doc.to_dict()
            if type(row.get("ciclo_lectivo")) is not int or row["ciclo_lectivo"] != CICLO_LECTIVO:
                continue
            grade, subjects = row.get("grado"), row.get("materias")
            if not isinstance(grade, str) or not isinstance(subjects, list):
                continue
            assignments.update((grade, subject) for subject in subjects if isinstance(subject, str) and subject)
            if row.get("es_guia") is True:
                guides.add(grade)
        return Principal(session["user_id"], "docente", profile["nombre"], teacher_id,
                         frozenset(assignments), frozenset(guides))
    except AccessDenied:
        raise
    except Exception:
        raise AccessDenied("No se pudieron verificar los permisos; acceso cancelado.") from None


def protected(module_name=None):
    """Protege también llamadas directas a funciones de vistas."""
    def decorate(function):
        signature = inspect.signature(function)

        @wraps(function)
        def guarded(*args, **kwargs):
            bound = signature.bind(*args, **kwargs)
            module = module_name or bound.arguments.get("opcion_seleccionada")
            db = bound.arguments.get("db")
            authorize(db, module)
            return function(*args, **kwargs)
        return guarded
    return decorate
