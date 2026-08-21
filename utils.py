import base64


def get_base64(path):
    """
    Convierte un archivo de imagen a Base64 para poder
    incrustarlo directamente dentro de HTML.
    """
    try:
        with open(path, "rb") as archivo:
            contenido = base64.b64encode(archivo.read()).decode()
            return f"data:image/png;base64,{contenido}"
    except Exception:
        return ""


def redondear_mined(valor):
    """
    Redondea una nota utilizando la regla aplicada
    actualmente por EduManager.
    """
    if valor is None:
        return 0.0

    parte_entera = int(valor)
    parte_decimal = valor - parte_entera

    if parte_decimal >= 0.5:
        return float(parte_entera + 1)

    return float(parte_entera)