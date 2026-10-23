"""Cuentas probadas con MySQL simulado y hashes scrypt reales de datos ficticios."""

from pathlib import Path
import re
from unittest.mock import MagicMock

import mysql.connector
import pytest
from werkzeug.security import check_password_hash, generate_password_hash

import usuarios


CLAVE_PRUEBA = "solo-para-pruebas-2026"


@pytest.fixture(scope="module")
def hash_prueba():
    return generate_password_hash(CLAVE_PRUEBA, method="scrypt")


@pytest.fixture
def fila_usuario(hash_prueba):
    return {
        "id": 7,
        "nombre": "Fernando_01",
        "rol": "operador",
        "activo": 1,
        "password_hash": hash_prueba,
    }


@pytest.fixture
def base_simulada(monkeypatch):
    cursor = MagicMock()
    cursor.lastrowid = 7
    conexion = MagicMock()
    conexion.cursor.return_value = cursor
    conectar = MagicMock(return_value=conexion)
    monkeypatch.setattr(usuarios, "conectar", conectar)

    yield conexion, cursor

    conectar.assert_called_once_with()
    conexion.cursor.assert_called_once_with(dictionary=True)
    cursor.close.assert_called_once()
    conexion.close.assert_called_once()


@pytest.mark.parametrize("rol", usuarios.ROLES)
def test_crear_usuario_guarda_hash_scrypt_y_solo_devuelve_datos_publicos(
    base_simulada, rol, capsys
):
    conexion, cursor = base_simulada

    resultado = usuarios.crear_usuario("  Fernando_01  ", CLAVE_PRUEBA, rol)

    assert resultado == {"id": 7, "nombre": "Fernando_01", "rol": rol}
    sql, parametros = cursor.execute.call_args.args
    assert sql.startswith("INSERT INTO usuarios")
    assert sql.count("%s") == 3
    assert parametros[0] == "Fernando_01"
    assert parametros[2] == rol
    assert parametros[1].startswith("scrypt:")
    assert check_password_hash(parametros[1], CLAVE_PRUEBA)
    conexion.commit.assert_called_once()
    conexion.rollback.assert_not_called()
    salida = capsys.readouterr()
    assert salida.out == salida.err == ""


@pytest.mark.parametrize("longitud", [12, 128])
def test_crear_usuario_acepta_limites_de_longitud_de_clave(base_simulada, longitud):
    _, cursor = base_simulada
    clave = " " + "x" * (longitud - 2) + " "

    usuarios.crear_usuario("usuario.demo-1", clave, "consulta")

    hash_guardado = cursor.execute.call_args.args[1][1]
    assert check_password_hash(hash_guardado, clave)
    assert not check_password_hash(hash_guardado, clave.strip())


@pytest.mark.parametrize(
    "nombre",
    [None, True, 123, [], {}, "", "  ", "ab", "a" * 81, "José", "a b", "a/b", "a'bc"],
)
def test_crear_usuario_rechaza_nombre_invalido_sin_abrir_base(monkeypatch, nombre):
    conectar = MagicMock()
    monkeypatch.setattr(usuarios, "conectar", conectar)

    with pytest.raises(ValueError, match="usuario"):
        usuarios.crear_usuario(nombre, CLAVE_PRUEBA, "consulta")

    conectar.assert_not_called()


@pytest.mark.parametrize("nombre", ["a_b", "A" * 80, "abc.DEF-123_"])
def test_crear_usuario_acepta_nombres_ascii_y_limites(base_simulada, nombre):
    resultado = usuarios.crear_usuario(nombre, CLAVE_PRUEBA, "consulta")

    assert resultado["nombre"] == nombre


@pytest.mark.parametrize("clave", [None, True, 123, [], {}, "", "a" * 11, "a" * 129])
def test_crear_usuario_rechaza_clave_invalida_sin_abrir_base(monkeypatch, clave):
    conectar = MagicMock()
    monkeypatch.setattr(usuarios, "conectar", conectar)

    with pytest.raises(ValueError, match="contraseña"):
        usuarios.crear_usuario("usuario", clave, "consulta")

    conectar.assert_not_called()


@pytest.mark.parametrize("rol", [None, True, [], {}, "", "admin", "Administrador"])
def test_crear_usuario_rechaza_rol_invalido_sin_abrir_base(monkeypatch, rol):
    conectar = MagicMock()
    monkeypatch.setattr(usuarios, "conectar", conectar)

    with pytest.raises(ValueError, match="rol"):
        usuarios.crear_usuario("usuario", CLAVE_PRUEBA, rol)

    conectar.assert_not_called()


def test_nombre_duplicado_revierte_y_no_expone_error_mysql(base_simulada):
    conexion, cursor = base_simulada
    cursor.execute.side_effect = mysql.connector.IntegrityError(
        "detalle privado de la base", errno=1062
    )

    with pytest.raises(usuarios.UsuarioDuplicado) as captura:
        usuarios.crear_usuario("usuario", CLAVE_PRUEBA, "consulta")

    assert str(captura.value) == "Ya existe un usuario con ese nombre."
    conexion.rollback.assert_called_once()
    conexion.commit.assert_not_called()


def test_otro_error_de_integridad_se_propaga(base_simulada):
    conexion, cursor = base_simulada
    error = mysql.connector.IntegrityError("Error de integridad", errno=9999)
    cursor.execute.side_effect = error

    with pytest.raises(mysql.connector.IntegrityError) as captura:
        usuarios.crear_usuario("usuario", CLAVE_PRUEBA, "consulta")

    assert captura.value is error
    conexion.rollback.assert_called_once()
    conexion.commit.assert_not_called()


def test_autenticar_devuelve_identidad_publica_y_recorta_nombre(
    base_simulada, fila_usuario
):
    conexion, cursor = base_simulada
    cursor.fetchone.return_value = fila_usuario

    resultado = usuarios.autenticar("  fernando_01  ", CLAVE_PRUEBA)

    assert resultado == {"id": 7, "nombre": "Fernando_01", "rol": "operador"}
    assert set(resultado) == {"id", "nombre", "rol"}
    assert cursor.execute.call_args.args[1] == ("fernando_01",)
    conexion.commit.assert_not_called()
    conexion.rollback.assert_not_called()


def test_autenticar_rechaza_clave_incorrecta(base_simulada, fila_usuario):
    _, cursor = base_simulada
    cursor.fetchone.return_value = fila_usuario

    assert usuarios.autenticar("Fernando_01", "otra-clave-para-pruebas") is None


@pytest.mark.parametrize("estado", ["ausente", "inactivo", "rol_invalido"])
def test_autenticar_cuenta_no_permitida_compara_hash_ficticio(
    base_simulada, fila_usuario, monkeypatch, estado
):
    _, cursor = base_simulada
    if estado == "ausente":
        cursor.fetchone.return_value = None
    else:
        fila_usuario["activo" if estado == "inactivo" else "rol"] = (
            0 if estado == "inactivo" else "superusuario"
        )
        cursor.fetchone.return_value = fila_usuario
    comparar = MagicMock(wraps=check_password_hash)
    monkeypatch.setattr(usuarios, "check_password_hash", comparar)

    assert usuarios.autenticar("Fernando_01", CLAVE_PRUEBA) is None

    comparar.assert_called_once_with(usuarios._HASH_FICTICIO, CLAVE_PRUEBA)


@pytest.mark.parametrize(
    "nombre,clave",
    [
        (None, CLAVE_PRUEBA),
        ([], CLAVE_PRUEBA),
        ({}, CLAVE_PRUEBA),
        (True, CLAVE_PRUEBA),
        ("a'bc", CLAVE_PRUEBA),
        ("usuario", None),
        ("usuario", []),
        ("usuario", {}),
        ("usuario", True),
        ("usuario", "corta"),
        ("usuario", "a" * 129),
    ],
)
def test_autenticar_entrada_invalida_no_filtra_excepciones(
    monkeypatch, nombre, clave
):
    conectar = MagicMock()
    comparar = MagicMock(wraps=check_password_hash)
    monkeypatch.setattr(usuarios, "conectar", conectar)
    monkeypatch.setattr(usuarios, "check_password_hash", comparar)

    assert usuarios.autenticar(nombre, clave) is None

    conectar.assert_not_called()
    comparar.assert_called_once_with(usuarios._HASH_FICTICIO, "")


@pytest.mark.parametrize("hash_guardado", [None, 123, "invalido", "scrypt:invalido$salt$valor"])
def test_autenticar_hash_invalido_no_permite_acceso(
    base_simulada, fila_usuario, hash_guardado
):
    _, cursor = base_simulada
    fila_usuario["password_hash"] = hash_guardado
    cursor.fetchone.return_value = fila_usuario

    assert usuarios.autenticar("Fernando_01", CLAVE_PRUEBA) is None


def test_obtener_usuario_lee_solo_datos_publicos_y_revalida_cada_vez(
    monkeypatch, fila_usuario
):
    cursor = MagicMock()
    conexion = MagicMock()
    conexion.cursor.return_value = cursor
    monkeypatch.setattr(usuarios, "conectar", lambda: conexion)
    cursor.fetchone.side_effect = [fila_usuario, {**fila_usuario, "activo": 0}]

    assert usuarios.obtener_usuario(7) == {
        "id": 7, "nombre": "Fernando_01", "rol": "operador"
    }
    assert usuarios.obtener_usuario(7) is None

    assert cursor.execute.call_count == 2
    assert "password_hash" not in cursor.execute.call_args.args[0]
    assert cursor.execute.call_args.args[1] == (7,)
    assert cursor.close.call_count == conexion.close.call_count == 2
    conexion.commit.assert_not_called()


@pytest.mark.parametrize("estado", ["ausente", "inactivo", "rol_invalido"])
def test_obtener_usuario_rechaza_cuentas_no_permitidas(
    base_simulada, fila_usuario, estado
):
    _, cursor = base_simulada
    if estado == "ausente":
        cursor.fetchone.return_value = None
    else:
        fila_usuario["activo" if estado == "inactivo" else "rol"] = (
            0 if estado == "inactivo" else "superusuario"
        )
        cursor.fetchone.return_value = fila_usuario

    assert usuarios.obtener_usuario(7) is None


@pytest.mark.parametrize("usuario_id", [None, True, False, "7", 7.0, [], {}, 0, -1, 2147483648])
def test_obtener_usuario_id_invalido_no_consulta_base(monkeypatch, usuario_id):
    conectar = MagicMock()
    monkeypatch.setattr(usuarios, "conectar", conectar)

    assert usuarios.obtener_usuario(usuario_id) is None

    conectar.assert_not_called()


@pytest.mark.parametrize("operacion", ["autenticar", "obtener_usuario", "crear_usuario"])
def test_fallo_sql_revierte_y_cierra_recursos(base_simulada, operacion):
    conexion, cursor = base_simulada
    error = mysql.connector.Error("Fallo SQL simulado")
    cursor.execute.side_effect = error
    argumentos = {
        "autenticar": ("usuario", CLAVE_PRUEBA),
        "obtener_usuario": (7,),
        "crear_usuario": ("usuario", CLAVE_PRUEBA, "consulta"),
    }

    with pytest.raises(mysql.connector.Error) as captura:
        getattr(usuarios, operacion)(*argumentos[operacion])

    assert captura.value is error
    conexion.rollback.assert_called_once()
    conexion.commit.assert_not_called()


def test_fallo_commit_revierte_y_cierra_recursos(base_simulada):
    conexion, _ = base_simulada
    error = mysql.connector.Error("No se pudo confirmar")
    conexion.commit.side_effect = error

    with pytest.raises(mysql.connector.Error) as captura:
        usuarios.crear_usuario("usuario", CLAVE_PRUEBA, "consulta")

    assert captura.value is error
    conexion.rollback.assert_called_once()


def test_fallo_al_crear_cursor_cierra_conexion(monkeypatch):
    conexion = MagicMock()
    error = mysql.connector.Error("No se pudo crear el cursor")
    conexion.cursor.side_effect = error
    monkeypatch.setattr(usuarios, "conectar", lambda: conexion)

    with pytest.raises(mysql.connector.Error) as captura:
        usuarios.obtener_usuario(7)

    assert captura.value is error
    conexion.rollback.assert_called_once()
    conexion.close.assert_called_once()


def test_fallo_al_cerrar_cursor_tambien_cierra_conexion(monkeypatch):
    conexion = MagicMock()
    cursor = conexion.cursor.return_value
    cursor.fetchone.return_value = None
    error = mysql.connector.Error("No se pudo cerrar el cursor")
    cursor.close.side_effect = error
    monkeypatch.setattr(usuarios, "conectar", lambda: conexion)

    with pytest.raises(mysql.connector.Error) as captura:
        usuarios.obtener_usuario(7)

    assert captura.value is error
    conexion.close.assert_called_once()


def test_migracion_crea_misma_tabla_sin_seleccionar_ni_modificar_otra_base():
    raiz = Path(__file__).resolve().parents[1]
    esquema = (raiz / "database" / "inventario.sql").read_text(encoding="utf-8")
    migracion = (raiz / "database" / "migrations" / "001_usuarios.sql").read_text(
        encoding="utf-8"
    )
    patron = r"CREATE TABLE IF NOT EXISTS usuarios \([\s\S]*?COLLATE utf8mb4_0900_as_ci;"
    tabla_inicial = re.search(patron, esquema)
    tabla_migrada = re.search(patron, migracion)

    assert tabla_inicial is not None
    assert tabla_migrada is not None
    assert tabla_inicial.group() == tabla_migrada.group()
    sentencias = "\n".join(
        linea for linea in migracion.splitlines() if not linea.lstrip().startswith("--")
    )
    assert re.search(r"\b(CREATE DATABASE|USE|DROP|TRUNCATE|INSERT|ALTER)\b", sentencias, re.I) is None
