import asyncio
import logging
import os

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from psycopg.rows import dict_row

from ..db import get_pool

log = logging.getLogger(__name__)
API_TOKEN = os.getenv("API_AUTH_TOKEN", "")
WS_INTERVAL = 10  # seconds between pushes

router = APIRouter()


def _serialize(row: dict) -> dict:
    """Convert datetime values to ISO strings for JSON serialization."""
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in row.items()}


async def _fetch_live_payload() -> dict:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
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
                )
                SELECT lt.consignment_id,
                       lq.quality_score,
                       lt.temperature_c,
                       lt.light_lux,
                       lt.humidity_pct,
                       lt.time AS latest_time
                FROM lt
                LEFT JOIN lq USING (consignment_id)
                ORDER BY lt.consignment_id;
                """
            )
            consignments = [_serialize(r) for r in await cur.fetchall()]

            await cur.execute(
                """
                SELECT id, time, consignment_id, alert_type, severity,
                       value, threshold, message
                FROM alerts
                ORDER BY time DESC
                LIMIT 20;
                """
            )
            recent_alerts = [_serialize(r) for r in await cur.fetchall()]

    return {"consignments": consignments, "recent_alerts": recent_alerts}


@router.websocket("/ws/live")
async def ws_live(websocket: WebSocket, token: str = Query(...)):
    if token != API_TOKEN:
        await websocket.close(code=1008)  # Policy Violation
        return

    await websocket.accept()
    log.info("WS client connected: %s", websocket.client)

    try:
        while True:
            payload = await _fetch_live_payload()
            await websocket.send_json(payload)
            await asyncio.sleep(WS_INTERVAL)
    except WebSocketDisconnect:
        log.info("WS client disconnected: %s", websocket.client)
    except Exception as exc:
        log.error("WS error: %s", exc)
