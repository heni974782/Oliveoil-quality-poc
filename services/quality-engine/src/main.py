"""Quality engine -- Phase 3.

Responsibility:
    Compute a quality / freshness index per consignment from cumulative
    thermal and light exposure over time, and raise alerts when thresholds
    are breached. Rule-based for the POC (no machine learning).

Not implemented yet -- see docs/roadmap.md, Phase 3.
"""

# TODO Phase 3:
#   - read telemetry from TimescaleDB
#   - compute cumulative exposure (degree-hours above threshold, lux-hours)
#   - derive a quality index per consignment
#   - persist index and alerts
