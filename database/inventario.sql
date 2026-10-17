-- Esquema inicial del sistema de inventario.
-- Requiere MySQL 8.0.16 o posterior para que se apliquen los CHECK.
-- Ejecutar desde el cliente mysql: SOURCE database/inventario.sql;
-- Este script crea objetos que no existen; no borra datos ni migra tablas
-- existentes. Antes de actualizar una instalacion anterior, compara su
-- estructura mediante SHOW CREATE TABLE productos / movimientos.

CREATE DATABASE IF NOT EXISTS inventario
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_as_ci;

USE inventario;

-- La colacion as_ci distingue acentos, pero no mayusculas: "Teclado"
-- y "teclado" comparten nombre. La clave unica tambien evita duplicados
-- cuando dos solicitudes intentan registrar el mismo producto a la vez.
-- DECIMAL(10,2) representa precios desde 0.01 hasta 99999999.99.
-- Los INT de existencias y cantidades admiten hasta 2147483647 unidades.
CREATE TABLE IF NOT EXISTS productos (
    id INT NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT NOT NULL,
    precio DECIMAL(10,2) NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    categoria VARCHAR(255) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_productos_nombre (nombre),
    KEY idx_productos_stock (stock),
    CONSTRAINT chk_productos_nombre CHECK (CHAR_LENGTH(TRIM(nombre)) > 0),
    CONSTRAINT chk_productos_descripcion CHECK (CHAR_LENGTH(TRIM(descripcion)) > 0),
    CONSTRAINT chk_productos_precio CHECK (precio > 0),
    CONSTRAINT chk_productos_stock CHECK (stock >= 0),
    CONSTRAINT chk_productos_categoria CHECK (CHAR_LENGTH(TRIM(categoria)) > 0)
) ENGINE=InnoDB
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_as_ci;

-- InnoDB permite confirmar en una transaccion el cambio de stock y su
-- movimiento. La aplicacion debe bloquear el producto al leer su stock
-- (SELECT ... FOR UPDATE) y guardar ambas operaciones antes del COMMIT.
-- La FK conserva el historial: un producto con movimientos no se elimina.
CREATE TABLE IF NOT EXISTS movimientos (
    id INT NOT NULL AUTO_INCREMENT,
    producto_id INT NOT NULL,
    tipo ENUM('Entrada', 'Salida') CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    cantidad INT NOT NULL,
    stock_anterior INT NOT NULL,
    stock_actual INT NOT NULL,
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_movimientos_producto (producto_id),
    CONSTRAINT fk_movimientos_producto FOREIGN KEY (producto_id)
        REFERENCES productos (id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,
    CONSTRAINT chk_movimientos_tipo CHECK (tipo IN ('Entrada', 'Salida')),
    CONSTRAINT chk_movimientos_cantidad CHECK (cantidad > 0),
    CONSTRAINT chk_movimientos_stock_anterior CHECK (stock_anterior >= 0),
    CONSTRAINT chk_movimientos_stock_actual CHECK (stock_actual >= 0),
    CONSTRAINT chk_movimientos_balance CHECK (
        (tipo = 'Entrada' AND stock_actual = stock_anterior + cantidad)
        OR
        (tipo = 'Salida' AND stock_actual = stock_anterior - cantidad)
    )
) ENGINE=InnoDB
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_as_ci;
