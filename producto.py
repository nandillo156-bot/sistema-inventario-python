class Producto:
    def __init__(self, id, nombre, descripcion, precio, stock, categoria):
        if not nombre.strip():
            raise ValueError("El nombre no puede estar vacío.")
 
        if not descripcion.strip():
            raise ValueError("La descripción no puede estar vacía.")
 
        if precio <= 0:
            raise ValueError("El precio debe ser mayor que 0.")
 
        if stock < 0:
            raise ValueError("El stock no puede ser negativo.")
 
        if not categoria.strip():
            raise ValueError("La categoría no puede estar vacía.")
 
        self.id = id
        self.nombre = nombre
        self.descripcion = descripcion
        self.precio = precio
        self.stock = stock
        self.categoria = categoria
 
    def mostrar(self):
        print("\n===== PRODUCTO REGISTRADO =====")
        print(f"ID: {self.id}")
        print(f"Nombre: {self.nombre}")
        print(f"Descripción: {self.descripcion}")
        print(f"Precio: ${self.precio:.2f}")
        print(f"Stock: {self.stock}")
        print(f"Categoría: {self.categoria}")
 