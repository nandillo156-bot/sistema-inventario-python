"""El límite de login también debe mantenerse entre hilos del mismo proceso."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from seguridad import IntentosLogin


def test_limite_login_no_admite_mas_intentos_concurrentes():
    limite = IntentosLogin(max_intentos=5)
    with ThreadPoolExecutor(max_workers=10) as hilos:
        resultados = list(hilos.map(limite.intentar, ["127.0.0.1"] * 20))
    assert resultados.count(0) == 5
    assert all(0 < espera <= 300 for espera in resultados if espera)


@pytest.mark.parametrize("valor", [0, -1, True, 1.5, "5", None])
def test_limite_login_exige_configuracion_valida(valor):
    with pytest.raises(ValueError, match="enteros positivos"):
        IntentosLogin(max_intentos=valor)
