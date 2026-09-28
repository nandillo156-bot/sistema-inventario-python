
# Sistema de Inventario con Python y MySQL

Sistema de gestión de inventarios desarrollado en Python
y MySQL. Permite administrar productos, controlar
existencias y registrar movimientos de mercancía.

## Funcionalidades

- Registrar nuevos productos.
- Consultar y buscar productos.
- Actualizar información de productos.
- Eliminar productos.
- Registrar entradas y salidas de mercancía.
- Consultar productos con existencias bajas.
- Visualizar el historial de movimientos.

## Tecnologías utilizadas

- Python
- MySQL 8
- Programación orientada a objetos
- Pipenv
- Git y GitHub

## Estructura del proyecto

```text
invetario/
├── database/
│   └── inventario.sql
├── .env.example
├── .gitignore
├── Pipfile
├── Pipfile.lock
├── Readme.md
├── conexion.py
├── inventario.py
├── main.py
├── movimiento.py
├── producto.py
└── validaciones.py
```

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/nandillo156-bot/sistema-inventario-python.git
cd sistema-inventario-python
```

### 2. Instalar las dependencias

Es necesario tener Python, Pipenv y MySQL instalados.

```bash
pipenv install
```

### 3. Configurar MySQL

Abre MySQL Workbench y ejecuta el archivo:

`database/inventario.sql`

Este script crea la base de datos y las tablas necesarias.

### 4. Configurar las variables de entorno

Crea un archivo `.env` tomando como referencia
el archivo `.env.example`.

Introduce tus propias credenciales de MySQL.

Nunca publiques el archivo `.env`.

### 5. Ejecutar el programa

```bash
pipenv run python main.py
```

## Base de datos

El sistema utiliza dos tablas:

**productos:** almacena el nombre, descripción,
precio, existencias y categoría de cada producto.

**movimientos:** registra las entradas y salidas,
incluyendo la cantidad, las existencias anteriores,
las nuevas existencias y la fecha del movimiento.

Ambas tablas están relacionadas mediante
el identificador del producto.

## Próximas mejoras

- Desarrollo de una interfaz web con Flask.
- Creación de un panel de control.
- Implementación de pruebas automatizadas.

## Autor

Fernando Ramos Alba

Estudiante de Ingeniería en Desarrollo de Software.

GitHub: https://github.com/nandillo156-bot
