# main.py

import logging
from fastapi import FastAPI
from api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(
    title="Claro Cobertura API",
    description="Verifica cobertura de fibra óptica en fibraoptica.claro.com.ar",
    version="1.0.0"
)

app.include_router(router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    # Puerto 8001 para no colisionar con sporting_tickets (8000)
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)