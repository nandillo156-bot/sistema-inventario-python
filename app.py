"""Servidor Flask del panel y su API de inventario."""

import os
import secrets
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import mysql.connector
from flask import Flask, jsonify, redirect, request, send_from_directory, url_for
from flask.json.provider import DefaultJSONProvider
from werkzeug.exceptions import HTTPException, UnsupportedMediaType

import servicio_inventario as inventario


WEB = Path(__file__).parent / "web"


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
    """Construye una aplicación independiente para ejecutarla o probarla."""
    app = Flask(__name__, static_folder=None)
    app.json = InventarioJSONProvider(app)
    app.json.ensure_ascii = False
    app.config.from_mapping(
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32),
        MAX_CONTENT_LENGTH=65536,
        TRUSTED_HOSTS=["localhost", "127.0.0.1", "[::1]"],
    )
    if config is not None:
        app.config.update(config)

    @app.before_request
    def comprobar_solicitud():
        if not request.path.startswith("/api/"):
            return None
        limite = app.config["MAX_CONTENT_LENGTH"]
        if limite is not None and request.content_length is not None:
            if request.content_length > limite:
                return jsonify(error="La solicitud supera el tamaño permitido."), 413
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origen = request.headers.get("Origin")
            if origen is not None and origen != request.host_url.rstrip("/"):
                return jsonify(error="Origen no permitido."), 403
        return None

    @app.after_request
    def cabeceras_respuesta(respuesta):
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        if request.path.startswith("/api/"):
            respuesta.headers["Cache-Control"] = "no-store"
        return respuesta

    def datos_json():
        # Rechaza formularios y JSON de tipo lista, null o texto antes de usar MySQL.
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

    @app.get("/app.js")
    def javascript():
        return send_from_directory(WEB, "app.js")

    @app.get("/style.css")
    def estilos():
        return send_from_directory(WEB, "style.css")

    @app.get("/api/productos")
    def listar_productos():
        return jsonify(inventario.listar_productos())

    @app.post("/api/productos")
    def registrar_producto():
        resultado = inventario.registrar_producto(datos_json())
        respuesta = jsonify(resultado)
        respuesta.status_code = 201
        respuesta.headers["Location"] = url_for(
            "obtener_producto", producto_id=resultado["id"]
        )
        return respuesta

    @app.get("/api/productos/<int:producto_id>")
    def obtener_producto(producto_id):
        return jsonify(inventario.obtener_producto(producto_id))

    @app.put("/api/productos/<int:producto_id>")
    def actualizar_producto(producto_id):
        return jsonify(inventario.actualizar_producto(producto_id, datos_json()))

    @app.delete("/api/productos/<int:producto_id>")
    def eliminar_producto(producto_id):
        return jsonify(inventario.eliminar_producto(producto_id))

    @app.get("/api/movimientos")
    def listar_movimientos():
        return jsonify(inventario.listar_movimientos())

    @app.post("/api/productos/<int:producto_id>/movimientos")
    def registrar_movimiento(producto_id):
        resultado = inventario.registrar_movimiento(producto_id, datos_json())
        return jsonify(resultado), 201

    # Conservamos las direcciones antiguas, pero sus formularios ya no escriben
    # directamente en la base. Todo cambio del panel pasa por el mismo servicio.
    @app.route("/registrar", methods=["GET", "POST"])
    @app.route("/editar/<int:producto_id>", methods=["GET", "POST"])
    @app.post("/eliminar/<int:producto_id>")
    def formulario_anterior(producto_id=None):
        if request.method == "GET":
            return redirect(url_for("inicio"))
        return jsonify(error="Este formulario ya no está activo. Usa el panel de inventario."), 410

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
        # Los detalles de conexión y SQL no se devuelven al navegador.
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
            500: "No se pudo completar la solicitud.",
        }
        # Conserva cabeceras HTTP como Allow en las respuestas 405.
        respuesta = error.get_response()
        respuesta.data = app.json.dumps({"error": mensajes.get(error.code, "No se pudo completar la solicitud.")})
        respuesta.content_type = "application/json"
        return respuesta

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
