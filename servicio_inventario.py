"""Operaciones del inventario compartidas por las interfaces de la aplicación.

Este módulo recibe datos de Python y devuelve resultados de Python. Las rutas
HTTP y los formularios deciden cómo presentar sus resultados y sus errores.
"""

from contextlib import contextmanager

from mysql.connector import IntegrityError

from conexion import conectar
from producto import Producto
from validaciones import STOCK_MAXIMO, validar_stock


class ProductoNoEncontrado(LookupError):
    """El producto solicitado no existe."""


class ConflictoInventario(ValueError):
    """La operación entra en conflicto con un nombre o un historial existente."""


@contextmanager
def _sesion():
    """Cierra ambos recursos y revierte cualquier operación que falle."""
    conexion = conectar()
    cursor = None
    try:
        cursor = conexion.cursor(dictionary=True)
        yield conexion, cursor
    except Exception as error:
        conexion.rollback()
        # La restricción SQL también protege contra solicitudes simultáneas;
        # comprobar duplicados antes del INSERT no basta para evitar esa carrera.
        if isinstance(error, IntegrityError):
            if error.errno == 1062:
                raise ConflictoInventario("Ya existe un producto con ese nombre.") from error
            if error.errno == 1451:
                raise ConflictoInventario(
                    "Este producto tiene movimientos registrados y no se puede eliminar."
                ) from error
        raise
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            # También se ejecuta si crear o cerrar el cursor falla.
            conexion.close()


def _validar_datos(datos, campos):
    if not isinstance(datos, dict):
        raise ValueError("Se requiere un objeto con los datos de la operación.")
    if any(campo not in datos for campo in campos):
        raise ValueError("Completa todos los campos requeridos.")


def _entero(valor, mensaje):
    """Acepta enteros o su representación en texto, sin truncar fracciones."""
    try:
        if isinstance(valor, bool):
            raise ValueError(mensaje)
        numero = int(valor)
        if str(valor).strip() != str(numero):
            raise ValueError(mensaje)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(mensaje) from None
    return numero


def _producto_con_stock(datos, stock):
    _validar_datos(datos, ("nombre", "descripcion", "precio", "categoria"))
    precio = datos["precio"]
    if isinstance(precio, str):
        try:
            precio = float(precio)
        except (ValueError, OverflowError):
            raise ValueError("El precio debe ser un número válido.") from None
    return Producto(
        None,
        datos["nombre"],
        datos["descripcion"],
        precio,
        stock,
        datos["categoria"],
    )


def producto_validado(datos):
    """Construye un producto de alta usando las reglas compartidas del modelo."""
    _validar_datos(datos, ("stock",))
    stock = _entero(datos["stock"], "El stock debe ser un entero.")
    return _producto_con_stock(datos, stock)


def listar_productos():
    with _sesion() as (_, cursor):
        cursor.execute(
            "SELECT id,nombre,descripcion,precio,stock,categoria "
            "FROM productos ORDER BY id DESC"
        )
        return cursor.fetchall()


def listar_movimientos():
    with _sesion() as (_, cursor):
        cursor.execute(
            "SELECT m.*,p.nombre AS nombre FROM movimientos m "
            "JOIN productos p ON p.id=m.producto_id "
            "ORDER BY m.id DESC LIMIT 200"
        )
        return cursor.fetchall()


def obtener_producto(producto_id):
    with _sesion() as (_, cursor):
        cursor.execute(
            "SELECT id,nombre,descripcion,precio,stock,categoria "
            "FROM productos WHERE id=%s",
            (producto_id,),
        )
        producto = cursor.fetchone()
        if producto is None:
            raise ProductoNoEncontrado("Producto no encontrado.")
        return producto


def registrar_producto(datos):
    with _sesion() as (conexion, cursor):
        producto = producto_validado(datos)
        cursor.execute(
            "SELECT id FROM productos WHERE LOWER(nombre)=LOWER(%s)",
            (producto.nombre,),
        )
        if cursor.fetchone():
            raise ConflictoInventario("Ya existe un producto con ese nombre.")
        cursor.execute(
            "INSERT INTO productos (nombre,descripcion,precio,stock,categoria) "
            "VALUES (%s,%s,%s,%s,%s)",
            (
                producto.nombre,
                producto.descripcion,
                producto.precio,
                producto.stock,
                producto.categoria,
            ),
        )
        producto_id = cursor.lastrowid
        conexion.commit()
        return {"id": producto_id}


def actualizar_producto(producto_id, datos):
    with _sesion() as (conexion, cursor):
        cursor.execute(
            "SELECT stock FROM productos WHERE id=%s FOR UPDATE", (producto_id,)
        )
        actual = cursor.fetchone()
        if actual is None:
            raise ProductoNoEncontrado("Producto no encontrado.")
        # El stock recibido se ignora; únicamente los movimientos lo modifican.
        producto = _producto_con_stock(datos, actual["stock"])
        cursor.execute(
            "SELECT id FROM productos WHERE LOWER(nombre)=LOWER(%s) AND id<>%s",
            (producto.nombre, producto_id),
        )
        if cursor.fetchone():
            raise ConflictoInventario("Ya existe un producto con ese nombre.")
        cursor.execute(
            "UPDATE productos SET nombre=%s,descripcion=%s,precio=%s,categoria=%s "
            "WHERE id=%s",
            (
                producto.nombre,
                producto.descripcion,
                producto.precio,
                producto.categoria,
                producto_id,
            ),
        )
        conexion.commit()
        return {"id": producto_id}


def eliminar_producto(producto_id):
    with _sesion() as (conexion, cursor):
        cursor.execute(
            "SELECT id FROM productos WHERE id=%s FOR UPDATE", (producto_id,)
        )
        if cursor.fetchone() is None:
            raise ProductoNoEncontrado("Producto no encontrado.")
        cursor.execute(
            "SELECT id FROM movimientos WHERE producto_id=%s LIMIT 1", (producto_id,)
        )
        if cursor.fetchone():
            raise ConflictoInventario(
                "Este producto tiene movimientos registrados y no se puede eliminar."
            )
        cursor.execute("DELETE FROM productos WHERE id=%s", (producto_id,))
        conexion.commit()
        return {"ok": True}


def registrar_movimiento(producto_id, datos):
    with _sesion() as (conexion, cursor):
        _validar_datos(datos, ("cantidad", "tipo"))
        mensaje = "La cantidad debe ser un entero mayor que cero."
        cantidad = _entero(datos["cantidad"], mensaje)
        if cantidad <= 0:
            raise ValueError(mensaje)
        if cantidad > STOCK_MAXIMO:
            raise ValueError(f"La cantidad no puede superar {STOCK_MAXIMO}.")
        tipo = datos["tipo"]
        if tipo not in ("Entrada", "Salida"):
            raise ValueError("Tipo de movimiento inválido.")

        cursor.execute(
            "SELECT stock FROM productos WHERE id=%s FOR UPDATE", (producto_id,)
        )
        producto = cursor.fetchone()
        if producto is None:
            raise ProductoNoEncontrado("Producto no encontrado.")
        anterior = producto["stock"]
        actual = anterior + cantidad if tipo == "Entrada" else anterior - cantidad
        if actual < 0:
            raise ValueError("No hay suficiente stock disponible.")
        validar_stock(actual)
        cursor.execute(
            "UPDATE productos SET stock=%s WHERE id=%s", (actual, producto_id)
        )
        cursor.execute(
            "INSERT INTO movimientos "
            "(producto_id,tipo,cantidad,stock_anterior,stock_actual) "
            "VALUES (%s,%s,%s,%s,%s)",
            (producto_id, tipo, cantidad, anterior, actual),
        )
        conexion.commit()
        return {"stock": actual}
