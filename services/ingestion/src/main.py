"""Ingestion service -- Phase 2.

Subscribes to oliveoil/+/+/telemetry on the MQTT broker, validates each
payload against the data contract (Pydantic), and persists valid rows into
TimescaleDB. This service is the trust boundary: device data is untrusted
until it clears validation here.

Env vars:
    MQTT_HOST                 broker hostname (Docker service name)
    MQTT_PORT                 broker port (default 1883)
    MQTT_USERNAME             MQTT credentials for the ingestion service
    MQTT_PASSWORD
    POSTGRES_HOST             TimescaleDB hostname (default timescaledb)
    POSTGRES_PORT             (default 5432)
    POSTGRES_DB
    POSTGRES_USER
    POSTGRES_PASSWORD
"""

import json
import logging
import os
import signal
import sys
import time

import psycopg
import paho.mqtt.client as mqtt
from pydantic import BaseModel, Field, ValidationError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
log = logging.getLogger("ingestion")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MQTT_HOST = os.environ["MQTT_HOST"]
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = os.environ["MQTT_USERNAME"]
MQTT_PASSWORD = os.environ["MQTT_PASSWORD"]

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "timescaledb")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.environ["POSTGRES_DB"]
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]

TELEMETRY_TOPIC = "oliveoil/+/+/telemetry"

# ---------------------------------------------------------------------------
# Data contract (Pydantic) — mirrors docs/data-contract.md schema_version 1
# ---------------------------------------------------------------------------

class Measurements(BaseModel):
    temperature_c: float = Field(ge=-50.0, le=100.0)
    light_lux: float = Field(ge=0.0, le=200_000.0)
    humidity_pct: float = Field(ge=0.0, le=100.0)


class TelemetryPayload(BaseModel):
    schema_version: str
    consignment_id: str
    device_id: str
    timestamp: str           # ISO 8601 string; psycopg casts to TIMESTAMPTZ
    measurements: Measurements
    event: str | None = None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

INSERT_SQL = """
INSERT INTO telemetry
    (time, consignment_id, device_id, temperature_c, light_lux, humidity_pct,
     event, schema_version)
VALUES
    (%(time)s, %(consignment_id)s, %(device_id)s, %(temperature_c)s,
     %(light_lux)s, %(humidity_pct)s, %(event)s, %(schema_version)s)
ON CONFLICT (consignment_id, time) DO NOTHING;
"""


def _connect_db() -> psycopg.Connection:
    return psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


def _connect_db_with_retry(max_attempts: int = 15, delay: float = 3.0) -> psycopg.Connection:
    for attempt in range(1, max_attempts + 1):
        try:
            conn = _connect_db()
            log.info("Connected to TimescaleDB at %s:%d/%s", POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB)
            return conn
        except Exception as exc:
            log.warning("DB connect attempt %d/%d failed: %s", attempt, max_attempts, exc)
            if attempt < max_attempts:
                time.sleep(delay)
    log.error("Could not connect to TimescaleDB after %d attempts — exiting.", max_attempts)
    sys.exit(1)


def _write_row(conn: psycopg.Connection, payload: TelemetryPayload) -> psycopg.Connection:
    """Write one validated row. Returns a (possibly new) live connection."""
    row = {
        "time": payload.timestamp,
        "consignment_id": payload.consignment_id,
        "device_id": payload.device_id,
        "temperature_c": payload.measurements.temperature_c,
        "light_lux": payload.measurements.light_lux,
        "humidity_pct": payload.measurements.humidity_pct,
        "event": payload.event,
        "schema_version": payload.schema_version,
    }
    try:
        with conn.cursor() as cur:
            cur.execute(INSERT_SQL, row)
        conn.commit()
        log.info(
            "Stored: consignment=%s device=%s time=%s event=%s",
            payload.consignment_id,
            payload.device_id,
            payload.timestamp,
            payload.event or "—",
        )
    except Exception as exc:
        log.error("DB write failed: %s — attempting reconnect.", exc)
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        conn = _connect_db_with_retry()
    return conn


# ---------------------------------------------------------------------------
# MQTT callbacks
# ---------------------------------------------------------------------------

def make_on_message(state: dict):
    """Closure so the callback can access and update the shared DB connection."""

    def on_message(client, userdata, message):
        raw = message.payload.decode("utf-8", errors="replace")
        topic = message.topic

        # JSON parse
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            log.warning("Rejected — JSON parse error on %s: %s | raw=%r", topic, exc, raw[:300])
            return

        # Schema validation
        try:
            payload = TelemetryPayload.model_validate(data)
        except ValidationError as exc:
            log.warning("Rejected — schema validation on %s: %s", topic, exc)
            return

        # Persist
        state["conn"] = _write_row(state["conn"], payload)

    return on_message


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("Ingestion service starting")

    conn = _connect_db_with_retry()
    state = {"conn": conn}

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            log.error("MQTT connect failed: %s", reason_code)
        else:
            client.subscribe(TELEMETRY_TOPIC, qos=1)
            log.info("Subscribed to %s", TELEMETRY_TOPIC)

    def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
        if reason_code.is_failure:
            log.warning("MQTT disconnected unexpectedly: %s — paho will retry.", reason_code)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = make_on_message(state)

    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)

    def _shutdown(sig, frame):
        log.info("Shutdown signal received — cleaning up.")
        client.loop_stop()
        client.disconnect()
        state["conn"].close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    client.loop_forever()


if __name__ == "__main__":
    main()
