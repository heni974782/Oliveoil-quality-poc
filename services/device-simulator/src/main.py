"""Device simulator -- Phase 1.

Publishes realistic telemetry for olive-oil consignments to the MQTT broker.
Each consignment runs its own publish thread. Incidents (door_open,
sun_exposure, cooling_failure) fire randomly and last several ticks, modeling
real-world events that degrade oil quality.

Topic pattern : oliveoil/<site_id>/<consignment_id>/telemetry
Payload format: docs/data-contract.md (schema_version 1)

Env vars:
    MQTT_HOST                       broker hostname
    MQTT_PORT                       broker port (default 1883)
    SIMULATOR_MQTT_USERNAME         MQTT credentials for this service
    SIMULATOR_MQTT_PASSWORD
    SIMULATOR_SITE_ID               logical site name (default warehouse-01)
    SIMULATOR_CONSIGNMENT_IDS       comma-separated list (default cons-001,cons-002)
    SIMULATOR_PUBLISH_INTERVAL      seconds between publishes (default 10)
    SIMULATOR_INCIDENT_PROBABILITY  chance of incident per publish tick (default 0.02)
"""

import json
import logging
import os
import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
log = logging.getLogger("device-simulator")

SCHEMA_VERSION = "1"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MQTT_HOST = os.environ["MQTT_HOST"]
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = os.environ["SIMULATOR_MQTT_USERNAME"]
MQTT_PASSWORD = os.environ["SIMULATOR_MQTT_PASSWORD"]

SITE_ID = os.environ.get("SIMULATOR_SITE_ID", "warehouse-01")
CONSIGNMENT_IDS = [
    c.strip()
    for c in os.environ.get("SIMULATOR_CONSIGNMENT_IDS", "cons-001,cons-002").split(",")
]
PUBLISH_INTERVAL = int(os.environ.get("SIMULATOR_PUBLISH_INTERVAL", "10"))
INCIDENT_PROBABILITY = float(os.environ.get("SIMULATOR_INCIDENT_PROBABILITY", "0.02"))

INCIDENT_TYPES = ["door_open", "sun_exposure", "cooling_failure"]


# ---------------------------------------------------------------------------
# Simulation model
# ---------------------------------------------------------------------------

@dataclass
class ConsignmentState:
    consignment_id: str
    device_id: str
    # Baselines drift slowly to simulate gradual environment changes
    temp_baseline: float = 18.0      # °C — ideal olive-oil storage
    light_baseline: float = 5.0      # lux — dark storage
    humidity_baseline: float = 45.0  # % RH
    active_incident: Optional[str] = None
    incident_ticks_left: int = 0


def _apply_incident(
    incident: str, temp: float, light: float
) -> tuple[float, float]:
    """Return (temp, light) modified by the active incident."""
    if incident == "door_open":
        # Brief opening: light floods in, slight warm-up
        return temp + random.uniform(2, 5), light + random.uniform(500, 2000)
    if incident == "sun_exposure":
        # Container left in direct sun
        return temp + random.uniform(5, 15), light + random.uniform(5000, 50000)
    if incident == "cooling_failure":
        # Refrigeration unit fault — no light effect
        return temp + random.uniform(10, 20), light
    return temp, light


def generate_reading(state: ConsignmentState) -> dict:
    """Produce one telemetry payload from the current consignment state."""
    temp = state.temp_baseline + random.gauss(0, 0.5)
    light = max(0.0, state.light_baseline + random.gauss(0, 2.0))
    humidity = state.humidity_baseline + random.gauss(0, 1.0)
    event = None

    # Roll for a new incident when none is active
    if state.active_incident is None and random.random() < INCIDENT_PROBABILITY:
        state.active_incident = random.choice(INCIDENT_TYPES)
        state.incident_ticks_left = random.randint(2, 6)
        log.info(
            "Consignment %s — incident started: %s (%d ticks)",
            state.consignment_id,
            state.active_incident,
            state.incident_ticks_left,
        )

    if state.active_incident:
        event = state.active_incident
        temp, light = _apply_incident(state.active_incident, temp, light)
        state.incident_ticks_left -= 1
        if state.incident_ticks_left <= 0:
            log.info(
                "Consignment %s — incident ended: %s",
                state.consignment_id,
                state.active_incident,
            )
            state.active_incident = None

    # Slow baseline drift — clipped to a realistic storage range
    state.temp_baseline = max(10.0, min(35.0, state.temp_baseline + random.gauss(0, 0.05)))

    return {
        "schema_version": SCHEMA_VERSION,
        "consignment_id": state.consignment_id,
        "device_id": state.device_id,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "measurements": {
            "temperature_c": round(temp, 2),
            "light_lux": round(light, 2),
            "humidity_pct": round(humidity, 2),
        },
        "event": event,
    }


# ---------------------------------------------------------------------------
# MQTT client
# ---------------------------------------------------------------------------

def build_mqtt_client() -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            log.error("MQTT connection failed: %s", reason_code)
        else:
            log.info("Connected to MQTT broker %s:%d", MQTT_HOST, MQTT_PORT)

    def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
        if reason_code.is_failure:
            log.warning("MQTT disconnected unexpectedly: %s", reason_code)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    return client


# ---------------------------------------------------------------------------
# Publish loop — one thread per consignment
# ---------------------------------------------------------------------------

def run_consignment(state: ConsignmentState, client: mqtt.Client) -> None:
    topic = f"oliveoil/{SITE_ID}/{state.consignment_id}/telemetry"
    log.info("Consignment loop started: %s → %s", state.consignment_id, topic)
    while True:
        payload = generate_reading(state)
        client.publish(topic, json.dumps(payload), qos=1)
        log.debug("Published: %s", payload)
        time.sleep(PUBLISH_INTERVAL)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    log.info(
        "Device simulator starting — site=%s consignments=%s interval=%ds",
        SITE_ID,
        CONSIGNMENT_IDS,
        PUBLISH_INTERVAL,
    )

    client = build_mqtt_client()
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    # Brief wait for the connection handshake before threads start publishing
    time.sleep(2)

    for i, cid in enumerate(CONSIGNMENT_IDS):
        state = ConsignmentState(consignment_id=cid, device_id=f"sim-{i + 1:03d}")
        t = threading.Thread(target=run_consignment, args=(state, client), daemon=True)
        t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Simulator shutting down")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
