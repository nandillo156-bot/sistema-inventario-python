# Sistema de inventario con Python, Flask y MySQL

Proyecto de portafolio para gestionar productos, existencias e historial de movimientos. El panel de HTML, CSS y JavaScript utiliza una API Flask que delega las operaciones en un servicio de inventario. También se conserva la versión de consola.

**Autor:** Fernando Ramos Alba · Estudiante de Ingeniería en Desarrollo de Software · [GitHub](https://github.com/nandillo156-bot)

## Qué puedes hacer

- Registrar, consultar, editar y eliminar productos sin historial.
- Buscar productos y filtrar los que tienen 5 unidades o menos.
- Registrar entradas y salidas sin permitir existencias negativas.
- Consultar los últimos 200 movimientos desde el panel web.
- Ver el número de productos, las unidades disponibles y las alertas de stock bajo.

El panel modifica las existencias mediante movimientos. El servicio guarda el cambio de stock y el historial en una misma transacción y bloquea el producto durante la operación. Editar sus datos conserva las existencias.

## Tecnologías

Python 3.14, Flask, MySQL 8.0.16 o posterior, HTML, CSS, JavaScript, mysql-connector-python, python-dotenv, Pipenv y pytest. Las versiones de las dependencias están fijadas en `Pipfile.lock`.

## Ejecutar en tu equipo

### 1. Clonar e instalar

Necesitas Python 3.14, Pipenv y un servidor MySQL en ejecución. El cliente `mysql` debe estar disponible para importar el esquema; también puedes ejecutar el archivo SQL desde MySQL Workbench.

```bash
git clone https://github.com/nandillo156-bot/sistema-inventario-python.git
cd sistema-inventario-python
python -m pip install pipenv
pipenv sync --dev
```

### 2. Crear la base de datos

Desde la raíz del proyecto abre el cliente MySQL. `-p` solicita tu contraseña sin escribirla en el comando:

```bash
mysql -h 127.0.0.1 -P 3306 -u tu_usuario -p
```

Dentro del cliente, ejecuta:

```sql
SOURCE database/inventario.sql;
SHOW TABLES FROM inventario;
```

El usuario necesita permisos para crear la base y las tablas. El script crea `inventario`, `productos` y `movimientos` si no existen, sin borrar datos. **No actualiza la estructura de tablas antiguas**: si ya tienes una base, revisa su estructura antes de reutilizarla.

Se requiere MySQL 8.0.16 o posterior porque versiones anteriores no aplican las restricciones `CHECK`. Consulta la [documentación de MySQL](https://dev.mysql.com/doc/refman/8.0/en/create-table-check-constraints.html).

### 3. Configurar `.env`

Si ya tienes un archivo `.env`, edítalo conservando tus credenciales. Para crear uno nuevo, copia `.env.example`. En PowerShell:

```powershell
Copy-Item .env.example .env
```

En macOS o Linux:

```bash
cp .env.example .env
```

Configura `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` y `DB_DATABASE` con los datos de tu instancia. El esquema inicial usa `inventario` como nombre de base. `.env` está excluido de Git.

### 4. Abrir el panel Flask

```bash
pipenv run python app.py
```

Abre [http://127.0.0.1:5000](http://127.0.0.1:5000). La aplicación se ejecuta en la interfaz local y con debug desactivado.

`web_app.py` es una entrada compatible al mismo servidor Flask:

```bash
pipenv run python web_app.py
pipenv run python web_app.py --port 8001
```

El primer comando usa [http://127.0.0.1:8000](http://127.0.0.1:8000); el segundo usa [http://127.0.0.1:8001](http://127.0.0.1:8001). Ejecuta uno de los comandos para iniciar el panel.

La consola sigue disponible con `pipenv run python main.py`; todavía usa las operaciones de `inventario.py` y su migración al servicio compartido está pendiente.

`FLASK_SECRET_KEY` es opcional para esta ejecución local. Flask recibe una clave temporal si no se configura. La aplicación todavía no implementa usuarios ni autenticación.

## Cómo se organiza el código

```text
sistema-inventario-python/
├── .github/workflows/tests.yml  # Pruebas automáticas en GitHub
├── database/inventario.sql      # Esquema inicial de MySQL
├── docs/guia-codigo.md          # Recorrido explicado y ejercicios
├── tests/                      # Modelo, servicio y API con conexiones simuladas
├── web/                        # HTML, CSS y JavaScript del panel
├── templates/                  # Referencia de los formularios anteriores
├── app.py                      # Factory Flask, rutas HTTP y respuestas JSON
├── web_app.py                  # Entrada compatible al mismo servidor Flask
├── servicio_inventario.py      # Validación y operaciones SQL del panel
├── main.py                     # Menú de consola
├── inventario.py               # Operaciones de consola pendientes de migrar
├── producto.py                 # Modelo y validación del producto
├── movimiento.py               # Representación de un movimiento de consola
├── validaciones.py             # Reglas de precio/stock y lectura de consola
├── conexion.py                 # Conexión a MySQL desde variables de entorno
├── .env.example                # Configuración de ejemplo sin datos personales
├── Pipfile
└── Pipfile.lock
```

`create_app(config=None)` construye la aplicación y permite cambiar su configuración en las pruebas. Las rutas de `app.py` reciben HTTP; `servicio_inventario.py` recibe datos de Python, aplica las reglas y consulta MySQL sin conocer las peticiones HTTP. Este patrón está descrito en la [guía oficial de factories de Flask](https://flask.palletsprojects.com/en/stable/patterns/appfactories/).

La [guía del código](docs/guia-codigo.md) explica el recorrido desde un clic hasta MySQL, la separación entre rutas y reglas y el uso de `with`, `yield` y `finally` para cerrar recursos.

## API del panel local

| Método | Ruta | Operación y respuesta correcta |
| --- | --- | --- |
| GET | `/api/productos` | Listar productos, 200. |
| POST | `/api/productos` | Registrar un producto, 201 con su `id` y cabecera `Location`. |
| GET | `/api/productos/{id}` | Consultar un producto, 200. |
| PUT | `/api/productos/{id}` | Editar datos sin cambiar stock, 200. |
| DELETE | `/api/productos/{id}` | Eliminar si no tiene movimientos, 200. |
| GET | `/api/movimientos` | Consultar los últimos 200 movimientos, 200. |
| POST | `/api/productos/{id}/movimientos` | Registrar una entrada o salida, 201 con el nuevo stock. |

Las escrituras reciben un objeto JSON con `Content-Type: application/json`. Para crear un producto se requieren `nombre`, `descripcion`, `precio`, `stock` y `categoria`. Para editar se requieren los mismos campos salvo `stock`: es opcional y se ignora si se envía. El stock guardado se lee dentro de la transacción. Un movimiento requiere `tipo` (`Entrada` o `Salida`) y `cantidad` entera positiva.

Los errores se devuelven como JSON con la forma `{"error": "mensaje"}`:

| Estado HTTP | Significado |
| --- | --- |
| 400 | Datos o JSON inválidos. |
| 403 | La escritura incluye un `Origin` distinto del servidor. |
| 404 | Producto o ruta inexistente. |
| 405 | Método HTTP no admitido para la ruta. |
| 409 | Nombre duplicado o intento de borrar un producto con historial. |
| 410 | Envío a uno de los formularios anteriores, ya retirados. |
| 413 | Petición de API superior al límite de 65 536 bytes. |
| 415 | El cuerpo enviado no usa `application/json`. |
| 503 | Error al acceder a MySQL; los detalles internos no se devuelven al navegador. |

`/` y `/productos` sirven el panel existente de `web/`. Las visitas GET a `/registrar` y `/editar/{id}` redirigen al panel. Los POST a esas rutas y a `/eliminar/{id}` devuelven 410 sin consultar la base. Los archivos de `templates/` se conservan como referencia y ya no tienen rutas activas que los rendericen.

Flask admite hosts locales (`localhost`, `127.0.0.1` y `::1`). Las escrituras que incluyen `Origin` deben coincidir con el origen del servidor. Estas comprobaciones acompañan el uso local; la autenticación y el despliegue público siguen pendientes.

## Base de datos y reglas

`productos` guarda el catálogo. `movimientos.producto_id` referencia a un producto y conserva tipo, cantidad, stock anterior, stock actual y fecha automática.

- El nombre es único sin distinguir mayúsculas y minúsculas; los acentos sí se distinguen.
- Nombre y categoría admiten hasta 255 caracteres; descripción se guarda como `TEXT`.
- MySQL guarda el precio como `DECIMAL(10,2)`. El modelo acepta precios finitos entre `0.01` y `99999999.99` y rechaza booleanos.
- Stock y cantidades se limitan al rango de `INT`: hasta `2147483647`. El stock puede ser cero; una cantidad de movimiento debe ser positiva.
- Una clave foránea impide borrar productos con historial, y los `CHECK` verifican cantidades positivas y balances de cada movimiento.

La precisión de precios con más de dos decimales todavía requiere una política explícita de redondeo y el uso de `Decimal` de extremo a extremo.

## Pruebas y validación

```bash
pipenv run python -m pytest -q
```

Las pruebas no requieren MySQL activo. Comprueban el modelo, las validaciones, la consola, el servicio y las respuestas HTTP usando el cliente de pruebas de Flask y conexiones simuladas. Cubren la conservación del stock al editar, movimientos, conflictos, rollback y cierre de recursos. También prueban recorridos de una ruta Flask hasta el servicio con la base simulada.

En la comprobación local de esta etapa se confirmó la conexión a MySQL y la presencia de las columnas requeridas en las tablas existentes. El panel Flask también se abrió en el navegador y consultó datos reales sin realizar escrituras. **No se ha importado el nuevo esquema ni verificado sus restricciones en una base desechable**; esa integración y los flujos completos de escritura en el navegador siguen pendientes.

El workflow de GitHub Actions instala las dependencias del archivo de bloqueo y ejecuta la suite en cada push y pull request. Su ejecución remota se comprobará cuando se publique el cambio.

## Estado y siguientes mejoras

La unificación web está implementada: el panel usa Flask y un servicio de inventario común. Los comandos `app.py` y `web_app.py` arrancan la misma aplicación. Esta etapa deja una aplicación local; todavía no hay una demo pública desplegada.

Las siguientes iteraciones son:

1. Migrar la consola al servicio para compartir validación, transacciones y manejo de errores.
2. Añadir pruebas de integración con MySQL y pruebas del navegador completo.
3. Definir el tratamiento de precios con más de dos decimales y usar `Decimal` de extremo a extremo.
4. Revisar el diseño adaptable y la accesibilidad, preparar capturas y documentar una demo.
5. Añadir autenticación y preparar el despliegue público.

La guía explica estas decisiones para poder defenderlas en una entrevista.
