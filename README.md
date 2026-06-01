# POC — Monitoring qualité huile d'olive (stockage & transport)

POC d'apprentissage : suivi simulé de la dégradation de l'huile d'olive
(température, lumière, humidité) pendant le stockage et le transport, avec
indice de qualité, alertes et dashboard web.

## Démarrage rapide

1. `cp .env.example .env` puis renseigner les valeurs.
2. Voir `broker/mosquitto/README.md` pour créer les identifiants du broker.
3. `docker compose up` — démarre le broker MQTT et la base TimescaleDB.

## Documentation

- `CLAUDE.md` — contexte et conventions du projet (lu par Claude Code).
- `docs/architecture.md` — architecture détaillée.
- `docs/data-contract.md` — contrat de données MQTT (interface device-agnostique).
- `docs/roadmap.md` — les 6 phases de développement.

## Statut

Phase 0 — scaffolding.
