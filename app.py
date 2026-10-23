"""Panel Flask: sesión, permisos y rutas de inventario."""

import secrets
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import click
import mysql.connector
from flask import Flask, g, jsonify, redirect, request, send_from_directory, session, url_for
from flask.json.provider import DefaultJSONProvider
from werkzeug.exceptions import HTTPException, UnsupportedMediaType

import demo
import servicio_inventario as inventario
import usuarios
from configuracion_web import configurar
from conexion import conectar
from seguridad import IntentosLogin, PERMISOS_POR_ROL, permisos_para


WEB = Path(__file__).parent / "web"
PERMISOS_POR_RUTA = {
    "listar_productos": "consultar",
    "obtener_producto": "consultar",
    "listar_movimientos": "consultar",
    "registrar_producto": "gestionar_productos",
    "actualizar_producto": "gestionar_productos",
    "eliminar_producto": "gestionar_productos",
    "registrar_movimiento": "mover_stock",
}
RUTAS_DE_ACCESO = {"sesion_actual", "iniciar_sesion", "cerrar_sesion"}
METODOS_DE_ESCRITURA = {"POST", "PUT", "PATCH", "DELETE"}


class InventarioJSONProvider(DefaultJSONProvider):
    """Conserva el formato que espera el panel para precios y fechas de MySQL."""

    @staticmethod
    def default(valor):
        if isinstance(valor, Decimal):
            return float(valor)
        if isinstance(valor, datetime):
            return valor.isoformat(sep=" ", timespec="seconds")
        return DefaultJSONProvider.default(valor)


def create_app(config=None):
    """Construye una aplicación independiente, protegida también en las pruebas."""
    app = Flask(__name__, static_folder=None)
    app.json = InventarioJSONProvider(app)
    app.json.ensure_ascii = False
    configurar(app, config)
    app.extensions["intentos_login"] = IntentosLogin(
        app.config["LOGIN_MAX_ATTEMPTS"], app.config["LOGIN_WINDOW_SECONDS"]
    )

    def es_demo():
        return app.config["APP_MODE"] == "demo"

    def token_csrf():
        token = session.get("csrf_token")
        if not isinstance(token, str) or not token:
            token = secrets.token_hex(32)
            session["csrf_token"] = token
        return token

    def cargar_usuario():
        g.usuario = None
        if es_demo():
            return
        identificador = session.get("usuario_id")
        if identificador is None:
            return
        if isinstance(identificador, bool) or not isinstance(identificador, int) or identificador <= 0:
            session.clear()
            return
        usuario = usuarios.obtener_usuario(identificador)
        if usuario is None or usuario.get("activo") is False or usuario.get("rol") not in PERMISOS_POR_ROL:
            session.clear()
            return
        g.usuario = {campo: usuario[campo] for campo in ("id", "nombre", "rol")}

    def estado_sesion():
        usuario = getattr(g, "usuario", None)
        return {
            "usuario": usuario,
            "modo_demo": es_demo(),
            "csrf_token": token_csrf(),
            "permisos": ["consultar"] if es_demo() else permisos_para(usuario),
        }

    @app.before_request
    def comprobar_solicitud():
        if not request.path.startswith("/api/"):
            return None
        limite = app.config["MAX_CONTENT_LENGTH"]
        if limite is not None and request.content_length is not None:
            if request.content_length > limite:
                return jsonify(error="La solicitud supera el tamaño permitido."), 413
        escritura = request.method in METODOS_DE_ESCRITURA
        if escritura:
            origen = request.headers.get("Origin")
            if origen is not None and origen != request.host_url.rstrip("/"):
                return jsonify(error="Origen no permitido."), 403

        permiso = PERMISOS_POR_RUTA.get(request.endpoint)
        es_ruta_acceso = request.endpoint in RUTAS_DE_ACCESO
        if permiso is None and not es_ruta_acceso:
            return None
        if es_demo() and escritura:
            return jsonify(error="La demostración es de solo lectura."), 403
        cargar_usuario()
        if permiso is not None and not es_demo():
            if g.usuario is None:
                return jsonify(error="Inicia sesión para acceder al inventario."), 401
            if permiso not in permisos_para(g.usuario):
                return jsonify(error="Tu cuenta no tiene permiso para realizar esta operación."), 403

        if escritura:
            esperado = session.get("csrf_token")
            recibido = request.headers.get("X-CSRF-Token", "")
            if not isinstance(esperado, str) or not esperado or not secrets.compare_digest(
                esperado.encode("utf-8"), recibido.encode("utf-8")
            ):
                return jsonify(error="La verificación de la sesión falló. Actualiza la página."), 403
        return None

    @app.after_request
    def cabeceras_respuesta(respuesta):
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["X-Frame-Options"] = "SAMEORIGIN"
        if request.path.startswith("/api/") or request.path == "/login":
            respuesta.headers["Cache-Control"] = "no-store"
        return respuesta

    def datos_json():
        if request.mimetype != "application/json":
            raise UnsupportedMediaType()
        datos = request.get_json()
        if not isinstance(datos, dict):
            raise ValueError("Se requiere un objeto JSON.")
        return datos

    @app.get("/productos")
    @app.get("/")
    def inicio():
        return send_from_directory(WEB, "index.html")

    @app.get("/login")
    def pagina_login():
        if es_demo():
            return redirect(url_for("inicio"))
        return send_from_directory(WEB, "login.html")

    @app.get("/app.js")
    def javascript():
        return send_from_directory(WEB, "app.js")

    @app.get("/login.js")
    def javascript_login():
        return send_from_directory(WEB, "login.js")

    @app.get("/style.css")
    def estilos():
        return send_from_directory(WEB, "style.css")

    @app.get("/auth.css")
    def estilos_acceso():
        return send_from_directory(WEB, "auth.css")

    @app.get("/api/sesion")
    def sesion_actual():
        return jsonify(estado_sesion())

    @app.post("/api/login")
    def iniciar_sesion():
        espera = app.extensions["intentos_login"].intentar(request.remote_addr or "desconocido")
        if espera:
            respuesta = jsonify(error="Demasiados intentos. Espera unos minutos y vuelve a intentar.")
            respuesta.status_code = 429
            respuesta.headers["Retry-After"] = str(espera)
            return respuesta
        datos = datos_json()
        if not isinstance(datos.get("nombre"), str) or not isinstance(datos.get("clave"), str):
            raise ValueError("Introduce usuario y contraseña.")
        usuario = usuarios.autenticar(datos["nombre"], datos["clave"])
        if usuario is None:
            return jsonify(error="Usuario o contraseña incorrectos."), 401
        session.clear()
        session["usuario_id"] = usuario["id"]
        session.permanent = True
        g.usuario = {campo: usuario[campo] for campo in ("id", "nombre", "rol")}
        # Al cambiar de identidad cambia también el token de las escrituras.
        return jsonify(estado_sesion())

    @app.post("/api/logout")
    def cerrar_sesion():
        session.clear()
        g.usuario = None
        return jsonify(estado_sesion())

    @app.get("/api/productos")
    def listar_productos():
        return jsonify(demo.listar_productos() if es_demo() else inventario.listar_productos())

    @app.post("/api/productos")
    def registrar_producto():
        resultado = inventario.registrar_producto(datos_json())
        respuesta = jsonify(resultado)
        respuesta.status_code = 201
        respuesta.headers["Location"] = url_for("obtener_producto", producto_id=resultado["id"])
        return respuesta

    @app.get("/api/productos/<int:producto_id>")
    def obtener_producto(producto_id):
        if es_demo():
            producto = demo.obtener_producto(producto_id)
            if producto is None:
                raise inventario.ProductoNoEncontrado("Producto no encontrado.")
            return jsonify(producto)
        return jsonify(inventario.obtener_producto(producto_id))

    @app.put("/api/productos/<int:producto_id>")
    def actualizar_producto(producto_id):
        return jsonify(inventario.actualizar_producto(producto_id, datos_json()))

    @app.delete("/api/productos/<int:producto_id>")
    def eliminar_producto(producto_id):
        return jsonify(inventario.eliminar_producto(producto_id))

    @app.get("/api/movimientos")
    def listar_movimientos():
        return jsonify(demo.listar_movimientos() if es_demo() else inventario.listar_movimientos())

    @app.post("/api/productos/<int:producto_id>/movimientos")
    def registrar_movimiento(producto_id):
        return jsonify(inventario.registrar_movimiento(producto_id, datos_json())), 201

    @app.route("/registrar", methods=["GET", "POST"])
    @app.route("/editar/<int:producto_id>", methods=["GET", "POST"])
    @app.post("/eliminar/<int:producto_id>")
    def formulario_anterior(producto_id=None):
        if request.method == "GET":
            return redirect(url_for("inicio"))
        return jsonify(error="Este formulario ya no está activo. Usa el panel de inventario."), 410

    @app.cli.command("inicializar-acceso")
    def inicializar_acceso():
        """Crea únicamente la tabla de usuarios en la base configurada."""
        if es_demo():
            raise click.ClickException("El modo demo no utiliza una base de usuarios.")
        conexion = None
        cursor = None
        try:
            conexion = conectar()
            cursor = conexion.cursor()
            migracion = Path(__file__).parent / "database" / "migrations" / "001_usuarios.sql"
            cursor.execute(migracion.read_text(encoding="utf-8-sig"))
            conexion.commit()
        except mysql.connector.Error:
            raise click.ClickException("No se pudo preparar el acceso. Revisa la conexión y los permisos de MySQL.") from None
        finally:
            try:
                if cursor is not None:
                    cursor.close()
            finally:
                if conexion is not None:
                    conexion.close()
        click.echo("Tabla de usuarios preparada. Los productos y movimientos se conservan.")

    @app.cli.command("crear-usuario")
    @click.option("--nombre", prompt="Usuario")
    @click.option("--rol", type=click.Choice(usuarios.ROLES), default="consulta", prompt="Rol")
    def crear_usuario(nombre, rol):
        """Crea una cuenta local; la contraseña se pide sin mostrarla."""
        if es_demo():
            raise click.ClickException("Cambia APP_MODE a private para administrar cuentas.")
        clave = click.prompt("Contraseña", hide_input=True, confirmation_prompt=True)
        try:
            usuario = usuarios.crear_usuario(nombre, clave, rol)
        except ValueError as error:
            raise click.ClickException(str(error)) from None
        except mysql.connector.Error:
            raise click.ClickException("No se pudo crear la cuenta. Ejecuta inicializar-acceso y revisa MySQL.") from None
        click.echo(f"Cuenta {usuario['nombre']} creada con rol {usuario['rol']}.")

    @app.errorhandler(inventario.ProductoNoEncontrado)
    def producto_no_encontrado(error):
        return jsonify(error=str(error)), 404

    @app.errorhandler(inventario.ConflictoInventario)
    def conflicto_inventario(error):
        return jsonify(error=str(error)), 409

    @app.errorhandler(KeyError)
    def faltan_campos(error):
        return jsonify(error="Completa todos los campos requeridos."), 400

    @app.errorhandler(ValueError)
    def datos_invalidos(error):
        return jsonify(error=str(error) or "Datos inválidos."), 400

    def formato_invalido(error):
        return jsonify(error="Datos inválidos. Revisa los campos."), 400

    app.register_error_handler(TypeError, formato_invalido)
    app.register_error_handler(OverflowError, formato_invalido)

    @app.errorhandler(mysql.connector.Error)
    def error_base_de_datos(error):
        return jsonify(error="No se pudo completar la operación en la base de datos. Comprueba MySQL."), 503

    @app.errorhandler(HTTPException)
    def error_http(error):
        mensajes = {
            400: "Solicitud inválida. Revisa el JSON y los datos enviados.",
            403: "Acceso no permitido.",
            404: "Ruta no encontrada.",
            405: "Método no permitido para esta ruta.",
            410: "Esta ruta ya no está disponible.",
            413: "La solicitud supera el tamaño permitido.",
            415: "Se requiere JSON (application/json).",
            429: "Demasiados intentos. Espera unos minutos y vuelve a intentar.",
            500: "No se pudo completar la solicitud.",
        }
        respuesta = error.get_response()
        respuesta.data = app.json.dumps({"error": mensajes.get(error.code, "No se pudo completar la solicitud.")})
        respuesta.content_type = "application/json"
        return respuesta

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
