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
-- Phase 3 — indice de qualité et alertes.
-- ---------------------------------------------------------------------------

-- Série temporelle du score qualité par consignation.
-- Chaque cycle du moteur insère une nouvelle ligne.
CREATE TABLE IF NOT EXISTS quality_index (
    time            TIMESTAMPTZ       NOT NULL,
    consignment_id  TEXT              NOT NULL,
    quality_score   DOUBLE PRECISION  NOT NULL,   -- 0–100
    degree_hours    DOUBLE PRECISION  NOT NULL,   -- exposition thermique cumulée au-dessus du seuil
    lux_hours       DOUBLE PRECISION  NOT NULL,   -- exposition lumineuse cumulée au-dessus du seuil
    PRIMARY KEY (consignment_id, time)
);

SELECT create_hypertable('quality_index', 'time', if_not_exists => TRUE);

-- Alertes générées par le moteur de qualité.
-- Table standard (pas de hypertable : PK BIGSERIAL incompatible avec TimescaleDB).
-- Indexée sur time pour les requêtes temporelles et sur (consignment_id, alert_type, time)
-- pour le déduplication par cooldown.
CREATE TABLE IF NOT EXISTS alerts (
    id              BIGSERIAL         PRIMARY KEY,
    time            TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
    consignment_id  TEXT              NOT NULL,
    alert_type      TEXT              NOT NULL,   -- 'quality_warning', 'quality_critical', 'high_temperature', etc.
    severity        TEXT              NOT NULL,   -- 'warning' | 'critical'
    value           DOUBLE PRECISION,             -- valeur qui a déclenché l'alerte
    threshold       DOUBLE PRECISION,             -- seuil dépassé
    message         TEXT              NOT NULL
);

CREATE INDEX IF NOT EXISTS alerts_time_idx
    ON alerts (time DESC);

CREATE INDEX IF NOT EXISTS alerts_consignment_type_time_idx
    ON alerts (consignment_id, alert_type, time DESC);
