"""Catálogo ficticio y de solo lectura: nunca se conecta al inventario real."""

from copy import deepcopy


_PRODUCTOS = [
    {"id": 1, "nombre": "Cuaderno A5", "descripcion": "Cuaderno de muestra, 80 hojas", "precio": 45.90, "stock": 12, "categoria": "Papelería"},
    {"id": 2, "nombre": "Lámpara de escritorio", "descripcion": "Artículo ficticio para explorar el panel", "precio": 299.00, "stock": 3, "categoria": "Hogar"},
    {"id": 3, "nombre": "Bolígrafo azul", "descripcion": "Ejemplo de producto agotado", "precio": 12.50, "stock": 0, "categoria": "Papelería"},
    {"id": 4, "nombre": "Botella reutilizable", "descripcion": "Catálogo de demostración sin datos reales", "precio": 159.00, "stock": 40, "categoria": "Accesorios"},
]
_MOVIMIENTOS = [
    {"id": 3, "producto_id": 2, "nombre": "Lámpara de escritorio", "tipo": "Salida", "cantidad": 2, "stock_anterior": 5, "stock_actual": 3, "fecha": "2026-10-01 12:30:00"},
    {"id": 2, "producto_id": 2, "nombre": "Lámpara de escritorio", "tipo": "Entrada", "cantidad": 5, "stock_anterior": 0, "stock_actual": 5, "fecha": "2026-10-01 12:00:00"},
    {"id": 1, "producto_id": 1, "nombre": "Cuaderno A5", "tipo": "Entrada", "cantidad": 12, "stock_anterior": 0, "stock_actual": 12, "fecha": "2026-10-01 11:00:00"},
]


def listar_productos():
    return deepcopy(_PRODUCTOS)


def listar_movimientos():
    return deepcopy(_MOVIMIENTOS)


def obtener_producto(producto_id):
    return deepcopy(next((p for p in _PRODUCTOS if p["id"] == producto_id), None))
