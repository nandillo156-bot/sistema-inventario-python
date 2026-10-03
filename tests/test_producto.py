import pytest

from producto import Producto

def test_crear_producto_valido():
    producto = Producto(
        1,
        "Teclado",
        "Teclado mecánico",
        850.50,
        10,
        "Periféricos"
    )

    assert producto.id == 1
    assert producto.nombre == "Teclado"
    assert producto.descripcion == "Teclado mecánico"
    assert producto.precio == 850.50
    assert producto.stock == 10
    assert producto.categoria == "Periféricos"

def test_producto_precio_cero():
    with pytest.raises(
        ValueError,
        match="El precio debe ser mayor que 0."
    ):
        Producto(
            1,
            "Mouse",
            "Mouse inalámbrico",
            0,
            10,
            "Periféricos"
        )

def test_producto_stock_negativo():
    with pytest.raises(
        ValueError,
        match="El stock no puede ser negativo."
    ):
        Producto(
            1,
            "Monitor",
            "Monitor de 24 pulgadas",
            2500,
            -1,
            "Monitores"
        )

def test_producto_nombre_vacio():
    with pytest.raises(
        ValueError,
        match="El nombre no puede estar vacío."
    ):
        Producto(
            1,
            "   ",
            "Mouse inalámbrico",
            500,
            10,
            "Periféricos"
        )

def test_producto_descripcion_vacia():
    with pytest.raises(
        ValueError,
        match="La descripción no puede estar vacía."
    ):
        Producto(
            1,
            "Teclado",
            "   ",
            850,
            10,
            "Periféricos"
        )

def test_producto_categoria_vacia():
    with pytest.raises(
        ValueError,
        match="La categoría no puede estar vacía."
    ):
        Producto(
            1,
            "Monitor",
            "Monitor de 24 pulgadas",
            2500,
            5,
            "   "
        )

def test_mostrar_producto(capsys):
    producto = Producto(
        1,
        "Teclado",
        "Teclado mecánico",
        850.50,
        10,
        "Periféricos"
    )

    producto.mostrar()

    salida = capsys.readouterr()

    assert "ID: 1" in salida.out
    assert "Nombre: Teclado" in salida.out
    assert "Descripción: Teclado mecánico" in salida.out
    assert "Precio: $850.50" in salida.out
    assert "Stock: 10" in salida.out
    assert "Categoría: Periféricos" in salida.out