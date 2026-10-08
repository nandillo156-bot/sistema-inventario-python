# Sistema de Inventario con Python y MySQL

Aplicación de consola para administrar productos, controlar existencias y consultar movimientos de mercancía almacenados en MySQL.

## Funcionalidades

| Opción | Función | Comportamiento |
| --- | --- | --- |
| 1 | Registrar producto | Guarda nombre, descripción, precio, stock y categoría. Rechaza nombres ya registrados sin distinguir mayúsculas de minúsculas. |
| 2 | Listar productos | Muestra los productos ordenados por ID. |
| 3 | Buscar producto | Busca por nombre completo sin distinguir mayúsculas de minúsculas. |
| 4 | Actualizar producto | Modifica descripción, precio y categoría de un producto existente. |
| 5 | Eliminar producto | Solicita confirmación. La restricción de clave foránea impide eliminar productos con movimientos registrados. |
| 6 | Entrada de stock | Suma existencias y registra la entrada en el historial. |
| 7 | Salida de stock | Resta existencias y registra la salida; rechaza cantidades superiores al stock disponible. |
| 8 | Productos con stock bajo | Muestra productos con stock menor o igual a 5, ordenados por stock ascendente. |
| 9 | Historial de movimientos | Muestra producto, tipo, cantidad, stock anterior, stock actual y fecha, ordenados por ID del movimiento. |
| 10 | Salir | Finaliza el programa. |

Al registrar un producto, su nombre, descripción y categoría no pueden estar vacíos. El precio debe ser mayor que cero y el stock debe ser un entero no negativo. Las entradas y salidas requieren cantidades enteras mayores que cero. El stock se modifica mediante las opciones de entrada y salida.

## Tecnologías y requisitos

- Python 3.14, según `Pipfile`.
- MySQL 8 (el entorno en la nube se validó con MySQL 8.4).
- Pipenv para gestionar las dependencias de `Pipfile.lock`.
- `mysql-connector-python` para acceder a MySQL y `python-dotenv` para cargar `.env`.
- `pytest` y `pytest-cov` para pruebas y cobertura.

## Estructura del proyecto

```text
sistema-inventario-python/
├── database/
│   └── inventario.sql
├── tests/
│   ├── test_inventario.py
│   ├── test_producto.py
│   └── test_validaciones.py
├── .env.example
├── .gitignore
├── Pipfile
├── Pipfile.lock
├── pytest.ini
├── Readme.md
├── conexion.py
├── inventario.py
├── main.py
├── movimiento.py
├── producto.py
├── prueba_mysql.py
└── validaciones.py
```

## Instalación local

### 1. Obtener el repositorio

```bash
git clone https://github.com/nandillo156-bot/sistema-inventario-python.git
cd sistema-inventario-python
```

### 2. Instalar las dependencias

Con Python 3.14 y Pipenv instalados, usa las versiones del archivo de bloqueo:

```bash
pipenv sync --dev
```

### 3. Preparar MySQL

Inicia MySQL y crea la base de datos y las tablas descritas en la sección «Base de datos». El archivo `database/inventario.sql` está vacío actualmente: ejecutarlo no crea el esquema. Para una instalación local, debes preparar ese esquema antes de usar las funciones del inventario.

### 4. Configurar la conexión

Crea un archivo `.env` en la raíz del proyecto con los siguientes campos y los datos de tu instancia de MySQL:

```dotenv
DB_HOST=127.0.0.1
DB_USER=tu_usuario
DB_PASSWORD=tu_clave
DB_DATABASE=inventario
```

`conexion.py` carga estas variables mediante `python-dotenv`. Sustituye los valores de ejemplo por tu configuración. `.env` está excluido de Git; no publiques credenciales.

### 5. Ejecutar la aplicación

```bash
pipenv run python main.py
```

Selecciona una opción del menú y responde a las preguntas de la consola.

## Entorno en la nube preparado

En el entorno configurado durante el onboarding, el checkout está en `/workspace/sistema-inventario-python`. Ya dispone de Python 3.14.7 y un entorno virtual `.venv` con las dependencias de `Pipfile.lock` verificadas por hash. Desde ese directorio:

```bash
# Iniciar MySQL y verificar la conexión y las tablas
.venv/bin/python /workspace/.onboarding/inventario/start.py

# Abrir el menú interactivo
.venv/bin/python main.py

# Ejecutar las pruebas
.venv/bin/python -m pytest
```

El helper externo al repositorio inicia el contenedor `inventario-dev-mysql` con MySQL 8.4, accesible en `127.0.0.1:3306`, y conserva los datos en `/workspace/.onboarding/inventario/mysql-data`. Las credenciales locales se generan durante la preparación y se guardan en archivos privados.

Como el SQL versionado está vacío, este helper crea un esquema de desarrollo inferido de las consultas del código. No constituye una migración oficial para producción. El helper y las rutas anteriores pertenecen al entorno preparado; no se incluyen al clonar el repositorio en otra máquina.

## Base de datos

La aplicación espera las siguientes tablas:

| Tabla | Columnas utilizadas |
| --- | --- |
| `productos` | `id`, `nombre`, `descripcion`, `precio`, `stock`, `categoria` |
| `movimientos` | `id`, `producto_id`, `tipo`, `cantidad`, `stock_anterior`, `stock_actual`, `fecha` |

Los ID deben generarse automáticamente. `movimientos.producto_id` referencia `productos.id`; la clave foránea debe impedir eliminar productos que tengan movimientos. `fecha` debe tener un valor predeterminado de fecha y hora, ya que el código no lo proporciona al insertar movimientos. Usa tablas transaccionales (por ejemplo, InnoDB) y un tipo decimal para el precio.

Cada entrada o salida actualiza el stock e inserta un movimiento con tipo `Entrada` o `Salida`, cantidad y existencias anteriores y posteriores.

## Pruebas automatizadas

Desde la raíz del proyecto:

```bash
pipenv run python -m pytest
pipenv run python -m pytest --cov=producto --cov=validaciones --cov=inventario --cov=movimiento --cov=conexion --cov-report=term-missing
```

Las pruebas existentes comprueban la clase `Producto`, las validaciones de entrada y las operaciones de inventario utilizando conexiones MySQL simuladas. No requieren una base de datos activa y no sustituyen una comprobación de la conexión real. Durante la preparación del entorno se ejecutaron 34 pruebas con resultado satisfactorio y se verificaron operaciones reales con MySQL.

## Próximas mejoras

- Añadir un script SQL versionado para crear el esquema.
- Ampliar las pruebas de integración con una base de datos real.
- Desarrollar una interfaz web y un panel de control.

## Autor

Fernando Ramos Alba

Estudiante de Ingeniería en Desarrollo de Software.

GitHub: https://github.com/nandillo156-bot
