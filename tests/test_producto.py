from decimal import Decimal

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


@pytest.mark.parametrize("precio", [0.001, 0.009, Decimal("0.001"), Decimal("0.009")])
def test_producto_rechaza_precio_menor_a_un_centavo(precio):
    with pytest.raises(ValueError, match="El precio mínimo es 0[.]01[.]"):
        Producto(1, "Teclado", "Teclado mecánico", precio, 1, "Periféricos")


@pytest.mark.parametrize("precio", [0.01, Decimal("0.01")])
def test_producto_acepta_un_centavo_sin_convertir_el_precio(precio):
    producto = Producto(1, "Teclado", "Teclado mecánico", precio, 1, "Periféricos")

    assert producto.precio is precio


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


@pytest.mark.parametrize("precio", [25, 25.50, Decimal("25.50")])
def test_producto_conserva_tipo_y_valor_del_precio(precio):
    producto = Producto(1, "Teclado", "Teclado mecánico", precio, 0, "Periféricos")

    assert producto.precio is precio
    assert producto.stock == 0


@pytest.mark.parametrize(
    "precio",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        Decimal("NaN"),
        Decimal("sNaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
    ],
)
def test_producto_rechaza_precio_no_finito(precio):
    with pytest.raises(ValueError, match="El precio debe ser un número finito"):
        Producto(1, "Teclado", "Teclado mecánico", precio, 1, "Periféricos")


@pytest.mark.parametrize("precio", [True, False, None, "25.50", 1 + 2j, []])
def test_producto_rechaza_tipo_de_precio_invalido(precio):
    with pytest.raises(ValueError, match="El precio debe ser un número válido"):
        Producto(1, "Teclado", "Teclado mecánico", precio, 1, "Periféricos")


@pytest.mark.parametrize(
    "stock", [True, False, 1.5, 1.0, "10", None, Decimal("10"), float("nan")]
)
def test_producto_rechaza_stock_que_no_es_entero(stock):
    with pytest.raises(ValueError, match="El stock debe ser un número entero"):
        Producto(1, "Teclado", "Teclado mecánico", 25, stock, "Periféricos")


@pytest.mark.parametrize("campo", ["nombre", "descripcion", "categoria"])
@pytest.mark.parametrize("valor", [None, 123, False, ["texto"]])
def test_producto_rechaza_tipo_de_texto_invalido(campo, valor):
    datos = {
        "id": 1,
        "nombre": "Teclado",
        "descripcion": "Teclado mecánico",
        "precio": 25,
        "stock": 1,
        "categoria": "Periféricos",
    }
    datos[campo] = valor

    with pytest.raises(ValueError, match="debe ser texto"):
        Producto(**datos)


def test_producto_recorta_espacios_en_los_extremos_del_texto():
    producto = Producto(
        1, "  Teclado  ", "\tTeclado  mecánico\n", 25, 1, "  Periféricos  "
    )

    assert producto.nombre == "Teclado"
    assert producto.descripcion == "Teclado  mecánico"
    assert producto.categoria == "Periféricos"


@pytest.mark.parametrize("campo", ["nombre", "categoria"])
@pytest.mark.parametrize("longitud", [255, 256])
def test_producto_limita_textos_al_tamano_de_la_base_de_datos(campo, longitud):
    datos = {
        "id": 1,
        "nombre": "Teclado",
        "descripcion": "Teclado mecánico",
        "precio": 25,
        "stock": 1,
        "categoria": "Periféricos",
    }
    datos[campo] = f"  {'á' * longitud}  "

    if longitud == 256:
        with pytest.raises(ValueError, match="no puede superar 255 caracteres"):
            Producto(**datos)
    else:
        producto = Producto(**datos)
        assert getattr(producto, campo) == "á" * longitud


def test_producto_acepta_limites_numericos_de_la_base_de_datos():
    producto = Producto(
        1, "Teclado", "Teclado mecánico", Decimal("99999999.99"), 2147483647, "Periféricos"
    )

    assert producto.precio == Decimal("99999999.99")
    assert producto.stock == 2147483647


@pytest.mark.parametrize("precio", [100000000, Decimal("100000000.00"), 10**400])
def test_producto_rechaza_precio_fuera_del_rango_de_la_base_de_datos(precio):
    with pytest.raises(ValueError, match="El precio no puede superar 99999999.99"):
        Producto(1, "Teclado", "Teclado mecánico", precio, 1, "Periféricos")


def test_producto_rechaza_stock_fuera_del_rango_de_la_base_de_datos():
    with pytest.raises(ValueError, match="El stock no puede superar 2147483647"):
        Producto(1, "Teclado", "Teclado mecánico", 25, 2147483648, "Periféricos")
