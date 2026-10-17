from validaciones import validar_precio, validar_stock


def _validar_texto(valor, campo, mensaje_vacio, limite=None):
    if not isinstance(valor, str):
        raise ValueError(f"{campo} debe ser texto.")

    valor = valor.strip()
    if not valor:
        raise ValueError(mensaje_vacio)

    if limite is not None and len(valor) > limite:
        raise ValueError(f"{campo} no puede superar {limite} caracteres.")

    return valor


class Producto:
    def __init__(self, id, nombre, descripcion, precio, stock, categoria):
        nombre = _validar_texto(
            nombre, "El nombre", "El nombre no puede estar vacío.", limite=255
        )
        descripcion = _validar_texto(
            descripcion, "La descripción", "La descripción no puede estar vacía."
        )
        validar_precio(precio)
        validar_stock(stock)
        categoria = _validar_texto(
            categoria,
            "La categoría",
            "La categoría no puede estar vacía.",
            limite=255,
        )

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
