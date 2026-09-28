from conexion import conectar


try:
    conexion = conectar()

    if conexion.is_connected():
        print("Conexión exitosa con MySQL")

except Exception as e:
    print(f"Error de conexión: {e}")

finally:
    if 'conexion' in locals() and conexion.is_connected():
        conexion.close()