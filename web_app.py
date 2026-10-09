"""Interfaz web local: python web_app.py (solo desarrollo)."""
import argparse
import json
import math
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

import mysql.connector
from conexion import conectar
from producto import Producto

WEB = Path(__file__).parent / 'web'


def producto_validado(data):
    precio = float(data['precio'])
    stock = data['stock']
    if isinstance(stock, bool) or str(stock).strip() != str(int(stock)):
        raise ValueError('El stock debe ser un entero.')
    if not math.isfinite(precio):
        raise ValueError('El precio debe ser un número finito.')
    p = Producto(None, str(data['nombre']).strip(), str(data['descripcion']).strip(), precio, int(stock), str(data['categoria']).strip())
    if len(p.nombre) > 255 or len(p.categoria) > 255:
        raise ValueError('Nombre y categoría admiten hasta 255 caracteres.')
    return p


def operacion(method, path, data=None):
    connection = conectar()
    cursor = connection.cursor(dictionary=True)
    try:
        if method == 'GET' and path == '/api/productos':
            cursor.execute('SELECT id,nombre,descripcion,precio,stock,categoria FROM productos ORDER BY id DESC')
            return cursor.fetchall()
        if method == 'GET' and path == '/api/movimientos':
            cursor.execute('SELECT m.*,p.nombre FROM movimientos m JOIN productos p ON p.id=m.producto_id ORDER BY m.id DESC LIMIT 200')
            return cursor.fetchall()
        parts = path.strip('/').split('/')
        if len(parts) < 2 or parts[:2] != ['api', 'productos']:
            raise LookupError('Ruta no encontrada.')
        if (method == 'POST' and len(parts) == 2) or (method == 'PUT' and len(parts) == 3):
            p = producto_validado(data)
            ident = int(parts[2]) if method == 'PUT' else None
            if ident is not None:
                cursor.execute('SELECT id FROM productos WHERE id=%s FOR UPDATE', (ident,))
                if not cursor.fetchone():
                    raise LookupError('Producto no encontrado.')
            cursor.execute('SELECT id FROM productos WHERE LOWER(nombre)=LOWER(%s) AND (%s IS NULL OR id<>%s)', (p.nombre, ident, ident))
            if cursor.fetchone():
                raise ValueError('Ya existe un producto con ese nombre.')
            if ident is None:
                cursor.execute('INSERT INTO productos (nombre,descripcion,precio,stock,categoria) VALUES (%s,%s,%s,%s,%s)', (p.nombre,p.descripcion,p.precio,p.stock,p.categoria))
                ident = cursor.lastrowid
            else:
                # El stock solo se modifica a través de movimientos.
                cursor.execute('UPDATE productos SET nombre=%s,descripcion=%s,precio=%s,categoria=%s WHERE id=%s', (p.nombre,p.descripcion,p.precio,p.categoria,ident))
            connection.commit()
            return {'id': ident}
        if method == 'DELETE' and len(parts) == 3:
            ident = int(parts[2])
            cursor.execute('SELECT id FROM productos WHERE id=%s FOR UPDATE', (ident,))
            if not cursor.fetchone():
                raise LookupError('Producto no encontrado.')
            cursor.execute('SELECT id FROM movimientos WHERE producto_id=%s LIMIT 1', (ident,))
            if cursor.fetchone():
                raise ValueError('Este producto tiene movimientos registrados y no se puede eliminar.')
            cursor.execute('DELETE FROM productos WHERE id=%s', (ident,))
            connection.commit()
            return {'ok': True}
        if method == 'POST' and len(parts) == 4 and parts[3] == 'movimientos':
            ident = int(parts[2])
            cantidad = data['cantidad']
            if isinstance(cantidad, bool) or str(cantidad).strip() != str(int(cantidad)) or int(cantidad) <= 0:
                raise ValueError('La cantidad debe ser un entero mayor que cero.')
            cantidad = int(cantidad)
            tipo = data['tipo']
            if tipo not in ('Entrada', 'Salida'):
                raise ValueError('Tipo de movimiento inválido.')
            cursor.execute('SELECT stock FROM productos WHERE id=%s FOR UPDATE', (ident,))
            row = cursor.fetchone()
            if not row:
                raise LookupError('Producto no encontrado.')
            anterior = row['stock']
            actual = anterior + cantidad if tipo == 'Entrada' else anterior - cantidad
            if actual < 0:
                raise ValueError('No hay suficiente stock disponible.')
            cursor.execute('UPDATE productos SET stock=%s WHERE id=%s', (actual, ident))
            cursor.execute('INSERT INTO movimientos (producto_id,tipo,cantidad,stock_anterior,stock_actual) VALUES (%s,%s,%s,%s,%s)', (ident,tipo,cantidad,anterior,actual))
            connection.commit()
            return {'stock': actual}
        raise LookupError('Ruta no encontrada.')
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body, mime='application/json; charset=utf-8'):
        if not isinstance(body, bytes):
            body = json.dumps(body, default=lambda value: float(value) if isinstance(value, Decimal) else str(value), ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def dispatch(self):
        path = urlparse(self.path).path
        if self.command == 'GET' and path in ('/', '/app.js', '/style.css'):
            filename, mime = {'/': ('index.html','text/html'), '/app.js': ('app.js','text/javascript'), '/style.css': ('style.css','text/css')}[path]
            return self.respond(200, (WEB / filename).read_bytes(), mime+'; charset=utf-8')
        if not path.startswith('/api/'):
            return self.respond(404, {'error': 'Ruta no encontrada.'})
        try:
            data = None
            if self.command in ('POST', 'PUT', 'DELETE'):
                host = self.headers.get('Host', '')
                origin = self.headers.get('Origin')
                if host not in (f'localhost:{self.server.server_port}', f'127.0.0.1:{self.server.server_port}') or origin and origin != 'http://' + host:
                    return self.respond(403, {'error': 'Origen no permitido.'})
                if self.command != 'DELETE':
                    if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                        return self.respond(415, {'error': 'Se requiere JSON.'})
                    size = int(self.headers.get('Content-Length', 0))
                    if not 0 < size <= 65536:
                        return self.respond(413, {'error': 'Solicitud demasiado grande o vacía.'})
                    data = json.loads(self.rfile.read(size))
                    if not isinstance(data, dict):
                        raise ValueError('Se requiere un objeto JSON.')
            result = operacion(self.command, path, data)
            self.respond(200, result)
        except KeyError:
            self.respond(400, {'error': 'Completa todos los campos requeridos.'})
        except LookupError as error:
            self.respond(404, {'error': str(error)})
        except ValueError as error:
            self.respond(400, {'error': str(error) or 'Datos inválidos.'})
        except (TypeError, KeyError, OverflowError):
            self.respond(400, {'error': 'Datos inválidos. Revisa los campos.'})
        except mysql.connector.Error:
            self.respond(503, {'error': 'No se pudo completar la operación en la base de datos. Comprueba MySQL.'})

    do_GET = do_POST = do_PUT = do_DELETE = dispatch


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    print(f'Interfaz local en http://127.0.0.1:{args.port} (Ctrl+C para detener)', flush=True)
    HTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
