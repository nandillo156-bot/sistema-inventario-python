# Sistema de Inventario

Programa de consola en Python para gestionar un inventario de productos:
registrar, listar, buscar, actualizar, eliminar y controlar entradas/salidas
de stock.

## Estructura del proyecto


├── main.py         # Punto de entrada: menú principal y ciclo de control
├── producto.py     # Clase Producto y funciones de entrada validada (precio, stock)
├── inventario.py   # Funciones que operan sobre la lista de productos
└── README.md


### producto.py
- *pedir_precio()*: pide un precio por teclado, valida que sea numérico y mayor a 0.
- *pedir_stock()*: pide un stock por teclado, valida que sea entero y no negativo.
- *Producto*: clase con atributos nombre, descripcion, precio, stock,
  categoria y el método mostrar() para imprimir la información formateada.

### inventario.py
Funciones que reciben la lista productos y operan sobre ella:

| Función | Descripción |
|---|---|
| registrar_producto(productos) | Pide datos y agrega un nuevo Producto a la lista |
| listar_productos(productos) | Muestra todos los productos registrados |
| buscar_producto(productos) | Busca por coincidencia parcial del nombre |
| actualizar_producto(productos) | Modifica descripción, precio, stock y categoría |
| eliminar_producto(productos) | Elimina un producto de la lista por nombre |
| entrada_stock(productos) | Suma unidades al stock de un producto |
| salida_stock(productos) | Resta unidades, validando que no quede negativo |
| productos_stock_bajo(productos) | Muestra productos con stock ≤ 5 |

### main.py
Importa las funciones de inventario.py y ejecuta el menú principal dentro
de un ciclo while True, delegando cada opción a la función correspondiente.

## Cómo ejecutar

bash
python main.py


Asegúrate de que los tres archivos .py estén en la misma carpeta, ya que
main.py depende de inventario.py, y este a su vez de producto.py.