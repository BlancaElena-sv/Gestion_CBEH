from firebase_service import conectar_firebase


# ============================================================
# CONFIGURACIÓN
# ============================================================

CICLO_ORIGEN = 2026


# ============================================================
# MIGRAR UNA COLECCIÓN
# ============================================================

def migrar_coleccion(db, nombre_coleccion):
    """
    Agrega ciclo_lectivo=2026 únicamente a los documentos
    que todavía no poseen ese campo.

    NO elimina información.
    NO modifica notas.
    NO modifica grados.
    NO cambia estados.
    """

    print(f"   Abriendo colección: {nombre_coleccion}")

    docs = db.collection(nombre_coleccion).stream()

    print(f"   Lectura iniciada: {nombre_coleccion}")

    actualizados = 0
    ignorados = 0
    procesados = 0

    for doc in docs:

        procesados += 1

        data = doc.to_dict()

        # ----------------------------------------------------
        # Solo migramos documentos que NO tienen ciclo_lectivo
        # ----------------------------------------------------

        if "ciclo_lectivo" not in data:

            doc.reference.update({
                "ciclo_lectivo": CICLO_ORIGEN
            })

            actualizados += 1

        else:
            ignorados += 1

        # Mostrar progreso cada 100 documentos
        if procesados % 100 == 0:
            print(
                f"   {nombre_coleccion}: "
                f"{procesados} documentos procesados..."
            )

    return actualizados, ignorados, procesados


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    print()
    print("=" * 60)
    print("MIGRACIÓN DE DATOS EXISTENTES A CICLO 2026")
    print("=" * 60)

    # --------------------------------------------------------
    # CONEXIÓN A FIREBASE
    # --------------------------------------------------------

    print("\nConectando con Firebase...")

    try:
        db, error = conectar_firebase()

    except Exception as e:
        print(f"\n❌ ERROR AL CONECTAR CON FIREBASE:")
        print(e)
        return

    if error:
        print(f"\n❌ ERROR DE CONEXIÓN:")
        print(error)
        return

    if not db:
        print("\n❌ No fue posible conectar con Firebase.")
        return

    print("✅ Conexión con Firebase establecida.")

    # --------------------------------------------------------
    # COLECCIONES QUE DEBEN TENER CICLO LECTIVO
    # --------------------------------------------------------

    colecciones = [
        "alumnos",
        "notas",
        "notas_mensuales",
        "asistencia",
        "carga_academica",
    ]

    total_actualizados = 0
    total_ignorados = 0
    total_procesados = 0

    # --------------------------------------------------------
    # MIGRACIÓN
    # --------------------------------------------------------

    for coleccion in colecciones:

        print()
        print("-" * 60)
        print(f"Procesando colección: {coleccion}")
        print("-" * 60)

        try:

            actualizados, ignorados, procesados = migrar_coleccion(
                db,
                coleccion
            )

            total_actualizados += actualizados
            total_ignorados += ignorados
            total_procesados += procesados

            print()
            print(
                f"✅ {coleccion}: "
                f"{actualizados} actualizados | "
                f"{ignorados} ya tenían ciclo | "
                f"{procesados} procesados"
            )

        except KeyboardInterrupt:

            print()
            print()
            print("⚠️ MIGRACIÓN INTERRUMPIDA POR EL USUARIO.")
            print(
                "Los documentos ya actualizados permanecen seguros."
            )
            print(
                "Puedes ejecutar nuevamente el script."
            )
            return

        except Exception as error:

            print()
            print(f"❌ ERROR EN LA COLECCIÓN '{coleccion}':")
            print(error)

            # No detenemos toda la migración.
            # Intentamos continuar con la siguiente colección.
            continue

    # --------------------------------------------------------
    # RESUMEN
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("MIGRACIÓN FINALIZADA")
    print("=" * 60)

    print(
        f"Documentos procesados:   {total_procesados}"
    )

    print(
        f"Documentos actualizados: {total_actualizados}"
    )

    print(
        f"Ya tenían ciclo:         {total_ignorados}"
    )

    print()
    print(
        f"Todos los documentos migrados fueron asignados "
        f"al ciclo lectivo {CICLO_ORIGEN}."
    )

    print()
    print(
        "IMPORTANTE: este script puede ejecutarse nuevamente "
        "sin duplicar la migración."
    )

    print("=" * 60)


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    main()