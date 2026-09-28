def pedir_precio():
    while True:
        try:
            precio = float(input("Precio: $"))

            if precio <= 0:
                print("Error: el precio debe ser mayor que 0.")
                continue

            return precio

        except ValueError:
            print("Error: ingresa un número válido.")


def pedir_stock():
    while True:
        try:
            stock = int(input("Stock: "))

            if stock < 0:
                print("Error: el stock no puede ser negativo.")
                continue

            return stock

        except ValueError:
            print("Error: ingresa un número entero válido.")