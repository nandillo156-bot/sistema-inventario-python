"""
main.py
Punto de entrada del programa.
Contiene el menú principal y el ciclo
que controla el sistema de inventario.
"""

from inventario import (
    registrar_producto,
    listar_productos,
    buscar_producto,
    actualizar_producto,
    eliminar_producto,
    entrada_stock,
    salida_stock,
    productos_stock_bajo,
    listar_movimientos,
)


def main():

    while True:

        print("\n===== SISTEMA DE INVENTARIO =====")
        print("1. Registrar producto")
        print("2. Listar productos")
        print("3. Buscar producto")
        print("4. Actualizar producto")
        print("5. Eliminar producto")
        print("6. Entrada de stock")
        print("7. Salida de stock")
        print("8.Productos con stock bajo")
        print("9.Historial de movimientos")
        print("10. Salir")

        opcion = input("Selecciona una opción: ")

        if opcion == "1":
            registrar_producto()

        elif opcion == "2":
            listar_productos()

        elif opcion == "3":
            buscar_producto()

        elif opcion == "4":
            actualizar_producto()

        elif opcion == "5":
            eliminar_producto()

        elif opcion == "6":
            entrada_stock()

        elif opcion == "10":
            print("Saliendo del sistema...")
            break

        elif opcion == "7":
            salida_stock()

        elif opcion == "8":
            productos_stock_bajo()

        elif opcion == "9":
            listar_movimientos()
        else:
            print("Opción no válida, intenta de nuevo.")


if __name__ == "__main__":
    main()