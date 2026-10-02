import random
import sys
from abc import ABC
from datetime import datetime, timedelta

from firebase_admin import firestore

from academic_config import (
    LISTA_GRADOS_TODO,
    LISTA_GRADOS_NOTAS,
    LISTA_MESES,
    MAPA_CURRICULAR,
)
from auth import generar_hash
from firebase_demo_service import conectar_firebase_demo


class _(ABC):
    """Wrapper útil para ejecutar la DEMO de EduManager."""

    def __init__(self, db=None):
        self.db = db

    def conectar(self):
        if self.db is None:
            self.db, _ = conectar_firebase_demo()
        return self.db

    def validar(self):
        self.conectar()
        confirmar_entorno(self.db)
        return self.db

    def crear(self):
        self.validar()

        print()
        print("Creando EduManager DEMO...")
        print()

        crear_configuracion(self.db)
        crear_usuarios(self.db)
        crear_docentes(self.db)

        alumnos = crear_alumnos(self.db)
        crear_carga_academica(self.db)
        crear_notas(self.db, alumnos)
        crear_asistencia(self.db, alumnos)
        crear_finanzas(self.db, alumnos)
        crear_bitacora(self.db, alumnos)

        return alumnos

    def ejecutar(self):
        alumnos = self.crear()

        print()
        print("=" * 65)
        print("EDUMANAGER DEMO CREADO CORRECTAMENTE")
        print("=" * 65)
        print(f"Institución : {NOMBRE_INSTITUCION}")
        print(f"Ciclo       : {CICLO}")
        print(f"Proyecto    : {self.db.project}")
        print()
        print("Usuario administrador:")
        print("  admin.demo")
        print("  Demo2027!")
        print()
        print("Usuario docente:")
        print("  docente.demo")
        print("  Demo2027!")
        print()
        print(
            "Todos los nombres, teléfonos, NIE y "
            "movimientos son ficticios."
        )
        print("=" * 65)

        return {
            "db": self.db,
            "alumnos": alumnos,
            "institucion": NOMBRE_INSTITUCION,
            "ciclo": CICLO,
        }

    def __call__(self):
        return self.ejecutar()


# ============================================================
# EDUMANAGER DEMO
# Generador de información completamente ficticia
# ============================================================

PROJECT_ID_PERMITIDO = "edumanager-demo"
CICLO = 2027

NOMBRE_INSTITUCION = "Centro Educativo Nuevo Horizonte"

random.seed(2027)


# ============================================================
# DATOS FICTICIOS
# ============================================================

NOMBRES = [
    "Sofía", "Valeria", "Andrea", "Daniela", "Camila",
    "Gabriela", "Lucía", "Mariana", "Natalia", "Fernanda",
    "Carlos", "Daniel", "Mateo", "Diego", "Gabriel",
    "Samuel", "Adrián", "Fernando", "Alejandro", "Sebastián",
    "José", "Luis", "Miguel", "David", "Javier",
]

SEGUNDOS_NOMBRES = [
    "Alejandra", "Isabel", "María", "Elena", "Carolina",
    "Antonio", "Eduardo", "Andrés", "Enrique", "Alexander",
    "",
]

APELLIDOS = [
    "Hernández", "Martínez", "López", "García", "Ramírez",
    "Flores", "Rivera", "Castro", "Morales", "Rivas",
    "Méndez", "Reyes", "Cruz", "Vásquez", "Escobar",
    "Aguilar", "Pérez", "Sánchez", "Torres", "Romero",
]

COLONIAS = [
    "Colonia Las Flores",
    "Residencial Los Pinos",
    "Colonia Santa Lucía",
    "Urbanización El Carmen",
    "Residencial Las Palmas",
    "Colonia San José",
    "Residencial La Esperanza",
    "Colonia El Progreso",
]


DOCENTES = [
    {
        "id": "doc001",
        "codigo": "DOC-001",
        "nombre": "Ana Lucía Martínez",
        "telefono": "7000-1001",
        "email": "ana.martinez@demo.edumanager",
    },
    {
        "id": "doc002",
        "codigo": "DOC-002",
        "nombre": "Carlos Eduardo Ramírez",
        "telefono": "7000-1002",
        "email": "carlos.ramirez@demo.edumanager",
    },
    {
        "id": "doc003",
        "codigo": "DOC-003",
        "nombre": "María Fernanda López",
        "telefono": "7000-1003",
        "email": "maria.lopez@demo.edumanager",
    },
    {
        "id": "doc004",
        "codigo": "DOC-004",
        "nombre": "José Antonio Rivera",
        "telefono": "7000-1004",
        "email": "jose.rivera@demo.edumanager",
    },
    {
        "id": "doc005",
        "codigo": "DOC-005",
        "nombre": "Gabriela Hernández",
        "telefono": "7000-1005",
        "email": "gabriela.hernandez@demo.edumanager",
    },
    {
        "id": "doc006",
        "codigo": "DOC-006",
        "nombre": "Daniel Alejandro Flores",
        "telefono": "7000-1006",
        "email": "daniel.flores@demo.edumanager",
    },
    {
        "id": "doc007",
        "codigo": "DOC-007",
        "nombre": "Patricia Elena Morales",
        "telefono": "7000-1007",
        "email": "patricia.morales@demo.edumanager",
    },
    {
        "id": "doc008",
        "codigo": "DOC-008",
        "nombre": "Roberto Enrique Castro",
        "telefono": "7000-1008",
        "email": "roberto.castro@demo.edumanager",
    },
]


# ============================================================
# UTILIDADES
# ============================================================

def confirmar_entorno(db):
    proyecto = db.project

    print()
    print("=" * 65)
    print("EDUMANAGER - GENERADOR DE BASE DEMOSTRATIVA")
    print("=" * 65)
    print(f"Proyecto detectado : {proyecto}")
    print(f"Proyecto permitido : {PROJECT_ID_PERMITIDO}")
    print(f"Institución         : {NOMBRE_INSTITUCION}")
    print(f"Ciclo lectivo       : {CICLO}")
    print("=" * 65)

    if proyecto != PROJECT_ID_PERMITIDO:
        print()
        print("OPERACIÓN CANCELADA.")
        print("La conexión NO corresponde a EduManager DEMO.")
        sys.exit(1)

    existentes = list(
        db.collection("alumnos").limit(1).stream()
    )

    if existentes:
        print()
        print("ADVERTENCIA:")
        print("La base DEMO ya contiene alumnos.")
        print(
            "Por seguridad este generador no sobrescribirá "
            "automáticamente una DEMO existente."
        )
        sys.exit(1)

    print()
    print("Esta operación creará SOLAMENTE datos ficticios.")
    confirmacion = input(
        "Escriba CREAR DEMO para continuar: "
    )

    if confirmacion.strip().upper() != "CREAR DEMO":
        print("Operación cancelada.")
        sys.exit(0)


def guardar_documento(db, coleccion, documento_id, datos):
    db.collection(coleccion).document(
        str(documento_id)
    ).set(datos)


def generar_nombre():
    nombre = random.choice(NOMBRES)
    segundo = random.choice(SEGUNDOS_NOMBRES)

    nombres = (
        f"{nombre} {segundo}".strip()
        if segundo
        else nombre
    )

    apellido1, apellido2 = random.sample(APELLIDOS, 2)

    return nombres, f"{apellido1} {apellido2}"


def generar_responsable(apellido):
    nombre = random.choice(
        [
            "María", "Ana", "Rosa", "Patricia",
            "Carlos", "José", "Miguel", "Roberto",
        ]
    )

    return {
        "nombre": f"{nombre} {apellido}",
        "telefono": (
            f"7{random.randint(100, 999)}-"
            f"{random.randint(1000, 9999)}"
        ),
        "direccion": random.choice(COLONIAS),
    }


def nota():
    return round(random.uniform(6.0, 10.0), 2)


def promedio_mined(valor):
    # Para la DEMO mantenemos nota final con un decimal.
    return round(valor, 1)


# ============================================================
# CONFIGURACIÓN
# ============================================================

def crear_configuracion(db):
    guardar_documento(
        db,
        "configuracion",
        "general",
        {
            "institucion": NOMBRE_INSTITUCION,
            "nombre_colegio": NOMBRE_INSTITUCION,
            "ciclo_lectivo": CICLO,
            "direccion": "San Salvador, El Salvador",
            "telefono": "2200-0000",
            "correo": "info@demo.edumanager",
            "modo": "DEMO",
        },
    )

    print("✓ Configuración institucional")


# ============================================================
# USUARIOS
# ============================================================

def crear_usuarios(db):
    usuarios = [
        {
            "usuario": "admin.demo",
            "nombre": "Administrador Demo",
            "rol": "admin",
            "password": "Demo2027!",
        },
        {
            "usuario": "docente.demo",
            "nombre": DOCENTES[0]["nombre"],
            "rol": "docente",
            "password": "Demo2027!",
        },
    ]

    for usuario in usuarios:
        guardar_documento(
            db,
            "usuarios",
            usuario["usuario"],
            {
                "usuario": usuario["usuario"],
                "nombre": usuario["nombre"],
                "rol": usuario["rol"],
                "password_hash": generar_hash(
                    usuario["password"]
                ),
                "activo": True,
            },
        )

    print("✓ Usuarios DEMO")


# ============================================================
# DOCENTES
# ============================================================

def crear_docentes(db):
    for docente in DOCENTES:
        guardar_documento(
            db,
            "maestros_perfil",
            docente["id"],
            {
                "codigo": docente["codigo"],
                "nombre": docente["nombre"],
                "telefono": docente["telefono"],
                "email": docente["email"],
                "direccion": random.choice(COLONIAS),
                "foto_url": None,
                "fecha_ingreso": "15/01/2027",
                "activo": True,
                "estado": "Activo",
            },
        )

    print(f"✓ Docentes: {len(DOCENTES)}")


# ============================================================
# ALUMNOS
# ============================================================

def crear_alumnos(db):
    alumnos = []

    # Repartimos ~120 alumnos por todos los niveles.
    cantidad_por_grado = 10

    correlativo = 1

    for grado in LISTA_GRADOS_TODO:

        for _ in range(cantidad_por_grado):

            nombres, apellidos = generar_nombre()

            nie = f"27{correlativo:06d}"

            primer_apellido = apellidos.split()[0]

            turno = (
                "Matutino"
                if grado in [
                    "Kinder 4",
                    "Kinder 5",
                    "Preparatoria",
                    "Primer Grado",
                    "Segundo Grado",
                    "Tercer Grado",
                    "Cuarto Grado",
                ]
                else "Vespertino"
            )

            alumno = {
                "nie": nie,
                "nombres": nombres,
                "apellidos": apellidos,
                "nombre_completo": (
                    f"{apellidos} {nombres}"
                ),
                "grado_actual": grado,
                "turno": turno,
                "estado": "Activo",
                "activo": True,
                "ciclo_lectivo": CICLO,
                "encargado": generar_responsable(
                    primer_apellido
                ),
                "documentos": {
                    "foto_url": None,
                    "doc_urls": [],
                },
                "historial_academico": [],
                "fecha_inscripcion": "10/01/2027",
            }

            guardar_documento(
                db,
                "alumnos",
                nie,
                alumno,
            )

            alumnos.append(alumno)
            correlativo += 1

    print(f"✓ Alumnos: {len(alumnos)}")

    return alumnos


# ============================================================
# CARGA ACADÉMICA
# ============================================================

def crear_carga_academica(db):
    contador = 0

    for indice, grado in enumerate(LISTA_GRADOS_TODO):

        materias = MAPA_CURRICULAR.get(
            grado,
            [],
        )

        if not materias:
            continue

        docente = DOCENTES[
            indice % len(DOCENTES)
        ]

        guardar_documento(
            db,
            "carga_academica",
            f"carga_{contador + 1:03d}",
            {
                "id_docente": docente["id"],
                "nombre_docente": docente["nombre"],
                "grado": grado,
                "materias": materias,
                "es_guia": True,
                "ciclo_lectivo": CICLO,
            },
        )

        contador += 1

    print(f"✓ Cargas académicas: {contador}")


# ============================================================
# NOTAS
# ============================================================

def crear_notas(db, alumnos):
    meses_demo = [
        mes
        for mes in LISTA_MESES
        if mes in [
            "Febrero",
            "Marzo",
            "Abril",
        ]
    ]

    contador_individual = 0
    contador_mensual = 0

    alumnos_por_grado = {}

    for alumno in alumnos:
        alumnos_por_grado.setdefault(
            alumno["grado_actual"],
            [],
        ).append(alumno)

    for grado in LISTA_GRADOS_NOTAS:

        estudiantes = alumnos_por_grado.get(
            grado,
            [],
        )

        materias = MAPA_CURRICULAR.get(
            grado,
            [],
        )

        for materia in materias:

            for mes in meses_demo:

                detalles = {}

                id_base = (
                    f"{grado}_{materia}_{mes}"
                    .replace(" ", "_")
                )

                id_doc = f"{CICLO}_{id_base}"

                for alumno in estudiantes:

                    nie = alumno["nie"]

                    if materia == "Conducta":

                        valor = promedio_mined(
                            random.uniform(7.0, 10.0)
                        )

                        detalles[nie] = {
                            "Nota Conducta": valor,
                            "Promedio": valor,
                        }

                    else:

                        act1 = nota()
                        act2 = nota()
                        alt1 = nota()
                        alt2 = nota()
                        examen = nota()

                        promedio = (
                            act1 * 0.25
                            + act2 * 0.25
                            + alt1 * 0.10
                            + alt2 * 0.10
                            + examen * 0.30
                        )

                        promedio = promedio_mined(
                            promedio
                        )

                        detalles[nie] = {
                            "Act1 (25%)": act1,
                            "Act2 (25%)": act2,
                            "Alt1 (10%)": alt1,
                            "Alt2 (10%)": alt2,
                            "Examen (30%)": examen,
                            "Promedio": promedio,
                        }

                    guardar_documento(
                        db,
                        "notas",
                        f"{nie}_{id_doc}",
                        {
                            "nie": nie,
                            "ciclo_lectivo": CICLO,
                            "grado": grado,
                            "materia": materia,
                            "mes": mes,
                            "promedio_final": (
                                detalles[nie]["Promedio"]
                            ),
                        },
                    )

                    contador_individual += 1

                guardar_documento(
                    db,
                    "notas_mensuales",
                    id_doc,
                    {
                        "ciclo_lectivo": CICLO,
                        "grado": grado,
                        "materia": materia,
                        "mes": mes,
                        "detalles": detalles,
                    },
                )

                contador_mensual += 1

    print(
        f"✓ Notas individuales: "
        f"{contador_individual}"
    )

    print(
        f"✓ Registros mensuales: "
        f"{contador_mensual}"
    )


# ============================================================
# ASISTENCIA
# ============================================================

def crear_asistencia(db, alumnos):
    alumnos_por_grado = {}

    for alumno in alumnos:
        alumnos_por_grado.setdefault(
            alumno["grado_actual"],
            [],
        ).append(alumno)

    fecha_base = datetime(
        2027,
        2,
        8,
    )

    contador = 0

    for dia in range(10):

        fecha = fecha_base + timedelta(
            days=dia
        )

        # No generar sábado/domingo
        if fecha.weekday() >= 5:
            continue

        for grado, estudiantes in (
            alumnos_por_grado.items()
        ):

            registros = {}
            observaciones = {}

            for alumno in estudiantes:

                estado = random.choices(
                    [
                        "Presente",
                        "Ausente",
                        "Tardanza",
                        "Permiso",
                    ],
                    weights=[
                        88,
                        5,
                        5,
                        2,
                    ],
                )[0]

                registros[
                    alumno["nie"]
                ] = estado

                if estado == "Ausente":
                    observaciones[
                        alumno["nie"]
                    ] = "Ausencia justificada."

                elif estado == "Tardanza":
                    observaciones[
                        alumno["nie"]
                    ] = "Ingreso posterior a la hora."

                else:
                    observaciones[
                        alumno["nie"]
                    ] = ""

            id_doc = (
                f"{CICLO}_"
                f"{fecha.date()}_"
                f"{grado}"
            )

            guardar_documento(
                db,
                "asistencia",
                id_doc,
                {
                    "fecha": fecha,
                    "ciclo_lectivo": CICLO,
                    "grado": grado,
                    "registros": registros,
                    "observaciones": observaciones,
                },
            )

            contador += 1

    print(f"✓ Registros de asistencia: {contador}")


# ============================================================
# FINANZAS
# ============================================================

def crear_finanzas(db, alumnos):
    contador = 0

    meses = [
        "Matrícula 2027",
        "Mes de Febrero",
        "Mes de Marzo",
    ]

    for alumno in alumnos:

        # La mayoría estará al día.
        cantidad_pagos = random.choices(
            [1, 2, 3],
            weights=[10, 25, 65],
        )[0]

        for concepto in meses[:cantidad_pagos]:

            if concepto == "Matrícula 2027":
                descripcion = (
                    "Matrícula - Ciclo 2027"
                )
                monto = 45.00
            else:
                descripcion = (
                    f"Colegiatura - {concepto}"
                )
                monto = 35.00

            fecha = datetime(
                2027,
                random.choice([1, 2, 3]),
                random.randint(1, 15),
                9,
                random.randint(0, 59),
            )

            guardar_documento(
                db,
                "finanzas",
                f"demo_ingreso_{contador + 1:05d}",
                {
                    "tipo": "ingreso",
                    "descripcion": descripcion,
                    "monto": monto,
                    "alumno_nie": alumno["nie"],
                    "nombre_persona": (
                        f"{alumno['apellidos']} "
                        f"{alumno['nombres']}"
                    ),
                    "grado_alumno": (
                        alumno["grado_actual"]
                    ),
                    "ciclo_lectivo": CICLO,
                    "observaciones": (
                        "Registro demostrativo"
                    ),
                    "fecha": fecha,
                    "fecha_legible": (
                        fecha.strftime(
                            "%d/%m/%Y %H:%M"
                        )
                    ),
                    "id_short": (
                        f"D{contador + 1:05d}"
                    ),
                },
            )

            contador += 1

    # Algunos gastos institucionales para que
    # los reportes financieros tengan movimiento.
    gastos = [
        ("Papelería y útiles", 86.50),
        ("Mantenimiento de instalaciones", 125.00),
        ("Material didáctico", 72.30),
        ("Servicio de Internet", 45.00),
        ("Limpieza y suministros", 58.75),
    ]

    for descripcion, monto in gastos:

        fecha = datetime(
            2027,
            2,
            random.randint(5, 20),
            10,
            0,
        )

        guardar_documento(
            db,
            "finanzas",
            f"demo_gasto_{contador + 1:05d}",
            {
                "tipo": "egreso",
                "descripcion": descripcion,
                "monto": float(monto),
                "nombre_persona": (
                    NOMBRE_INSTITUCION
                ),
                "ciclo_lectivo": CICLO,
                "observaciones": (
                    "Movimiento ficticio DEMO"
                ),
                "fecha": fecha,
                "fecha_legible": (
                    fecha.strftime(
                        "%d/%m/%Y %H:%M"
                    )
                ),
                "id_short": (
                    f"G{contador + 1:05d}"
                ),
            },
        )

        contador += 1

    print(f"✓ Movimientos financieros: {contador}")


# ============================================================
# BITÁCORA
# ============================================================

def crear_bitacora(db, alumnos):
    ejemplos = [
        "Excelente participación durante la jornada.",
        "Responsable asistió a reunión de seguimiento.",
        "Se destacó por colaboración con sus compañeros.",
        "Se brindaron indicaciones para mejorar hábitos de estudio.",
        "Participó satisfactoriamente en actividad institucional.",
    ]

    seleccionados = random.sample(
        alumnos,
        min(20, len(alumnos)),
    )

    for indice, alumno in enumerate(
        seleccionados,
        start=1,
    ):

        fecha = datetime(
            2027,
            2,
            random.randint(5, 25),
            11,
            0,
        )

        guardar_documento(
            db,
            "bitacora",
            f"demo_bitacora_{indice:03d}",
            {
                "nie": alumno["nie"],
                "alumno": (
                    f"{alumno['apellidos']} "
                    f"{alumno['nombres']}"
                ),
                "grado": alumno["grado_actual"],
                "fecha": fecha,
                "fecha_legible": (
                    fecha.strftime(
                        "%d/%m/%Y %H:%M"
                    )
                ),
                "autor": "Docente Demo",
                "contenido": random.choice(
                    ejemplos
                ),
                "ciclo_lectivo": CICLO,
            },
        )

    print(
        f"✓ Registros de bitácora: "
        f"{len(seleccionados)}"
    )


# ============================================================
# PROCESO PRINCIPAL
# ============================================================

def main():

    db, _ = conectar_firebase_demo()

    confirmar_entorno(db)

    print()
    print("Creando EduManager DEMO...")
    print()

    crear_configuracion(db)
    crear_usuarios(db)
    crear_docentes(db)

    alumnos = crear_alumnos(db)

    crear_carga_academica(db)
    crear_notas(db, alumnos)
    crear_asistencia(db, alumnos)
    crear_finanzas(db, alumnos)
    crear_bitacora(db, alumnos)

    print()
    print("=" * 65)
    print("EDUMANAGER DEMO CREADO CORRECTAMENTE")
    print("=" * 65)
    print(f"Institución : {NOMBRE_INSTITUCION}")
    print(f"Ciclo       : {CICLO}")
    print(f"Proyecto    : {db.project}")
    print()
    print("Usuario administrador:")
    print("  admin.demo")
    print("  Demo2027!")
    print()
    print("Usuario docente:")
    print("  docente.demo")
    print("  Demo2027!")
    print()
    print(
        "Todos los nombres, teléfonos, NIE y "
        "movimientos son ficticios."
    )
    print("=" * 65)


if __name__ == "__main__":
    main()