"""Prueba Flask, servicio y modelo juntos; solo sustituye la conexión MySQL."""

from unittest.mock import MagicMock
from urllib.parse import urlsplit

import mysql.connector
import pytest

import app as modulo_app
import servicio_inventario as servicio


@pytest.fixture
def base_simulada(monkeypatch):
    cursor = MagicMock()
    conexion = MagicMock()
    conexion.cursor.return_value = cursor
    conectar = MagicMock(return_value=conexion)
    monkeypatch.setattr(servicio, "conectar", conectar)

    yield conexion, cursor

    conectar.assert_called_once_with()
    conexion.cursor.assert_called_once_with(dictionary=True)
    cursor.close.assert_called_once()
    conexion.close.assert_called_once()


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr(
        modulo_app.usuarios,
        "obtener_usuario",
        MagicMock(return_value={"id": 7, "nombre": "admin", "rol": "administrador"}),
    )
    aplicacion = modulo_app.create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "clave-pruebas",
            "APP_MODE": "private",
            "APP_ENV": "development",
        }
    )
    cliente = aplicacion.test_client()
    with cliente.session_transaction() as sesion:
        sesion["usuario_id"] = 7
        sesion["csrf_token"] = "csrf-pruebas"
    cliente.environ_base["HTTP_X_CSRF_TOKEN"] = "csrf-pruebas"
    return cliente


def test_alta_normaliza_datos_y_devuelve_ubicacion_del_producto(cliente, base_simulada):
    conexion, cursor = base_simulada
    cursor.fetchone.return_value = None
    cursor.lastrowid = 73

    respuesta = cliente.post(
        "/api/productos",
        json={
            "nombre": "  Teclado  ",
            "descripcion": "  Teclado mecánico  ",
            "precio": "850.50",
            "stock": "10",
            "categoria": "  Periféricos  ",
        },
    )

    assert respuesta.status_code == 201
    assert respuesta.json == {"id": 73}
    assert urlsplit(respuesta.headers["Location"]).path == "/api/productos/73"
    sql, parametros = cursor.execute.call_args.args
    assert sql.upper().startswith("INSERT INTO PRODUCTOS")
    assert parametros == ("Teclado", "Teclado mecánico", 850.50, 10, "Periféricos")
    conexion.commit.assert_called_once()
    conexion.rollback.assert_not_called()


def test_salida_confirma_stock_e_historial_en_la_misma_solicitud(cliente, base_simulada):
    conexion, cursor = base_simulada
    cursor.fetchone.return_value = {"stock": 10}

    respuesta = cliente.post(
        "/api/productos/7/movimientos", json={"tipo": "Salida", "cantidad": 4}
    )

    assert respuesta.status_code == 201
    assert respuesta.json == {"stock": 6}
    consultas = [llamada.args for llamada in cursor.execute.call_args_list]
    assert "FOR UPDATE" in consultas[0][0].upper()
    assert consultas[0][1] == (7,)
    assert consultas[1][0].upper().startswith("UPDATE PRODUCTOS")
    assert consultas[1][1] == (6, 7)
    assert consultas[2][0].upper().startswith("INSERT INTO MOVIMIENTOS")
    assert consultas[2][1] == (7, "Salida", 4, 10, 6)
    conexion.commit.assert_called_once()
    conexion.rollback.assert_not_called()


def test_fallo_del_historial_revierte_la_salida_y_oculta_detalles_mysql(
    cliente, base_simulada
):
    conexion, cursor = base_simulada
    cursor.fetchone.return_value = {"stock": 10}
    detalle_privado = "detalle-interno-mysql-que-no-debe-llegar-al-navegador"

    def ejecutar(sql, parametros):
        if sql.upper().startswith("INSERT INTO MOVIMIENTOS"):
            raise mysql.connector.Error(detalle_privado)

    cursor.execute.side_effect = ejecutar

    respuesta = cliente.post(
        "/api/productos/7/movimientos", json={"tipo": "Salida", "cantidad": 4}
    )

    assert respuesta.status_code == 503
    assert respuesta.json == {
        "error": "No se pudo completar la operación en la base de datos. Comprueba MySQL."
    }
    assert detalle_privado not in respuesta.get_data(as_text=True)
    assert cursor.execute.call_args_list[-2].args[1] == (6, 7)
    assert cursor.execute.call_args_list[-1].args[1] == (7, "Salida", 4, 10, 6)
    conexion.rollback.assert_called_once()
    conexion.commit.assert_not_called()
