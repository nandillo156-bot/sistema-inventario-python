"""Permisos y límites de acceso compartidos por las rutas Flask."""

import math
import time
from collections import OrderedDict, deque
from threading import Lock


PERMISOS_POR_ROL = {
    "consulta": frozenset({"consultar"}),
    "operador": frozenset({"consultar", "mover_stock"}),
    "administrador": frozenset({"consultar", "mover_stock", "gestionar_productos"}),
}


def permisos_para(usuario):
    """Los permisos proceden del rol guardado en el servidor."""
    if usuario is None:
        return []
    return sorted(PERMISOS_POR_ROL.get(usuario.get("rol"), ()))


class IntentosLogin:
    """Limita intentos por IP en este proceso, sin almacenar contraseñas.

    Un despliegue con varios procesos necesita además un límite compartido
    en el proxy o en un servicio como Redis. No sustituye ese control global.
    """

    def __init__(self, max_intentos=5, ventana=300, max_clientes=10000):
        if any(isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0
               for valor in (max_intentos, ventana, max_clientes)):
            raise ValueError("Los límites de acceso deben ser enteros positivos.")
        self.max_intentos = max_intentos
        self.ventana = ventana
        self.max_clientes = max_clientes
        self._clientes = OrderedDict()
        self._lock = Lock()

    def intentar(self, cliente):
        """Devuelve segundos de espera, o cero si se admite el intento."""
        ahora = time.monotonic()
        with self._lock:
            intentos = self._clientes.get(cliente)
            if intentos is None:
                # La memoria está acotada incluso con muchas direcciones distintas.
                if len(self._clientes) >= self.max_clientes:
                    self._clientes.popitem(last=False)
                intentos = deque()
                self._clientes[cliente] = intentos
            self._clientes.move_to_end(cliente)
            while intentos and intentos[0] <= ahora - self.ventana:
                intentos.popleft()
            if len(intentos) >= self.max_intentos:
                return max(1, math.ceil(intentos[0] + self.ventana - ahora))
            intentos.append(ahora)
            return 0
