"""
Script para diagnosticar y limpiar notas duplicadas o con nombres de mes inconsistentes.
Ejecutar con: streamlit run diagnosticar_notas.py
"""

import os
import sys

import streamlit as st

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
try:
    from firebase_service import db  # type: ignore[reportMissingImports]
except ModuleNotFoundError as exc:
    raise RuntimeError(
        "No se pudo cargar firebase_service desde la raíz del proyecto."
    ) from exc

st.set_page_config(page_title="Diagnóstico de Notas", layout="wide")
st.title("🔍 Diagnóstico de Notas - Octavo Grado / Matemáticas / Agosto")

if st.button("Ejecutar Diagnóstico"):
    # Buscar todas las notas de Octavo Grado, Matemáticas y Datos
    notas_ref = (
        db.collection("notas")
        .where("grado", "==", "Octavo Grado")
        .where("materia", "==", "Matemáticas y Datos")
        .stream()
    )

    st.subheader("📋 Documentos encontrados en Firestore:")
    
    documentos_encontrados = []
    for doc in notas_ref:
        data = doc.to_dict()
        documentos_encontrados.append({
            "ID": doc.id,
            "NIE": data.get("nie"),
            "Mes": data.get("mes"),
            "Mes (repr)": repr(data.get("mes")),  # Muestra comillas y tipo exacto
            "Promedio": data.get("promedio_final"),
            "Ciclo": data.get("ciclo_lectivo")
        })

    if documentos_encontrados:
        import pandas as pd
        df = pd.DataFrame(documentos_encontrados)
        st.dataframe(df, width="stretch")
        
        # Agrupar por NIE y Mes para detectar duplicados
        st.subheader("🔎 Duplicados detectados:")
        duplicados = df.groupby(["NIE", "Mes"]).size().reset_index(name='Cantidad')
        duplicados = duplicados[duplicados['Cantidad'] > 1]
        
        if len(duplicados) > 0:
            st.error(f"⚠️ Se encontraron {len(duplicados)} casos de notas duplicadas:")
            st.dataframe(duplicados, width="stretch")
        else:
            st.success("✅ No se encontraron duplicados exactos")
        
        # Mostrar todos los valores únicos de "mes" para detectar inconsistencias
        st.subheader("📝 Valores únicos del campo 'mes':")
        meses_unicos = df["Mes"].unique()
        st.write(meses_unicos)
        
        st.subheader(" Representación exacta de los meses (para detectar mayúsculas/minúsculas):")
        meses_repr = df["Mes (repr)"].unique()
        st.write(meses_repr)
        
    else:
        st.warning("No se encontraron documentos con esos criterios")