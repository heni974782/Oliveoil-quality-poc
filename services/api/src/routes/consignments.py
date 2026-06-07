from fastapi import APIRouter, Depends, Query
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from ..auth import verify_token
from ..db import get_db
from ..models import ConsignmentSummary, TelemetryPoint, QualityPoint

router = APIRouter(dependencies=[Depends(verify_token)])

_SUMMARY_SQL = """
    WITH lt AS (
        SELECT DISTINCT ON (consignment_id)
            consignment_id, temperature_c, light_lux, humidity_pct, time
        FROM telemetry
        ORDER BY consignment_id, time DESC
    ),
    lq AS (
        SELECT DISTINCT ON (consignment_id)
            consignment_id, quality_score
        FROM quality_index
        ORDER BY consignment_id, time DESC
    ),
    ac AS (
        SELECT consignment_id, COUNT(*) AS cnt
        FROM alerts
        WHERE time > NOW() - INTERVAL '24 hours'
        GROUP BY consignment_id
    )
    SELECT
        lt.consignment_id,
        lq.quality_score,
        lt.temperature_c,
        lt.light_lux,
        lt.humidity_pct,
        lt.time          AS latest_time,
        COALESCE(ac.cnt, 0) AS active_alerts
    FROM lt
    LEFT JOIN lq USING (consignment_id)
    LEFT JOIN ac USING (consignment_id)
    ORDER BY lt.consignment_id;
"""


@router.get("/", response_model=list[ConsignmentSummary])
async def list_consignments(conn: AsyncConnection = Depends(get_db)):
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(_SUMMARY_SQL)
        return [ConsignmentSummary(**row) for row in await cur.fetchall()]


def _bucket_for_hours(hours: int) -> str:
    """Pick a downsampling bucket so any window yields ~100-200 points.

    Keeps charts readable and the payload small regardless of the time span,
    leveraging TimescaleDB's time_bucket() — the reason the DB was chosen.
    """
    if hours <= 1:
        return "1 minute"
    if hours <= 6:
        return "5 minutes"
    if hours <= 24:
        return "15 minutes"
    if hours <= 72:
        return "30 minutes"
    return "1 hour"


@router.get("/{consignment_id}/telemetry", response_model=list[TelemetryPoint])
async def get_telemetry(
    consignment_id: str,
    hours: int = Query(default=24, ge=1, le=720),
    conn: AsyncConnection = Depends(get_db),
):
    bucket = _bucket_for_hours(hours)
    async with conn.cursor(row_factory=dict_row) as cur:
        # Bucketed averages over the rolling window. event is dropped — an
        # aggregate has no single event marker.
        await cur.execute(
            """
            SELECT time_bucket(%s::interval, time) AS time,
                   avg(temperature_c) AS temperature_c,
                   avg(light_lux)     AS light_lux,
                   avg(humidity_pct)  AS humidity_pct
            FROM telemetry
            WHERE consignment_id = %s
              AND time >= now() - make_interval(hours => %s)
            GROUP BY 1
            ORDER BY 1 ASC;
            """,
            (bucket, consignment_id, hours),
        )
        rows = await cur.fetchall()
    return [TelemetryPoint(**row, event=None) for row in rows]


@router.get("/{consignment_id}/quality", response_model=list[QualityPoint])
async def get_quality(
    consignment_id: str,
    hours: int = Query(default=24, ge=1, le=720),
    conn: AsyncConnection = Depends(get_db),
):
    bucket = _bucket_for_hours(hours)
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            SELECT time_bucket(%s::interval, time) AS time,
                   avg(quality_score) AS quality_score,
                   avg(degree_hours)  AS degree_hours,
                   avg(lux_hours)     AS lux_hours
            FROM quality_index
            WHERE consignment_id = %s
              AND time >= now() - make_interval(hours => %s)
            GROUP BY 1
            ORDER BY 1 ASC;
            """,
            (bucket, consignment_id, hours),
        )
        rows = await cur.fetchall()
    return [QualityPoint(**row) for row in rows]
