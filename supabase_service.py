import os
import re
from datetime import datetime
from io import BytesIO

import streamlit as st
from PIL import Image
from supabase import Client, create_client

from config import SUPABASE_KEY, SUPABASE_URL


# ==========================================
# CONEXIÓN A SUPABASE
# ==========================================
@st.cache_resource
def conectar_supabase():
    """
    Inicializa la conexión a Supabase y devuelve el cliente.
    Se cachea para no crear una conexión nueva en cada recarga de Streamlit.
    """
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return supabase, None
    except Exception as error:
        return None, str(error)


# ==========================================
# FUNCIONES DE BASE DE DATOS (CRUD)
# ==========================================
def obtener_usuario(usuario):
    """
    Busca un usuario por su nombre de usuario.
    Retorna el diccionario del usuario o None.
    """
    try:
        supabase, _ = conectar_supabase()
        if not supabase:
            return None

        response = (
            supabase.table("usuarios").select("*").eq("usuario", usuario).execute()
        )
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as error:
        print(f"Error al obtener usuario: {error}")
        return None


def obtener_datos(tabla, campo_filtro=None, valor_filtro=None, limite=None):
    """
    Obtiene datos de una tabla con filtros opcionales.
    """
    try:
        supabase, _ = conectar_supabase()
        if not supabase:
            return []

        query = supabase.table(tabla).select("*")
        if campo_filtro and valor_filtro is not None:
            query = query.eq(campo_filtro, valor_filtro)
        if limite:
            query = query.limit(limite)

        response = query.execute()
        return response.data
    except Exception as error:
        print(f"Error al obtener datos de {tabla}: {error}")
        return []


def insertar_dato(tabla, datos):
    """
    Inserta un registro en una tabla.
    """
    try:
        supabase, _ = conectar_supabase()
        if not supabase:
            return None

        response = supabase.table(tabla).insert(datos).execute()
        return response.data
    except Exception as error:
        print(f"Error al insertar dato en {tabla}: {error}")
        return None


def actualizar_dato(tabla, campo_id, id_valor, datos):
    """
    Actualiza un registro en una tabla basado en un campo ID.
    """
    try:
        supabase, _ = conectar_supabase()
        if not supabase:
            return None

        response = supabase.table(tabla).update(datos).eq(campo_id, id_valor).execute()
        return response.data
    except Exception as error:
        print(f"Error al actualizar dato en {tabla}: {error}")
        return None


def eliminar_dato(tabla, campo_id, id_valor):
    """
    Elimina un registro de una tabla basado en un campo ID.
    """
    try:
        supabase, _ = conectar_supabase()
        if not supabase:
            return None

        response = supabase.table(tabla).delete().eq(campo_id, id_valor).execute()
        return response.data
    except Exception as error:
        print(f"Error al eliminar dato en {tabla}: {error}")
        return None


# ==========================================
# FUNCIONES DE ARCHIVOS (STORAGE)
# ==========================================
def limpiar_nombre_archivo(nombre):
    """Limpia el nombre del archivo eliminando caracteres especiales."""
    nombre_sin_ext = os.path.splitext(nombre)[0]
    extension = os.path.splitext(nombre)[1].lower()
    nombre_limpio = re.sub(r"[^a-zA-Z0-9_\-]", "_", nombre_sin_ext)
    nombre_limpio = re.sub(r"_+", "_", nombre_limpio)
    nombre_limpio = nombre_limpio.strip("_")
    if not nombre_limpio:
        nombre_limpio = "archivo"
    return f"{nombre_limpio}{extension}"


def comprimir_imagen(archivo, max_size_kb=200, max_dimension=800):
    """Comprime una imagen para que pese menos de max_size_kb KB."""
    try:
        img = Image.open(archivo)
        if img.mode == "RGBA":
            img = img.convert("RGB")
        if max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        buffer = BytesIO()
        calidad = 85
        img.save(buffer, format="JPEG", quality=calidad, optimize=True)
        tamano_kb = buffer.tell() / 1024
        while tamano_kb > max_size_kb and calidad > 10:
            buffer = BytesIO()
            calidad -= 10
            img.save(buffer, format="JPEG", quality=calidad, optimize=True)
            tamano_kb = buffer.tell() / 1024
        buffer.seek(0)
        return buffer, "image/jpeg"
    except Exception as e:
        print(f"Error al comprimir imagen: {e}")
        return None, None


def subir_archivo(archivo, ruta_carpeta, bucket_name="imagenes", comprimir=True):
    """
    Sube un archivo a Supabase Storage usando el SDK oficial.
    Retorna la URL pública del archivo subido.
    """
    if not archivo:
        return None
    try:
        supabase, _ = conectar_supabase()
        if not supabase:
            return None

        # 1. Comprimir si es imagen
        if comprimir and archivo.type.startswith("image/"):
            archivo_comprimido, tipo_mime = comprimir_imagen(archivo)
            if archivo_comprimido is None:
                return None
            contenido = archivo_comprimido.read()
            extension = ".jpg"
        else:
            contenido = archivo.read()
            tipo_mime = archivo.type
            extension = os.path.splitext(archivo.name)[1].lower()

        # 2. Generar nombre único
        nombre_base = limpiar_nombre_archivo(archivo.name)
        nombre_base_sin_ext = os.path.splitext(nombre_base)[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_final = f"{nombre_base_sin_ext}_{timestamp}{extension}"
        ruta_final = f"{ruta_carpeta}/{nombre_final}"

        # 3. Subir usando el SDK oficial de Supabase
        res = supabase.storage.from_(bucket_name).upload(
            path=ruta_final, file=contenido, file_options={"content-type": tipo_mime}
        )

        # 4. Obtener y retornar la URL pública
        url_publica = supabase.storage.from_(bucket_name).get_public_url(ruta_final)
        return url_publica

    except Exception as error:
        print(f"Error al subir archivo a Supabase: {error}")
        return None
