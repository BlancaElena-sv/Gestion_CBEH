"""Adaptador Firestore de alcance docente; solo expone operaciones necesarias.

No entrega referencias SDK a las vistas. Revalida sesión y cargas al escribir.
"""
from copy import deepcopy
from datetime import date
import math

from academic_config import LISTA_MESES
from authorization import AccessDenied, authorize
from config import CICLO_LECTIVO


class Snapshot:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self.exists = data is not None
        self._data = deepcopy(data)

    def to_dict(self):
        return deepcopy(self._data)


class TeacherStore:
    ALLOWED = frozenset({"alumnos", "asistencia", "notas", "notas_mensuales",
                         "carga_academica", "maestros_perfil", "configuracion", "agenda"})

    def __init__(self, db, principal, module):
        if db.project != "edumanager-demo" or principal.role != "docente":
            raise AccessDenied("Cliente docente no válido.")
        self._db, self._principal, self._module = db, principal, module
        self.project = db.project

    def collection(self, name):
        if name not in self.ALLOWED:
            raise AccessDenied("Colección no autorizada para docentes.")
        return Query(self, name)

    def batch(self):
        if self._module != "Cargar Notas":
            raise AccessDenied("Operación por lotes no autorizada.")
        return Batch(self)

    def _refresh(self):
        current = authorize(self._db, self._module)
        if current.user_id != self._principal.user_id or current.teacher_id != self._principal.teacher_id:
            raise AccessDenied("La identidad docente cambió; repita el acceso.")
        self._principal = current

    def _grade(self, grade, subject=None):
        if grade not in self._principal.grades:
            raise AccessDenied("Grado fuera de las asignaciones docentes.")
        if subject is not None and (grade, subject) not in self._principal.assignments:
            raise AccessDenied("Materia fuera de las asignaciones docentes.")

    def _students(self, grade):
        self._grade(grade)
        docs = (self._db.collection("alumnos").where("grado_actual", "==", grade)
                .where("ciclo_lectivo", "==", CICLO_LECTIVO).where("estado", "==", "Activo").stream())
        return {str(doc.to_dict().get("nie", doc.id)) for doc in docs}

    def _record(self, name, doc_id, data):
        if data.get("ciclo_lectivo") != CICLO_LECTIVO or type(data.get("ciclo_lectivo")) is not int:
            raise AccessDenied("Ciclo fuera del alcance autorizado.")
        grade = data.get("grado")
        self._grade(grade, data.get("materia") if name != "asistencia" else None)
        if name == "asistencia":
            prefix = f"{CICLO_LECTIVO}_"
            suffix = f"_{grade}"
            try:
                day = date.fromisoformat(doc_id[len(prefix):-len(suffix)])
            except (ValueError, TypeError):
                raise AccessDenied("Identificador de asistencia no válido.") from None
            if doc_id != f"{CICLO_LECTIVO}_{day}_{grade}":
                raise AccessDenied("Identificador de asistencia fuera de alcance.")
        else:
            if data.get("mes") not in LISTA_MESES or not data.get("materia"):
                raise AccessDenied("Registro de notas fuera de alcance.")
            base = f"{grade}_{data['materia']}_{data['mes']}".replace(" ", "_")
            expected = f"{CICLO_LECTIVO}_{base}"
            if name == "notas":
                expected = f"{data.get('nie')}_{expected}"
            if doc_id != expected:
                raise AccessDenied("Identificador de notas fuera de alcance.")

    def _document_scope(self, name, doc_id):
        if name == "configuracion" and doc_id == "dashboard":
            return
        if name == "maestros_perfil" and doc_id == self._principal.teacher_id:
            return
        if name == "notas_mensuales" and self._module == "Cargar Notas":
            permitted = {
                f"{CICLO_LECTIVO}_{grade}_{subject}_{month}".replace(" ", "_")
                for grade, subject in self._principal.assignments for month in LISTA_MESES
            }
            if doc_id in permitted:
                return
        if name == "asistencia" and self._module == "Tomar Asistencia":
            for grade in self._principal.grades:
                try:
                    suffix = f"_{grade}"
                    day = date.fromisoformat(doc_id[len(f"{CICLO_LECTIVO}_"):-len(suffix)])
                    if doc_id == f"{CICLO_LECTIVO}_{day}_{grade}":
                        return
                except ValueError:
                    continue
        raise AccessDenied("Documento no autorizado.")

    def _write_check(self, name, doc_id, data, student_sets=None):
        expected_module = "Tomar Asistencia" if name == "asistencia" else "Cargar Notas"
        if name not in {"asistencia", "notas", "notas_mensuales"} or self._module != expected_module:
            raise AccessDenied("Escritura docente no autorizada.")
        fields = {
            "asistencia": {"fecha", "ciclo_lectivo", "grado", "registros", "observaciones"},
            "notas": {"nie", "ciclo_lectivo", "grado", "materia", "mes", "promedio_final"},
            "notas_mensuales": {"ciclo_lectivo", "grado", "materia", "mes", "detalles"},
        }
        if not isinstance(data, dict) or not set(data) <= fields[name]:
            raise AccessDenied("Campos de escritura no autorizados.")
        self._record(name, doc_id, data)
        if student_sets is None:
            students = self._students(data["grado"])
        else:
            if data["grado"] not in student_sets:
                student_sets[data["grado"]] = self._students(data["grado"])
            students = student_sets[data["grado"]]
        if name == "asistencia":
            records, observations = data.get("registros"), data.get("observaciones")
            if (not isinstance(records, dict) or not isinstance(observations, dict)
                    or not set(records) <= students or not set(observations) <= set(records)
                    or any(value not in {"Presente", "Ausente", "Tardanza", "Permiso"} for value in records.values())):
                raise AccessDenied("Asistencia contiene alumnos o estados no autorizados.")
        elif name == "notas":
            if str(data.get("nie")) not in students:
                raise AccessDenied("Alumno fuera del grado y ciclo autorizados.")
            self._number(data.get("promedio_final"))
        else:
            details = data.get("detalles")
            if not isinstance(details, dict) or not set(details) <= students:
                raise AccessDenied("Detalle mensual contiene alumnos fuera de alcance.")
            for row in details.values():
                if not isinstance(row, dict):
                    raise AccessDenied("Detalle mensual no válido.")
                for value in row.values():
                    self._number(value)
        existing = self._db.collection(name).document(doc_id).get()
        if existing.exists:
            self._record(name, doc_id, existing.to_dict())

    @staticmethod
    def _number(value):
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 10:
            raise AccessDenied("Calificación fuera del rango permitido.")


class Query:
    def __init__(self, store, name, filters=()):
        self._store, self._name, self._filters = store, name, filters

    def where(self, field, operator, value):
        if operator != "==":
            raise AccessDenied("Filtro docente no permitido.")
        return Query(self._store, self._name, self._filters + ((field, operator, value),))

    def document(self, doc_id):
        if not isinstance(doc_id, str) or not doc_id or "/" in doc_id:
            raise AccessDenied("Identificador no válido.")
        return Document(self._store, self._name, doc_id)

    def stream(self):
        store, name, principal = self._store, self._name, self._store._principal
        filters = dict((field, value) for field, _, value in self._filters)
        if name == "maestros_perfil":
            doc = store._db.collection(name).document(principal.teacher_id).get()
            docs = [doc] if doc.exists else []
        else:
            query = store._db.collection(name)
            if name in {"alumnos", "notas"}:
                if (name == "alumnos" and store._module not in {"Mis Listados", "Tomar Asistencia", "Cargar Notas"}
                        or name == "notas" and store._module != "Cargar Notas"):
                    raise AccessDenied("Consulta no autorizada para el módulo.")
                grade = filters.get("grado_actual" if name == "alumnos" else "grado")
                store._grade(grade)
                query = query.where("ciclo_lectivo", "==", CICLO_LECTIVO)
                if name == "alumnos":
                    query = query.where("estado", "==", "Activo")
                else:
                    subjects = sorted(subject for g, subject in principal.assignments if g == grade)
                    if not subjects or len(subjects) > 30:
                        raise AccessDenied("Asignaciones de materias no válidas.")
                    query = query.where("materia", "in", subjects)
            elif name == "carga_academica":
                query = query.where("id_docente", "==", principal.teacher_id).where("ciclo_lectivo", "==", CICLO_LECTIVO)
            elif name == "agenda" and store._module == "Inicio":
                query = query.where("audiencia", "in", ["Todos", "Docentes"])
            else:
                raise AccessDenied("Consulta docente no autorizada.")
            for field, operator, value in self._filters:
                if field == "ciclo_lectivo" and value != CICLO_LECTIVO:
                    raise AccessDenied("Ciclo no autorizado.")
                query = query.where(field, operator, value)
            docs = query.stream()
        for doc in docs:
            data = doc.to_dict()
            if not all(data.get(field) == value for field, _, value in self._filters):
                continue
            if name == "alumnos":
                if data.get("ciclo_lectivo") != CICLO_LECTIVO or data.get("grado_actual") not in principal.grades:
                    continue
                data = {key: data[key] for key in ("nie", "nombres", "apellidos", "grado_actual", "estado", "ciclo_lectivo") if key in data}
            if name == "notas" and (data.get("ciclo_lectivo") != CICLO_LECTIVO or (data.get("grado"), data.get("materia")) not in principal.assignments):
                continue
            if name == "carga_academica" and (data.get("id_docente") != principal.teacher_id or data.get("ciclo_lectivo") != CICLO_LECTIVO):
                continue
            if name == "maestros_perfil":
                data = {key: data[key] for key in ("nombre", "foto_url", "telefono", "email", "activo") if key in data}
            yield Snapshot(doc.id, data)


class Document:
    def __init__(self, store, name, doc_id):
        self._store, self._name, self.id = store, name, doc_id

    def get(self):
        self._store._document_scope(self._name, self.id)
        doc = self._store._db.collection(self._name).document(self.id).get()
        data = doc.to_dict() if doc.exists else None
        if data is not None and self._name == "maestros_perfil":
            data = {key: data[key] for key in ("nombre", "foto_url", "telefono", "email", "activo") if key in data}
        if data is not None and self._name in {"asistencia", "notas_mensuales"}:
            self._store._record(self._name, self.id, data)
            students = self._store._students(data["grado"])
            for key in ("registros", "observaciones", "detalles"):
                if key in data:
                    data[key] = {nie: row for nie, row in data[key].items() if nie in students}
        return Snapshot(self.id, data)

    def set(self, data):
        self._store._refresh()
        self._store._write_check(self._name, self.id, data)
        self._store._db.collection(self._name).document(self.id).set(data)


class Batch:
    def __init__(self, store):
        self._store, self._pending = store, []

    def set(self, ref, data):
        if not isinstance(ref, Document) or ref._store is not self._store:
            raise AccessDenied("Referencia de escritura no autorizada.")
        self._pending.append((ref, deepcopy(data)))

    def commit(self):
        self._store._refresh()
        if len(self._pending) > 500:
            raise AccessDenied("El lote supera el límite de escrituras de Firestore.")
        student_sets = {}
        for ref, data in self._pending:
            self._store._write_check(ref._name, ref.id, data, student_sets)
        batch = self._store._db.batch()
        for ref, data in self._pending:
            batch.set(self._store._db.collection(ref._name).document(ref.id), data)
        result = batch.commit()
        self._pending.clear()
        return result
