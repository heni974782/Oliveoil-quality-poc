-- Schéma initial — POC monitoring huile d'olive.
-- Exécuté automatiquement par TimescaleDB au tout premier démarrage.

-- Active l'extension time-series.
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ---------------------------------------------------------------------------
-- Phase 2 — table de télémétrie.
-- Contrat : docs/data-contract.md (schema_version 1).
-- La contrainte d'unicité (consignment_id, time) assure l'idempotence des
-- INSERTs — un duplicate payload est silencieusement ignoré.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS telemetry (
    time            TIMESTAMPTZ       NOT NULL,
    consignment_id  TEXT              NOT NULL,
    device_id       TEXT              NOT NULL,
    temperature_c   DOUBLE PRECISION  NOT NULL,
    light_lux       DOUBLE PRECISION  NOT NULL,
    humidity_pct    DOUBLE PRECISION  NOT NULL,
    event           TEXT,
    schema_version  TEXT              NOT NULL,
    PRIMARY KEY (consignment_id, time)
);

-- Hypertable partitionné sur la colonne temporelle.
SELECT create_hypertable('telemetry', 'time', if_not_exists => TRUE);

-- ---------------------------------------------------------------------------
-- Phase 3 — tables quality_index et alerts (à décommenter en Phase 3).
-- ---------------------------------------------------------------------------
-- CREATE TABLE IF NOT EXISTS quality_index ( ... );
-- CREATE TABLE IF NOT EXISTS alerts ( ... );
