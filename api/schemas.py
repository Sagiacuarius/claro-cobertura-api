# api/schemas.py
#
# Modelos Pydantic para la comunicación HTTP con n8n.
# Distintos a las entidades del dominio a propósito:
# el dominio no sabe cómo se llaman los campos en JSON.

from pydantic import BaseModel
from typing import Optional
from domain.entities import TipoEdificio


class SolicitudCoberturaRequest(BaseModel):
    """Body del POST que envía n8n."""
    direccion: str
    edificio:  TipoEdificio = TipoEdificio.NO   # default: No
    piso:      Optional[str] = None             # Requerido solo si edificio=true

    model_config = {
        "json_schema_extra": {
            "example": {
                "direccion": "SANTA FE 1270, CHABAS, CASEROS, SANTA FE",
                "edificio": "true",
                "piso": "3"
            }
        }
    }


class ResultadoCoberturaResponse(BaseModel):
    """Respuesta que recibe n8n."""
    tiene_cobertura: bool
    resultado:       str            # "con_cobertura" | "sin_cobertura" | "error"
    mensaje_banner:  Optional[str] = None
    error:           Optional[str] = None


class HealthResponse(BaseModel):
    status:  str
    version: str = "1.0.0"
