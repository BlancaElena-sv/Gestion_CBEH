import json
import time
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from config import CICLO_LECTIVO, TZ_SV


def mostrar_panel_docente(
    opcion_seleccionada,
    db,
    lista_grados,
    lista_grados_notas,
    lista_meses,
    mapa_curricular,
    redondear_mined,
    get_base64,
    obtener_fecha_hoy,
    obtener_hora_actual,
):
    usuario_actual = st.session_state.get("user_name", "Docente")

    if opcion_seleccionada == "Mis Listados":
        st.title("🖨️ Imprimir Listas")
        g = st.selectbox("Grado:", lista_grados)
        mes_lista = st.selectbox("Mes:", lista_meses)
        if st.button("Generar Hoja de Control"):
            res_alumnos = (
                db.table("alumnos")
                .select("nombres, apellidos")
                .eq("grado_actual", g)
                .eq("estado", "Activo")
                .execute()
            )
            alumnos_data = res_alumnos.data if res_alumnos.data else []

            lista = sorted(
                [
                    f"{a.get('apellidos', '')} {a.get('nombres', '')}"
                    for a in alumnos_data
                ]
            )
            if not lista:
                st.warning("Sin alumnos")
            else:
                logo = get_base64("logo.png")
                hi = f'<img src="{logo}" height="50">' if logo else ""
                rows = ""
                for i, n in enumerate(lista):
                    rows += f"<tr><td>{i + 1}</td><td style='text-align:left;padding-left:5px;'>{n}</td><td></td><td></td><td></td><td></td><td></td><td></td></tr>"
                html = f"""<div style='font-family:Arial;font-size:12px;padding:20px;'><div style='display:flex;align-items:center;border-bottom:2px solid black;margin-bottom:10px;'>{hi}<div style='margin-left:15px'><h3>COLEGIO PROFA. BLANCA ELENA</h3><h4>CONTROL DE EVALUACIÓN - {mes_lista.upper()} - {g.upper()}</h4></div></div><table border='1' style='width:100%;border-collapse:collapse;text-align:center;'><tr style='background:#eee;font-weight:bold;'><td width='5%'>No.</td><td width='40%'>NOMBRE</td><td width='8%'>ACT1</td><td width='8%'>ACT2</td><td width='8%'>ALT1</td><td width='8%'>ALT2</td><td width='8%'>EXAM</td><td width='10%'>PROM</td></tr>{rows}</table></div>"""
                components.html(
                    f"""<html><body>{html}<br><button onclick="window.print()">🖨️ IMPRIMIR LISTADO</button><style>@media print{{button{{display:none;}}}}</style></body></html>""",
                    height=600,
                    scrolling=True,
                )

    elif opcion_seleccionada == "Tomar Asistencia":
        # (Este bloque ya te funcionaba, lo dejo igual)
        st.title("📅 Control de Asistencia")
        c1, c2 = st.columns(2)
        fecha_asist = c1.date_input("Fecha:", obtener_fecha_hoy())
        grado_asist = c2.selectbox("Grado:", lista_grados)

        if grado_asist:
            id_asistencia = f"{CICLO_LECTIVO}_{fecha_asist}_{grado_asist}"
            res_asist = (
                db.table("asistencia").select("*").eq("id", id_asistencia).execute()
            )
            datos_asist = res_asist.data[0] if res_asist.data else {}

            res_alumnos = (
                db.table("alumnos")
                .select("nie, nombres, apellidos")
                .eq("grado_actual", grado_asist)
                .eq("estado", "Activo")
                .execute()
            )
            alumnos_data = res_alumnos.data if res_alumnos.data else []

            lista_alumnos = [
                {
                    "NIE": a["nie"],
                    "Nombre": f"{a.get('apellidos', '')} {a.get('nombres', '')}",
                }
                for a in alumnos_data
            ]
            lista_alumnos.sort(key=lambda x: x["Nombre"])

            if lista_alumnos:
                regs_actuales = datos_asist.get("registros", {})
                obs_actuales = datos_asist.get("observaciones", {})
                if isinstance(regs_actuales, str):
                    try:
                        regs_actuales = json.loads(regs_actuales)
                    except:
                        regs_actuales = {}
                if isinstance(obs_actuales, str):
                    try:
                        obs_actuales = json.loads(obs_actuales)
                    except:
                        obs_actuales = {}

                data_editor = []
                for alum in lista_alumnos:
                    data_editor.append(
                        {
                            "NIE": alum["NIE"],
                            "Nombre": alum["Nombre"],
                            "Estado": regs_actuales.get(alum["NIE"], "Presente"),
                            "Observación": obs_actuales.get(alum["NIE"], ""),
                        }
                    )
                df_asist = pd.DataFrame(data_editor)
                ed = st.data_editor(
                    df_asist,
                    column_config={
                        "NIE": st.column_config.TextColumn(disabled=True),
                        "Nombre": st.column_config.TextColumn(disabled=True),
                        "Estado": st.column_config.SelectboxColumn(
                            "Estado",
                            options=["Presente", "Ausente", "Tardanza", "Permiso"],
                            required=True,
                        ),
                        "Observación": st.column_config.TextColumn(width="medium"),
                    },
                    hide_index=True,
                    width="stretch",
                    key=id_asistencia,
                )

                if st.button("💾 Guardar Asistencia"):
                    regs = {r["NIE"]: r["Estado"] for r in ed.to_dict(orient="records")}
                    obs_regs = {
                        r["NIE"]: r["Observación"] for r in ed.to_dict(orient="records")
                    }
                    datos_guardar = {
                        "id": id_asistencia,
                        "fecha": fecha_asist.isoformat(),
                        "ciclo_lectivo": CICLO_LECTIVO,
                        "grado": grado_asist,
                        "registros": regs,
                        "observaciones": obs_regs,
                    }
                    db.table("asistencia").upsert(datos_guardar).execute()
                    st.success("Guardado.")
            else:
                st.warning("Sin alumnos.")

    elif opcion_seleccionada == "Cargar Notas":
        st.title("📝 Registro de Notas")
        st.info(f"📅 Ciclo lectivo activo: {CICLO_LECTIVO}")

        c1, c2, c3 = st.columns(3)
        grado = c1.selectbox(
            "Grado", ["Select..."] + lista_grados_notas, key="doc_notas_grado"
        )
        materias = mapa_curricular.get(grado, []) if grado != "Select..." else []
        materia = c2.selectbox(
            "Materia", ["Select..."] + materias, key="doc_notas_materia"
        )
        mes = c3.selectbox("Mes", lista_meses, key="doc_notas_mes")

        if grado == "Select..." or materia == "Select...":
            return

        res_alumnos = (
            db.table("alumnos")
            .select("*")
            .eq("grado_actual", grado)
            .eq("estado", "Activo")
            .execute()
        )
        alumnos = []
        if res_alumnos.data:
            for datos in res_alumnos.data:
                ciclo_alumno = datos.get("ciclo_lectivo", CICLO_LECTIVO)
                if int(ciclo_alumno) != CICLO_LECTIVO:
                    continue
                nie = str(datos.get("nie", "")).strip()
                nombre = (
                    f"{datos.get('apellidos', '')} {datos.get('nombres', '')}".strip()
                )
                alumnos.append({"NIE": nie, "Nombre": nombre})

        if not alumnos:
            st.warning("No hay alumnos activos para este grado.")
            return

        df = pd.DataFrame(alumnos).sort_values("Nombre")
        id_nuevo = f"{CICLO_LECTIVO}_{grado}_{materia}_{mes}".replace(" ", "_")

        # SOLUCIÓN 1: Buscar por 'id' o por sus campos individuales
        res_nm = db.table("notas_mensuales").select("*").eq("id", id_nuevo).execute()
        detalles = {}
        if res_nm.data:
            detalles = res_nm.data[0].get("detalles", {})
        else:
            # Búsqueda de respaldo por si el ID no coincide (ej. migración de Firebase)
            res_alt = (
                db.table("notas_mensuales")
                .select("*")
                .eq("grado", grado)
                .eq("materia", materia)
                .eq("mes", mes)
                .execute()
            )
            if res_alt.data:
                detalles = res_alt.data[0].get("detalles", {})

        if isinstance(detalles, str):
            try:
                detalles = json.loads(detalles)
            except:
                detalles = {}

        detalles = {
            str(k).strip(): v if isinstance(v, dict) else {}
            for k, v in detalles.items()
        }

        columnas_notas = (
            ["Nota Conducta"]
            if materia == "Conducta"
            else [
                "Act1 (25%)",
                "Act2 (25%)",
                "Alt1 (10%)",
                "Alt2 (10%)",
                "Examen (30%)",
            ]
        )

        for columna in columnas_notas:
            df[columna] = df["NIE"].map(
                lambda nie, c=columna: detalles.get(str(nie).strip(), {}).get(c, 0.0)
            )

        if "Promedio" not in df.columns:
            if materia == "Conducta":
                df["Promedio"] = df["Nota Conducta"]
            else:
                df["Promedio"] = (
                    df["Act1 (25%)"] * 0.25
                    + df["Act2 (25%)"] * 0.25
                    + df["Alt1 (10%)"] * 0.10
                    + df["Alt2 (10%)"] * 0.10
                    + df["Examen (30%)"] * 0.30
                ).apply(redondear_mined)

        config_columnas = {
            "NIE": st.column_config.TextColumn(disabled=True),
            "Nombre": st.column_config.TextColumn(disabled=True, width="medium"),
            "Promedio": st.column_config.NumberColumn(disabled=True),
        }
        for columna in columnas_notas:
            config_columnas[columna] = st.column_config.NumberColumn(
                min_value=0.0, max_value=10.0, step=0.01
            )

        editor = st.data_editor(
            df,
            column_config=config_columnas,
            hide_index=True,
            width="stretch",
            key=f"doc_editor_{id_nuevo}",
        )

        if st.button("💾 Guardar Notas", type="primary", key="doc_guardar_notas"):
            detalles_guardar = {}
            for _, fila in editor.iterrows():
                promedio = (
                    fila["Nota Conducta"]
                    if materia == "Conducta"
                    else (
                        fila["Act1 (25%)"] * 0.25
                        + fila["Act2 (25%)"] * 0.25
                        + fila["Alt1 (10%)"] * 0.10
                        + fila["Alt2 (10%)"] * 0.10
                        + fila["Examen (30%)"] * 0.30
                    )
                )
                promedio_final = redondear_mined(promedio)
                nie = str(fila["NIE"]).strip()
                detalles_guardar[nie] = {
                    col: float(fila[col]) for col in columnas_notas
                }
                detalles_guardar[nie]["Promedio"] = promedio_final

                db.table("notas").upsert(
                    {
                        "id": f"{nie}_{id_nuevo}",
                        "nie": nie,
                        "ciclo_lectivo": CICLO_LECTIVO,
                        "grado": grado,
                        "materia": materia,
                        "mes": mes,
                        "promedio_final": promedio_final,
                    }
                ).execute()

            db.table("notas_mensuales").upsert(
                {
                    "id": id_nuevo,
                    "ciclo_lectivo": CICLO_LECTIVO,
                    "grado": grado,
                    "materia": materia,
                    "mes": mes,
                    "detalles": detalles_guardar,
                }
            ).execute()
            st.success("✅ Notas guardadas correctamente.")
            time.sleep(1)
            st.rerun()

        # SOLUCIÓN 2: PDF del Cuadro de Notas (Restaurado)
        st.markdown("---")
        st.markdown("### 🖨️ Respaldo del Cuadro de Notas")
        if st.button("📄 Generar PDF del Cuadro de este Mes", key="doc_pdf_cuadro_mes"):
            logo_b64 = get_base64("logo.png")
            imagen_logo = f'<img src="{logo_b64}" height="50">' if logo_b64 else ""
            fecha_impresion = time.strftime("%d/%m/%Y %H:%M")
            df_impresion = editor.copy()

            if materia == "Conducta":
                df_impresion["Promedio"] = df_impresion[columnas_notas[0]]
            else:
                df_impresion["Promedio"] = (
                    df_impresion["Act1 (25%)"] * 0.25
                    + df_impresion["Act2 (25%)"] * 0.25
                    + df_impresion["Alt1 (10%)"] * 0.10
                    + df_impresion["Alt2 (10%)"] * 0.10
                    + df_impresion["Examen (30%)"] * 0.30
                ).apply(redondear_mined)

            filas_html = ""
            for _, fila in df_impresion.iterrows():
                celdas_notas = "".join(
                    [f"<td>{fila[col]}</td>" for col in columnas_notas]
                )
                filas_html += f"<tr><td style='text-align:left; padding-left:5px;'>{fila['Nombre']}</td><td>{fila['NIE']}</td>{celdas_notas}<td style='background:#1e3a8a; color:white; font-weight:bold;'>{fila['Promedio']}</td></tr>"

            encabezados_notas = "".join([f"<th>{col}</th>" for col in columnas_notas])
            html_cuadro = f"""<div style="font-family: Arial, sans-serif; padding: 20px;"><div style="display:flex; align-items:center; border-bottom:2px solid #333; margin-bottom:15px;">{imagen_logo}<div style="margin-left:20px;"><h2 style="margin:0;">COLEGIO PROFA. BLANCA ELENA DE HERNÁNDEZ</h2><h4 style="margin:5px 0 0 0; color:#555;">CUADRO DE NOTAS MENSUAL - CICLO {CICLO_LECTIVO}</h4></div></div><table style="width:100%; font-size:12px; margin-bottom:15px;"><tr><td><b>GRADO:</b> {grado}</td><td><b>ASIGNATURA:</b> {materia}</td><td><b>MES:</b> {mes}</td></tr><tr><td><b>TOTAL ALUMNOS:</b> {len(df_impresion)}</td><td><b>FECHA DE IMPRESIÓN:</b> {fecha_impresion}</td><td></td></tr></table><table border="1" style="width:100%; border-collapse:collapse; text-align:center; font-size:11px;"><tr style="background:#f2f2f2; font-weight:bold;"><th style="text-align:left; padding-left:5px;">NOMBRE DEL ALUMNO</th><th>NIE</th>{encabezados_notas}<th style="background:#1e3a8a; color:white;">PROMEDIO</th></tr>{filas_html}</table><br><br><div style="display:flex; justify-content:space-between; margin-top:60px;"><div style="width:40%; border-top:1px solid black; text-align:center; font-size:11px;"><br>Firma del Docente</div><div style="width:40%; border-top:1px solid black; text-align:center; font-size:11px;"><br>Firma de Coordinación</div></div></div>"""

            components.html(
                f"""<html><head><style>@media print {{ button {{ display:none; }} body {{ margin: 0.5cm; }} }} body {{ font-family: Arial, sans-serif; }}</style></head><body>{html_cuadro}<br><center><button onclick="window.print()" style="padding:12px 24px; background:#2e7d32; color:white; border:none; border-radius:5px; font-size:15px; cursor:pointer;">🖨️ IMPRIMIR / GUARDAR COMO PDF</button></center></body></html>""",
                height=700,
                scrolling=True,
            )

    elif opcion_seleccionada == "Ver Mis Cargas":
        st.title("📋 Mi Carga Académica")
        res_cargas = (
            db.table("carga_academica")
            .select("*")
            .eq("nombre_docente", usuario_actual)
            .execute()
        )
        cargas = res_cargas.data if res_cargas.data else []
        found = False
        for d in cargas:
            ciclo_carga = d.get("ciclo_lectivo", CICLO_LECTIVO)
            if int(ciclo_carga) != CICLO_LECTIVO:
                continue
            found = True
            with st.container(border=True):
                st.subheader(d["grado"])
                st.write("**Materias:** " + ", ".join(d.get("materias", [])))
                st.caption(f"📅 Ciclo lectivo: {CICLO_LECTIVO}")
                if d.get("es_guia"):
                    st.success("🌟 MAESTRO GUÍA")
        if not found:
            st.info(
                f"No se encontraron cargas asignadas para el ciclo {CICLO_LECTIVO}."
            )

    elif opcion_seleccionada == "Expediente Alumnos":
        st.title("📂 Bitácora del Alumno")
        c1, c2 = st.columns(2)
        grado_sel = c1.selectbox("Seleccionar Grado", lista_grados)

        res_alumnos = (
            db.table("alumnos")
            .select("*")
            .eq("grado_actual", grado_sel)
            .eq("estado", "Activo")
            .execute()
        )
        alumnos_data = res_alumnos.data if res_alumnos.data else []
        dict_alumnos = {
            f"{a.get('apellidos', '')} {a.get('nombres', '')}": a for a in alumnos_data
        }

        if dict_alumnos:
            nombre_alum = c2.selectbox(
                "Seleccionar Alumno",
                ["Seleccionar..."] + sorted(list(dict_alumnos.keys())),
            )
            if nombre_alum != "Seleccionar...":
                alum_data = dict_alumnos[nombre_alum]
                nie_actual = alum_data["nie"]
                cp1, cp2 = st.columns([1, 4])
                with cp1:
                    foto_url_alum = alum_data.get("foto_url")
                    if foto_url_alum:
                        try:
                            st.image(foto_url_alum, width=130)
                        except:
                            st.markdown("👤", unsafe_allow_html=True)
                    else:
                        st.markdown("👤", unsafe_allow_html=True)
                with cp2:
                    st.subheader(
                        f"{alum_data.get('apellidos', '')} {alum_data.get('nombres', '')}"
                    )
                    st.write(
                        f"**NIE:** {alum_data['nie']} | **Responsable:** {alum_data.get('encargado_nombre', '-')}"
                    )
                    st.write(f"**Tel:** {alum_data.get('encargado_telefono', '-')}")
                st.divider()
                st.markdown("### 📝 Historial de Observaciones")
                with (
                    st.expander("➕ Agregar Nueva Nota / Observación", expanded=True),
                    st.form("form_bitacora"),
                ):
                    nota_texto = st.text_area("Escriba la observación:")
                    if st.form_submit_button("Guardar en Bitácora"):
                        if nota_texto:
                            # Generar un ID único basado en el momento exacto
                            import uuid

                            id_unico = str(uuid.uuid4())
                            nueva_entrada = {
                                "id": id_unico,
                                "nie": nie_actual,
                                "alumno": nombre_alum,
                                "grado": grado_sel,
                                "fecha": datetime.now(TZ_SV).isoformat(),
                                "fecha_legible": obtener_hora_actual(),
                                "autor": usuario_actual,
                                "contenido": nota_texto,
                            }
                            db.table("bitacora").insert(nueva_entrada).execute()
                            st.success("Nota agregada.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("La nota no puede estar vacía.")
                res_logs = (
                    db.table("bitacora").select("*").eq("nie", nie_actual).execute()
                )
                lista_logs = res_logs.data if res_logs.data else []
                lista_logs.sort(key=lambda x: x.get("fecha_legible", ""), reverse=True)
                if lista_logs:
                    for log in lista_logs:
                        with st.container(border=True):
                            c_meta, c_body = st.columns([1, 3])
                            with c_meta:
                                st.caption(f"📅 {log.get('fecha_legible')}")
                                st.caption(f"✍️ **{log.get('autor')}**")
                            with c_body:
                                st.write(log.get("contenido"))
                else:
                    st.info("No hay registros en la bitácora de este alumno.")
        else:
            c2.warning("No hay alumnos inscritos en este grado.")

    elif opcion_seleccionada == "Boletas de Notas":
        st.title("🖨️ Impresión de Boletas de Notas")
        c1, c2 = st.columns(2)
        grado_sel = c1.selectbox("Seleccionar Grado", lista_grados_notas)

        res_alumnos = (
            db.table("alumnos")
            .select("*")
            .eq("grado_actual", grado_sel)
            .eq("estado", "Activo")
            .execute()
        )
        alumnos_data = res_alumnos.data if res_alumnos.data else []
        dict_alumnos = {}
        for datos in alumnos_data:
            if int(datos.get("ciclo_lectivo", CICLO_LECTIVO)) != CICLO_LECTIVO:
                continue
            dict_alumnos[
                f"{datos.get('apellidos', '')} {datos.get('nombres', '')}".strip()
            ] = datos

        if not dict_alumnos:
            c2.warning("No hay alumnos activos.")
            return

        nombre_alum = c2.selectbox(
            "Seleccionar Alumno", ["Seleccionar..."] + sorted(dict_alumnos.keys())
        )
        if nombre_alum == "Seleccionar...":
            return

        alum_data = dict_alumnos[nombre_alum]
        malla_completa = mapa_curricular.get(grado_sel, [])
        st.markdown("---")
        st.subheader("Configuración de Boleta")
        materias_seleccionadas = st.multiselect(
            "Materias a incluir:", malla_completa, default=malla_completa
        )

        if not (st.button("Generar Boleta") and materias_seleccionadas):
            return

        q_guia = (
            db.table("carga_academica")
            .select("*")
            .eq("grado", grado_sel)
            .eq("es_guia", True)
            .execute()
        )
        maestro_guia = "No Asignado"
        if q_guia.data:
            for datos_guia in q_guia.data:
                if int(datos_guia.get("ciclo_lectivo", CICLO_LECTIVO)) == CICLO_LECTIVO:
                    maestro_guia = datos_guia.get("nombre_docente", "No Asignado")
                    break

        notas_docs = db.table("notas").select("*").eq("nie", alum_data["nie"]).execute()
        nm = {}
        if notas_docs.data:
            for dd in notas_docs.data:
                if int(dd.get("ciclo_lectivo", CICLO_LECTIVO)) != CICLO_LECTIVO:
                    continue
                if dd.get("grado") != grado_sel:
                    continue
                materia = dd.get("materia")
                mes = dd.get("mes")
                if not materia or not mes:
                    continue
                if materia not in nm:
                    nm[materia] = {}
                nm[materia][mes] = dd.get("promedio_final", 0)

        filas = []
        for mat in materias_seleccionadas:
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
                    f"""<tr><td style='text-align:left'>{mat}</td><td>{n.get("Febrero", "-")}</td><td>{n.get("Marzo", "-")}</td><td>{n.get("Abril", "-")}</td><td style='background:#eee'><b>{t1}</b></td><td>{n.get("Mayo", "-")}</td><td>{n.get("Junio", "-")}</td><td>{n.get("Julio", "-")}</td><td style='background:#eee'><b>{t2}</b></td><td>{n.get("Agosto", "-")}</td><td>{n.get("Septiembre", "-")}</td><td>{n.get("Octubre", "-")}</td><td style='background:#eee'><b>{t3}</b></td><td style='background:#d9edf7'><b>{fin}</b></td></tr>"""
                )

        # SOLUCIÓN 3: Restaurado el HTML de la Boleta
        logo = get_base64("logo.png")
        sello = get_base64("sello.png")
        hi = f'<img src="{logo}" height="60">' if logo else ""
        hs = f'<img src="{sello}" height="80">' if sello else ""
        html = f"""<div style="font-family:Arial; font-size:12px; padding:20px;"><div style="display:flex; align-items:center; border-bottom:2px solid black; margin-bottom:10px;">{hi}<div style="margin-left:20px"><h2>COLEGIO PROFA. BLANCA ELENA</h2><h4>INFORME DE NOTAS</h4></div></div><p><b>Alumno:</b> {alum_data.get("apellidos", "")} {alum_data.get("nombres", "")} | <b>Grado:</b> {grado_sel} | <b>Guía:</b> {maestro_guia}</p><table border="1" style="width:100%; border-collapse:collapse; text-align:center;"><tr style="background:#ddd; font-weight:bold;"><td>ASIGNATURA</td><td>F</td><td>M</td><td>A</td><td>T1</td><td>M</td><td>J</td><td>J</td><td>T2</td><td>A</td><td>S</td><td>O</td><td>T3</td><td>FIN</td></tr>{"".join(filas)}</table><br><br><br><div style="display:flex; justify-content:space-between; align-items:end; padding:0 50px;"><div style="text-align:center; width:30%;"><div style="border-top:1px solid black; width:100%;">Orientador</div></div><div style="text-align:center;">{hs}</div><div style="text-align:center; width:30%;"><div style="border-top:1px solid black; width:100%;">Dirección</div></div></div></div>"""

        components.html(
            f"""<html><body>{html}<br><button onclick="window.print()">🖨️ IMPRIMIR BOLETA</button><style>@media print {{ button {{ display:none; }} }}</style></body></html>""",
            height=600,
            scrolling=True,
        )
