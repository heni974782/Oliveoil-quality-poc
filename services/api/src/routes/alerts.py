from fastapi import APIRouter, Depends, Query
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from ..auth import verify_token
from ..db import get_db
from ..models import Alert

router = APIRouter(dependencies=[Depends(verify_token)])


@router.get("/", response_model=list[Alert])
async def list_alerts(
    consignment_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    conn: AsyncConnection = Depends(get_db),
):
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            SELECT id, time, consignment_id, alert_type, severity,
                   value, threshold, message
            FROM alerts
            WHERE (%s::text IS NULL OR consignment_id = %s)
            ORDER BY time DESC
            LIMIT %s;
            """,
            (consignment_id, consignment_id, limit),
        )
        return [Alert(**row) for row in await cur.fetchall()]
