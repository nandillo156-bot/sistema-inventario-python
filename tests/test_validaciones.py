import pytest

from validaciones import pedir_precio, pedir_stock


def test_pedir_precio_valido(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "25.50")

    resultado = pedir_precio()

    assert resultado == 25.50


def test_precio_menor_a_un_centavo_y_luego_valido(monkeypatch, capsys):
    respuestas = iter(["0.001", "1.00"])
    monkeypatch.setattr("builtins.input", lambda _: next(respuestas))

    resultado = pedir_precio()

    assert resultado == 1.00
    assert "Error: el precio mínimo es 0.01." in capsys.readouterr().out


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


@pytest.mark.parametrize("entrada", ["nan", "NaN", "inf", "-inf", "Infinity", "1e309"])
def test_precio_no_finito_y_luego_valido(monkeypatch, capsys, entrada):
    respuestas = iter([entrada, "25.50"])
    monkeypatch.setattr("builtins.input", lambda _: next(respuestas))

    resultado = pedir_precio()

    assert resultado == 25.50
    assert "Error: el precio debe ser un número finito." in capsys.readouterr().out


@pytest.mark.parametrize(
    "pedir_valor, entrada, mensaje",
    [
        (pedir_precio, "100000000", "Error: el precio no puede superar 99999999.99."),
        (pedir_stock, "2147483648", "Error: el stock no puede superar 2147483647."),
        (pedir_stock, "1.5", "Error: ingresa un número entero válido."),
    ],
)
def test_valor_incompatible_con_base_de_datos_y_luego_valido(
    monkeypatch, capsys, pedir_valor, entrada, mensaje
):
    respuestas = iter([entrada, "25"])
    monkeypatch.setattr("builtins.input", lambda _: next(respuestas))

    resultado = pedir_valor()

    assert resultado == 25
    assert mensaje in capsys.readouterr().out
