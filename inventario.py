"""
inventario.py
Contiene todas las funciones que operan sobre los productos
almacenados en MySQL.
"""

from producto import Producto
from movimiento import Movimiento
from validaciones import pedir_precio, pedir_stock
from conexion import conectar


def registrar_producto():
    nombre = input("Nombre: ")

    conexion = conectar()
    cursor = conexion.cursor()

    # Comprobar si ya existe
    sql = "SELECT id FROM productos WHERE LOWER(nombre) = LOWER(%s)"
    cursor.execute(sql, (nombre,))
    producto_existente = cursor.fetchone()

    if producto_existente:
        print(f"Error: ya existe un producto registrado con el nombre '{nombre}'.")
        cursor.close()
        conexion.close()
        return

    descripcion = input("Descripción: ")
    precio = pedir_precio()
    stock = pedir_stock()
    categoria = input("Categoría: ")

    try:
        # Validamos los datos utilizando nuestra clase Producto
        producto = Producto(
            None,
            nombre,
            descripcion,
            precio,
            stock,
            categoria
        )

        sql = """
            INSERT INTO productos
            (nombre, descripcion, precio, stock, categoria)
            VALUES (%s, %s, %s, %s, %s)
        """

        valores = (
            producto.nombre,
            producto.descripcion,
            producto.precio,
            producto.stock,
            producto.categoria
        )

        cursor.execute(sql, valores)
        conexion.commit()

        print("Producto registrado correctamente.")

    except ValueError as e:
        print(f"Error: {e}")

    finally:
        cursor.close()
        conexion.close()


def listar_productos():
    conexion = conectar()
    cursor = conexion.cursor()

    print("\n===== LISTA DE PRODUCTOS =====")

    sql = """
        SELECT id, nombre, descripcion, precio, stock, categoria
        FROM productos
        ORDER BY id
    """

    cursor.execute(sql)
    productos = cursor.fetchall()

    if not productos:
        print("No hay productos registrados.")
        cursor.close()
        conexion.close()
        return

    for datos in productos:
        producto = Producto(
            datos[0],
            datos[1],
            datos[2],
            float(datos[3]),
            datos[4],
            datos[5]
        )

        producto.mostrar()

    cursor.close()
    conexion.close()


def buscar_producto():
    buscado = input("Nombre del producto a buscar: ")

    conexion = conectar()
    cursor = conexion.cursor()

    sql = """
        SELECT id, nombre, descripcion, precio, stock, categoria
        FROM productos
        WHERE LOWER(nombre) = LOWER(%s)
    """

    cursor.execute(sql, (buscado,))
    datos = cursor.fetchone()

    if datos:
        producto = Producto(
            datos[0],
            datos[1],
            datos[2],
            float(datos[3]),
            datos[4],
            datos[5]
        )

        producto.mostrar()
    else:
        print("Producto no encontrado.")

    cursor.close()
    conexion.close()

def actualizar_producto():
    buscado = input("Nombre del producto a actualizar: ")

    conexion = conectar()
    cursor = conexion.cursor()

    sql = """
        SELECT id, nombre, descripcion, precio, stock, categoria
        FROM productos
        WHERE LOWER(nombre) = LOWER(%s)
    """

    cursor.execute(sql, (buscado,))
    datos = cursor.fetchone()

    if not datos:
        print("Producto no encontrado.")
        cursor.close()
        conexion.close()
        return

    producto = Producto(
        datos[0],
        datos[1],
        datos[2],
        float(datos[3]),
        datos[4],
        datos[5]
    )

    print(f"\nProducto encontrado: {producto.nombre}")
    print(f"Stock actual: {producto.stock}")

    nueva_descripcion = input("Nueva descripción: ")
    nuevo_precio = pedir_precio()
    nueva_categoria = input("Nueva categoría: ")

    sql = """
        UPDATE productos
        SET descripcion = %s,
            precio = %s,
            categoria = %s
        WHERE id = %s
    """

    valores = (
        nueva_descripcion,
        nuevo_precio,
        nueva_categoria,
        producto.id
    )

    cursor.execute(sql, valores)
    conexion.commit()

    producto.descripcion = nueva_descripcion
    producto.precio = nuevo_precio
    producto.categoria = nueva_categoria

    print("\nProducto actualizado correctamente.")
    producto.mostrar()

    cursor.close()
    conexion.close()


def eliminar_producto():
    buscado = input("Nombre del producto a eliminar: ")

    conexion = conectar()
    cursor = conexion.cursor()

    sql = """
        SELECT id, nombre
        FROM productos
        WHERE LOWER(nombre) = LOWER(%s)
    """

    cursor.execute(sql, (buscado,))
    datos = cursor.fetchone()

    if not datos:
        print("Producto no encontrado.")
        cursor.close()
        conexion.close()
        return

    producto_id = datos[0]
    nombre = datos[1]

    confirmar = input(
        f"¿Seguro que quieres eliminar '{nombre}'? (s/n): "
    )

    if confirmar.lower() != "s":
        print("Eliminación cancelada.")
        cursor.close()
        conexion.close()
        return

    try:
        sql = "DELETE FROM productos WHERE id = %s"

        cursor.execute(sql, (producto_id,))
        conexion.commit()

        print("Producto eliminado correctamente.")

    except Exception:
        conexion.rollback()

        print(
            "\nNo se puede eliminar este producto porque "
            "tiene movimientos registrados."
        )

    cursor.close()
    conexion.close()    

def entrada_stock():
    buscado = input("Nombre del producto: ")

    conexion = conectar()
    cursor = conexion.cursor()

    sql = """
        SELECT id, nombre, descripcion, precio, stock, categoria
        FROM productos
        WHERE LOWER(nombre) = LOWER(%s)
    """

    cursor.execute(sql, (buscado,))
    datos = cursor.fetchone()

    if not datos:
        print("Producto no encontrado.")
        cursor.close()
        conexion.close()
        return

    producto = Producto(
        datos[0],
        datos[1],
        datos[2],
        float(datos[3]),
        datos[4],
        datos[5]
    )

    while True:
        try:
            cantidad = int(input("Cantidad a ingresar: "))

            if cantidad <= 0:
                print("Error: la cantidad debe ser mayor que 0.")
                continue

            break

        except ValueError:
            print("Error: ingresa un número entero válido.")

    stock_anterior = producto.stock
    stock_actual = stock_anterior + cantidad

    sql = """
        UPDATE productos
        SET stock = %s
        WHERE id = %s
    """

    cursor.execute(sql, (stock_actual, producto.id))

    sql = """
        INSERT INTO movimientos
        (producto_id, tipo, cantidad, stock_anterior, stock_actual)
        VALUES (%s, %s, %s, %s, %s)
    """

    valores = (
        producto.id,
        "Entrada",
        cantidad,
        stock_anterior,
        stock_actual
    )

    cursor.execute(sql, valores)

    conexion.commit()

    producto.stock = stock_actual

    movimiento = Movimiento(
        producto,
        "Entrada",
        cantidad,
        stock_anterior,
        stock_actual
    )

    print("\nEntrada registrada correctamente.")
    movimiento.mostrar()

    cursor.close()
    conexion.close()

def salida_stock():
    buscado = input("Nombre del producto: ")

    conexion = conectar()
    cursor = conexion.cursor()

    sql = """
        SELECT id, nombre, descripcion, precio, stock, categoria
        FROM productos
        WHERE LOWER(nombre) = LOWER(%s)
    """

    cursor.execute(sql, (buscado,))
    datos = cursor.fetchone()

    if not datos:
        print("Producto no encontrado.")
        cursor.close()
        conexion.close()
        return

    producto = Producto(
        datos[0],
        datos[1],
        datos[2],
        float(datos[3]),
        datos[4],
        datos[5]
    )

    while True:
        try:
            cantidad = int(input("Cantidad a retirar: "))

            if cantidad <= 0:
                print("Error: la cantidad debe ser mayor que 0.")
                continue

            if cantidad > producto.stock:
                print(
                    f"Error: no hay suficiente stock "
                    f"(disponible: {producto.stock})."
                )
                continue

            break

        except ValueError:
            print("Error: ingresa un número entero válido.")

    stock_anterior = producto.stock
    stock_actual = stock_anterior - cantidad

    sql = """
        UPDATE productos
        SET stock = %s
        WHERE id = %s
    """

    cursor.execute(sql, (stock_actual, producto.id))

    sql = """
        INSERT INTO movimientos
        (producto_id, tipo, cantidad, stock_anterior, stock_actual)
        VALUES (%s, %s, %s, %s, %s)
    """

    valores = (
        producto.id,
        "Salida",
        cantidad,
        stock_anterior,
        stock_actual
    )

    cursor.execute(sql, valores)

    conexion.commit()

    producto.stock = stock_actual

    movimiento = Movimiento(
        producto,
        "Salida",
        cantidad,
        stock_anterior,
        stock_actual
    )

    print("\nSalida registrada correctamente.")
    movimiento.mostrar()

    cursor.close()
    conexion.close()

def productos_stock_bajo():
    conexion = conectar()
    cursor = conexion.cursor()

    sql = """
        SELECT id, nombre, descripcion, precio, stock, categoria
        FROM productos
        WHERE stock <= 5
        ORDER BY stock ASC
    """

    cursor.execute(sql)
    productos = cursor.fetchall()

    print("\n===== PRODUCTOS CON STOCK BAJO =====")

    if not productos:
        print("No hay productos con stock bajo.")
        cursor.close()
        conexion.close()
        return

    for datos in productos:
        producto = Producto(
            datos[0],
            datos[1],
            datos[2],
            float(datos[3]),
            datos[4],
            datos[5]
        )

        producto.mostrar()

    cursor.close()
    conexion.close()

def listar_movimientos():
    conexion = conectar()
    cursor = conexion.cursor()

    sql = """
        SELECT
            m.id,
            p.nombre,
            m.tipo,
            m.cantidad,
            m.stock_anterior,
            m.stock_actual,
            m.fecha
        FROM movimientos m
        JOIN productos p ON p.id = m.producto_id
        ORDER BY m.id
    """

    cursor.execute(sql)
    movimientos = cursor.fetchall()

    print("\n===== HISTORIAL DE MOVIMIENTOS =====")

    if not movimientos:
        print("No hay movimientos registrados.")
        cursor.close()
        conexion.close()
        return

    for movimiento in movimientos:
        print("\n------------------------------")
        print(f"ID movimiento: {movimiento[0]}")
        print(f"Producto: {movimiento[1]}")
        print(f"Tipo: {movimiento[2]}")
        print(f"Cantidad: {movimiento[3]}")
        print(f"Stock anterior: {movimiento[4]}")
        print(f"Stock actual: {movimiento[5]}")
        print(f"Fecha: {movimiento[6]}")

    cursor.close()
    conexion.close()