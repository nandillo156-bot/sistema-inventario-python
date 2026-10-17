from decimal import Decimal
from math import isfinite


# Estos límites coinciden con DECIMAL(10,2) e INT de la base de datos.
PRECIO_MAXIMO = Decimal("99999999.99")
STOCK_MAXIMO = 2147483647


def validar_precio(precio):
    """Valida el precio sin convertir ni redondear el valor recibido."""
    if isinstance(precio, bool) or not isinstance(precio, (int, float, Decimal)):
        raise ValueError("El precio debe ser un número válido.")

    # NaN no es menor ni mayor que cero; por eso se comprueba por separado.
    if isinstance(precio, Decimal):
        es_finito = precio.is_finite()
    else:
        es_finito = not isinstance(precio, float) or isfinite(precio)

    if not es_finito:
        raise ValueError("El precio debe ser un número finito.")

    if precio <= 0:
        raise ValueError("El precio debe ser mayor que 0.")

    if precio < Decimal("0.01"):
        raise ValueError("El precio mínimo es 0.01.")

    if precio > PRECIO_MAXIMO:
        raise ValueError("El precio no puede superar 99999999.99.")


def validar_stock(stock):
    """Exige unidades enteras dentro del rango que puede guardar MySQL."""
    # bool hereda de int en Python, pero True no representa una cantidad.
    if isinstance(stock, bool) or not isinstance(stock, int):
        raise ValueError("El stock debe ser un número entero.")

    if stock < 0:
        raise ValueError("El stock no puede ser negativo.")

    if stock > STOCK_MAXIMO:
        raise ValueError("El stock no puede superar 2147483647.")


def pedir_precio():
    while True:
        try:
            precio = float(input("Precio: $"))

        except ValueError:
            print("Error: ingresa un número válido.")
            continue

        try:
            validar_precio(precio)
        except ValueError as error:
            print(f"Error: {str(error).lower()}")
            continue

        return precio


def pedir_stock():
    while True:
        try:
            stock = int(input("Stock: "))

        except ValueError:
            print("Error: ingresa un número entero válido.")
            continue

        try:
            validar_stock(stock)
        except ValueError as error:
            print(f"Error: {str(error).lower()}")
            continue

        return stock
