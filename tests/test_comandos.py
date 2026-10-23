"""Preparar usuarios es una acción explícita; nunca sucede al arrancar Flask."""

from unittest.mock import MagicMock

import mysql.connector

import app as modulo_app


def aplicacion(modo="private"):
    return modulo_app.create_app({"TESTING": True, "APP_MODE": modo, "APP_ENV": "development"})


def test_inicializar_acceso_crea_solo_tabla_usuarios(monkeypatch):
    conexion = MagicMock()
    cursor = conexion.cursor.return_value
    monkeypatch.setattr(modulo_app, "conectar", lambda: conexion)

    resultado = aplicacion().test_cli_runner().invoke(args=["inicializar-acceso"])

    assert resultado.exit_code == 0
    sql = cursor.execute.call_args.args[0]
    assert "CREATE TABLE IF NOT EXISTS usuarios" in sql
    assert "DROP TABLE" not in sql
    assert "INSERT INTO" not in sql
    conexion.commit.assert_called_once()
    cursor.close.assert_called_once()
    conexion.close.assert_called_once()


def test_crear_usuario_pide_clave_oculta_y_no_la_imprime(monkeypatch):
    crear = MagicMock(return_value={"id": 1, "nombre": "fernando", "rol": "administrador"})
    monkeypatch.setattr(modulo_app.usuarios, "crear_usuario", crear)
    clave = "clave-de-prueba-larga"

    resultado = aplicacion().test_cli_runner().invoke(
        args=["crear-usuario", "--nombre", "fernando", "--rol", "administrador"],
        input=f"{clave}\n{clave}\n",
    )

    assert resultado.exit_code == 0
    crear.assert_called_once_with("fernando", clave, "administrador")
    assert "Cuenta fernando creada" in resultado.output
    assert clave not in resultado.output


def test_demo_no_ejecuta_comandos_de_base_de_datos(monkeypatch):
    conectar = MagicMock()
    crear = MagicMock()
    monkeypatch.setattr(modulo_app, "conectar", conectar)
    monkeypatch.setattr(modulo_app.usuarios, "crear_usuario", crear)
    runner = aplicacion("demo").test_cli_runner()

    resultado = runner.invoke(args=["inicializar-acceso"])
    assert resultado.exit_code != 0
    resultado = runner.invoke(args=["crear-usuario", "--nombre", "fernando", "--rol", "consulta"])
    assert resultado.exit_code != 0
    conectar.assert_not_called()
    crear.assert_not_called()


def test_error_inicializando_acceso_cierra_conexion_sin_filtrar_detalles(monkeypatch):
    conexion = MagicMock()
    conexion.cursor.side_effect = mysql.connector.Error("detalle-interno-privado")
    monkeypatch.setattr(modulo_app, "conectar", lambda: conexion)

    resultado = aplicacion().test_cli_runner().invoke(args=["inicializar-acceso"])

    assert resultado.exit_code != 0
    assert "detalle-interno-privado" not in resultado.output
    conexion.close.assert_called_once()
