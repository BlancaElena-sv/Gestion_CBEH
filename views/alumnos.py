import time

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from config import CICLO_LECTIVO


def eliminar_documentos_consulta(db, tabla, campo, valor):
    """
    Elimina todos los registros de una tabla de Supabase
    donde campo == valor.
    """
    try:
        response = db.table(tabla).select("*").eq(campo, valor).execute()
        eliminados = 0
        if response.data:
            for row in response.data:
                # Buscar la llave primaria de forma inteligente
                if "id" in row:
                    id_col = "id"
                elif "nie" in row:
                    id_col = "nie"
                elif "alumno_nie" in row:
                    id_col = "alumno_nie"
                else:
                    # Si no encuentra un ID obvio, usa la misma columna de búsqueda
                    id_col = campo

                # Validar que el valor del ID exista antes de borrar
                valor_id = row.get(id_col)
                if valor_id is not None:
                    db.table(tabla).delete().eq(id_col, valor_id).execute()
                    eliminados += 1
        return eliminados
    except Exception as e:
        st.error(f"Error al eliminar de {tabla}: {e}")
        return 0


def _es_alumno_graduado(data):
    """
    Detecta expedientes graduados de forma tolerante a mayúsculas,
    espacios y registros antiguos.
    """
    estado = str(data.get("estado", "")).strip().casefold()
    motivo = str(data.get("motivo_baja", "")).strip().casefold()
    return (
        estado == "graduado"
        or motivo in {"graduación", "graduacion"}
        or bool(data.get("fecha_graduacion"))
    )


def mostrar_consulta_alumnos(
    db,
    lista_grados,
    mapa_curricular,
    redondear_mined,
    get_base64,
    obtener_fecha_hoy,
    subir_archivo,
):
    """
    Vista del expediente electrónico del alumno.
    db: cliente de Supabase
    """
    st.title("🔎 Expediente Electrónico")

    col_search, col_res = st.columns([1, 3])
    with col_search:
        st.markdown("### 🔍 Búsqueda")
        metodo = st.radio("Criterio:", ["NIE", "Grado"])

        if metodo == "NIE":
            val = st.text_input("Ingrese NIE:")
            if st.button("Buscar Expediente") and val:
                response = db.table("alumnos").select("*").eq("nie", val).execute()
                if response.data and len(response.data) > 0:
                    st.session_state.alum_view = response.data[0]
                else:
                    st.error("No existe")
        else:
            g = st.selectbox("Filtrar Grado", ["Todos"] + lista_grados)
            res = []

            if g != "Todos":
                response = (
                    db.table("alumnos").select("*").eq("grado_actual", g).execute()
                )
                if response.data:
                    for data in response.data:
                        if _es_alumno_graduado(data):
                            continue
                        res.append(data)
            else:
                response = db.table("alumnos").select("*").limit(50).execute()
                if response.data:
                    for data in response.data:
                        if _es_alumno_graduado(data):
                            continue
                        res.append(data)
                        if len(res) >= 50:
                            break

            sel = st.selectbox(
                "Seleccionar Alumno",
                ["Seleccionar..."]
                + [
                    f"{r['nie']} - {r.get('apellidos', '')} {r.get('nombres', '')}"
                    for r in res
                ],
            )

            if sel != "Seleccionar...":
                nie_sel = sel.split(" - ")[0]
                response = db.table("alumnos").select("*").eq("nie", nie_sel).execute()
                if response.data and len(response.data) > 0:
                    st.session_state.alum_view = response.data[0]

    # ==========================================
    # EXPEDIENTE
    # ==========================================
    if "alum_view" not in st.session_state:
        st.info(
            "Busque un alumno por NIE o seleccione uno por grado "
            "para visualizar su expediente."
        )
        return

    a = st.session_state.alum_view

    # Buscar maestro guía
    response = (
        db.table("carga_academica")
        .select("*")
        .eq("grado", a["grado_actual"])
        .eq("es_guia", True)
        .execute()
    )
    maestro_guia = "No Asignado"
    if response.data and len(response.data) > 0:
        maestro_guia = response.data[0]["nombre_docente"]

    st.markdown("---")
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 3, 2])
        with c1:
            # En Supabase, la foto está en el campo aplanado 'foto_url'
            foto_url_alum = a.get("foto_url")
            if not foto_url_alum:
                foto_url_alum = "https://via.placeholder.com/150"
            st.image(foto_url_alum, width=130)
        with c2:
            st.title(f"{a.get('apellidos', '')} {a.get('nombres', '')}")
            st.markdown(f"#### **NIE:** {a['nie']}")
            st.markdown(f"**Grado:** {a['grado_actual']} | **Turno:** {a.get('turno')}")
            st.markdown(f"**Ciclo Lectivo:** {a.get('ciclo_lectivo', 'No definido')}")
            st.info(f"👨‍ **Maestro Guía:** {maestro_guia}")
        with c3:
            estado = a.get("estado", "Activo")
            color = "green" if estado == "Activo" else "red"
            st.markdown(
                f"""
                <h3 style="
                    color:{color};
                    text-align:center;
                    border:2px solid {color};
                    padding:5px;
                    border-radius:10px;
                ">
                    {estado.upper()}
                </h3>
                """,
                unsafe_allow_html=True,
            )

    tabs = st.tabs(
        [
            "📋 Datos y Documentos",
            "💰 Historial y Solvencia",
            "📊 Boleta de Notas",
            "⚙️ Edición Expediente",
            "📒 Bitácora",
            "️ Estado y Baja",
            " Historial Académico",
        ]
    )

    # ==========================================
    # TAB 1 - DATOS Y DOCUMENTOS
    # ==========================================
    with tabs[0]:
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.subheader("Datos Personales")
            # En Supabase los campos están aplanados
            st.write(f"**Responsable:** {a.get('encargado_nombre', '')}")
            st.write(f"**Teléfono:** {a.get('encargado_telefono', '')}")
            st.write(f"**Dirección:** {a.get('encargado_direccion', '')}")
        with col_d2:
            st.subheader(" Documentos")
            # En Supabase los documentos están en 'otros_documentos' (JSONB)
            docs = a.get("otros_documentos", [])
            if isinstance(docs, str):
                import json

                try:
                    docs = json.loads(docs)
                except Exception:
                    docs = []
            if docs:
                for i, url in enumerate(set(docs), start=1):
                    with st.expander(f"👁️ Visualizar Documento {i}"):
                        g_view = (
                            f"https://docs.google.com/gview?embedded=true&url={url}"
                        )
                        st.markdown(
                            f"""
                            <iframe
                                src="{g_view}"
                                width="100%"
                                height="500px"
                                style="border:none;">
                            </iframe>
                            """,
                            unsafe_allow_html=True,
                        )
                        st.caption(f"[Enlace Directo]({url})")
            else:
                st.info("Sin documentos.")

    # ==========================================
    # TAB 2 - HISTORIAL Y SOLVENCIA
    # ==========================================
    with tabs[1]:
        col_fin1, col_fin2 = st.columns([2, 1])
        with col_fin1:
            st.subheader("Historial de Pagos")
            response = (
                db.table("finanzas")
                .select("*")
                .eq("alumno_nie", a["nie"])
                .eq("tipo", "ingreso")
                .execute()
            )
            raw_pagos = response.data if response.data else []

            if raw_pagos:
                df_pagos = pd.DataFrame(raw_pagos)
                cols_mostrar = [
                    c
                    for c in ["fecha_legible", "descripcion", "monto"]
                    if c in df_pagos.columns
                ]
                st.dataframe(df_pagos[cols_mostrar], width="stretch")
                st.write("---")
                st.write("**🖨️ Reimprimir Recibo Histórico**")
                opciones_recibo = {}
                for p in raw_pagos:
                    key = f"{p.get('fecha_legible', '')} - {p.get('descripcion', '')} (${p.get('monto', 0)})"
                    opciones_recibo[key] = p
                sel_recibo = st.selectbox(
                    "Seleccione un pago:",
                    ["Seleccionar..."] + list(opciones_recibo.keys()),
                )
                if sel_recibo != "Seleccionar...":
                    p_obj = opciones_recibo[sel_recibo]
                    if st.button(
                        "Visualizar Recibo", key="btn_visualizar_recibo_alumno"
                    ):
                        logo = get_base64("logo.png")
                        hi = f'<img src="{logo}" height="60">' if logo else ""
                        html_recibo = f"""
                        <div style="
                            border:2px solid #333;
                            padding:20px;
                            font-family:Helvetica, sans-serif;
                            max-width:700px;
                            margin:auto;
                        ">
                            <table width="100%">
                                <tr>
                                    <td width="20%">{hi}</td>
                                    <td width="60%" align="center">
                                        <h3 style="margin:0;">COLEGIO PROFA. BLANCA ELENA DE HERNÁNDEZ</h3>
                                        <p style="margin:5px; font-size:12px;">San Felipe, San Bartolo, Ilopango</p>
                                        <p style="margin:0; font-size:12px;"><b>COMPROBANTE DE INGRESO (COPIA)</b></p>
                                    </td>
                                    <td width="20%" align="right">
                                        <h4 style="margin:0; color:#d32f2f;">NO. {p_obj.get("id_short", "000")}</h4>
                                        <p style="font-size:12px;">{p_obj.get("fecha_legible", "")}</p>
                                    </td>
                                </tr>
                            </table>
                            <hr>
                            <div style="padding:10px;">
                                <p><b>RECIBIMOS DE:</b> {p_obj.get("nombre_persona", "")}</p>
                                <p><b>LA CANTIDAD DE:</b> <span style="font-size:18px; font-weight:bold;">${p_obj.get("monto", 0):.2f}</span></p>
                                <p><b>POR CONCEPTO DE:</b> {p_obj.get("descripcion", "")}</p>
                            </div>
                            <br><br>
                            <table width="100%">
                                <tr>
                                    <td align="center" style="border-top:1px solid #000; width:40%;">Entregado Por</td>
                                    <td width="20%"></td>
                                    <td align="center" style="border-top:1px solid #000; width:40%;">Recibido (Caja)</td>
                                </tr>
                            </table>
                        </div>
                        """
                        components.html(
                            f"""
                            <html>
                                <body>
                                    {html_recibo}
                                    <br>
                                    <center>
                                        <button onclick="window.print()">🖨️ IMPRIMIR COPIA</button>
                                    </center>
                                </body>
                            </html>
                            """,
                            height=400,
                            scrolling=True,
                        )
            else:
                st.info("Sin pagos registrados.")

        with col_fin2:
            st.markdown("### 🎫 Solvencia")
            periodo = st.selectbox(
                "Examen:",
                ["I Trimestre", "II Trimestre", "III Trimestre", "Final"],
            )
            if st.button("Generar Taco", key="btn_generar_taco"):
                fecha = obtener_fecha_hoy().strftime("%d/%m/%Y")
                logo = get_base64("logo.png")
                hi = f'<img src="{logo}" height="40">' if logo else ""
                html = f"""
                <div style="
                    font-family:monospace;
                    width:300px;
                    margin:auto;
                    padding:10px;
                    border:1px dashed black;
                    text-align:center;
                ">
                    <div style="display:flex; align-items:center; justify-content:center;">
                        {hi}
                        <b>COLEGIO BLANCA ELENA</b>
                    </div>
                    <h4 style="background:black; color:white; margin:5px 0;">SOLVENCIA EXAMEN</h4>
                    <div style="text-align:left; font-size:11px;">
                        <b>ALUMNO:</b> {a.get("apellidos", "")} {a.get("nombres", "")}<br>
                        <b>NIE:</b> {a["nie"]}<br>
                        <b>PERIODO:</b> {periodo}<br>
                        <b>ESTADO:</b> SOLVENTE ✅
                    </div>
                    <br>
                    <table border="1" style="width:100%; font-size:10px; border-collapse:collapse; text-align:center;">
                        <tr><td>LUN</td><td>MAR</td><td>MIE</td><td>JUE</td><td>VIE</td></tr>
                        <tr><td height="30"></td><td></td><td></td><td></td><td></td></tr>
                    </table>
                    <br>
                    <span style="font-size:9px;">Fecha: {fecha}</span>
                </div>
                """
                components.html(
                    f"""
                    <html>
                        <body>
                            {html}
                            <br>
                            <center>
                                <button onclick="window.print()">🖨️ IMPRIMIR</button>
                            </center>
                        </body>
                    </html>
                    """,
                    height=350,
                )

    # ==========================================
    # TAB 3 - BOLETA
    # ==========================================
    with tabs[2]:
        st.subheader("Boleta Oficial")
        ciclo_actual_alumno = str(a.get("ciclo_lectivo", CICLO_LECTIVO))
        response = db.table("notas").select("*").eq("nie", a["nie"]).execute()
        notas_data = response.data if response.data else []

        nm = {}
        for dd in notas_data:
            # Filtro crítico: ignorar notas de otros ciclos
            if str(dd.get("ciclo_lectivo", "")) != ciclo_actual_alumno:
                continue
            if dd["materia"] not in nm:
                nm[dd["materia"]] = {}
            nm[dd["materia"]][dd["mes"]] = dd["promedio_final"]

        filas = []
        malla = mapa_curricular.get(a["grado_actual"], [])
        for mat in malla:
            if mat in nm:
                n = nm[mat]
                t1 = redondear_mined(
                    (n.get("Febrero", 0) + n.get("Marzo", 0) + n.get("Abril", 0)) / 3
                )
                t2 = redondear_mined(
                    (n.get("Mayo", 0) + n.get("Junio", 0) + n.get("Julio", 0)) / 3
                )
                t3 = redondear_mined(
                    (n.get("Agosto", 0) + n.get("Septiembre", 0) + n.get("Octubre", 0))
                    / 3
                )
                fin = redondear_mined((t1 + t2 + t3) / 3)
                filas.append(
                    f"""
                    <tr>
                        <td style="text-align:left">{mat}</td>
                        <td>{n.get("Febrero", "-")}</td>
                        <td>{n.get("Marzo", "-")}</td>
                        <td>{n.get("Abril", "-")}</td>
                        <td style="background:#eee"><b>{t1}</b></td>
                        <td>{n.get("Mayo", "-")}</td>
                        <td>{n.get("Junio", "-")}</td>
                        <td>{n.get("Julio", "-")}</td>
                        <td style="background:#eee"><b>{t2}</b></td>
                        <td>{n.get("Agosto", "-")}</td>
                        <td>{n.get("Septiembre", "-")}</td>
                        <td>{n.get("Octubre", "-")}</td>
                        <td style="background:#eee"><b>{t3}</b></td>
                        <td style="background:#333; color:white;"><b>{fin}</b></td>
                    </tr>
                    """
                )

        logo = get_base64("logo.png")
        sello = get_base64("sello.png")
        hi = f'<img src="{logo}" height="60">' if logo else ""
        hs = f'<img src="{sello}" height="80">' if sello else ""
        html = f"""
        <div style="font-family:Arial; font-size:12px; padding:20px;">
            <div style="display:flex; align-items:center; border-bottom:2px solid black; margin-bottom:10px;">
                {hi}
                <div style="margin-left:20px">
                    <h2>COLEGIO PROFA. BLANCA ELENA</h2>
                    <h4>INFORME DE NOTAS</h4>
                </div>
            </div>
            <p>
                <b>Alumno:</b> {a.get("apellidos", "")} {a.get("nombres", "")} |
                <b>Grado:</b> {a["grado_actual"]} |
                <b>Guía:</b> {maestro_guia}
            </p>
            <table border="1" style="width:100%; border-collapse:collapse; text-align:center;">
                <tr style="background:#ddd; font-weight:bold;">
                    <td>ASIGNATURA</td><td>F</td><td>M</td><td>A</td><td>T1</td>
                    <td>M</td><td>J</td><td>J</td><td>T2</td>
                    <td>A</td><td>S</td><td>O</td><td>T3</td><td>FIN</td>
                </tr>
                {"".join(filas)}
            </table>
            <br><br><br>
            <div style="display:flex; justify-content:space-between; align-items:end; padding:0 50px;">
                <div style="text-align:center; width:30%;">
                    <div style="border-top:1px solid black; width:100%;">Orientador</div>
                </div>
                <div style="text-align:center;">{hs}</div>
                <div style="text-align:center; width:30%;">
                    <div style="border-top:1px solid black; width:100%;">Dirección</div>
                </div>
            </div>
        </div>
        """
        components.html(
            f"""
            <html>
                <body>
                    {html}
                    <br>
                    <button onclick="window.print()">🖨️ IMPRIMIR BOLETA</button>
                    <style>
                        @media print {{ button {{ display:none; }} }}
                    </style>
                </body>
            </html>
            """,
            height=600,
            scrolling=True,
        )

    # ==========================================
    # TAB 4 - EDICIÓN
    # ==========================================
    with tabs[3]:
        st.subheader("Gestión del Expediente")
        with st.form("edit_full"):
            c1, c2 = st.columns(2)
            nn = c1.text_input("Nombres", a.get("nombres", ""))
            na = c2.text_input("Apellidos", a.get("apellidos", ""))
            indice_grado = (
                lista_grados.index(a["grado_actual"])
                if a["grado_actual"] in lista_grados
                else 0
            )
            ng = c1.selectbox("Grado", lista_grados, index=indice_grado)
            turnos = ["Matutino", "Vespertino"]
            turno_actual = a.get("turno", "Matutino")
            indice_turno = turnos.index(turno_actual) if turno_actual in turnos else 0
            nt = c2.selectbox("Turno", turnos, index=indice_turno)
            estados = ["Activo", "Inactivo", "Retirado"]
            estado_actual = a.get("estado", "Activo")
            indice_estado = (
                estados.index(estado_actual) if estado_actual in estados else 0
            )
            ne = c1.selectbox("Estado", estados, index=indice_estado)
            # En Supabase los campos están aplanados
            nres = c2.text_input("Responsable", a.get("encargado_nombre", ""))
            ntel = c1.text_input("Teléfono", a.get("encargado_telefono", ""))
            ndir = c2.text_area("Dirección", a.get("encargado_direccion", ""))
            st.markdown("---")
            new_foto = st.file_uploader(
                "Actualizar Foto", ["jpg", "png"], key="up_foto"
            )
            new_doc = st.file_uploader(
                "Adjuntar Documento", ["pdf", "jpg", "png"], key="up_doc"
            )

            if st.form_submit_button("💾 Guardar Cambios"):
                # En Supabase usamos campos aplanados
                update_data = {
                    "nombres": nn,
                    "apellidos": na,
                    "nombre_completo": f"{na} {nn}",
                    "grado_actual": ng,
                    "turno": nt,
                    "estado": ne,
                    "encargado_nombre": nres,
                    "encargado_telefono": ntel,
                    "encargado_direccion": ndir,
                }

                if new_foto:
                    url = subir_archivo(new_foto, f"expedientes/{a['nie']}")
                    if url:
                        update_data["foto_url"] = url

                if new_doc:
                    url = subir_archivo(new_doc, f"expedientes/{a['nie']}")
                    if url:
                        docs_actuales = a.get("otros_documentos", [])
                        if isinstance(docs_actuales, str):
                            import json

                            try:
                                docs_actuales = json.loads(docs_actuales)
                            except Exception:
                                docs_actuales = []
                        docs_actuales.append(url)
                        update_data["otros_documentos"] = docs_actuales

                db.table("alumnos").update(update_data).eq("nie", a["nie"]).execute()

                # Actualizar también la copia de sesión
                response = db.table("alumnos").select("*").eq("nie", a["nie"]).execute()
                if response.data and len(response.data) > 0:
                    st.session_state.alum_view = response.data[0]

                st.success("Expediente actualizado.")
                time.sleep(1)
                st.rerun()

    # ==========================================
    # TAB 5 - BITÁCORA
    # ==========================================
    with tabs[4]:
        st.markdown("### 📒 Bitácora del Alumno")
        response = db.table("bitacora").select("*").eq("nie", a["nie"]).execute()
        lista_logs = response.data if response.data else []
        lista_logs.sort(key=lambda x: x.get("fecha_legible", ""), reverse=True)

        if lista_logs:
            for log in lista_logs:
                with st.container(border=True):
                    c_meta, c_body = st.columns([1, 3])
                    with c_meta:
                        st.caption(f"📅 {log.get('fecha_legible')}")
                        st.caption(f"️ **{log.get('autor')}**")
                    with c_body:
                        st.write(log.get("contenido"))
        else:
            st.info("No hay registros en la bitácora.")

    # ==========================================
    # TAB 6 - ESTADO, BAJA Y ELIMINACIÓN
    # ==========================================
    with tabs[5]:
        st.subheader("🛡️ Gestión del Estado del Alumno")
        estado_actual = a.get("estado", "Activo")
        col_estado, col_info = st.columns([1, 2])
        with col_estado:
            if estado_actual == "Activo":
                st.success("✅ Alumno actualmente ACTIVO")
            elif estado_actual == "Retirado":
                st.warning("⚠️ Alumno dado de BAJA")
            else:
                st.info(f"Estado actual: {estado_actual}")
        with col_info:
            if a.get("fecha_baja"):
                st.write(f"**Fecha de baja:** {a.get('fecha_baja')}")
            if a.get("motivo_baja"):
                st.write(f"**Motivo:** {a.get('motivo_baja')}")
            if a.get("baja_realizada_por"):
                st.write(f"**Registrado por:** {a.get('baja_realizada_por')}")

        st.divider()

        # ==========================================
        # DAR DE BAJA
        # ==========================================
        st.markdown("### 🟠 Dar de baja")
        st.caption(
            "Esta opción conserva completamente el expediente "
            "académico, financiero y administrativo del alumno."
        )
        motivos_baja = [
            "Retiro voluntario",
            "Cambio de institución",
            "Finalización de estudios",
            "Inasistencia prolongada",
            "Razones económicas",
            "Otro",
        ]
        motivo = st.selectbox(
            "Motivo de baja", motivos_baja, key=f"motivo_baja_{a['nie']}"
        )
        motivo_otro = ""
        if motivo == "Otro":
            motivo_otro = st.text_input(
                "Especifique el motivo", key=f"motivo_otro_{a['nie']}"
            )

        if estado_actual == "Activo":
            if st.button("🟠 Dar de baja al alumno", key=f"btn_baja_{a['nie']}"):
                motivo_final = motivo_otro.strip() if motivo == "Otro" else motivo
                if motivo == "Otro" and not motivo_final:
                    st.error("Debe especificar el motivo.")
                else:
                    datos_baja = {
                        "estado": "Retirado",
                        "fecha_baja": obtener_fecha_hoy().strftime("%d/%m/%Y"),
                        "motivo_baja": motivo_final,
                        "baja_realizada_por": st.session_state.get(
                            "user_name", "Administrador"
                        ),
                    }
                    db.table("alumnos").update(datos_baja).eq("nie", a["nie"]).execute()
                    st.session_state.alum_view.update(datos_baja)
                    st.success("✅ Alumno dado de baja correctamente.")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("El alumno ya se encuentra dado de baja.")
            if st.button("️ Reactivar alumno", key=f"btn_reactivar_{a['nie']}"):
                datos_reactivacion = {
                    "estado": "Activo",
                    "fecha_baja": None,
                    "motivo_baja": None,
                    "baja_realizada_por": None,
                }
                db.table("alumnos").update(datos_reactivacion).eq(
                    "nie", a["nie"]
                ).execute()
                st.session_state.alum_view.update(datos_reactivacion)
                st.success("✅ Alumno reactivado.")
                time.sleep(1)
                st.rerun()

        # ==========================================
        # ZONA DE PELIGRO
        # ==========================================
        st.divider()
        st.markdown("### 🔴 Zona de peligro")
        st.error(
            "La eliminación definitiva no se puede deshacer. "
            "Se eliminarán también notas, pagos y bitácora "
            "relacionados con este alumno."
        )
        st.write(f"Para confirmar escriba el NIE: **{a['nie']}**")
        confirmacion = st.text_input("Confirmación", key=f"confirm_delete_{a['nie']}")
        confirmar_eliminacion = st.checkbox(
            "Entiendo que esta acción es irreversible.",
            key=f"check_delete_{a['nie']}",
        )

        if st.button("🗑️ ELIMINAR DEFINITIVAMENTE", key=f"delete_alumno_{a['nie']}"):
            if confirmacion.strip() != str(a["nie"]):
                st.error("El NIE escrito no coincide.")
            elif not confirmar_eliminacion:
                st.error(
                    "Debe confirmar que comprende que la eliminación es irreversible."
                )
            else:
                try:
                    nie = a["nie"]

                    # 1. NOTAS INDIVIDUALES
                    notas_eliminadas = eliminar_documentos_consulta(
                        db, "notas", "nie", nie
                    )

                    # 2. FINANZAS
                    pagos_eliminados = eliminar_documentos_consulta(
                        db, "finanzas", "alumno_nie", nie
                    )

                    # 3. BITÁCORA
                    logs_eliminados = eliminar_documentos_consulta(
                        db, "bitacora", "nie", nie
                    )

                    # 4. NOTAS MENSUALES (actualizar JSONB)
                    response_nm = db.table("notas_mensuales").select("*").execute()
                    if response_nm.data:
                        for row in response_nm.data:
                            detalles = row.get("detalles", {})
                            if isinstance(detalles, str):
                                import json

                                try:
                                    detalles = json.loads(detalles)
                                except Exception:
                                    detalles = {}
                            if nie in detalles:
                                detalles.pop(nie, None)
                                db.table("notas_mensuales").update(
                                    {"detalles": detalles}
                                ).eq("id", row["id"]).execute()

                    # 5. ASISTENCIA (actualizar JSONB)
                    response_asist = db.table("asistencia").select("*").execute()
                    if response_asist.data:
                        for row in response_asist.data:
                            registros = row.get("registros", {})
                            observaciones = row.get("observaciones", {})
                            if isinstance(registros, str):
                                import json

                                try:
                                    registros = json.loads(registros)
                                except Exception:
                                    registros = {}
                            if isinstance(observaciones, str):
                                import json

                                try:
                                    observaciones = json.loads(observaciones)
                                except Exception:
                                    observaciones = {}
                            modificado = False
                            if nie in registros:
                                registros.pop(nie, None)
                                modificado = True
                            if nie in observaciones:
                                observaciones.pop(nie, None)
                                modificado = True
                            if modificado:
                                db.table("asistencia").update(
                                    {
                                        "registros": registros,
                                        "observaciones": observaciones,
                                    }
                                ).eq("id", row["id"]).execute()

                    # 6. DOCUMENTO PRINCIPAL
                    db.table("alumnos").delete().eq("nie", nie).execute()

                    # Limpiar sesión
                    if "alum_view" in st.session_state:
                        del st.session_state["alum_view"]

                    st.success(
                        "✅ Alumno y registros relacionados eliminados definitivamente."
                    )
                    st.write(f"Notas eliminadas: {notas_eliminadas}")
                    st.write(f"Movimientos financieros eliminados: {pagos_eliminados}")
                    st.write(f"Registros de bitácora eliminados: {logs_eliminados}")
                    time.sleep(2)
                    st.rerun()
                except Exception as error:
                    st.error(f"No se pudo completar la eliminación: {error}")

    # ==========================================
    # TAB 7 - HISTORIAL ACADÉMICO
    # ==========================================
    with tabs[6]:
        st.subheader("📚 Historial Académico")
        historial = a.get("historial_academico", [])
        if isinstance(historial, str):
            import json

            try:
                historial = json.loads(historial)
            except Exception:
                historial = []

        if not historial:
            st.info("Este alumno todavía no tiene registros históricos de promoción.")
            st.caption(
                "El historial comenzará a generarse cuando se ejecute una promoción de grado."
            )
        else:
            historial_ordenado = sorted(
                historial, key=lambda registro: registro.get("ciclo", 0), reverse=True
            )
            filas = []
            for registro in historial_ordenado:
                resultado = registro.get("resultado", "-")
                grado = registro.get("grado", "-")
                grado_destino = registro.get("grado_destino", "-")
                ciclo = registro.get("ciclo", "-")
                ciclo_destino = registro.get("ciclo_destino", "-")
                fecha = registro.get("fecha", "-")
                usuario = registro.get("usuario", "-")

                if resultado == "Graduado":
                    destino_mostrar = "Graduado"
                else:
                    destino_mostrar = grado_destino

                filas.append(
                    {
                        "Ciclo": ciclo,
                        "Grado cursado": grado,
                        "Resultado": resultado,
                        "Destino": destino_mostrar,
                        "Ciclo destino": ciclo_destino,
                        "Fecha": fecha,
                        "Procesado por": usuario,
                    }
                )
            df_historial = pd.DataFrame(filas)
            st.dataframe(df_historial, width="stretch", hide_index=True)
            st.divider()
            st.markdown("### 📖 Trayectoria del alumno")
            for registro in historial_ordenado:
                ciclo = registro.get("ciclo", "-")
                grado = registro.get("grado", "-")
                resultado = registro.get("resultado", "-")
                grado_destino = registro.get("grado_destino", "")
                if resultado == "Graduado":
                    st.success(f"🎓 {ciclo} · {grado} · Graduado")
                elif resultado == "Promovido":
                    st.info(f"📘 {ciclo} · {grado} → {grado_destino}")
                else:
                    st.write(f"{ciclo} · {grado} · {resultado}")
