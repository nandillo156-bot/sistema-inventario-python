from validaciones import pedir_precio, pedir_stock


def test_pedir_precio_valido(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "25.50")

    resultado = pedir_precio()

    assert resultado == 25.50


def test_pedir_stock_valido(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "10")

    resultado = pedir_stock()

    assert resultado == 10


def test_stock_puede_ser_cero(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "0")

    resultado = pedir_stock()

    assert resultado == 0

def test_pedir_precio_negativo_y_luego_valido(monkeypatch):
    respuestas = iter(["-10", "25"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(respuestas)
    )

    resultado = pedir_precio()

    assert resultado == 25

def test_mensaje_error_precio_negativo(monkeypatch, capsys):
    respuestas = iter(["-10", "25"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(respuestas)
    )

    resultado = pedir_precio()

    salida = capsys.readouterr()

    assert resultado == 25
    assert "Error: el precio debe ser mayor que 0." in salida.out

def test_precio_texto_invalido(monkeypatch, capsys):
    respuestas = iter(["hola", "50"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(respuestas)
    )

    resultado = pedir_precio()

    salida = capsys.readouterr()

    assert resultado == 50
    assert "Error: ingresa un número válido." in salida.out

def test_stock_negativo_y_luego_valido(monkeypatch, capsys):
    respuestas = iter(["-5", "10"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(respuestas)
    )

    resultado = pedir_stock()

    salida = capsys.readouterr()

    assert resultado == 10
    assert "Error: el stock no puede ser negativo." in salida.out

def test_stock_texto_invalido(monkeypatch, capsys):
    respuestas = iter(["hola", "15"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(respuestas)
    )

    resultado = pedir_stock()

    salida = capsys.readouterr()

    assert resultado == 15
    assert "Error: ingresa un número entero válido." in salida.out