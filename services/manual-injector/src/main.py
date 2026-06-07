"""Manual injector — demo/learning affordance.

Lets an operator inject telemetry by hand from the dashboard to see how the
quality model reacts. Crucially, it does NOT write to the database directly:
it publishes contract-compliant JSON to MQTT exactly like any other emitter,
so the ingestion service validates it (Pydantic) before it ever reaches the
database. A manual injection is just another device on the data contract —
which is the whole point of the device-agnostic design.

This service deliberately bridges iot-net (to reach the broker) and
backend-net (to receive HTTP from the dashboard via Nginx). It is the only
new cross-network component besides ingestion, and exists for the POC demo;
in production it would be restricted or removed.

Env vars:
    MQTT_HOST                 broker hostname
    MQTT_PORT                 broker port (default 1883)
    INJECTOR_MQTT_USERNAME    MQTT credentials (reuses the simulator user)
    INJECTOR_MQTT_PASSWORD
    INJECTOR_SITE_ID          default logical site (default warehouse-01)
    API_AUTH_TOKEN            same Bearer token as the API
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import paho.mqtt.client as mqtt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
log = logging.getLogger("manual-injector")

SCHEMA_VERSION = "1"
DEVICE_ID = "manual-injector"

MQTT_HOST = os.environ["MQTT_HOST"]
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = os.environ["INJECTOR_MQTT_USERNAME"]
MQTT_PASSWORD = os.environ["INJECTOR_MQTT_PASSWORD"]
SITE_ID = os.environ.get("INJECTOR_SITE_ID", "warehouse-01")
API_TOKEN = os.getenv("API_AUTH_TOKEN", "")

# ---------------------------------------------------------------------------
# Auth — same Bearer token as the API
# ---------------------------------------------------------------------------

_bearer = HTTPBearer(auto_error=True)


def verify_token(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> None:
    if not API_TOKEN:
        raise HTTPException(status_code=500, detail="API_AUTH_TOKEN not configured")
    if creds.credentials != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------------------------------------------------------------------
# MQTT client (persistent, shared)
# ---------------------------------------------------------------------------

_client: mqtt.Client | None = None


def _build_client() -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="manual-injector")
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            log.error("MQTT connect failed: %s", reason_code)
        else:
            log.info("Connected to MQTT broker %s:%d", MQTT_HOST, MQTT_PORT)

    client.on_connect = on_connect
    return client


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _client
    _client = _build_client()
    _client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    _client.loop_start()
    log.info("Manual injector ready — site=%s", SITE_ID)
    yield
    _client.loop_stop()
    _client.disconnect()


app = FastAPI(title="Manual Injector", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Request models — mirror the data contract ranges, reject bad input early
# ---------------------------------------------------------------------------

class PointRequest(BaseModel):
    consignment_id: str = Field(min_length=1)
    temperature_c: float = Field(ge=-50.0, le=100.0)
    light_lux: float = Field(ge=0.0, le=200_000.0)
    humidity_pct: float = Field(ge=0.0, le=100.0)
    event: str | None = None
    site_id: str | None = None


class ScenarioRequest(BaseModel):
    consignment_id: str = Field(min_length=1)
    temperature_c: float = Field(ge=-50.0, le=100.0)
    light_lux: float = Field(ge=0.0, le=200_000.0)
    humidity_pct: float = Field(ge=0.0, le=100.0)
    duration_minutes: int = Field(ge=1, le=1440)  # capped at 24h (rolling window)
    points: int = Field(ge=2, le=500)
    event: str | None = None
    site_id: str | None = None


# ---------------------------------------------------------------------------
# Publishing
# ---------------------------------------------------------------------------

def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _payload(consignment_id: str, ts: datetime, temp: float, lux: float, hum: float, event: str | None) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "consignment_id": consignment_id,
        "device_id": DEVICE_ID,
        "timestamp": _iso(ts),
        "measurements": {
            "temperature_c": round(temp, 2),
            "light_lux": round(lux, 2),
            "humidity_pct": round(hum, 2),
        },
        "event": event,
    }


def _publish(site_id: str, payload: dict) -> None:
    if _client is None:
        raise HTTPException(status_code=503, detail="MQTT client not ready")
    topic = f"oliveoil/{site_id}/{payload['consignment_id']}/telemetry"
    info = _client.publish(topic, json.dumps(payload), qos=1)
    info.wait_for_publish(timeout=5.0)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/point", dependencies=[Depends(verify_token)])
def inject_point(req: PointRequest):
    site = req.site_id or SITE_ID
    payload = _payload(
        req.consignment_id, datetime.now(timezone.utc),
        req.temperature_c, req.light_lux, req.humidity_pct, req.event,
    )
    _publish(site, payload)
    log.info("Injected point: %s temp=%.1f lux=%.0f hum=%.1f",
             req.consignment_id, req.temperature_c, req.light_lux, req.humidity_pct)
    return {"published": 1, "topic": f"oliveoil/{site}/{req.consignment_id}/telemetry"}


@app.post("/scenario", dependencies=[Depends(verify_token)])
def inject_scenario(req: ScenarioRequest):
    """Publish N backdated points spread over duration_minutes.

    Timestamps are backdated so the quality engine's trapezoidal integration
    sees a *sustained* exposure across real elapsed time — a single point at
    'now' has a near-zero time delta and barely moves the cumulative score.
    """
    site = req.site_id or SITE_ID
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=req.duration_minutes)
    step = (now - start) / (req.points - 1)

    for i in range(req.points):
        ts = start + step * i
        payload = _payload(
            req.consignment_id, ts,
            req.temperature_c, req.light_lux, req.humidity_pct, req.event,
        )
        _publish(site, payload)

    log.info("Injected scenario: %s %d points over %d min — temp=%.1f lux=%.0f hum=%.1f",
             req.consignment_id, req.points, req.duration_minutes,
             req.temperature_c, req.light_lux, req.humidity_pct)
    return {
        "published": req.points,
        "duration_minutes": req.duration_minutes,
        "topic": f"oliveoil/{site}/{req.consignment_id}/telemetry",
    }
