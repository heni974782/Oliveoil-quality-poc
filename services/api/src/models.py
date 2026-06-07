from datetime import datetime
from pydantic import BaseModel


class ConsignmentSummary(BaseModel):
    consignment_id: str
    quality_score: float | None
    temperature_c: float | None
    light_lux: float | None
    humidity_pct: float | None
    latest_time: datetime | None
    active_alerts: int


class TelemetryPoint(BaseModel):
    time: datetime
    temperature_c: float
    light_lux: float
    humidity_pct: float
    event: str | None


class QualityPoint(BaseModel):
    time: datetime
    quality_score: float
    degree_hours: float
    lux_hours: float


class Alert(BaseModel):
    id: int
    time: datetime
    consignment_id: str
    alert_type: str
    severity: str
    value: float | None
    threshold: float | None
    message: str


class LiveConsignment(BaseModel):
    consignment_id: str
    quality_score: float | None
    temperature_c: float | None
    light_lux: float | None
    humidity_pct: float | None
    latest_time: datetime | None


class LivePayload(BaseModel):
    consignments: list[LiveConsignment]
    recent_alerts: list[Alert]
