"""Integración real optativa: RUN_MYSQL_INTEGRATION=1 python -m pytest -m mysql.

El usuario de conexión necesita CREATE/DROP DATABASE. Cada prueba crea una
base con UUID y elimina únicamente esa base, nunca DB_DATABASE original.
"""

import os
from pathlib import Path
import re
from uuid import uuid4

import pytest

from app import create_app
from conexion import conectar
import usuarios


pytestmark = [
    pytest.mark.mysql,
    pytest.mark.skipif(
        os.getenv("RUN_MYSQL_INTEGRATION") != "1",
        reason="Activa RUN_MYSQL_INTEGRATION=1 para usar MySQL desechable.",
    ),
]
CLAVE_PRUEBA = "Clave-exclusiva-de-pruebas-2026"


@pytest.fixture
def base_temporal(monkeypatch):
    nombre = "inventario_test_" + uuid4().hex
    assert re.fullmatch(r"inventario_test_[a-f0-9]{32}", nombre)
    administracion = conectar()
    cursor = None
    creada = False
    try:
        cursor = administracion.cursor()
        # Sin IF NOT EXISTS: una colisión no autoriza a usar ni borrar esa base.
        cursor.execute(f"CREATE DATABASE `{nombre}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci")
        creada = True
        cursor.execute(f"USE `{nombre}`")
        archivo = Path(__file__).resolve().parents[1] / "database" / "inventario.sql"
        # El esquema contiene DDL simple, sin procedimientos ni ';' en literales.
        sql = "\n".join(
            linea for linea in archivo.read_text(encoding="utf-8-sig").splitlines()
            if not linea.lstrip().startswith("--")
        )
        for sentencia in sql.split(";"):
            sentencia = sentencia.strip()
            if not sentencia or sentencia.upper().startswith(("CREATE DATABASE", "USE ")):
                continue
            cursor.execute(sentencia)
        administracion.commit()
        monkeypatch.setenv("DB_DATABASE", nombre)
        yield nombre
    finally:
        try:
            if creada:
                administracion.rollback()
                # nombre es el UUID propio que se creó correctamente más arriba.
                cursor.execute(f"DROP DATABASE `{nombre}`")
        finally:
            try:
                if cursor is not None:
                    cursor.close()
            finally:
                administracion.close()


def cliente_con_usuario(rol):
    usuario = usuarios.crear_usuario("cuenta_prueba", CLAVE_PRUEBA, rol)
    aplicacion = create_app({
        "TESTING": True,
        "APP_ENV": "development",
        "APP_MODE": "private",
        "SECRET_KEY": "clave-de-sesion-exclusiva-para-integracion",
    })
    cliente = aplicacion.test_client()
    token = cliente.get("/api/sesion").json["csrf_token"]
    respuesta = cliente.post(
        "/api/login", json={"nombre": "cuenta_prueba", "clave": CLAVE_PRUEBA},
        headers={"X-CSRF-Token": token},
    )
    assert respuesta.status_code == 200
    assert respuesta.json["usuario"] == usuario
    assert "password_hash" not in respuesta.get_data(as_text=True)
    return aplicacion, cliente, {"X-CSRF-Token": respuesta.json["csrf_token"]}, usuario


def test_login_admin_producto_movimiento_y_logout_reales(base_temporal):
    _, cliente, cabeceras, _ = cliente_con_usuario("administrador")
    alta = cliente.post("/api/productos", headers=cabeceras, json={
        "nombre": "Cuaderno de integración", "descripcion": "Datos desechables",
        "precio": "45.90", "stock": 10, "categoria": "Pruebas",
    })
    assert alta.status_code == 201
    producto_id = alta.json["id"]
    salida = cliente.post(
        f"/api/productos/{producto_id}/movimientos", headers=cabeceras,
        json={"tipo": "Salida", "cantidad": 4},
    )
    assert salida.status_code == 201
    assert salida.json == {"stock": 6}
    assert cliente.get(f"/api/productos/{producto_id}").json["stock"] == 6
    historial = cliente.get("/api/movimientos").json
    assert len(historial) == 1
    assert (historial[0]["stock_anterior"], historial[0]["stock_actual"]) == (10, 6)
    assert cliente.post("/api/logout", headers=cabeceras).status_code == 200
    assert cliente.get("/api/productos").status_code == 401


def test_consulta_no_escribe_y_desactivacion_revoca_sesion_real(base_temporal):
    _, cliente, cabeceras, usuario = cliente_con_usuario("consulta")
    assert cliente.get("/api/productos").status_code == 200
    assert cliente.post("/api/productos", headers=cabeceras, json={}).status_code == 403
    conexion = conectar()
    cursor = conexion.cursor()
    try:
        cursor.execute("UPDATE usuarios SET activo=FALSE WHERE id=%s", (usuario["id"],))
        conexion.commit()
    finally:
        cursor.close()
        conexion.close()
    assert cliente.get("/api/productos").status_code == 401
    assert cliente.get("/api/sesion").json["usuario"] is None


def test_migracion_acceso_se_puede_repetir_sin_borrar_cuentas(base_temporal):
    aplicacion, _, _, usuario = cliente_con_usuario("administrador")
    resultado = aplicacion.test_cli_runner().invoke(args=["inicializar-acceso"])
    assert resultado.exit_code == 0
    assert usuarios.autenticar("cuenta_prueba", CLAVE_PRUEBA) == usuario
