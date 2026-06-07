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

---

## Phase 3 — Moteur de qualité + alertes ✅ Terminée

### Ce qui est fait

| Tâche | Statut |
|-------|--------|
| `db/init/01_schema.sql` — tables `quality_index` (hypertable) + `alerts` (indexes) | ✅ |
| Schéma appliqué sur la base courante | ✅ |
| `services/quality-engine/src/main.py` — moteur complet | ✅ |
| `services/quality-engine/requirements.txt` — `psycopg[binary]==3.2.6` épinglé | ✅ |
| `docker-compose.yml` — service `quality-engine` décommenté | ✅ |
| `.env.example` — variables du moteur documentées | ✅ |
| Service buildé et lancé | ✅ |
| Indice et alertes calculés et stockés (vérifiés via `SELECT`) | ✅ |

### Logique du moteur

- **Cycle** : toutes les `QUALITY_RUN_INTERVAL` secondes (défaut : 30 s).
- **Exposition cumulée** : intégration trapézoïdale sur toute l'historique de télémétrie — exposition thermique (degré-heures au-dessus de `QUALITY_TEMP_BASELINE` = 18 °C) et lumineuse (lux-heures au-dessus de `QUALITY_LIGHT_BASELINE` = 50 lux).
- **Indice de qualité** : `score = 100 − (degree_hours × 2.0) − (lux_hours × 0.1)`, clampé [0, 100].

**Interprétation du score :**

| Score | Signification | Couleur dashboard |
|-------|---------------|-------------------|
| ≥ 70 | Qualité acceptable | Vert |
| 50 – 70 | Dégradation notable | Ambre |
| < 50 | Critique | Rouge |
| 0 | Exposition cumulée trop élevée — huile déclassée | Rouge (plancher) |

> Un score de 0 indique que l'exposition thermique et/ou lumineuse cumulée a dépassé le seuil de déclassement du modèle. La valeur reste à 0 même si les conditions redeviennent favorables — l'exposition est irréversible.

- **Alertes** avec cooldown 1 h (pas de doublon) :
  - `quality_warning` — score < 70
  - `quality_critical` — score < 50
  - `high_temperature` — dernière mesure > 30 °C
  - `high_light` — dernière mesure > 5 000 lux
  - `high_humidity` — dernière mesure > 70 %

### Résultats au premier cycle (2026-06-03)

| Consignation | Score | Degré-heures | Lux-heures | Alerte |
|---|---|---|---|---|
| cons-001 | 66.8 | 0.256 | 326.8 | quality_warning |
| cons-002 | 54.6 | 1.106 | 431.8 | quality_warning |

---

---

## Phase 4 — API + Dashboard ✅ Terminée

### Ce qui est fait

| Tâche | Statut |
|-------|--------|
| `services/api/` — FastAPI complet (auth, pool DB, routes REST + WebSocket) | ✅ |
| `services/dashboard/` — React + Vite + Tailwind (feature-based architecture) | ✅ |
| `services/dashboard/nginx.conf` — reverse proxy `/api/*` → FastAPI, SPA fallback | ✅ |
| `docker-compose.yml` — services `api` (port 8000) + `dashboard` (port 3000) actifs | ✅ |
| API health + `/consignments/` retournent 200 | ✅ |
| Dashboard servi via Nginx + proxy `/api/` fonctionnel | ✅ |

### Architecture déployée

```
Browser :3000 → Nginx → /api/* → FastAPI :8000 → TimescaleDB
                       → /*     → React SPA (dist/)
```

### Endpoints API

| Méthode | Chemin | Auth | Description |
|---------|--------|------|-------------|
| GET | `/health` | Non | Health check |
| GET | `/consignments/` | Bearer | Liste + résumé (score, métriques, alertes 24h) |
| GET | `/consignments/{id}/telemetry` | Bearer | Télémétrie downsamplée (`hours=1..720`, `time_bucket` TimescaleDB) |
| GET | `/consignments/{id}/quality` | Bearer | Scores downsamplés (`hours=1..720`, `time_bucket` TimescaleDB) |
| GET | `/alerts/` | Bearer | Alertes récentes (filtre consignment_id, limit=50) |
| WS | `/ws/live?token=` | Query param | Push toutes les 10 s |

### Sélecteur de fenêtre temporelle + downsampling

La page détail expose un sélecteur `1h / 6h / 24h / 7j` qui pilote les graphes
télémétrie **et** score qualité. Le paramètre `hours` est transmis à l'API.

Pour éviter de renvoyer des dizaines de milliers de points (24 h ≈ 8 600 points
bruts, 7 j ≈ 60 000), l'API **downsample** via `time_bucket()` de TimescaleDB.
La taille du bucket s'adapte à la fenêtre — résultat : ~100-200 points quelle
que soit la durée, graphes lisibles, payload léger.

| Fenêtre (`hours`) | Bucket |
|-------------------|--------|
| ≤ 1 h  | 1 min |
| ≤ 6 h  | 5 min |
| ≤ 24 h | 15 min |
| ≤ 72 h | 30 min |
| > 72 h | 1 h |

Choix structurant : le downsampling exploite directement la base time-series —
ce n'est pas un contournement applicatif. Argument défendable côté client.

### Injection manuelle (démo / apprentissage)

Page `/inject` du dashboard permettant à un opérateur de saisir de la
télémétrie à la main pour observer la réaction du modèle.

**Architecture — respect du contrat device-agnostique :** la saisie ne touche
**jamais** la base directement. Un service dédié `manual-injector` publie le
payload JSON sur MQTT → l'ingestion valide (Pydantic) → écrit en base. Une
injection manuelle = juste un autre émetteur sur le contrat. C'est exactement
ce que le contrat device-agnostique permet.

```
Dashboard /inject → Nginx /inject/ → manual-injector → MQTT
   → ingestion (valide) → TimescaleDB → quality-engine (recalcule)
```

`manual-injector` est le **2ᵉ composant à cheval** sur `iot-net` + `backend-net`
(après l'ingestion). Affordance de démo — à restreindre/retirer en production.

**Deux modes :**
- **Point unique** : une mesure → déclenche les alertes instantanées (temp /
  lux / humidité). Impact négligeable sur le score cumulé.
- **Scénario soutenu** : rafale de points **horodatés dans le passé** sur une
  durée simulée → l'intégration trapézoïdale voit une exposition prolongée →
  le score bouge réellement. Presets : canicule 2h, exposition lumière, humidité.

*Validé end-to-end (2026-06-07)* : scénario canicule (38°C, 2h) → score
cons-001 92.7 → 45.3 (`quality_critical`), 24 lignes via ingestion.

### Feature-based architecture React

```
src/
  shared/           # types, apiClient, auth, useLiveData, Navbar, StatusBadge
  features/
    auth/           # LoginPage
    consignments/   # api, hooks, ConsignmentsPage, ConsignmentCard,
                    # ConsignmentDetailPage, TelemetryChart, QualityChart,
                    # TimeWindowSelector
    alerts/         # api, hooks, AlertsTable
    inject/         # api, InjectPage
```

### Dashboard — accès

| URL | Description |
|-----|-------------|
| http://localhost:3000 | Page principale — cards par consignation (live via WS) |
| http://localhost:3000/consignments/{id} | Détail — charts télémétrie + score + alertes |
| http://localhost:8000/docs | OpenAPI auto-générée (FastAPI) |

---

---

## Phase 5 — Durcissement sécurité + documentation ✅ Terminée

### Ce qui est fait

| Tâche | Statut |
|-------|--------|
| ACL MQTT activée — `simulator` write only, `ingestion` read only | ✅ |
| Pipeline validé après activation ACL | ✅ |
| Revue secure-by-design complète — `docs/security-review.md` | ✅ |
| Audit secrets Git — `.gitignore` vérifié | ✅ |
| Actions prod documentées (TLS, CORS, rotation tokens) | ✅ |

### Résultat de la revue

- **7 items OK** : ACL, auth MQTT, Pydantic, segmentation réseau, secrets Git, Bearer token API, WS auth
- **7 items MITIGÉS** (acceptables POC, documentés pour prod) : TLS, CORS, rate limiting, token React baked, port 8000 exposé
- **2 items ACTION** (obligatoires avant tout déploiement réel) : rotation `API_AUTH_TOKEN` et passwords MQTT

Voir `docs/security-review.md` pour le détail complet.

---

## Fixes post-livraison

| Date | Fix | Cause | Action |
|------|-----|-------|--------|
| 2026-06-07 | `API_AUTH_TOKEN` roté | Token `change_me` en production | Nouveau token 64 hex chars dans `.env`, rebuild dashboard |
| 2026-06-07 | Auth DB TimescaleDB (`oliveoil_app`) | `POSTGRES_PASSWORD` dans `.env` divergeait du volume initialisé | `ALTER USER oliveoil_app PASSWORD '...'` dans le container |

---

## POC complet — toutes phases livrées

| Phase | Statut |
|-------|--------|
| Phase 0 — Scaffolding | ✅ |
| Phase 1 — Simulateur | ✅ |
| Phase 2 — Ingestion + persistance | ✅ |
| Phase 3 — Moteur de qualité + alertes | ✅ |
| Phase 4 — API + Dashboard | ✅ |
| Phase 5 — Durcissement sécurité + doc | ✅ |
