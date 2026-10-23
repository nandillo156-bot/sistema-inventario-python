"""Acceso HTTP, sesiones y demo sin conexiones reales a MySQL."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import mysql.connector
import pytest

import app as modulo_app


ADMIN = {"id": 7, "nombre": "admin", "rol": "administrador"}
PRODUCTO = {
    "id": 7,
    "nombre": "Teclado privado",
    "descripcion": "Producto de prueba del servicio",
    "precio": 850.50,
    "stock": 10,
    "categoria": "Periféricos",
}
DATOS_PRODUCTO = {campo: valor for campo, valor in PRODUCTO.items() if campo != "id"}
CSRF_PRUEBA = "csrf-pruebas"
RUTAS_INVENTARIO = [
    ("GET", "/api/productos", "listar_productos", 200, "consultar"),
    ("GET", "/api/productos/7", "obtener_producto", 200, "consultar"),
    ("GET", "/api/movimientos", "listar_movimientos", 200, "consultar"),
    ("POST", "/api/productos", "registrar_producto", 201, "gestionar_productos"),
    ("PUT", "/api/productos/7", "actualizar_producto", 200, "gestionar_productos"),
    ("DELETE", "/api/productos/7", "eliminar_producto", 200, "gestionar_productos"),
    (
        "POST", "/api/productos/7/movimientos", "registrar_movimiento", 201,
        "mover_stock",
    ),
]
PERMISOS = {
    "consulta": {"consultar"},
    "operador": {"consultar", "mover_stock"},
    "administrador": {"consultar", "mover_stock", "gestionar_productos"},
}


@pytest.fixture
def dependencias(monkeypatch):
    obtener_usuario = MagicMock(return_value=None)
    autenticar = MagicMock(return_value=None)
    monkeypatch.setattr(modulo_app.usuarios, "obtener_usuario", obtener_usuario)
    monkeypatch.setattr(modulo_app.usuarios, "autenticar", autenticar)
    resultados = {
        "listar_productos": [PRODUCTO],
        "obtener_producto": PRODUCTO,
        "registrar_producto": {"id": 7},
        "actualizar_producto": {"id": 7},
        "eliminar_producto": {"ok": True},
        "listar_movimientos": [],
        "registrar_movimiento": {"stock": 14},
    }
    inventario = {}
    for nombre, resultado in resultados.items():
        simulado = MagicMock(return_value=resultado)
        monkeypatch.setattr(modulo_app.inventario, nombre, simulado)
        inventario[nombre] = simulado
    return SimpleNamespace(
        obtener_usuario=obtener_usuario,
        autenticar=autenticar,
        inventario=SimpleNamespace(**inventario),
    )


@pytest.fixture
def fabricar_app(dependencias):
    def fabricar(**config):
        return modulo_app.create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "clave-pruebas",
                "APP_MODE": "private",
                "APP_ENV": "development",
                **config,
            }
        )

    return fabricar


@pytest.fixture
def aplicacion(fabricar_app):
    return fabricar_app()


def establecer_sesion(cliente, usuario_id=7, csrf_token=CSRF_PRUEBA):
    with cliente.session_transaction() as sesion:
        sesion["usuario_id"] = usuario_id
        sesion["csrf_token"] = csrf_token


def comprobar_error(respuesta, estado):
    assert respuesta.status_code == estado
    assert respuesta.is_json
    assert respuesta.json["error"]


def comprobar_inventario_sin_llamadas(dependencias):
    for simulado in vars(dependencias.inventario).values():
        simulado.assert_not_called()


def token_sesion(cliente):
    respuesta = cliente.get("/api/sesion")
    assert respuesta.status_code == 200
    return respuesta.json["csrf_token"]


def test_sesion_publica_entrega_token_sin_abrir_la_base(aplicacion, dependencias):
    cliente = aplicacion.test_client()

    respuesta = cliente.get("/api/sesion")

    assert respuesta.status_code == 200
    assert respuesta.json["usuario"] is None
    assert respuesta.json["modo_demo"] is False
    assert respuesta.json["permisos"] == []
    assert isinstance(respuesta.json["csrf_token"], str)
    assert respuesta.json["csrf_token"]
    assert token_sesion(cliente) == respuesta.json["csrf_token"]
    dependencias.obtener_usuario.assert_not_called()
    dependencias.autenticar.assert_not_called()
    comprobar_inventario_sin_llamadas(dependencias)


@pytest.mark.parametrize("rol", list(PERMISOS))
def test_sesion_expone_usuario_y_permisos_sin_datos_de_clave(
    aplicacion, dependencias, rol
):
    usuario = {**ADMIN, "rol": rol, "clave_hash": "dato-privado-del-servidor"}
    dependencias.obtener_usuario.return_value = usuario
    cliente = aplicacion.test_client()
    establecer_sesion(cliente)

    respuesta = cliente.get("/api/sesion")

    assert respuesta.status_code == 200
    assert respuesta.json["usuario"] == {**ADMIN, "rol": rol}
    assert set(respuesta.json["permisos"]) == PERMISOS[rol]
    assert "dato-privado-del-servidor" not in respuesta.get_data(as_text=True)
    dependencias.obtener_usuario.assert_called_once_with(7)


@pytest.mark.parametrize("metodo,ruta,funcion,estado,permiso", RUTAS_INVENTARIO)
def test_inventario_privado_exige_sesion(
    aplicacion, dependencias, metodo, ruta, funcion, estado, permiso
):
    respuesta = aplicacion.test_client().open(ruta, method=metodo, json=DATOS_PRODUCTO)

    comprobar_error(respuesta, 401)
    comprobar_inventario_sin_llamadas(dependencias)
    dependencias.obtener_usuario.assert_not_called()


@pytest.mark.parametrize("rol", list(PERMISOS))
@pytest.mark.parametrize("metodo,ruta,funcion,estado,permiso", RUTAS_INVENTARIO)
def test_permisos_se_aplican_en_el_servidor(
    aplicacion, dependencias, rol, metodo, ruta, funcion, estado, permiso
):
    dependencias.obtener_usuario.return_value = {**ADMIN, "rol": rol}
    cliente = aplicacion.test_client()
    establecer_sesion(cliente)
    datos = {"tipo": "Entrada", "cantidad": 4} if permiso == "mover_stock" else DATOS_PRODUCTO

    respuesta = cliente.open(
        ruta, method=metodo, json=datos, headers={"X-CSRF-Token": CSRF_PRUEBA}
    )

    servicio = getattr(dependencias.inventario, funcion)
    if permiso in PERMISOS[rol]:
        assert respuesta.status_code == estado
        servicio.assert_called_once()
    else:
        comprobar_error(respuesta, 403)
        comprobar_inventario_sin_llamadas(dependencias)


def test_rol_desconocido_no_recibe_permisos(aplicacion, dependencias):
    dependencias.obtener_usuario.return_value = {**ADMIN, "rol": "superusuario"}
    cliente = aplicacion.test_client()
    establecer_sesion(cliente)

    respuesta = cliente.get("/api/productos")

    comprobar_error(respuesta, 401)
    assert cliente.get("/api/sesion").json["usuario"] is None
    comprobar_inventario_sin_llamadas(dependencias)


@pytest.mark.parametrize("usuario", [None, {**ADMIN, "activo": False}])
def test_usuario_desactivado_o_eliminado_pierde_acceso(aplicacion, dependencias, usuario):
    dependencias.obtener_usuario.return_value = usuario
    cliente = aplicacion.test_client()
    establecer_sesion(cliente)

    respuesta = cliente.get("/api/productos")

    comprobar_error(respuesta, 401)
    assert cliente.get("/api/sesion").json["usuario"] is None
    comprobar_inventario_sin_llamadas(dependencias)


def test_cambio_de_rol_se_aplica_a_una_sesion_abierta(aplicacion, dependencias):
    dependencias.obtener_usuario.return_value = ADMIN
    cliente = aplicacion.test_client()
    establecer_sesion(cliente)
    cliente.environ_base["HTTP_X_CSRF_TOKEN"] = CSRF_PRUEBA
    assert cliente.post("/api/productos", json=DATOS_PRODUCTO).status_code == 201
    dependencias.inventario.registrar_producto.reset_mock()
    dependencias.obtener_usuario.return_value = {**ADMIN, "rol": "consulta"}

    respuesta = cliente.post("/api/productos", json=DATOS_PRODUCTO)

    comprobar_error(respuesta, 403)
    dependencias.inventario.registrar_producto.assert_not_called()


@pytest.mark.parametrize("token", [None, "token-incorrecto"], ids=["ausente", "invalido"])
@pytest.mark.parametrize(
    "metodo,ruta",
    [(metodo, ruta) for metodo, ruta, *_ in RUTAS_INVENTARIO if metodo != "GET"],
)
def test_mutaciones_exigen_csrf_valido(
    aplicacion, dependencias, metodo, ruta, token
):
    dependencias.obtener_usuario.return_value = ADMIN
    cliente = aplicacion.test_client()
    establecer_sesion(cliente)
    headers = {} if token is None else {"X-CSRF-Token": token}

    respuesta = cliente.open(ruta, method=metodo, json=DATOS_PRODUCTO, headers=headers)

    comprobar_error(respuesta, 403)
    comprobar_inventario_sin_llamadas(dependencias)


@pytest.mark.parametrize("ruta", ["/api/login", "/api/logout"])
@pytest.mark.parametrize("token", [None, "token-incorrecto"])
def test_login_y_logout_exigen_csrf(aplicacion, dependencias, ruta, token):
    cliente = aplicacion.test_client()
    token_sesion(cliente)
    headers = {} if token is None else {"X-CSRF-Token": token}

    respuesta = cliente.post(
        ruta, json={"nombre": "admin", "clave": "clave-prueba"}, headers=headers
    )

    comprobar_error(respuesta, 403)
    dependencias.autenticar.assert_not_called()


@pytest.mark.parametrize("ruta", ["/api/login", "/api/logout"])
def test_origen_externo_no_puede_cambiar_la_sesion(aplicacion, dependencias, ruta):
    cliente = aplicacion.test_client()
    token = token_sesion(cliente)

    respuesta = cliente.post(
        ruta,
        json={"nombre": "admin", "clave": "clave-correcta"},
        headers={"X-CSRF-Token": token, "Origin": "https://otro-ejemplo.test"},
    )

    comprobar_error(respuesta, 403)
    dependencias.autenticar.assert_not_called()


def test_login_rota_csrf_y_guarda_solo_identidad(aplicacion, dependencias):
    dependencias.autenticar.return_value = ADMIN
    dependencias.obtener_usuario.return_value = ADMIN
    cliente = aplicacion.test_client()
    token_anterior = token_sesion(cliente)

    respuesta = cliente.post(
        "/api/login",
        json={"nombre": "admin", "clave": "clave-correcta"},
        headers={"X-CSRF-Token": token_anterior},
    )

    assert respuesta.status_code == 200
    assert respuesta.json["usuario"] == ADMIN
    token_nuevo = respuesta.json["csrf_token"]
    assert token_nuevo and token_nuevo != token_anterior
    dependencias.autenticar.assert_called_once_with("admin", "clave-correcta")
    with cliente.session_transaction() as sesion:
        assert sesion["usuario_id"] == 7
        assert sesion["csrf_token"] == token_nuevo
        assert "rol" not in sesion
        assert "clave" not in sesion
        assert "clave_hash" not in sesion
    comprobar_error(
        cliente.post(
            "/api/productos", json=DATOS_PRODUCTO,
            headers={"X-CSRF-Token": token_anterior},
        ),
        403,
    )
    assert cliente.post(
        "/api/productos", json=DATOS_PRODUCTO,
        headers={"X-CSRF-Token": token_nuevo},
    ).status_code == 201


def test_login_fallido_no_revela_si_el_usuario_existe(aplicacion, dependencias):
    cliente = aplicacion.test_client()
    token = token_sesion(cliente)
    respuestas = [
        cliente.post(
            "/api/login", json={"nombre": nombre, "clave": "incorrecta"},
            headers={"X-CSRF-Token": token},
        )
        for nombre in ("admin", "usuario-inexistente")
    ]

    for respuesta in respuestas:
        comprobar_error(respuesta, 401)
        assert "incorrecta" not in respuesta.get_data(as_text=True)
    assert respuestas[0].json == respuestas[1].json
    assert cliente.get("/api/sesion").json["usuario"] is None


def test_logout_elimina_identidad_y_rota_csrf(aplicacion, dependencias):
    dependencias.obtener_usuario.return_value = ADMIN
    cliente = aplicacion.test_client()
    establecer_sesion(cliente)

    respuesta = cliente.post("/api/logout", headers={"X-CSRF-Token": CSRF_PRUEBA})

    assert respuesta.status_code == 200
    assert respuesta.json["usuario"] is None
    assert respuesta.json["csrf_token"] != CSRF_PRUEBA
    with cliente.session_transaction() as sesion:
        assert "usuario_id" not in sesion
        assert sesion["csrf_token"] == respuesta.json["csrf_token"]
    comprobar_error(cliente.get("/api/productos"), 401)


def test_cookie_con_firma_alterada_no_autentica(aplicacion, dependencias):
    dependencias.obtener_usuario.return_value = ADMIN
    cliente = aplicacion.test_client()
    establecer_sesion(cliente)
    nombre_cookie = aplicacion.config["SESSION_COOKIE_NAME"]
    cookie = cliente.get_cookie(nombre_cookie)
    contenido, firma = cookie.value.rsplit(".", 1)
    firma_alterada = ("a" if firma[0] != "a" else "b") + firma[1:]
    cliente.set_cookie(nombre_cookie, f"{contenido}.{firma_alterada}")

    respuesta = cliente.get("/api/productos")

    comprobar_error(respuesta, 401)
    dependencias.obtener_usuario.assert_not_called()
    comprobar_inventario_sin_llamadas(dependencias)


@pytest.mark.parametrize("ruta", ["/api/sesion", "/api/login"])
def test_fallos_de_usuarios_ocultan_detalles_mysql(aplicacion, dependencias, ruta):
    cliente = aplicacion.test_client()
    token = token_sesion(cliente)
    detalle = "detalle-interno-usuarios-privado"
    error = mysql.connector.Error(detalle)
    if ruta == "/api/sesion":
        establecer_sesion(cliente)
        dependencias.obtener_usuario.side_effect = error
        respuesta = cliente.get(ruta)
    else:
        dependencias.autenticar.side_effect = error
        respuesta = cliente.post(
            ruta, json={"nombre": "admin", "clave": "clave-correcta"},
            headers={"X-CSRF-Token": token},
        )

    comprobar_error(respuesta, 503)
    assert detalle not in respuesta.get_data(as_text=True)
    comprobar_inventario_sin_llamadas(dependencias)


def test_demo_consulta_datos_ficticios_sin_mysql(fabricar_app, dependencias):
    cliente = fabricar_app(APP_MODE="demo").test_client()

    sesion = cliente.get("/api/sesion")
    productos = cliente.get("/api/productos")
    movimientos = cliente.get("/api/movimientos")

    assert sesion.status_code == 200
    assert sesion.json["modo_demo"] is True
    assert sesion.json["usuario"] is None
    assert set(sesion.json["permisos"]) == {"consultar"}
    assert productos.status_code == 200
    assert productos.json and isinstance(productos.json, list)
    assert productos.json != [PRODUCTO]
    detalle = cliente.get(f"/api/productos/{productos.json[0]['id']}")
    assert detalle.status_code == 200
    assert detalle.json == productos.json[0]
    assert movimientos.status_code == 200
    assert isinstance(movimientos.json, list)
    dependencias.obtener_usuario.assert_not_called()
    dependencias.autenticar.assert_not_called()
    comprobar_inventario_sin_llamadas(dependencias)


def test_demo_ignora_una_sesion_privada_anterior(fabricar_app, dependencias):
    cliente = fabricar_app(APP_MODE="demo").test_client()
    establecer_sesion(cliente)

    respuesta = cliente.get("/api/sesion")

    assert respuesta.status_code == 200
    assert respuesta.json["usuario"] is None
    assert respuesta.json["modo_demo"] is True
    assert cliente.get("/api/productos").status_code == 200
    dependencias.obtener_usuario.assert_not_called()
    dependencias.autenticar.assert_not_called()
    comprobar_inventario_sin_llamadas(dependencias)


@pytest.mark.parametrize(
    "metodo,ruta",
    [(metodo, ruta) for metodo, ruta, *_ in RUTAS_INVENTARIO if metodo != "GET"]
    + [("POST", "/api/login"), ("POST", "/api/logout")],
)
def test_demo_bloquea_escrituras_antes_de_los_servicios(
    fabricar_app, dependencias, metodo, ruta
):
    cliente = fabricar_app(APP_MODE="demo").test_client()

    respuesta = cliente.open(ruta, method=metodo, json=DATOS_PRODUCTO)

    comprobar_error(respuesta, 403)
    dependencias.obtener_usuario.assert_not_called()
    dependencias.autenticar.assert_not_called()
    comprobar_inventario_sin_llamadas(dependencias)


@pytest.mark.parametrize("clave", [None, "", "x" * 31])
def test_produccion_exige_una_clave_estable_suficiente(fabricar_app, clave):
    with pytest.raises(ValueError, match="FLASK_SECRET_KEY"):
        fabricar_app(APP_ENV="production", SECRET_KEY=clave)


def test_cookies_de_produccion_son_seguras(fabricar_app):
    aplicacion = fabricar_app(APP_ENV="production", SECRET_KEY="x" * 32)
    cliente = aplicacion.test_client()

    respuesta = cliente.get("/api/sesion", base_url="https://localhost")

    assert respuesta.status_code == 200
    cookie = respuesta.headers["Set-Cookie"]
    assert "Secure" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_modo_desconocido_no_arranca(fabricar_app):
    with pytest.raises(ValueError):
        fabricar_app(APP_MODE="publico")


def test_sexto_intento_de_login_se_limita_antes_de_autenticar(aplicacion, dependencias):
    cliente = aplicacion.test_client()
    token = token_sesion(cliente)
    datos = {"nombre": "admin", "clave": "incorrecta"}
    for _ in range(5):
        comprobar_error(
            cliente.post("/api/login", json=datos, headers={"X-CSRF-Token": token}),
            401,
        )

    respuesta = cliente.post(
        "/api/login", json=datos, headers={"X-CSRF-Token": token}
    )

    comprobar_error(respuesta, 429)
    assert dependencias.autenticar.call_count == 5


def test_limite_de_login_distingue_ips(fabricar_app, dependencias):
    cliente = fabricar_app(LOGIN_MAX_ATTEMPTS=1).test_client()
    token = token_sesion(cliente)
    datos = {"nombre": "admin", "clave": "incorrecta"}
    argumentos = {"json": datos, "headers": {"X-CSRF-Token": token}}
    comprobar_error(cliente.post("/api/login", **argumentos), 401)
    comprobar_error(cliente.post("/api/login", **argumentos), 429)

    respuesta = cliente.post(
        "/api/login", environ_overrides={"REMOTE_ADDR": "203.0.113.8"}, **argumentos
    )

    comprobar_error(respuesta, 401)
    assert dependencias.autenticar.call_count == 2


def test_limite_de_login_expira_sin_bloquear_para_siempre(
    fabricar_app, dependencias, monkeypatch
):
    import seguridad

    reloj = [1000.0]
    monkeypatch.setattr(seguridad.time, "monotonic", lambda: reloj[0])
    cliente = fabricar_app(LOGIN_MAX_ATTEMPTS=2, LOGIN_WINDOW_SECONDS=300).test_client()
    token = token_sesion(cliente)
    argumentos = {
        "json": {"nombre": "admin", "clave": "incorrecta"},
        "headers": {"X-CSRF-Token": token},
    }
    comprobar_error(cliente.post("/api/login", **argumentos), 401)
    comprobar_error(cliente.post("/api/login", **argumentos), 401)
    comprobar_error(cliente.post("/api/login", **argumentos), 429)

    reloj[0] += 301
    respuesta = cliente.post("/api/login", **argumentos)

    comprobar_error(respuesta, 401)
    assert dependencias.autenticar.call_count == 3


def test_login_correcto_tambien_cuenta_para_el_limite(fabricar_app, dependencias):
    dependencias.autenticar.return_value = ADMIN
    dependencias.obtener_usuario.return_value = ADMIN
    cliente = fabricar_app(LOGIN_MAX_ATTEMPTS=1).test_client()
    token = token_sesion(cliente)
    datos = {"nombre": "admin", "clave": "correcta"}
    primero = cliente.post(
        "/api/login", json=datos, headers={"X-CSRF-Token": token}
    )
    assert primero.status_code == 200

    segundo = cliente.post(
        "/api/login", json=datos,
        headers={"X-CSRF-Token": primero.json["csrf_token"]},
    )

    comprobar_error(segundo, 429)
    dependencias.autenticar.assert_called_once()
