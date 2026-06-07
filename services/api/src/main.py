import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import create_pool, close_pool
from .routes import consignments, alerts, ws

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool()
    log.info("DB pool ready")
    yield
    await close_pool()
    log.info("DB pool closed")


app = FastAPI(
    title="Olive Oil Quality API",
    version="1.0",
    lifespan=lifespan,
)

# CORS is managed at the network level by Nginx in production.
# Kept open here for local dev with `uvicorn --reload`.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(consignments.router, prefix="/consignments", tags=["consignments"])
app.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
app.include_router(ws.router, tags=["websocket"])


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
