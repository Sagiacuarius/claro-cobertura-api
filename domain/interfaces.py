# domain/interfaces.py
#
# PUERTO — contrato abstracto entre el dominio y la infraestructura.
#
# El caso de uso solo conoce este puerto.
# No sabe si detrás hay Playwright, Selenium, o una API REST.
# Eso es la inversión de dependencias (D de SOLID).

from abc import ABC, abstractmethod
from domain.entities import SolicitudCobertura, ResultadoCoberturaDomain


class CoberturaPort(ABC):

    @abstractmethod
    async def verificar(
        self,
        solicitud: SolicitudCobertura
    ) -> ResultadoCoberturaDomain:
        """
        Ejecuta el flujo de verificación:
        1. Escribe la dirección
        2. Confirma en el mapa
        3. Responde el modal de edificio
        4. Captura y retorna el banner
        """
        ...
