# infrastructure/scraper.py
#
# ADAPTADOR -- implementacion concreta del puerto CoberturaPort.
#
# Flujo (Mayo 2026):
#   1. Obtener JWT de /api/auth_jwt
#   2. Navegar a web-institucional.claro.com.ar con el token
#   3. Tipear direccion + Enter (activa mapa Leaflet)
#   4. Confirmar en popup del mapa
#   5. Responder modal de edificio (SI/NO)
#   6. Interceptar respuesta de Principal.aspx/VerDisponibilidad
#
# Si maniana Claro cambia algo, solo tocas este archivo.

import json
import logging
from playwright.async_api import (
    async_playwright, Page,
    TimeoutError as PlaywrightTimeout
)
from domain.entities import (
    SolicitudCobertura, ResultadoCoberturaDomain,
    ResultadoCobertura, TipoEdificio
)
from domain.interfaces import CoberturaPort

logger = logging.getLogger(__name__)

# URLs
URL_NEXTJS      = "https://fibraoptica.claro.com.ar/"
URL_AUTH_JWT    = "https://fibraoptica.claro.com.ar/api/auth_jwt?lat=&lon="
URL_INSTITUCIONAL = "https://web-institucional.claro.com.ar/"

# Selectores (sitio viejo Angular + Leaflet)
SEL_DIRECCION       = "#txtBuscarXYGO"
SEL_POPUP_BTN       = ".leaflet-popup-content button.btnPopUpTrue"
SEL_MODAL_EDIFICIO  = "#modaledificio"
SEL_RADIO_EDIFICIO  = 'input[name="edificio"][value="{v}"]'
SEL_BTN_CONFIRMAR   = "#confirmarpopup"


async def _obtener_jwt(page: Page) -> str:
    """Obtiene el JWT necesario para acceder al sitio institucional."""
    logger.info("Obteniendo JWT...")
    await page.goto(URL_AUTH_JWT, timeout=10000)
    body = await page.evaluate("document.body.innerText")
    token = json.loads(body)["token"]
    logger.info(f"JWT: {token[:30]}...")
    return token


async def _escribir_direccion(page: Page, direccion: str) -> None:
    """Escribe la direccion y presiona Enter para activar la busqueda en el mapa."""
    logger.info(f"Escribiendo: '{direccion}'")
    await page.wait_for_selector(SEL_DIRECCION, timeout=15000)
    await page.click(SEL_DIRECCION)
    await page.wait_for_timeout(300)

    # type() con delay para activar el ng-change de Angular
    await page.type(SEL_DIRECCION, direccion, delay=50)
    await page.wait_for_timeout(2000)

    # Enter dispara la busqueda en el mapa Leaflet
    logger.info("Presionando Enter...")
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(1500)


async def _confirmar_en_mapa(page: Page) -> bool:
    """
    Click en 'Confirmar direccion' del popup de Leaflet.
    Retorna False si el popup nunca aparece (direccion no reconocida).
    """
    logger.info("Esperando popup 'Confirmar direccion'...")
    try:
        await page.wait_for_selector(SEL_POPUP_BTN, timeout=20000)
        await page.click(SEL_POPUP_BTN)
        logger.info("Popup confirmado")
        await page.wait_for_timeout(1500)
        return True
    except PlaywrightTimeout:
        logger.warning("Popup no aparecio - direccion no reconocida por el geocoder")
        return False


async def _responder_modal_edificio(page: Page, edificio: TipoEdificio) -> None:
    """Responde el modal 'Tu edificio tiene mas de 3 pisos...?'"""
    logger.info(f"Modal edificio: {edificio.name}")
    await page.wait_for_selector(SEL_MODAL_EDIFICIO, state="visible", timeout=15000)

    # Seleccionar SI o NO
    await page.click(SEL_RADIO_EDIFICIO.format(v=edificio.value))
    await page.wait_for_timeout(500)

    # Confirmar
    await page.click(SEL_BTN_CONFIRMAR)
    logger.info("Modal confirmado")


def _parsear_respuesta_api(response_body: str) -> ResultadoCoberturaDomain:
    """
    Parsea la respuesta de Principal.aspx/VerDisponibilidad.
    
    Respuesta con cobertura:
      {"d":"[{\"Estado\":\"Poligono con disponibilidad\",\"Tecnologia\":\"GPON\",...}]"}
    
    Respuesta sin cobertura:
      {"d":"[{\"Estado\":\"Sin disponibilidad\",...}]"}  (u otro mensaje)
    """
    try:
        data = json.loads(response_body)
        inner = json.loads(data["d"])

        if not inner or not isinstance(inner, list):
            return ResultadoCoberturaDomain(
                resultado=ResultadoCobertura.SIN_COBERTURA,
                mensaje_banner="Sin resultados"
            )

        # Tomar el primer resultado
        primero = inner[0]
        estado = primero.get("Estado", "")
        tecnologia = primero.get("Tecnologia", "")

        tiene = "disponibilidad" in estado.lower() and "sin" not in estado.lower()

        return ResultadoCoberturaDomain(
            resultado=ResultadoCobertura.CON_COBERTURA if tiene
                      else ResultadoCobertura.SIN_COBERTURA,
            mensaje_banner=f"{estado} | {tecnologia}" if tecnologia else estado
        )

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"Error parseando respuesta API: {e}")
        return ResultadoCoberturaDomain(
            resultado=ResultadoCobertura.SIN_COBERTURA,
            mensaje_banner=response_body[:200]
        )


class PlaywrightCoberturaAdapter(CoberturaPort):
    """
    Implementacion concreta del puerto usando Playwright.
    Intercepta la respuesta de la API interna para obtener el resultado
    en lugar de hacer scraping del DOM.
    """

    async def verificar(
        self,
        solicitud: SolicitudCobertura
    ) -> ResultadoCoberturaDomain:

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
            )
            page = await browser.new_page(
                viewport={"width": 1366, "height": 768}
            )

            # Variable para capturar la respuesta de la API
            api_response_body = None

            async def _capturar_respuesta(response):
                nonlocal api_response_body
                if "VerDisponibilidad" in response.url:
                    try:
                        api_response_body = await response.text()
                        logger.info(f"API interceptada: {api_response_body[:200]}")
                    except Exception:
                        pass

            page.on("response", _capturar_respuesta)

            try:
                # 1. Obtener JWT
                jwt = await _obtener_jwt(page)

                # 2. Navegar al sitio viejo con el JWT
                logger.info("Abriendo sitio institucional...")
                await page.goto(
                    f"{URL_INSTITUCIONAL}?token={jwt}",
                    wait_until="domcontentloaded",
                    timeout=30000
                )
                await page.wait_for_timeout(1500)

                # 3. Flujo de verificacion
                await _escribir_direccion(page, solicitud.direccion)
                ok = await _confirmar_en_mapa(page)
                if not ok:
                    return ResultadoCoberturaDomain(
                        resultado=ResultadoCobertura.ERROR,
                        error="Direccion no reconocida por el geocoder del mapa"
                    )
                await _responder_modal_edificio(page, solicitud.edificio)

                # 4. Esperar la respuesta de la API
                await page.wait_for_timeout(3000)

                if api_response_body:
                    return _parsear_respuesta_api(api_response_body)
                else:
                    logger.error("No se intercepto respuesta de VerDisponibilidad")
                    return ResultadoCoberturaDomain(
                        resultado=ResultadoCobertura.ERROR,
                        error="No se recibio respuesta de la API de cobertura"
                    )

            except PlaywrightTimeout as e:
                logger.error(f"Timeout: {e}")
                return ResultadoCoberturaDomain(
                    resultado=ResultadoCobertura.ERROR,
                    error=f"Timeout: {str(e)}"
                )
            except Exception as e:
                logger.error(f"Error en scraper: {e}")
                return ResultadoCoberturaDomain(
                    resultado=ResultadoCobertura.ERROR,
                    error=str(e)
                )
            finally:
                await browser.close()
