-- Migracion 001: cuentas de acceso al inventario.
-- Requiere MySQL 8.0.16 o posterior y una base de datos ya seleccionada.
-- Crea la tabla si falta; no modifica cuentas ni estructuras existentes.
-- No se insertan cuentas ni contraseñas predeterminadas.
CREATE TABLE IF NOT EXISTS usuarios (
    id INT NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(80) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    rol ENUM('consulta', 'operador', 'administrador')
        CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_usuarios_nombre (nombre),
    CONSTRAINT chk_usuarios_nombre CHECK (CHAR_LENGTH(TRIM(nombre)) BETWEEN 3 AND 80),
    CONSTRAINT chk_usuarios_rol CHECK (rol IN ('consulta', 'operador', 'administrador')),
    CONSTRAINT chk_usuarios_activo CHECK (activo IN (0, 1))
) ENGINE=InnoDB
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_as_ci;
