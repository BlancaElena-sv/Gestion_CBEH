import base64
import json
from datetime import date, datetime
from pathlib import Path

from firebase_service import conectar_firebase

try:
    from google.cloud.firestore_v1 import GeoPoint
except Exception:
    GeoPoint = None


def deserializar_valor(valor, db):
    if isinstance(valor, list):
        return [deserializar_valor(v, db) for v in valor]

    if not isinstance(valor, dict):
        return valor

    tipo = valor.get("__tipo__")

    if tipo == "datetime":
        return datetime.fromisoformat(valor["valor"])

    if tipo == "date":
        return date.fromisoformat(valor["valor"])

    if tipo == "bytes":
        return base64.b64decode(valor["valor"])

    if tipo == "document_reference":
        return db.document(valor["valor"])

    if tipo == "geopoint":
        if GeoPoint is None:
            raise RuntimeError(
                "No se pudo importar GeoPoint de google-cloud-firestore."
            )
        return GeoPoint(
            valor["latitude"],
            valor["longitude"],
        )

    if tipo == "repr":
        return valor["valor"]

    return {
        k: deserializar_valor(v, db)
        for k, v in valor.items()
    }


def restaurar_coleccion(collection_ref, documentos, db):
    for item in documentos:
        doc_id = item["_id"]
        datos = deserializar_valor(
            item.get("data", {}),
            db,
        )

        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(datos)

        subcolecciones = item.get(
            "_subcollections",
            {},
        )

        for nombre_subcol, docs_subcol in subcolecciones.items():
            restaurar_coleccion(
                doc_ref.collection(nombre_subcol),
                docs_subcol,
                db,
            )


def main():
    print("=" * 68)
    print("EDUMANAGER - RESTAURACIÓN DE FIRESTORE")
    print("=" * 68)
    print()
    print("ADVERTENCIA: este proceso escribe datos en Firestore.")
    print("Úsalo únicamente para restaurar un respaldo conocido.")
    print()

    ruta = input(
        "Ruta de la carpeta del respaldo: "
    ).strip().strip('"')

    carpeta = Path(ruta)

    if not carpeta.exists():
        print("La carpeta indicada no existe.")
        return

    manifest = carpeta / "_manifest.json"

    if not manifest.exists():
        print(
            "No se encontró _manifest.json. "
            "No parece un respaldo válido de EduManager."
        )
        return

    confirmacion = input(
        'Para continuar escriba exactamente RESTAURAR: '
    ).strip()

    if confirmacion != "RESTAURAR":
        print("Restauración cancelada.")
        return

    db, error = conectar_firebase()

    if error:
        print(f"ERROR DE FIREBASE: {error}")
        return

    if not db:
        print("No fue posible conectar con Firebase.")
        return

    archivos = sorted(
        p for p in carpeta.glob("*.json")
        if p.name != "_manifest.json"
    )

    for archivo in archivos:
        contenido = json.loads(
            archivo.read_text(
                encoding="utf-8"
            )
        )

        nombre_coleccion = contenido["coleccion"]
        documentos = contenido.get(
            "documentos",
            [],
        )

        print(
            f"Restaurando {nombre_coleccion} "
            f"({len(documentos)} documentos)..."
        )

        restaurar_coleccion(
            db.collection(nombre_coleccion),
            documentos,
            db,
        )

    print()
    print("Restauración finalizada.")


if __name__ == "__main__":
    main()
