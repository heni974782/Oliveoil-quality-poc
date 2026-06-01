# Contrat de données — télémétrie MQTT

Ce contrat est l'**interface device-agnostique** du système. Tout émetteur qui
le respecte (simulateur, futur ESP32) se branche sans modifier le back-end.
Toute évolution incompatible impose de bumper `schema_version`.

## Topic

    oliveoil/<site_id>/<consignment_id>/telemetry

- `site_id` — site logique (entrepôt, route de transport).
- `consignment_id` — lot d'huile suivi.

## Payload (JSON, schema_version 1)

    {
      "schema_version": "1",
      "consignment_id": "cons-001",
      "device_id": "sim-001",
      "timestamp": "2026-05-25T14:30:00Z",
      "measurements": {
        "temperature_c": 24.7,
        "light_lux": 120.0,
        "humidity_pct": 45.2
      },
      "event": null
    }

| Champ                        | Type    | Description |
|------------------------------|---------|-------------|
| `schema_version`             | string  | Version du contrat. |
| `consignment_id`             | string  | Lot d'huile suivi. |
| `device_id`                  | string  | Émetteur de la mesure. |
| `timestamp`                  | string  | Horodatage ISO 8601, UTC. |
| `measurements.temperature_c` | number  | Température (°C). |
| `measurements.light_lux`     | number  | Luminosité (lux). |
| `measurements.humidity_pct`  | number  | Humidité relative (%). |
| `event`                      | string? | Incident optionnel (ex. `door_open`, `sun_exposure`). `null` si rien. |

## Règles de versionnement

- Ajout d'un champ optionnel -> rétrocompatible, pas de bump.
- Renommage, suppression, changement de type -> bump de `schema_version`.
- L'ingestion doit refuser tout payload dont `schema_version` est inconnu.

## QoS MQTT

POC : QoS 1 (au moins une livraison). L'ingestion doit donc tolérer les
doublons — idempotence sur le couple (`consignment_id`, `timestamp`).
