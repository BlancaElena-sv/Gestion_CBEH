"""Presentación del respaldo mensual de main, sin acceso a datos ni escrituras."""
from datetime import datetime
from html import escape

import streamlit as st
import streamlit.components.v1 as components

from config import CICLO_LECTIVO, COLEGIO_NOMBRE, LOGO_INSTITUCIONAL, TZ_SV


def mostrar_respaldo_mensual(editor, columnas_notas, grado, materia, mes,
                              redondear_mined, get_base64, solo_promedios=False, button_key=None):
    st.markdown("---")
    st.markdown("### 🖨️ Respaldo del Cuadro de Notas")
    if st.button("📄 Generar PDF del Cuadro de este Mes", key=button_key):
        logo_b64 = get_base64(LOGO_INSTITUCIONAL)
        imagen_logo = (
            f'<img src="{logo_b64}" height="50">' if logo_b64 else ""
        )
        fecha_impresion = datetime.now(TZ_SV).strftime("%d/%m/%Y %H:%M")
        df_impresion = editor.copy()
        # Solo texto en campos identificativos; nunca HTML procedente de registros.
        for columna in ("Nombre", "NIE"):
            df_impresion[columna] = df_impresion[columna].map(lambda valor: escape(str(valor)))

        if solo_promedios:
            for columna in columnas_notas:
                df_impresion[columna] = "–"
        elif materia == "Conducta":
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
                [f"<td>{escape(str(fila[col]))}</td>" for col in columnas_notas]
            )
            filas_html += f"<tr><td style='text-align:left; padding-left:5px;'>{fila['Nombre']}</td><td>{fila['NIE']}</td>{celdas_notas}<td style='background:#1e3a8a; color:white; font-weight:bold;'>{escape(str(fila['Promedio']))}</td></tr>"

        encabezados_notas = "".join(
            [f"<th>{col}</th>" for col in columnas_notas]
        )
        html_cuadro = f"""<div style="font-family: Arial, sans-serif; padding: 20px;"><div style="display:flex; align-items:center; border-bottom:2px solid #333; margin-bottom:15px;">{imagen_logo}<div style="margin-left:20px;"><h2 style="margin:0;">{escape(COLEGIO_NOMBRE.upper())}</h2><h4 style="margin:5px 0 0 0; color:#555;">CUADRO DE NOTAS MENSUAL - CICLO {CICLO_LECTIVO}</h4></div></div><table style="width:100%; font-size:12px; margin-bottom:15px;"><tr><td><b>GRADO:</b> {escape(str(grado))}</td><td><b>ASIGNATURA:</b> {escape(str(materia))}</td><td><b>MES:</b> {escape(str(mes))}</td></tr><tr><td><b>TOTAL ALUMNOS:</b> {len(df_impresion)}</td><td><b>FECHA DE IMPRESIÓN:</b> {fecha_impresion}</td><td></td></tr></table><table border="1" style="width:100%; border-collapse:collapse; text-align:center; font-size:11px;"><tr style="background:#f2f2f2; font-weight:bold;"><th style="text-align:left; padding-left:5px;">NOMBRE DEL ALUMNO</th><th>NIE</th>{encabezados_notas}<th style="background:#1e3a8a; color:white;">PROMEDIO</th></tr>{filas_html}</table><br><br><div style="display:flex; justify-content:space-between; margin-top:60px;"><div style="width:40%; border-top:1px solid black; text-align:center; font-size:11px;"><br>Firma del Docente</div><div style="width:40%; border-top:1px solid black; text-align:center; font-size:11px;"><br>Firma de Coordinación</div></div></div>"""

        if solo_promedios:
            html_cuadro += "<p>Solo promedio final guardado; actividades detalladas no disponibles.</p>"

        components.html(
            f"""<html><head><style>@media print {{ button {{ display:none; }} body {{ margin: 0.5cm; }} }} body {{ font-family: Arial, sans-serif; }}</style></head><body>{html_cuadro}<br><center><button onclick="window.print()" style="padding:12px 24px; background:#2e7d32; color:white; border:none; border-radius:5px; font-size:15px; cursor:pointer;">🖨️ IMPRIMIR / GUARDAR COMO PDF</button></center></body></html>""",
            height=700,
            scrolling=True,
        )
