# État d'avancement du POC

## Phase 0 — Scaffolding ✅ Terminée

### Infra Docker (`docker-compose.yml`)

- 2 services actifs : **Mosquitto** (port 1883) + **TimescaleDB** (port 5432)
- 4 services déclarés en commentaire, décommentés phase par phase
- Segmentation réseau : `iot-net` (devices) / `backend-net` (back-end)
- L'ingestion sera le seul composant à cheval sur les deux réseaux

### Broker MQTT — secure by design

- `broker/mosquitto/config/mosquitto.conf` : `allow_anonymous false`
- Fichier `passwd` créé avec credentials device
- ACL préparée (commentée) — activée en Phase 5

### Base de données

- `db/init/01_schema.sql` : extension TimescaleDB activée
- Structure de la table `telemetry` documentée en TODO (créée en Phase 2)

### Contrat de données (`docs/data-contract.md`)

Interface device-agnostique : tout émetteur qui publie ce JSON sur
`oliveoil/<site_id>/<consignment_id>/telemetry` se branche sans modifier
le back-end.

```json
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
```

### Scaffolding services (squelettes vides)

| Service | Dossier | Phase |
|---------|---------|-------|
| Simulateur device | `services/device-simulator/` | Phase 1 |
| Ingestion | `services/ingestion/` | Phase 2 |
| Moteur de qualité | `services/quality-engine/` | Phase 3 |
| API | `services/api/` | Phase 4 |

Chaque service a son `Dockerfile`, `requirements.txt` et `src/main.py` avec TODOs.

---

## Phase 1 — Simulateur ✅ Terminée

### Ce qui est fait

| Tâche | Statut |
|-------|--------|
| `services/device-simulator/src/main.py` — implémentation complète | ✅ |
| `services/device-simulator/requirements.txt` — `paho-mqtt==2.1.0` épinglé | ✅ |
| `docker-compose.yml` — service `device-simulator` décommenté | ✅ |
| `.env` + `.env.example` — variables simulateur ajoutées | ✅ |
| User MQTT `simulator` créé dans `broker/mosquitto/config/passwd` | ✅ |
| Service buildé et lancé (`docker compose up --build`) | ✅ |
| Messages visibles sur le broker (vérifiés via `mosquitto_sub -C 3`) | ✅ |

### Logique du simulateur

- **Thread par consignation** : chaque lot tourne indépendamment, publie toutes les `SIMULATOR_PUBLISH_INTERVAL` secondes.
- **Mesures réalistes** : température (~18 °C baseline), luminosité (~5 lux), humidité (~45 %) avec bruit gaussien et dérive lente du baseline.
- **Incidents injectables** (probabilité `SIMULATOR_INCIDENT_PROBABILITY` par tick) :
  - `door_open` — pic luminosité 500-2000 lux, +2-5 °C
  - `sun_exposure` — pic luminosité 5000-50000 lux, +5-15 °C
  - `cooling_failure` — +10-20 °C, durée 2-6 ticks
- **QoS 1** — au moins une livraison, conformément au contrat de données.

### Variables d'environnement simulateur

| Variable | Valeur par défaut | Rôle |
|----------|-------------------|------|
| `SIMULATOR_MQTT_USERNAME` | — | User MQTT dédié (`simulator`) |
| `SIMULATOR_SITE_ID` | `warehouse-01` | Site logique |
| `SIMULATOR_CONSIGNMENT_IDS` | `cons-001,cons-002` | Lots simulés |
| `SIMULATOR_PUBLISH_INTERVAL` | `10` | Secondes entre publishes |
| `SIMULATOR_INCIDENT_PROBABILITY` | `0.02` | Probabilité d'incident par tick |

*Terminé quand* : les messages arrivent sur le broker (vérifiable via `mosquitto_sub`).

---

---

## Phase 2 — Ingestion + persistance ✅ Terminée

### Ce qui est fait

| Tâche | Statut |
|-------|--------|
| `db/init/01_schema.sql` — table `telemetry` + hypertable TimescaleDB | ✅ |
| Schéma appliqué sur la base courante | ✅ |
| `services/ingestion/src/main.py` — abonnement MQTT, validation Pydantic, écriture DB | ✅ |
| `services/ingestion/requirements.txt` — versions épinglées (`paho-mqtt==2.1.0`, `pydantic==2.11.5`, `psycopg[binary]==3.2.6`) | ✅ |
| `docker-compose.yml` — service `ingestion` décommenté | ✅ |
| Service buildé et lancé | ✅ |
| Télémétrie valide visible en base (vérifiée via `SELECT … FROM telemetry`) | ✅ |

### Notes de mise en service

- Hash MQTT `ingestion` dans `passwd` ne correspondait pas au `.env` — corrigé via `mosquitto_passwd -b`.
- Password TimescaleDB divergeait (volume initialisé avant `.env` finalisé) — corrigé via `ALTER USER oliveoil_app PASSWORD 'change_me'`.

---

## Phases suivantes

| Phase | Objectif | Critère de fin |
|-------|----------|----------------|
| Phase 3 | Moteur de qualité + alertes | Indice et alertes calculés et stockés |
| Phase 4 | API + dashboard React | Dashboard montre les consignations en temps réel |
| Phase 5 | Durcissement sécurité + doc finale | Revue secure-by-design, documentation livrée |
