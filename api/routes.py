# api/routes.py
#
# ADAPTADOR PRIMARIO — recibe el request HTTP y llama al caso de uso.
# No contiene lógica de negocio.

from fastapi import APIRouter, HTTPException
from api.schemas import (
    SolicitudCoberturaRequest,
    ResultadoCoberturaResponse,
    HealthResponse
)
from application.use_cases import VerificarCoberturaUseCase
from infrastructure.scraper import PlaywrightCoberturaAdapter
from domain.entities import SolicitudCobertura

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")


@router.post("/verificar-cobertura", response_model=ResultadoCoberturaResponse)
async def verificar_cobertura(body: SolicitudCoberturaRequest):
    """
    Verifica si hay cobertura de fibra óptica Claro en la dirección dada.

    Retorna el resultado y el texto exacto del banner de la web.
    """
    # 1. Crear adaptador e inyectarlo en el caso de uso
    adaptador = PlaywrightCoberturaAdapter()
    use_case  = VerificarCoberturaUseCase(adaptador)

    # 2. Convertir schema → entidad del dominio
    solicitud = SolicitudCobertura(
        direccion=body.direccion,
        edificio=body.edificio
    )

    # 3. Ejecutar
    resultado = await use_case.execute(solicitud)

    # 4. Si hubo error técnico → 500
    if resultado.resultado.value == "error":
        raise HTTPException(status_code=500, detail=resultado.error)

    # 5. Convertir entidad del dominio → schema de respuesta
    return ResultadoCoberturaResponse(
        tiene_cobertura=resultado.tiene_cobertura,
        resultado=resultado.resultado.value,
        mensaje_banner=resultado.mensaje_banner,
        error=resultado.error
    )
