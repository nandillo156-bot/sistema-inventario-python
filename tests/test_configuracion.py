"""La configuración se prueba sin abrir conexiones ni usar credenciales reales."""

from unittest.mock import MagicMock

import pytest

import conexion


@pytest.mark.parametrize("puerto,esperado", [(None, 3306), ("3307", 3307)])
def test_conexion_usa_variables_de_entorno(monkeypatch, puerto, esperado):
    valores = {
        "DB_HOST": "servidor-pruebas",
        "DB_USER": "usuario-pruebas",
        "DB_PASSWORD": "clave-de-prueba",
        "DB_DATABASE": "inventario-pruebas",
    }
    for nombre, valor in valores.items():
        monkeypatch.setenv(nombre, valor)
    monkeypatch.delenv("DB_PORT", raising=False)
    if puerto:
        monkeypatch.setenv("DB_PORT", puerto)

    conectar_falso = MagicMock()
    monkeypatch.setattr(conexion.mysql.connector, "connect", conectar_falso)

    assert conexion.conectar() is conectar_falso.return_value
    conectar_falso.assert_called_once_with(
        host="servidor-pruebas",
        port=esperado,
        user="usuario-pruebas",
        password="clave-de-prueba",
        database="inventario-pruebas",
        connection_timeout=5,
    )


def test_flask_arranca_sin_clave_configurada(monkeypatch):
    import app

    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    aplicacion = app.create_app()
    assert aplicacion.secret_key
    assert not aplicacion.debug
    respuesta = aplicacion.test_client().get("/")
    assert respuesta.status_code == 200
    assert 'id="product-form"' in respuesta.get_data(as_text=True)


def test_flask_respeta_clave_configurada(monkeypatch):
    import app

    monkeypatch.setenv("FLASK_SECRET_KEY", "clave-solo-para-pruebas")
    aplicacion = app.create_app()
    assert aplicacion.secret_key == "clave-solo-para-pruebas"
