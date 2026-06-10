import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import signal, technical, context, forecast

app = FastAPI(
    title="SmartTrade Backend",
    description="Motor de análisis técnico e IA para traders retail.",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    # TODO: restringir a dominios SmartTrade antes de deploy a producción final
    # Ej: allow_origins=["https://smarttrade.app", "https://www.smarttrade.app"]
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(signal.router, prefix="/v1")
app.include_router(technical.router, prefix="/v1")
app.include_router(context.router, prefix="/v1")
app.include_router(forecast.router, prefix="/v1")


@app.get("/")
def root():
    return {
        "status": "ok",
        "servicio": "SmartTrade Backend",
        "version": "3.0.0",
        "fase": "Fase 3 — M4 Forecast Engine",
        "endpoints": {
            "señal":    "/v1/signal/{ticker}",
            "técnico":  "/v1/technical/{ticker}",
            "contexto": "/v1/context/{ticker}",
            "forecast": "/v1/forecast/{ticker}",
            "backtest": "/v1/backtest/{ticker} (Fase 4 — próximamente)",
        },
    }


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
