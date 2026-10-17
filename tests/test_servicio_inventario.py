from decimal import Decimal
from unittest.mock import MagicMock

import mysql.connector
import pytest

import servicio_inventario as servicio


@pytest.fixture
def datos_producto():
    return {
        "nombre": "Teclado",
        "descripcion": "Teclado mecánico",
        "precio": 850.50,
        "stock": 10,
        "categoria": "Periféricos",
    }


@pytest.fixture
def base_simulada(monkeypatch):
    cursor = MagicMock()
    conexion = MagicMock()
    conexion.cursor.return_value = cursor
    monkeypatch.setattr(servicio, "conectar", lambda: conexion)

    yield conexion, cursor

    conexion.cursor.assert_called_once_with(dictionary=True)
    cursor.close.assert_called_once()
    conexion.close.assert_called_once()


@pytest.mark.parametrize("campo", ["nombre", "descripcion", "categoria"])
@pytest.mark.parametrize("valor", [None, [], {}], ids=["null", "lista", "objeto"])
def test_producto_rechaza_campos_que_no_son_texto(datos_producto, campo, valor):
    datos_producto[campo] = valor

    with pytest.raises(ValueError, match="debe ser texto"):
        servicio.producto_validado(datos_producto)


@pytest.mark.parametrize("precio", [True, False])
def test_producto_rechaza_precio_booleano(datos_producto, precio):
    datos_producto["precio"] = precio

    with pytest.raises(ValueError):
        servicio.producto_validado(datos_producto)


@pytest.mark.parametrize("stock_enviado", [999, None, True, "inválido", {}, "omitir"])
def test_actualizar_producto_conserva_stock(
    datos_producto, base_simulada, stock_enviado
):
    conexion, cursor = base_simulada
    cursor.fetchone.side_effect = [{"stock": 10}, None]
    if stock_enviado == "omitir":
        datos_producto.pop("stock")
    else:
        datos_producto["stock"] = stock_enviado

    resultado = servicio.actualizar_producto(1, datos_producto)

    assert resultado == {"id": 1}
    actualizaciones = [
        llamada.args
        for llamada in cursor.execute.call_args_list
        if llamada.args[0].lstrip().upper().startswith("UPDATE")
    ]
    assert len(actualizaciones) == 1
    sql, parametros = actualizaciones[0]
    campos_actualizados = sql.upper().split("SET", 1)[1].split("WHERE", 1)[0]
    assert "STOCK" not in campos_actualizados
    assert parametros == (
        "Teclado", "Teclado mecánico", 850.50, "Periféricos", 1
    )
    consulta_inicial = cursor.execute.call_args_list[0].args
    assert "STOCK" in consulta_inicial[0].upper()
    assert "FOR UPDATE" in consulta_inicial[0].upper()
    assert consulta_inicial[1] == (1,)
    conexion.commit.assert_called_once()
    conexion.rollback.assert_not_called()


@pytest.mark.parametrize("tipo,stock_final", [("Entrada", 14), ("Salida", 6)])
def test_movimiento_actualiza_stock_y_registra_historial(
    base_simulada, tipo, stock_final
):
    conexion, cursor = base_simulada
    cursor.fetchone.return_value = {"stock": 10}

    resultado = servicio.registrar_movimiento(1, {"tipo": tipo, "cantidad": 4})

    assert resultado == {"stock": stock_final}
    escrituras = [
        llamada.args
        for llamada in cursor.execute.call_args_list
        if llamada.args[0].lstrip().upper().startswith(("UPDATE", "INSERT"))
    ]
    assert len(escrituras) == 2
    assert escrituras[0][0].startswith("UPDATE productos")
    assert escrituras[0][1] == (stock_final, 1)
    assert escrituras[1][0].startswith("INSERT INTO movimientos")
    assert escrituras[1][1] == (1, tipo, 4, 10, stock_final)
    conexion.commit.assert_called_once()
    conexion.rollback.assert_not_called()


def test_salida_sin_stock_revierte_sin_escribir(base_simulada):
    conexion, cursor = base_simulada
    cursor.fetchone.return_value = {"stock": 10}

    with pytest.raises(ValueError, match="No hay suficiente stock"):
        servicio.registrar_movimiento(1, {"tipo": "Salida", "cantidad": 11})

    assert not any(
        llamada.args[0].lstrip().upper().startswith(("UPDATE", "INSERT"))
        for llamada in cursor.execute.call_args_list
    )
    conexion.rollback.assert_called_once()
    conexion.commit.assert_not_called()


@pytest.mark.parametrize("operacion", ["listar_productos", "listar_movimientos"])
def test_listados_devuelven_filas_de_la_base_de_datos(base_simulada, operacion):
    conexion, cursor = base_simulada
    filas = [{"id": 1, "nombre": "Teclado", "precio": Decimal("850.50")}]
    cursor.fetchall.return_value = filas

    resultado = getattr(servicio, operacion)()

    assert resultado is filas
    assert cursor.execute.call_args.args[0].lstrip().upper().startswith("SELECT")
    conexion.commit.assert_not_called()
    conexion.rollback.assert_not_called()


def test_obtener_producto_devuelve_sus_datos(base_simulada):
    conexion, cursor = base_simulada
    producto = {"id": 1, "nombre": "Teclado", "stock": 10}
    cursor.fetchone.return_value = producto

    resultado = servicio.obtener_producto(1)

    assert resultado is producto
    assert cursor.execute.call_args.args[1] == (1,)
    conexion.commit.assert_not_called()
    conexion.rollback.assert_not_called()


@pytest.mark.parametrize(
    "operacion",
    ["obtener_producto", "actualizar_producto", "eliminar_producto", "registrar_movimiento"],
)
def test_producto_inexistente_revierte_sin_escribir(
    datos_producto, base_simulada, operacion
):
    conexion, cursor = base_simulada
    cursor.fetchone.return_value = None
    argumentos = {
        "obtener_producto": (1,),
        "actualizar_producto": (1, datos_producto),
        "eliminar_producto": (1,),
        "registrar_movimiento": (1, {"tipo": "Entrada", "cantidad": 2}),
    }

    with pytest.raises(servicio.ProductoNoEncontrado, match="Producto no encontrado"):
        getattr(servicio, operacion)(*argumentos[operacion])

    assert not any(
        llamada.args[0].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for llamada in cursor.execute.call_args_list
    )
    conexion.rollback.assert_called_once()
    conexion.commit.assert_not_called()


def test_registrar_producto_guarda_datos_y_devuelve_id(datos_producto, base_simulada):
    conexion, cursor = base_simulada
    cursor.fetchone.return_value = None
    cursor.lastrowid = 73

    resultado = servicio.registrar_producto(datos_producto)

    assert resultado == {"id": 73}
    sql, parametros = cursor.execute.call_args.args
    assert sql.lstrip().upper().startswith("INSERT INTO PRODUCTOS")
    assert parametros == ("Teclado", "Teclado mecánico", 850.50, 10, "Periféricos")
    conexion.commit.assert_called_once()
    conexion.rollback.assert_not_called()


@pytest.mark.parametrize("editar", [False, True], ids=["alta", "editar"])
def test_nombre_duplicado_devuelve_conflicto_sin_escribir(
    datos_producto, base_simulada, editar
):
    conexion, cursor = base_simulada
    cursor.fetchone.side_effect = (
        [{"stock": 10}, {"id": 2}] if editar else [{"id": 2}]
    )

    with pytest.raises(servicio.ConflictoInventario, match="Ya existe un producto"):
        if editar:
            servicio.actualizar_producto(1, datos_producto)
        else:
            servicio.registrar_producto(datos_producto)

    assert not any(
        llamada.args[0].lstrip().upper().startswith(("INSERT", "UPDATE"))
        for llamada in cursor.execute.call_args_list
    )
    conexion.rollback.assert_called_once()
    conexion.commit.assert_not_called()


@pytest.mark.parametrize("editar", [False, True], ids=["alta", "editar"])
def test_duplicado_detectado_por_mysql_se_traduce_a_conflicto(
    datos_producto, base_simulada, editar
):
    conexion, cursor = base_simulada
    cursor.fetchone.side_effect = [{"stock": 10}, None] if editar else [None]
    error_duplicado = mysql.connector.IntegrityError("Duplicate entry", errno=1062)

    def ejecutar(sql, parametros):
        if sql.lstrip().upper().startswith(("INSERT", "UPDATE")):
            raise error_duplicado

    cursor.execute.side_effect = ejecutar

    with pytest.raises(servicio.ConflictoInventario, match="Ya existe un producto"):
        if editar:
            servicio.actualizar_producto(1, datos_producto)
        else:
            servicio.registrar_producto(datos_producto)

    conexion.rollback.assert_called_once()
    conexion.commit.assert_not_called()


def test_eliminar_producto_con_historial_devuelve_conflicto(base_simulada):
    conexion, cursor = base_simulada
    cursor.fetchone.side_effect = [{"id": 1}, {"id": 9}]

    with pytest.raises(servicio.ConflictoInventario, match="movimientos registrados"):
        servicio.eliminar_producto(1)

    assert not any(
        llamada.args[0].lstrip().upper().startswith("DELETE")
        for llamada in cursor.execute.call_args_list
    )
    conexion.rollback.assert_called_once()
    conexion.commit.assert_not_called()


def test_eliminar_producto_sin_historial_confirma_cambio(base_simulada):
    conexion, cursor = base_simulada
    cursor.fetchone.side_effect = [{"id": 1}, None]

    resultado = servicio.eliminar_producto(1)

    assert resultado == {"ok": True}
    sql, parametros = cursor.execute.call_args.args
    assert sql.lstrip().upper().startswith("DELETE FROM PRODUCTOS")
    assert parametros == (1,)
    conexion.commit.assert_called_once()
    conexion.rollback.assert_not_called()


@pytest.mark.parametrize("operacion", ["listar_productos", "registrar_producto"])
def test_error_sql_desconocido_se_propaga_y_revierte(
    datos_producto, base_simulada, operacion
):
    conexion, cursor = base_simulada
    error = mysql.connector.Error("Fallo SQL inesperado", errno=9999)
    cursor.execute.side_effect = error

    with pytest.raises(mysql.connector.Error) as captura:
        if operacion == "registrar_producto":
            servicio.registrar_producto(datos_producto)
        else:
            servicio.listar_productos()

    assert captura.value is error
    conexion.rollback.assert_called_once()
    conexion.commit.assert_not_called()


def test_fallo_al_crear_cursor_cierra_conexion(monkeypatch):
    conexion = MagicMock()
    error = mysql.connector.Error("No se pudo crear el cursor")
    conexion.cursor.side_effect = error
    monkeypatch.setattr(servicio, "conectar", lambda: conexion)

    with pytest.raises(mysql.connector.Error) as captura:
        servicio.listar_productos()

    assert captura.value is error
    conexion.cursor.assert_called_once_with(dictionary=True)
    conexion.close.assert_called_once()
    conexion.commit.assert_not_called()


def test_movimiento_rechaza_cantidad_fuera_de_rango(base_simulada):
    conexion, cursor = base_simulada
    cursor.fetchone.return_value = {"stock": 10}

    with pytest.raises(ValueError, match="La cantidad no puede superar"):
        servicio.registrar_movimiento(1, {"tipo": "Entrada", "cantidad": 2147483648})

    assert not any(
        llamada.args[0].lstrip().upper().startswith(("UPDATE", "INSERT"))
        for llamada in cursor.execute.call_args_list
    )
    conexion.rollback.assert_called_once()
    conexion.commit.assert_not_called()


def test_entrada_rechaza_stock_resultante_fuera_de_rango(base_simulada):
    conexion, cursor = base_simulada
    cursor.fetchone.return_value = {"stock": 2147483647}

    with pytest.raises(ValueError, match="El stock no puede superar"):
        servicio.registrar_movimiento(1, {"tipo": "Entrada", "cantidad": 1})

    assert not any(
        llamada.args[0].lstrip().upper().startswith(("UPDATE", "INSERT"))
        for llamada in cursor.execute.call_args_list
    )
    conexion.rollback.assert_called_once()
    conexion.commit.assert_not_called()


def test_fallo_del_historial_revierte_cambio_de_stock(base_simulada):
    conexion, cursor = base_simulada
    cursor.fetchone.return_value = {"stock": 10}

    def ejecutar(sql, parametros):
        if sql.startswith("INSERT INTO movimientos"):
            raise mysql.connector.Error("No se pudo guardar el movimiento")

    cursor.execute.side_effect = ejecutar

    with pytest.raises(mysql.connector.Error, match="guardar el movimiento"):
        servicio.registrar_movimiento(1, {"tipo": "Salida", "cantidad": 4})

    assert cursor.execute.call_args_list[-2].args[1] == (6, 1)
    assert cursor.execute.call_args_list[-1].args[1] == (1, "Salida", 4, 10, 6)
    conexion.rollback.assert_called_once()
    conexion.commit.assert_not_called()
