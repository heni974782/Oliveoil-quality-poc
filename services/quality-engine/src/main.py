"""
Quality engine — Phase 3.

Reads telemetry from TimescaleDB on a configurable interval, computes
cumulative thermal and light exposure per consignment using trapezoidal
integration, derives a quality score (0–100), persists it to quality_index,
and raises deduped alerts when thresholds are breached.

No ML — pure rule-based model, intentional for the POC.
"""

import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta, timezone

import psycopg

from . import notifier

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
POSTGRES_HOST     = os.getenv("POSTGRES_HOST", "timescaledb")
POSTGRES_PORT     = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB       = os.getenv("POSTGRES_DB", "oliveoil")
POSTGRES_USER     = os.getenv("POSTGRES_USER", "oliveoil_app")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

# Baselines: exposure above these values contributes to degradation
TEMP_BASELINE_C   = float(os.getenv("QUALITY_TEMP_BASELINE", "18.0"))
LIGHT_BASELINE_LX = float(os.getenv("QUALITY_LIGHT_BASELINE", "50.0"))

# Penalty weights: quality points lost per exposure unit
TEMP_WEIGHT  = float(os.getenv("QUALITY_TEMP_WEIGHT", "2.0"))   # per degree-hour
LIGHT_WEIGHT = float(os.getenv("QUALITY_LIGHT_WEIGHT", "0.1"))  # per lux-hour

# Score thresholds
WARNING_SCORE  = float(os.getenv("QUALITY_ALERT_WARNING_SCORE", "70.0"))
CRITICAL_SCORE = float(os.getenv("QUALITY_ALERT_CRITICAL_SCORE", "50.0"))

# Instant-measurement alert thresholds
TEMP_ALERT_C   = float(os.getenv("QUALITY_TEMP_ALERT", "30.0"))
LIGHT_ALERT_LX = float(os.getenv("QUALITY_LIGHT_ALERT", "5000.0"))
HUMIDITY_ALERT = float(os.getenv("QUALITY_HUMIDITY_ALERT", "70.0"))

# Re-raise same alert only after this cooldown (seconds)
ALERT_COOLDOWN_S = int(os.getenv("QUALITY_ALERT_COOLDOWN", "3600"))

# Rolling window: only telemetry within the last N days is used for exposure
# computation. 0 = unlimited (full history). Default 1 day — realistic for
# transport monitoring (evaluate recent conditions, not lifetime history).
QUALITY_WINDOW_DAYS = int(os.getenv("QUALITY_WINDOW_DAYS", "1"))

RUN_INTERVAL_S = int(os.getenv("QUALITY_RUN_INTERVAL", "30"))

DB_RETRY_COUNT = 15
DB_RETRY_DELAY = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DB connection
# ---------------------------------------------------------------------------

def connect_db() -> psycopg.Connection:
    dsn = (
        f"host={POSTGRES_HOST} port={POSTGRES_PORT} dbname={POSTGRES_DB} "
        f"user={POSTGRES_USER} password={POSTGRES_PASSWORD}"
    )
    for attempt in range(1, DB_RETRY_COUNT + 1):
        try:
            conn = psycopg.connect(dsn, autocommit=False)
            log.info("Connected to TimescaleDB")
            return conn
        except psycopg.OperationalError as exc:
            log.warning("DB connect attempt %d/%d failed: %s", attempt, DB_RETRY_COUNT, exc)
            if attempt == DB_RETRY_COUNT:
                log.error("Could not connect to DB after %d attempts — exiting", DB_RETRY_COUNT)
                sys.exit(1)
            time.sleep(DB_RETRY_DELAY)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def get_consignment_ids(conn: psycopg.Connection) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT consignment_id FROM telemetry;")
        return [row[0] for row in cur.fetchall()]


def get_telemetry(conn: psycopg.Connection, consignment_id: str) -> list[dict]:
    """Telemetry rows for a consignment within the rolling window, sorted ASC.

    If QUALITY_WINDOW_DAYS > 0, only rows within the last N days are returned.
    QUALITY_WINDOW_DAYS = 0 means full history (original behaviour).
    """
    if QUALITY_WINDOW_DAYS > 0:
        since = datetime.now(timezone.utc) - timedelta(days=QUALITY_WINDOW_DAYS)
        query = """
            SELECT time, temperature_c, light_lux, humidity_pct
            FROM telemetry
            WHERE consignment_id = %s
              AND time >= %s
            ORDER BY time ASC;
        """
        params = (consignment_id, since)
    else:
        query = """
            SELECT time, temperature_c, light_lux, humidity_pct
            FROM telemetry
            WHERE consignment_id = %s
            ORDER BY time ASC;
        """
        params = (consignment_id,)

    with conn.cursor() as cur:
        cur.execute(query, params)
        return [
            {
                "time":          row[0],
                "temperature_c": row[1],
                "light_lux":     row[2],
                "humidity_pct":  row[3],
            }
            for row in cur.fetchall()
        ]


def already_alerted(conn: psycopg.Connection, consignment_id: str, alert_type: str) -> bool:
    """True if same alert type was raised for this consignment within the cooldown window."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=ALERT_COOLDOWN_S)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM alerts
            WHERE consignment_id = %s
              AND alert_type = %s
              AND time > %s
            LIMIT 1;
            """,
            (consignment_id, alert_type, cutoff),
        )
        return cur.fetchone() is not None


def insert_alert(
    conn: psycopg.Connection,
    consignment_id: str,
    alert_type: str,
    severity: str,
    value: float,
    threshold: float,
    message: str,
) -> None:
    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO alerts
                (time, consignment_id, alert_type, severity, value, threshold, message)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
            """,
            (now, consignment_id, alert_type, severity, value, threshold, message),
        )
    log.warning(
        "ALERT [%s] %s | type=%s value=%.1f threshold=%.1f",
        severity.upper(), consignment_id, alert_type, value, threshold,
    )


def insert_quality_index(
    conn: psycopg.Connection,
    consignment_id: str,
    score: float,
    degree_hours: float,
    lux_hours: float,
) -> None:
    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO quality_index
                (time, consignment_id, quality_score, degree_hours, lux_hours)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (consignment_id, time) DO NOTHING;
            """,
            (now, consignment_id, score, degree_hours, lux_hours),
        )


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def compute_exposure(rows: list[dict]) -> tuple[float, float]:
    """
    Trapezoidal integration over consecutive telemetry rows.

    Returns (total_degree_hours, total_lux_hours) accumulated above baselines.
    Only exposure above the baseline counts — mild conditions don't contribute.
    """
    degree_hours = 0.0
    lux_hours    = 0.0

    for i in range(1, len(rows)):
        dt_hours = (rows[i]["time"] - rows[i - 1]["time"]).total_seconds() / 3600.0
        avg_temp = (rows[i]["temperature_c"] + rows[i - 1]["temperature_c"]) / 2.0
        avg_lux  = (rows[i]["light_lux"]     + rows[i - 1]["light_lux"])     / 2.0

        degree_hours += max(0.0, avg_temp - TEMP_BASELINE_C)   * dt_hours
        lux_hours    += max(0.0, avg_lux  - LIGHT_BASELINE_LX) * dt_hours

    return degree_hours, lux_hours


def compute_quality_score(degree_hours: float, lux_hours: float) -> float:
    score = 100.0 - (degree_hours * TEMP_WEIGHT) - (lux_hours * LIGHT_WEIGHT)
    return max(0.0, min(100.0, score))


def check_and_raise_alerts(
    conn: psycopg.Connection,
    consignment_id: str,
    score: float,
    degree_hours: float,
    lux_hours: float,
    latest: dict,
) -> None:
    """Evaluate all alert conditions; persist new ones that aren't in cooldown."""
    temp_penalty  = degree_hours * TEMP_WEIGHT
    light_penalty = lux_hours * LIGHT_WEIGHT

    checks = [
        (
            "quality_critical", "critical", score, CRITICAL_SCORE,
            score < CRITICAL_SCORE,
            (
                f"Score {score:.1f}/100 — critique. "
                f"Thermique: {degree_hours:.2f}°·h (−{temp_penalty:.1f} pts), "
                f"lumière: {lux_hours:.1f} lx·h (−{light_penalty:.1f} pts)."
            ),
        ),
        (
            "quality_warning", "warning", score, WARNING_SCORE,
            CRITICAL_SCORE <= score < WARNING_SCORE,
            (
                f"Score {score:.1f}/100 — dégradation. "
                f"Thermique: {degree_hours:.2f}°·h (−{temp_penalty:.1f} pts), "
                f"lumière: {lux_hours:.1f} lx·h (−{light_penalty:.1f} pts)."
            ),
        ),
        (
            "high_temperature", "warning",
            latest["temperature_c"], TEMP_ALERT_C,
            latest["temperature_c"] > TEMP_ALERT_C,
            f"Température instantanée {latest['temperature_c']:.1f}°C — seuil {TEMP_ALERT_C}°C dépassé.",
        ),
        (
            "high_light", "warning",
            latest["light_lux"], LIGHT_ALERT_LX,
            latest["light_lux"] > LIGHT_ALERT_LX,
            f"Luminosité instantanée {latest['light_lux']:.0f} lux — seuil {LIGHT_ALERT_LX:.0f} lux dépassé.",
        ),
        (
            "high_humidity", "warning",
            latest["humidity_pct"], HUMIDITY_ALERT,
            latest["humidity_pct"] > HUMIDITY_ALERT,
            f"Humidité instantanée {latest['humidity_pct']:.1f}% — seuil {HUMIDITY_ALERT:.0f}% dépassé.",
        ),
    ]

    for alert_type, severity, value, threshold, condition, message in checks:
        if condition and not already_alerted(conn, consignment_id, alert_type):
            insert_alert(conn, consignment_id, alert_type, severity, value, threshold, message)
            notifier.notify(alert_type, severity, consignment_id, value, threshold, message)


# ---------------------------------------------------------------------------
# Engine loop
# ---------------------------------------------------------------------------

def run_once(conn: psycopg.Connection) -> None:
    consignments = get_consignment_ids(conn)
    if not consignments:
        log.info("No consignments in telemetry — nothing to compute")
        return

    for cid in consignments:
        rows = get_telemetry(conn, cid)
        if len(rows) < 2:
            log.debug("Consignment %s: <2 rows — skipping", cid)
            continue

        degree_hours, lux_hours = compute_exposure(rows)
        score = compute_quality_score(degree_hours, lux_hours)

        insert_quality_index(conn, cid, score, degree_hours, lux_hours)
        check_and_raise_alerts(conn, cid, score, degree_hours, lux_hours, rows[-1])

        log.info(
            "Consignment %s: score=%.1f | deg-h=%.4f | lux-h=%.4f",
            cid, score, degree_hours, lux_hours,
        )

    conn.commit()


def main() -> None:
    shutdown = {"flag": False}

    def _handle_signal(sig, _frame):
        log.info("Signal %s received — shutting down", sig)
        shutdown["flag"] = True

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    conn = connect_db()

    log.info(
        "Quality engine started | interval=%ds | temp_baseline=%.1f°C | light_baseline=%.1f lux",
        RUN_INTERVAL_S, TEMP_BASELINE_C, LIGHT_BASELINE_LX,
    )

    try:
        while not shutdown["flag"]:
            run_once(conn)
            # Sleep in 1s ticks so SIGTERM is handled promptly
            for _ in range(RUN_INTERVAL_S):
                if shutdown["flag"]:
                    break
                time.sleep(1)
    finally:
        conn.close()
        log.info("Quality engine stopped")


if __name__ == "__main__":
    main()
