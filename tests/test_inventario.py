from unittest.mock import MagicMock

import inventario

def test_buscar_producto_no_encontrado(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso
    cursor_falso.fetchone.return_value = None

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "Teclado"
    )

    inventario.buscar_producto()

    salida = capsys.readouterr()

    assert "Producto no encontrado." in salida.out

    cursor_falso.close.assert_called_once()
    conexion_falsa.close.assert_called_once()

def test_buscar_producto_encontrado(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso

    cursor_falso.fetchone.return_value = (
        1,
        "Teclado",
        "Teclado mecánico",
        850.50,
        10,
        "Periféricos"
    )

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "Teclado"
    )

    inventario.buscar_producto()

    salida = capsys.readouterr()

    assert "ID: 1" in salida.out
    assert "Nombre: Teclado" in salida.out
    assert "Descripción: Teclado mecánico" in salida.out
    assert "Precio: $850.50" in salida.out
    assert "Stock: 10" in salida.out
    assert "Categoría: Periféricos" in salida.out

    cursor_falso.close.assert_called_once()
    conexion_falsa.close.assert_called_once()

    cursor_falso.execute.assert_called_once()

    argumentos = cursor_falso.execute.call_args

    sql_ejecutado = argumentos[0][0]
    valores = argumentos[0][1]

    assert "SELECT" in sql_ejecutado
    assert "FROM productos" in sql_ejecutado
    assert valores == ("Teclado",)

def test_registrar_producto_correctamente(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso

    # Simulamos que el SELECT no encuentra un producto duplicado
    cursor_falso.fetchone.return_value = None

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

    respuestas = iter([
        "Teclado",
        "Teclado mecánico",
        "Periféricos"
    ])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(respuestas)
    )

    monkeypatch.setattr(
        inventario,
        "pedir_precio",
        lambda: 850.50
    )

    monkeypatch.setattr(
        inventario,
        "pedir_stock",
        lambda: 10
    )

    inventario.registrar_producto()

    salida = capsys.readouterr()

    assert "Producto registrado correctamente." in salida.out

    conexion_falsa.commit.assert_called_once()

    cursor_falso.close.assert_called_once()
    conexion_falsa.close.assert_called_once()
    assert cursor_falso.execute.call_count == 2

    segunda_llamada = cursor_falso.execute.call_args_list[1]

    sql_insert = segunda_llamada[0][0]
    valores_insert = segunda_llamada[0][1]

    assert "INSERT INTO productos" in sql_insert

    assert valores_insert == (
    "Teclado",
    "Teclado mecánico",
    850.50,
    10,
    "Periféricos"
    )

def test_registrar_producto_duplicado(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso

    # Simulamos que MySQL encontró un producto existente
    cursor_falso.fetchone.return_value = (1,)

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "Teclado"
    )

    inventario.registrar_producto()

    salida = capsys.readouterr()

    assert "ya existe un producto registrado" in salida.out

    # Solo debe ejecutarse el SELECT
    assert cursor_falso.execute.call_count == 1

    # No debe guardar nada
    conexion_falsa.commit.assert_not_called()

    cursor_falso.close.assert_called_once()
    conexion_falsa.close.assert_called_once()

def test_entrada_stock_correctamente(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso

    # Simulamos que MySQL encuentra el producto
    cursor_falso.fetchone.return_value = (
        1,
        "Teclado",
        "Teclado mecánico",
        850.50,
        10,
        "Periféricos"
    )

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

    respuestas = iter([
        "Teclado",
        "5"
    ])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(respuestas)
    )

    inventario.entrada_stock()

    salida = capsys.readouterr()

    assert "Entrada registrada correctamente." in salida.out

    # SELECT + UPDATE + INSERT movimiento
    assert cursor_falso.execute.call_count == 3

    conexion_falsa.commit.assert_called_once()

    cursor_falso.close.assert_called_once()
    conexion_falsa.close.assert_called_once()

    llamadas = cursor_falso.execute.call_args_list

    llamada_update = llamadas[1]

    sql_update = llamada_update[0][0]
    valores_update = llamada_update[0][1]

    assert "UPDATE productos" in sql_update
    assert valores_update == (15, 1)
    llamada_movimiento = llamadas[2]

    sql_movimiento = llamada_movimiento[0][0]
    valores_movimiento = llamada_movimiento[0][1]

    assert "INSERT INTO movimientos" in sql_movimiento

    assert valores_movimiento == (
    1,
    "Entrada",
    5,
    10,
    15
    )
def test_salida_stock_correctamente(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso

    # Producto con 10 unidades disponibles
    cursor_falso.fetchone.return_value = (
        1,
        "Teclado",
        "Teclado mecánico",
        850.50,
        10,
        "Periféricos"
    )

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

def test_salida_stock_insuficiente_y_luego_valida(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso

    cursor_falso.fetchone.return_value = (
        1,
        "Teclado",
        "Teclado mecánico",
        850.50,
        10,
        "Periféricos"
    )

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

    respuestas = iter([
        "Teclado",
        "15",   # No hay suficiente stock
        "4"     # Cantidad válida
    ])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(respuestas)
    )

    inventario.salida_stock()

    salida = capsys.readouterr()

    assert "Error: no hay suficiente stock" in salida.out
    assert "Salida registrada correctamente." in salida.out

    llamadas = cursor_falso.execute.call_args_list

    assert len(llamadas) == 3

    # UPDATE
    valores_update = llamadas[1][0][1]

    assert valores_update == (6, 1)

    # INSERT del movimiento
    valores_movimiento = llamadas[2][0][1]

    assert valores_movimiento == (
        1,
        "Salida",
        4,
        10,
        6
    )

    conexion_falsa.commit.assert_called_once()
def test_salida_stock_insuficiente_y_luego_valida(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso

    cursor_falso.fetchone.return_value = (
        1,
        "Teclado",
        "Teclado mecánico",
        850.50,
        10,
        "Periféricos"
    )

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

    respuestas = iter([
        "Teclado",
        "15",
        "4"
    ])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(respuestas)
    )

    inventario.salida_stock()

    salida = capsys.readouterr()

    assert "Error: no hay suficiente stock" in salida.out
    assert "Salida registrada correctamente." in salida.out

    llamadas = cursor_falso.execute.call_args_list

    assert len(llamadas) == 3

    assert llamadas[1][0][1] == (6, 1)

    assert llamadas[2][0][1] == (
        1,
        "Salida",
        4,
        10,
        6
    )

    conexion_falsa.commit.assert_called_once()
def test_actualizar_producto_correctamente(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso

    cursor_falso.fetchone.return_value = (
        1,
        "Teclado",
        "Teclado viejo",
        500.00,
        10,
        "Periféricos"
    )

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

    respuestas = iter([
        "Teclado",
        "Teclado mecánico RGB",
        "Gaming"
    ])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(respuestas)
    )

    monkeypatch.setattr(
        inventario,
        "pedir_precio",
        lambda: 950.50
    )

    inventario.actualizar_producto()

    salida = capsys.readouterr()

    assert "Producto actualizado correctamente." in salida.out

    assert cursor_falso.execute.call_count == 2

    llamadas = cursor_falso.execute.call_args_list

    sql_update = llamadas[1][0][0]
    valores_update = llamadas[1][0][1]

    assert "UPDATE productos" in sql_update

    assert valores_update == (
        "Teclado mecánico RGB",
        950.50,
        "Gaming",
        1
    )

    conexion_falsa.commit.assert_called_once()

    cursor_falso.close.assert_called_once()
    conexion_falsa.close.assert_called_once()
def test_actualizar_producto_no_encontrado(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso
    cursor_falso.fetchone.return_value = None

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "Producto inexistente"
    )

    inventario.actualizar_producto()

    salida = capsys.readouterr()

    assert "Producto no encontrado." in salida.out

    assert cursor_falso.execute.call_count == 1

    conexion_falsa.commit.assert_not_called()

    cursor_falso.close.assert_called_once()
    conexion_falsa.close.assert_called_once()

def test_eliminar_producto_correctamente(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso

    cursor_falso.fetchone.return_value = (
        1,
        "Teclado"
    )

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

    respuestas = iter([
        "Teclado",
        "s"
    ])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(respuestas)
    )

    inventario.eliminar_producto()

    salida = capsys.readouterr()

    assert "Producto eliminado correctamente." in salida.out

    assert cursor_falso.execute.call_count == 2

    llamadas = cursor_falso.execute.call_args_list

    sql_delete = llamadas[1][0][0]
    valores_delete = llamadas[1][0][1]

    assert "DELETE FROM productos" in sql_delete
    assert valores_delete == (1,)

    conexion_falsa.commit.assert_called_once()

    cursor_falso.close.assert_called_once()
    conexion_falsa.close.assert_called_once()

def test_eliminar_producto_cancelado(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso

    cursor_falso.fetchone.return_value = (
        1,
        "Teclado"
    )

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

    respuestas = iter([
        "Teclado",
        "n"
    ])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(respuestas)
    )

    inventario.eliminar_producto()

    salida = capsys.readouterr()

    assert "Eliminación cancelada." in salida.out

    # Únicamente SELECT
    assert cursor_falso.execute.call_count == 1

    conexion_falsa.commit.assert_not_called()

    cursor_falso.close.assert_called_once()
    conexion_falsa.close.assert_called_once()

def test_eliminar_producto_no_encontrado(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso
    cursor_falso.fetchone.return_value = None

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "Producto inexistente"
    )

    inventario.eliminar_producto()

    salida = capsys.readouterr()

    assert "Producto no encontrado." in salida.out

    assert cursor_falso.execute.call_count == 1

    conexion_falsa.commit.assert_not_called()

    cursor_falso.close.assert_called_once()
    conexion_falsa.close.assert_called_once()

def test_eliminar_producto_con_movimientos(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso

    cursor_falso.fetchone.return_value = (
        1,
        "Teclado"
    )

    def ejecutar(sql, valores=None):
        if "DELETE FROM productos" in sql:
            raise Exception("Restricción de clave foránea")

    cursor_falso.execute.side_effect = ejecutar

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

    respuestas = iter([
        "Teclado",
        "s"
    ])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(respuestas)
    )

    inventario.eliminar_producto()

    salida = capsys.readouterr()

    assert "tiene movimientos registrados" in salida.out

    conexion_falsa.rollback.assert_called_once()
    conexion_falsa.commit.assert_not_called()

def test_listar_productos(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso

    cursor_falso.fetchall.return_value = [
        (
            1,
            "Teclado",
            "Teclado mecánico",
            850.50,
            10,
            "Periféricos"
        ),
        (
            2,
            "Mouse",
            "Mouse inalámbrico",
            450.00,
            5,
            "Periféricos"
        )
    ]

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

    inventario.listar_productos()

    salida = capsys.readouterr()

    assert "Teclado" in salida.out
    assert "Mouse" in salida.out
    assert "$850.50" in salida.out
    assert "$450.00" in salida.out

    cursor_falso.close.assert_called_once()
    conexion_falsa.close.assert_called_once()

def test_listar_productos_vacio(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso
    cursor_falso.fetchall.return_value = []

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

    inventario.listar_productos()

    salida = capsys.readouterr()

    assert "No hay productos registrados." in salida.out

    cursor_falso.close.assert_called_once()
    conexion_falsa.close.assert_called_once()

def test_productos_stock_bajo(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso

    cursor_falso.fetchall.return_value = [
        (
            1,
            "Mouse",
            "Mouse inalámbrico",
            450.00,
            3,
            "Periféricos"
        )
    ]

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

    inventario.productos_stock_bajo()

    salida = capsys.readouterr()

    assert "PRODUCTOS CON STOCK BAJO" in salida.out
    assert "Mouse" in salida.out
    assert "Stock: 3" in salida.out

    cursor_falso.execute.assert_called_once()

    sql = cursor_falso.execute.call_args[0][0]

    assert "stock <= 5" in sql

    cursor_falso.close.assert_called_once()
    conexion_falsa.close.assert_called_once()

def test_productos_stock_bajo_vacio(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso
    cursor_falso.fetchall.return_value = []

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

    inventario.productos_stock_bajo()

    salida = capsys.readouterr()

    assert "No hay productos con stock bajo." in salida.out

    cursor_falso.close.assert_called_once()
    conexion_falsa.close.assert_called_once()

def test_listar_movimientos(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso

    cursor_falso.fetchall.return_value = [
        (
            1,
            "Teclado",
            "Entrada",
            5,
            10,
            15,
            "2026-10-02 18:00:00"
        )
    ]

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

    inventario.listar_movimientos()

    salida = capsys.readouterr()

    assert "HISTORIAL DE MOVIMIENTOS" in salida.out
    assert "Producto: Teclado" in salida.out
    assert "Tipo: Entrada" in salida.out
    assert "Cantidad: 5" in salida.out
    assert "Stock anterior: 10" in salida.out
    assert "Stock actual: 15" in salida.out

    cursor_falso.close.assert_called_once()
    conexion_falsa.close.assert_called_once()

def test_listar_movimientos_vacio(monkeypatch, capsys):
    cursor_falso = MagicMock()
    conexion_falsa = MagicMock()

    conexion_falsa.cursor.return_value = cursor_falso
    cursor_falso.fetchall.return_value = []

    monkeypatch.setattr(
        inventario,
        "conectar",
        lambda: conexion_falsa
    )

    inventario.listar_movimientos()

    salida = capsys.readouterr()

    assert "No hay movimientos registrados." in salida.out

    cursor_falso.close.assert_called_once()
    conexion_falsa.close.assert_called_once()