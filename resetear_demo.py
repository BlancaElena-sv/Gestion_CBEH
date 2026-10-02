"""
Script auxiliar para resetear la DEMO.

Borra TODAS las colecciones de la base edumanager-demo
para poder volver a correr crear_demo.py desde cero.

SOLO FUNCIONA EN LA DEMO. Verifica el proyecto antes de borrar.
"""

import sys

from firebase_demo_service import conectar_firebase_demo


COLECCIONES_A_BORRAR = [
    "usuarios",
    "docentes",
    "alumnos",
    "carga_academica",
    "notas",
    "notas_mensuales",
    "asistencia",
    "finanzas",
    "bitacora",
    "configuracion",
]

PROYECTO_PERMITIDO = "edumanager-demo"


def borrar_coleccion(db, nombre):
    """Borra todos los documentos de una colección en lotes."""
    total = 0

    while True:
        docs = list(db.collection(nombre).limit(400).stream())
        if not docs:
            break

        batch = db.batch()
        for doc in docs:
            batch.delete(doc.reference)
        batch.commit()

        total += len(docs)

    return total


def main():
    print()
    print("=" * 60)
    print("RESETEO DE EDU MANAGER DEMO")
    print("=" * 60)

    db, error = conectar_firebase_demo()

    if error:
        print(f"\nError al conectar: {error}")
        sys.exit(1)

    # Verificar que es la demo
    if db.project != PROYECTO_PERMITIDO:
        print(f"\nERROR: Proyecto detectado: {db.project}")
        print(f"Proyecto permitido: {PROYECTO_PERMITIDO}")
        print("OPERACIÓN CANCELADA POR SEGURIDAD.")
        sys.exit(1)

    print(f"\nProyecto: {db.project}")
    print(f"Colecciones a borrar: {len(COLECCIONES_A_BORRAR)}")
    print()

    confirmacion = input(
        "Escriba RESET DEMO para confirmar el borrado: "
    )

    if confirmacion.strip().upper() != "RESET DEMO":
        print("\nOperación cancelada.")
        sys.exit(0)

    print()
    total_global = 0

    for coleccion in COLECCIONES_A_BORRAR:
        try:
            cantidad = borrar_coleccion(db, coleccion)
            total_global += cantidad
            print(f"  ✓ {coleccion}: {cantidad} documentos borrados")
        except Exception as e:
            print(f"  ✗ {coleccion}: error -> {e}")

    print()
    print("=" * 60)
    print(f"RESETEO COMPLETO: {total_global} documentos borrados")
    print("=" * 60)
    print()
    print("Ahora puedes ejecutar: python crear_demo.py")
    print()


if __name__ == "__main__":
    main()
