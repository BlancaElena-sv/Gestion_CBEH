import bcrypt


def generar_hash(password):
    """
    Convierte una contraseña normal en un hash seguro.
    """

    password_bytes = password.encode("utf-8")

    hash_generado = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt()
    )

    return hash_generado.decode("utf-8")


def verificar_password(password, password_hash):
    """
    Comprueba si una contraseña corresponde
    al hash almacenado.
    """

    try:
        password_bytes = password.encode("utf-8")
        hash_bytes = password_hash.encode("utf-8")

        return bcrypt.checkpw(
            password_bytes,
            hash_bytes
        )

    except (ValueError, TypeError):
        return False