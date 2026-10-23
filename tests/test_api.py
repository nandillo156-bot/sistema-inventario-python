import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.parse import urlsplit

from flask import Flask
import mysql.connector
import pytest

import app as modulo_app


PRODUCTO = {
    "id": 7,
    "nombre": "Teclado",
    "descripcion": "Teclado mecánico",
    "precio": 850.50,
    "stock": 10,
    "categoria": "Periféricos",
}
DATOS_PRODUCTO = {campo: valor for campo, valor in PRODUCTO.items() if campo != "id"}
MOVIMIENTO = {
    "id": 3,
    "producto_id": 7,
    "nombre": "Teclado",
    "tipo": "Entrada",
    "cantidad": 4,
    "stock_anterior": 10,
    "stock_actual": 14,
    "fecha": "2026-10-16 12:00:00",
}


@pytest.fixture
def servicios(monkeypatch):
    resultados = {
        "listar_productos": [PRODUCTO],
        "obtener_producto": PRODUCTO,
        "registrar_producto": {"id": 7},
        "actualizar_producto": {"id": 7},
        "eliminar_producto": {"ok": True},
        "listar_movimientos": [MOVIMIENTO],
        "registrar_movimiento": {"stock": 14},
    }
    simulados = {}
    for nombre, resultado in resultados.items():
        simulado = MagicMock(return_value=resultado)
        monkeypatch.setattr(modulo_app.inventario, nombre, simulado)
        simulados[nombre] = simulado
    return SimpleNamespace(**simulados)


@pytest.fixture
def cliente(servicios, monkeypatch):
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


def comprobar_error(respuesta, estado):
    assert respuesta.status_code == estado
    assert respuesta.is_json
    assert isinstance(respuesta.json.get("error"), str)
    assert respuesta.json["error"]


def comprobar_servicios_sin_llamadas(servicios):
    for servicio in vars(servicios).values():
        servicio.assert_not_called()


def test_factory_y_aplicacion_global_disponibles():
    assert isinstance(modulo_app.app, Flask)
    aplicacion = modulo_app.create_app({"TESTING": True, "SECRET_KEY": "prueba"})
    assert aplicacion.testing
    assert aplicacion.config["SECRET_KEY"] == "prueba"


@pytest.mark.parametrize(
    "ruta,archivo,mime",
    [
        ("/", "index.html", "text/html"),
        ("/productos", "index.html", "text/html"),
        ("/app.js", "app.js", "text/javascript"),
        ("/style.css", "style.css", "text/css"),
        ("/login", "login.html", "text/html"),
        ("/login.js", "login.js", "text/javascript"),
        ("/auth.css", "auth.css", "text/css"),
    ],
)
def test_interfaz_sirve_los_recursos_del_panel(cliente, servicios, ruta, archivo, mime):
    respuesta = cliente.get(ruta)

    assert respuesta.status_code == 200
    assert respuesta.mimetype in (
        {"text/javascript", "application/javascript"} if archivo.endswith(".js") else {mime}
    )
    esperado = Path(__file__).resolve().parents[1] / "web" / archivo
    assert respuesta.data == esperado.read_bytes()
    comprobar_servicios_sin_llamadas(servicios)


@pytest.mark.parametrize(
    "ruta,funcion,argumentos,resultado",
    [
        ("/api/productos", "listar_productos", (), [PRODUCTO]),
        ("/api/productos/7", "obtener_producto", (7,), PRODUCTO),
        ("/api/movimientos", "listar_movimientos", (), [MOVIMIENTO]),
    ],
)
def test_consultas_devuelven_datos_del_servicio(
    cliente, servicios, ruta, funcion, argumentos, resultado
):
    respuesta = cliente.get(ruta)

    assert respuesta.status_code == 200
    assert respuesta.json == resultado
    getattr(servicios, funcion).assert_called_once_with(*argumentos)


def test_registrar_producto_devuelve_ubicacion_del_recurso(cliente, servicios):
    respuesta = cliente.post("/api/productos", json=DATOS_PRODUCTO)

    assert respuesta.status_code == 201
    assert respuesta.json == {"id": 7}
    assert urlsplit(respuesta.headers["Location"]).path == "/api/productos/7"
    servicios.registrar_producto.assert_called_once_with(DATOS_PRODUCTO)


def test_tipos_mysql_se_serializan_para_el_panel(cliente, servicios):
    servicios.listar_productos.return_value = [
        {**PRODUCTO, "precio": Decimal("850.50")}
    ]
    servicios.listar_movimientos.return_value = [
        {**MOVIMIENTO, "fecha": datetime(2026, 10, 16, 12, 0, 0)}
    ]

    productos = cliente.get("/api/productos")
    movimientos = cliente.get("/api/movimientos")

    assert productos.json[0]["precio"] == 850.50
    assert movimientos.json[0]["fecha"] == "2026-10-16 12:00:00"


def test_actualizar_producto_delega_los_datos_al_servicio(cliente, servicios):
    datos = {**DATOS_PRODUCTO, "nombre": "Teclado RGB", "stock": 999}

    respuesta = cliente.put("/api/productos/7", json=datos)

    assert respuesta.status_code == 200
    assert respuesta.json == {"id": 7}
    servicios.actualizar_producto.assert_called_once_with(7, datos)
    servicios.registrar_movimiento.assert_not_called()


def test_eliminar_producto_delega_al_servicio(cliente, servicios):
    respuesta = cliente.delete("/api/productos/7")

    assert respuesta.status_code == 200
    assert respuesta.json == {"ok": True}
    servicios.eliminar_producto.assert_called_once_with(7)


def test_registrar_movimiento_devuelve_stock_resultante(cliente, servicios):
    datos = {"tipo": "Entrada", "cantidad": 4}

    respuesta = cliente.post("/api/productos/7/movimientos", json=datos)

    assert respuesta.status_code == 201
    assert respuesta.json == {"stock": 14}
    servicios.registrar_movimiento.assert_called_once_with(7, datos)


@pytest.mark.parametrize(
    "tipo,estado",
    [
        ("validacion", 400),
        ("campo_ausente", 400),
        ("tipo", 400),
        ("desbordamiento", 400),
        ("no_encontrado", 404),
        ("conflicto", 409),
        ("mysql", 503),
    ],
)
def test_errores_del_servicio_tienen_respuesta_json(cliente, servicios, tipo, estado):
    secreto = "detalle-interno-mysql-privado"
    errores = {
        "validacion": ValueError("El nombre no puede estar vacío."),
        "campo_ausente": KeyError("nombre"),
        "tipo": TypeError("Tipo de dato incorrecto"),
        "desbordamiento": OverflowError("Número demasiado grande"),
        "no_encontrado": modulo_app.inventario.ProductoNoEncontrado(
            "Producto no encontrado."
        ),
        "conflicto": modulo_app.inventario.ConflictoInventario(
            "Ya existe un producto con ese nombre."
        ),
        "mysql": mysql.connector.Error(secreto),
    }
    servicios.registrar_producto.side_effect = errores[tipo]

    respuesta = cliente.post("/api/productos", json=DATOS_PRODUCTO)

    comprobar_error(respuesta, estado)
    if tipo == "campo_ausente":
        assert "campo" in respuesta.json["error"].lower()
    if tipo == "mysql":
        assert secreto not in respuesta.get_data(as_text=True)


@pytest.mark.parametrize(
    "metodo,ruta",
    [
        ("POST", "/api/productos"),
        ("PUT", "/api/productos/7"),
        ("POST", "/api/productos/7/movimientos"),
    ],
)
def test_escrituras_exigen_content_type_json(cliente, servicios, metodo, ruta):
    respuesta = cliente.open(
        ruta, method=metodo, data=json.dumps(DATOS_PRODUCTO), content_type="text/plain"
    )

    comprobar_error(respuesta, 415)
    comprobar_servicios_sin_llamadas(servicios)


@pytest.mark.parametrize("datos", [None, [], "texto", 1, True])
def test_json_debe_ser_un_objeto(cliente, servicios, datos):
    respuesta = cliente.post(
        "/api/productos", data=json.dumps(datos), content_type="application/json"
    )

    comprobar_error(respuesta, 400)
    comprobar_servicios_sin_llamadas(servicios)


def test_json_malformado_se_rechaza_sin_consultar_datos(cliente, servicios):
    respuesta = cliente.post(
        "/api/productos", data='{"nombre":', content_type="application/json"
    )

    comprobar_error(respuesta, 400)
    comprobar_servicios_sin_llamadas(servicios)


def test_cuerpo_demasiado_grande_se_rechaza_sin_consultar_datos(cliente, servicios):
    respuesta = cliente.post(
        "/api/productos", data=b"x" * 65537, content_type="application/json"
    )

    comprobar_error(respuesta, 413)
    comprobar_servicios_sin_llamadas(servicios)


@pytest.mark.parametrize(
    "metodo,ruta",
    [
        ("POST", "/api/productos"),
        ("PUT", "/api/productos/7"),
        ("DELETE", "/api/productos/7"),
        ("POST", "/api/productos/7/movimientos"),
    ],
)
def test_origen_externo_no_puede_escribir(cliente, servicios, metodo, ruta):
    respuesta = cliente.open(
        ruta,
        method=metodo,
        json=DATOS_PRODUCTO,
        headers={"Origin": "https://otro-ejemplo.test"},
    )

    comprobar_error(respuesta, 403)
    comprobar_servicios_sin_llamadas(servicios)


def test_origen_que_coincide_con_host_y_puerto_puede_escribir(cliente, servicios):
    respuesta = cliente.post(
        "/api/productos",
        json=DATOS_PRODUCTO,
        base_url="http://localhost:5000",
        headers={"Origin": "http://localhost:5000"},
    )

    assert respuesta.status_code == 201
    servicios.registrar_producto.assert_called_once_with(DATOS_PRODUCTO)


def test_consultas_admiten_origen_externo(cliente, servicios):
    respuesta = cliente.get(
        "/api/productos", headers={"Origin": "https://otro-ejemplo.test"}
    )

    assert respuesta.status_code == 200
    servicios.listar_productos.assert_called_once_with()


@pytest.mark.parametrize(
    "metodo,ruta,estado",
    [
        ("GET", "/api/productos", 200),
        ("GET", "/api/ruta-inexistente", 404),
        ("PATCH", "/api/productos/7", 405),
    ],
)
def test_api_incluye_cabeceras_y_errores_json(cliente, metodo, ruta, estado):
    respuesta = cliente.open(ruta, method=metodo)

    assert respuesta.status_code == estado
    assert respuesta.is_json
    assert respuesta.headers["X-Content-Type-Options"] == "nosniff"
    assert respuesta.headers["Cache-Control"] == "no-store"
    if estado >= 400:
        assert respuesta.json["error"]


@pytest.mark.parametrize("ruta", ["/registrar", "/editar/7"])
def test_formularios_anteriores_redirigen_al_panel(cliente, servicios, ruta):
    respuesta = cliente.get(ruta)

    assert respuesta.status_code == 302
    assert urlsplit(respuesta.headers["Location"]).path == "/"
    comprobar_servicios_sin_llamadas(servicios)


@pytest.mark.parametrize("ruta", ["/registrar", "/editar/7", "/eliminar/7"])
def test_escrituras_anteriores_estan_retiradas(cliente, servicios, ruta):
    respuesta = cliente.post(ruta, data=DATOS_PRODUCTO)

    comprobar_error(respuesta, 410)
    comprobar_servicios_sin_llamadas(servicios)
