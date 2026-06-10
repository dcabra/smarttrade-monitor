# SmartTrade · Forecast Router (Fase 3 · M4)
# Endpoint: GET /v1/forecast/{ticker}
#
# Pipeline: OHLCV → M1 → M3 → M4 Forecast Engine → cached response
# Cache TTL: CACHE_TTL_FORECAST = 900s (15 min), defined in constants.py
#
# M2 context is intentionally excluded from the forecast pipeline:
# forecasts are price-level projections anchored on technical structure
# (ATR + Ichimoku + M3 score). M2 already flows into M3 score, so its
# influence is captured indirectly.
#
# Cache key uses asset_class prefix to avoid collision when multi-asset
# support is added (equity vs crypto vs ETF).
# Current default: "equity". Extend to "crypto" / "etf" in Fase 4+.

from fastapi import APIRouter, HTTPException

from app.shared import cache
from app.shared.constants import CACHE_TTL_FORECAST
from app.shared.data_fetcher import DataSourceError, TickerNotFoundError, get_ohlcv
from app.modules.m1_technical import engine as m1
from app.modules.m2_context import engine as m2
from app.modules.m3_signal import engine as m3
from app.modules.m4_forecast import forecast_engine as m4

router = APIRouter(prefix="/forecast", tags=["forecast"])

# Default asset class — extend when crypto/ETF routes are added
_DEFAULT_ASSET_CLASS = "equity"


@router.get("/{ticker}")
def get_forecast(ticker: str):
    """
    Probabilistic price forecast for a ticker.

    Returns p10/p50/p90 price levels for 1D, 3D, 7D horizons,
    derived from ATR-scaled drift + Ichimoku structural bias + M3 score.

    Cache TTL: 15 minutes.
    Cache key: forecast:{asset_class}:{ticker} — avoids collision across asset classes.
    """
    ticker = ticker.upper()
    cache_key = f"forecast:{_DEFAULT_ASSET_CLASS}:{ticker}"

    cached = cache.get(cache_key)
    if cached:
        return cached

    # ── M1: OHLCV + technical indicators ────────────────────────────────────
    try:
        df = get_ohlcv(ticker, days=90)
    except TickerNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No se pudo encontrar información para el ticker '{ticker}'. "
                "Verifica que el símbolo sea correcto."
            ),
        )
    except DataSourceError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error en la fuente de datos: {str(e)}",
        )

    m1_output = m1.run(ticker, df)

    # ── M2: context (non-blocking, feeds M3 indirectly) ─────────────────────
    m2_output = None
    try:
        m2_output = m2.run(ticker)
    except Exception:
        pass  # M2 failure is non-fatal — M3 degrades to technical-only

    # ── M3: signal (M4 reads score_final + confianza from M3 output) ────────
    m3_output = m3.run(m1_output=m1_output, m2_output=m2_output)

    # ── M4: forecast engine ──────────────────────────────────────────────────
    result = m4.run(m1_output=m1_output, m3_output=m3_output)

    cache.set(cache_key, result, CACHE_TTL_FORECAST)
    return result
