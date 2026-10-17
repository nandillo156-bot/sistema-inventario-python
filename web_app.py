"""Entrada compatible: el panel ahora utiliza el mismo servidor Flask de app.py."""

import argparse

from app import app


def main():
    parser = argparse.ArgumentParser(description="Abrir el panel Flask del inventario.")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("El puerto debe estar entre 1 y 65535.")
    app.run(host="127.0.0.1", port=args.port, debug=False)


if __name__ == "__main__":
    main()
