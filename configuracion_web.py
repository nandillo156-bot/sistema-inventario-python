"""Diferencia los valores locales de los requisitos de producción."""

import os
import secrets
from datetime import timedelta


def configurar(app, valores=None):
    hosts = os.getenv("TRUSTED_HOSTS", "localhost,127.0.0.1,[::1]")
    app.config.from_mapping(
        APP_ENV=os.getenv("APP_ENV", "development"),
        APP_MODE=os.getenv("APP_MODE", "private"),
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY") or None,
        MAX_CONTENT_LENGTH=65536,
        TRUSTED_HOSTS=[host.strip() for host in hosts.split(",") if host.strip()],
        SESSION_COOKIE_NAME="inventario_sesion",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
        SESSION_REFRESH_EACH_REQUEST=False,
        LOGIN_MAX_ATTEMPTS=5,
        LOGIN_WINDOW_SECONDS=300,
    )
    if valores is not None:
        app.config.update(valores)

    if app.config["APP_ENV"] not in {"development", "production"}:
        raise ValueError("APP_ENV debe ser development o production.")
    if app.config["APP_MODE"] not in {"private", "demo"}:
        raise ValueError("APP_MODE debe ser private o demo.")
    if app.config["APP_MODE"] == "demo" and (valores is None or "SESSION_COOKIE_NAME" not in valores):
        app.config["SESSION_COOKIE_NAME"] = "inventario_demo"
    if not app.config["TRUSTED_HOSTS"]:
        raise ValueError("Configura al menos un dominio en TRUSTED_HOSTS.")

    clave = app.config["SECRET_KEY"]
    if app.config["APP_ENV"] == "production":
        if not isinstance(clave, (str, bytes)) or len(clave) < 32:
            raise ValueError("Configura FLASK_SECRET_KEY estable de al menos 32 caracteres en producción.")
        if app.debug:
            raise ValueError("El modo debug debe estar desactivado en producción.")
        app.config["SESSION_COOKIE_SECURE"] = True
    elif not clave:
        # Solo en desarrollo: reiniciar el servidor invalida las sesiones.
        app.config["SECRET_KEY"] = secrets.token_hex(32)
