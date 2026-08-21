import streamlit as st
from firebase_admin import firestore


def mostrar_inscripcion(
    db,
    lista_grados,
    subir_archivo,
):
    """
    Vista para registrar nuevos alumnos en EduManager.
    """

    st.title("📝 Inscripción 2026")

    with st.form("form_inscripcion"):
        c1, c2 = st.columns(2)

        with c1:
            nie = st.text_input("NIE*")
            nombres = st.text_input("Nombres*")
            apellidos = st.text_input("Apellidos*")

        with c2:
            grado = st.selectbox(
                "Grado",
                lista_grados
            )

            turno = st.selectbox(
                "Turno",
                [
                    "Matutino",
                    "Vespertino"
                ]
            )

            responsable = st.text_input(
                "Responsable"
            )

            telefono = st.text_input(
                "Teléfono"
            )

        direccion = st.text_area(
            "Dirección"
        )

        st.markdown("---")

        c3, c4 = st.columns(2)

        with c3:
            foto = st.file_uploader(
                "Foto",
                [
                    "jpg",
                    "jpeg",
                    "png"
                ]
            )

        with c4:
            documentos = st.file_uploader(
                "Documentos",
                [
                    "pdf",
                    "jpg",
                    "jpeg",
                    "png"
                ],
                accept_multiple_files=True
            )

        guardar = st.form_submit_button(
            "💾 Guardar inscripción",
            width="stretch"
        )

        if guardar:
            # ==========================================
            # VALIDACIONES
            # ==========================================

            nie = nie.strip()
            nombres = nombres.strip()
            apellidos = apellidos.strip()

            if not nie:
                st.error(
                    "El NIE es obligatorio."
                )
                return

            if not nombres:
                st.error(
                    "Los nombres son obligatorios."
                )
                return

            if not apellidos:
                st.error(
                    "Los apellidos son obligatorios."
                )
                return

            try:
                doc_ref = (
                    db.collection("alumnos")
                    .document(nie)
                )

                # Evitar NIE duplicado
                if doc_ref.get().exists:
                    st.error(
                        f"⛔ El NIE {nie} ya está registrado."
                    )
                    return

                ruta = f"expedientes/{nie}"

                # ==========================================
                # DOCUMENTOS
                # ==========================================

                urls_documentos = []

                for archivo in documentos or []:
                    url = subir_archivo(
                        archivo,
                        ruta
                    )

                    if url:
                        urls_documentos.append(
                            url
                        )

                # ==========================================
                # FOTO
                # ==========================================

                foto_url = None

                if foto:
                    foto_url = subir_archivo(
                        foto,
                        ruta
                    )

                # ==========================================
                # GUARDAR ALUMNO
                # ==========================================

                alumno = {
                    "nie": nie,
                    "nombre_completo": (
                        f"{apellidos} {nombres}"
                    ),
                    "nombres": nombres,
                    "apellidos": apellidos,
                    "grado_actual": grado,
                    "turno": turno,
                    "estado": "Activo",

                    "encargado": {
                        "nombre": responsable,
                        "telefono": telefono,
                        "direccion": direccion,
                    },

                    "documentos": {
                        "foto_url": foto_url,
                        "doc_urls": urls_documentos,
                    },

                    "fecha_registro": (
                        firestore.SERVER_TIMESTAMP
                    ),
                }

                doc_ref.set(alumno)

                st.success(
                    f"✅ Alumno {nombres} {apellidos} "
                    f"inscrito correctamente."
                )

            except Exception as error:
                st.error(
                    f"Error al registrar alumno: {error}"
                )