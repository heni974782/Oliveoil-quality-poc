from fastapi import APIRouter, Depends, HTTPException, Query
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


@router.get("/{consignment_id}/telemetry", response_model=list[TelemetryPoint])
async def get_telemetry(
    consignment_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    conn: AsyncConnection = Depends(get_db),
):
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            SELECT time, temperature_c, light_lux, humidity_pct, event
            FROM telemetry
            WHERE consignment_id = %s
            ORDER BY time ASC
            LIMIT %s;
            """,
            (consignment_id, limit),
        )
        rows = await cur.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail=f"Consignment '{consignment_id}' not found")
    return [TelemetryPoint(**row) for row in rows]


@router.get("/{consignment_id}/quality", response_model=list[QualityPoint])
async def get_quality(
    consignment_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    conn: AsyncConnection = Depends(get_db),
):
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            SELECT time, quality_score, degree_hours, lux_hours
            FROM quality_index
            WHERE consignment_id = %s
            ORDER BY time ASC
            LIMIT %s;
            """,
            (consignment_id, limit),
        )
        rows = await cur.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail=f"Consignment '{consignment_id}' not found")
    return [QualityPoint(**row) for row in rows]
