# application/use_cases.py
#
# CASO DE USO — orquesta el flujo, contiene las reglas de negocio.
#
# No sabe nada de HTTP ni de Playwright.
# Solo habla con el puerto CoberturaPort.

import logging
from domain.entities import SolicitudCobertura, ResultadoCoberturaDomain, ResultadoCobertura
from domain.interfaces import CoberturaPort

logger = logging.getLogger(__name__)


class VerificarCoberturaUseCase:

    def __init__(self, cobertura_port: CoberturaPort):
        # Inyección de dependencia: recibe el puerto, no la implementación
        self._port = cobertura_port

    async def execute(
        self,
        solicitud: SolicitudCobertura
    ) -> ResultadoCoberturaDomain:

        logger.info(f"Verificando cobertura para: '{solicitud.direccion}'")

        try:
            resultado = await self._port.verificar(solicitud)

            if resultado.tiene_cobertura:
                logger.info(f"✅ Cobertura disponible | '{resultado.mensaje_banner}'")
            else:
                logger.info(f"❌ Sin cobertura | resultado: {resultado.resultado}")

            return resultado

        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            return ResultadoCoberturaDomain(
                resultado=ResultadoCobertura.ERROR,
                error=str(e)
            )
