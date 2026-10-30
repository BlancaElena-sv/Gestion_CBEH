import json  # <-- Importante para la conversión
from datetime import datetime

import streamlit as st

from config import CICLO_LECTIVO, TZ_SV


def mostrar_inscripcion(
    db,
    lista_grados,
    subir_archivo,
):
    st.title(" Inscripción 2026")

    with st.form("form_inscripcion"):
        # ... (tus campos iguales, omito para brevedad) ...
        c1, c2 = st.columns(2)
        with c1:
            nie = st.text_input("NIE*")
            nombres = st.text_input("Nombres*")
            apellidos = st.text_input("Apellidos*")
        with c2:
            grado = st.selectbox("Grado", lista_grados)
            turno = st.selectbox("Turno", ["Matutino", "Vespertino"])
            responsable = st.text_input("Responsable")
            telefono = st.text_input("Teléfono")
        direccion = st.text_area("Dirección")
        st.markdown("---")
        c3, c4 = st.columns(2)
        with c3:
            foto = st.file_uploader("Foto", ["jpg", "jpeg", "png"])
        with c4:
            documentos = st.file_uploader(
                "Documentos", ["pdf", "jpg", "jpeg", "png"], accept_multiple_files=True
            )
        guardar = st.form_submit_button(" Guardar inscripción", width="stretch")

        if guardar:
            nie = nie.strip()
            nombres = nombres.strip()
            apellidos = apellidos.strip()

            if not nie or not nombres or not apellidos:
                st.error("NIE, Nombres y Apellidos son obligatorios.")
                return

            try:
                response = db.table("alumnos").select("nie").eq("nie", nie).execute()
                if response.data and len(response.data) > 0:
                    st.error(f"⛔ El NIE {nie} ya está registrado.")
                    return

                ruta = f"expedientes/{nie}"

                # ==========================================
                # DOCUMENTOS
                # ==========================================
                urls_documentos = []
                for archivo in documentos or []:
                    archivo.seek(0)  # <-- Asegurar que el puntero esté al inicio
                    url = subir_archivo(archivo, ruta)
                    if url:
                        urls_documentos.append(url)

                # ==========================================
                # FOTO
                # ==========================================
                foto_url = None
                if foto:
                    foto.seek(0)  # <-- Asegurar que el puntero esté al inicio
                    foto_url = subir_archivo(foto, ruta)

                # ==========================================
                # GUARDAR ALUMNO
                # ==========================================
                alumno = {
                    "nie": nie,
                    "nombre_completo": f"{apellidos} {nombres}",
                    "nombres": nombres,
                    "apellidos": apellidos,
                    "grado_actual": grado,
                    "turno": turno,
                    "estado": "Activo",
                    "ciclo_lectivo": CICLO_LECTIVO,
                    "encargado_nombre": responsable,
                    "encargado_telefono": telefono,
                    "encargado_direccion": direccion,
                    "foto_url": foto_url,
                    # Si la columna en Supabase es JSONB, usa json.dumps
                    # Si es TEXT[], déjalo como urls_documentos
                    "otros_documentos": json.dumps(urls_documentos),
                    "fecha_registro": datetime.now(TZ_SV).isoformat(),
                }

                res = db.table("alumnos").insert(alumno).execute()
                st.success(f"✅ Alumno {nombres} {apellidos} inscrito correctamente.")

                # Opcional: st.rerun() para limpiar el formulario después de guardar
                # st.rerun()

            except Exception as error:
                st.error(f"Error al registrar alumno: {error}")
