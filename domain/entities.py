# domain/entities.py
#
# DOMINIO PURO — Python sin imports externos.
# Solo lo necesario para verificar cobertura.
# Cuando en el futuro agregues datos del cliente,
# solo extendés acá — no tocás nada más.

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class TipoEdificio(str, Enum):
    """
    Respuesta al modal del mapa.
    Los valores coinciden con el atributo value
    de los radio buttons del HTML de Claro.
    """
    SI = "true"
    NO = "false"


class ResultadoCobertura(str, Enum):
    CON_COBERTURA = "con_cobertura"
    SIN_COBERTURA = "sin_cobertura"
    ERROR         = "error"


@dataclass
class SolicitudCobertura:
    """
    Datos de entrada — lo mínimo para verificar cobertura.
    Viene desde n8n via JSON.
    """
    direccion: str
    edificio:  TipoEdificio


@dataclass
class ResultadoCoberturaDomain:
    """
    Resultado que el microservicio devuelve a n8n.
    """
    resultado:      ResultadoCobertura
    mensaje_banner: Optional[str] = None   # "¡Tenés cobertura en tu zona!"
    error:          Optional[str] = None

    @property
    def tiene_cobertura(self) -> bool:
        return self.resultado == ResultadoCobertura.CON_COBERTURA
