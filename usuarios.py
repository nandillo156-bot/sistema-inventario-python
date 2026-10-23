"""Usuarios y contraseñas del inventario, sin dependencias del protocolo HTTP."""

from contextlib import contextmanager
import re
import secrets

from mysql.connector import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from conexion import conectar


ROLES = ("consulta", "operador", "administrador")
_PATRON_NOMBRE = re.compile(r"[A-Za-z0-9_.-]{3,80}", re.ASCII)
# Se calcula una vez con el mismo algoritmo que las cuentas reales. Compararlo
# también para cuentas ausentes o inactivas evita omitir el trabajo del hash.
_HASH_FICTICIO = generate_password_hash(secrets.token_urlsafe(32), method="scrypt")


class UsuarioDuplicado(ValueError):
    """Ya existe una cuenta con el nombre solicitado."""


@contextmanager
def _sesion():
    conexion = conectar()
    cursor = None
    try:
        cursor = conexion.cursor(dictionary=True)
        yield conexion, cursor
    except Exception:
        conexion.rollback()
        raise
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            conexion.close()


def _validar_nombre(nombre):
    if not isinstance(nombre, str):
        raise ValueError("El usuario debe ser texto.")
    nombre = nombre.strip()
    if _PATRON_NOMBRE.fullmatch(nombre) is None:
        raise ValueError(
            "El usuario debe tener entre 3 y 80 caracteres: letras ASCII, "
            "números, guion, guion bajo o punto."
        )
    return nombre


def _validar_clave(clave):
    if not isinstance(clave, str) or not 12 <= len(clave) <= 128:
        raise ValueError("La contraseña debe tener entre 12 y 128 caracteres.")


def _usuario_publico(fila):
    """Devuelve únicamente datos permitidos, revalidando el estado de la cuenta."""
    if not isinstance(fila, dict) or fila.get("activo") not in (True, 1):
        return None
    if fila.get("rol") not in ROLES:
        return None
    usuario_id = fila.get("id")
    if isinstance(usuario_id, bool) or not isinstance(usuario_id, int):
        return None
    if not 1 <= usuario_id <= 2147483647:
        return None
    try:
        nombre = _validar_nombre(fila.get("nombre"))
    except ValueError:
        return None
    return {"id": usuario_id, "nombre": nombre, "rol": fila["rol"]}


def autenticar(nombre, clave):
    """Comprueba credenciales; los rechazos devuelven siempre el mismo None."""
    try:
        nombre = _validar_nombre(nombre)
        _validar_clave(clave)
    except ValueError:
        check_password_hash(_HASH_FICTICIO, "")
        return None

    with _sesion() as (_, cursor):
        cursor.execute(
            "SELECT id,nombre,rol,activo,password_hash FROM usuarios "
            "WHERE nombre=%s LIMIT 1",
            (nombre,),
        )
        fila = cursor.fetchone()

    usuario = _usuario_publico(fila)
    hash_guardado = fila.get("password_hash") if usuario is not None else None
    hash_valido = isinstance(hash_guardado, str) and hash_guardado.startswith("scrypt:")
    hash_comprobado = hash_guardado if hash_valido else _HASH_FICTICIO
    try:
        coincide = check_password_hash(hash_comprobado, clave)
    except (TypeError, ValueError):
        # Una cuenta con un hash mal formado tampoco permite iniciar sesión.
        check_password_hash(_HASH_FICTICIO, clave)
        return None
    return usuario if usuario is not None and hash_valido and coincide else None


def obtener_usuario(usuario_id):
    """Lee de nuevo el rol y el estado; no confía en los datos de una sesión."""
    if isinstance(usuario_id, bool) or not isinstance(usuario_id, int):
        return None
    if not 1 <= usuario_id <= 2147483647:
        return None
    with _sesion() as (_, cursor):
        cursor.execute(
            "SELECT id,nombre,rol,activo FROM usuarios WHERE id=%s LIMIT 1",
            (usuario_id,),
        )
        return _usuario_publico(cursor.fetchone())


def crear_usuario(nombre, clave, rol):
    """Crea una cuenta con hash scrypt y devuelve solo su identidad pública."""
    nombre = _validar_nombre(nombre)
    _validar_clave(clave)
    if not isinstance(rol, str) or rol not in ROLES:
        raise ValueError("El rol debe ser consulta, operador o administrador.")
    password_hash = generate_password_hash(clave, method="scrypt")
    try:
        with _sesion() as (conexion, cursor):
            cursor.execute(
                "INSERT INTO usuarios (nombre,password_hash,rol) VALUES (%s,%s,%s)",
                (nombre, password_hash, rol),
            )
            usuario_id = cursor.lastrowid
            conexion.commit()
    except IntegrityError as error:
        if error.errno == 1062:
            raise UsuarioDuplicado("Ya existe un usuario con ese nombre.") from error
        raise
    return {"id": usuario_id, "nombre": nombre, "rol": rol}
