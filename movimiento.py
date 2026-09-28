class Movimiento:
    def __init__(self, producto, tipo, cantidad, stock_anterior, stock_actual):
        self.producto = producto
        self.tipo = tipo
        self.cantidad = cantidad
        self.stock_anterior = stock_anterior
        self.stock_actual = stock_actual
 
    def mostrar(self):
        print("\n===== MOVIMIENTO DE STOCK =====")
        print(f"Producto: {self.producto.nombre}")
        print(f"Tipo: {self.tipo}")
        print(f"Cantidad: {self.cantidad}")
        print(f"Stock anterior: {self.stock_anterior}")
        print(f"Stock actual: {self.stock_actual}")
 