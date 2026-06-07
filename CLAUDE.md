# CLAUDE.md — Contexte projet

> Ce fichier est lu automatiquement par Claude Code à chaque session.
> Il fige les décisions d'architecture et les conventions du projet.
> Mets-le à jour quand une décision change (voir « Journal des décisions »).

## 1. Projet

POC d'apprentissage : **monitoring de la qualité de l'huile d'olive pendant le
stockage et le transport**. Des « consignations » (lots d'huile) sont suivies
en température, luminosité et humidité ; le système calcule un indice de
qualité, lève des alertes, et visualise le tout sur un dashboard web.

Tout est **simulé** — pas d'accès terrain, pas de matériel physique. Mais le
POC n'est **pas jetable** : il est conçu pour évoluer vers la production et,
à terme, des livraisons client.

## 2. Architecture (validée)

Architecture de référence IoT, pub/sub :

    device simulé -> broker MQTT -> service d'ingestion -> base time-series
    -> moteur de qualité -> API -> dashboard

Décision structurante : le **contrat de données est un payload JSON versionné**
(voir `docs/data-contract.md`). C'est l'interface device-agnostique — tout
émetteur qui respecte ce contrat (un futur ESP32, un autre simulateur) se
branche sans modifier le back-end.

Détail dans `docs/architecture.md`.

## 3. Stack technique

| Couche        | Choix              | Pourquoi |
|---------------|--------------------|----------|
| Broker        | Eclipse Mosquitto  | Broker MQTT de référence, léger |
| Transport     | MQTT               | Standard IoT, pub/sub qui découple devices et back-end |
| Ingestion     | Python + paho-mqtt | Abonnement MQTT, validation, écriture en base |
| Validation    | Pydantic           | Schéma strict à la frontière de confiance device -> back-end |
| Base          | TimescaleDB        | PostgreSQL + time-series : SQL transférable, choix de prod réel |
| API           | FastAPI            | Async, génère la doc OpenAPI automatiquement |
| Dashboard     | React              | Choix standard pour une SPA de dashboard |
| Orchestration | Docker Compose     | Reproductibilité, démarrage en une commande |

Tous les services back-end sont en **Python** : choix délibéré pour la
cohérence et la lisibilité (un seul langage à maîtriser pour ce POC).

## 4. Conventions

- **Langue** : code et commentaires de code en **anglais** (portabilité,
  standard professionnel, réutilisation client). Documentation humaine
  (`README.md`, `docs/`) en **français**. — *Décision modifiable, voir §7.*
- Un service = un dossier sous `services/`, avec son `Dockerfile` et son
  `requirements.txt`.
- Tout secret passe par variable d'environnement. `.env` est gitignoré ;
  `.env.example` documente les variables sans valeurs sensibles.
- Code commenté sur la **logique et les choix**, pas sur l'évident.
- Versions des dépendances épinglées au moment d'implémenter chaque service.

## 5. Sécurité — secure by design (non négociable)

- Le broker MQTT exige une **authentification** (`allow_anonymous false`).
  Credentials par device ; ACL pour qu'un device ne publie que sur son topic.
- Le service d'ingestion **valide tout payload entrant** (Pydantic). On ne
  fait jamais confiance à la donnée device (malformé, injection, replay).
- **Aucun secret en dur** dans le code ou dans Git.
- L'**API exige un token** d'authentification, même en POC.
- **Segmentation réseau** : broker + devices sur le réseau Docker `iot-net` ;
  base + services métier sur `backend-net`. L'ingestion est le seul composant
  à cheval sur les deux. Le dashboard ne parle jamais MQTT.
- TLS sur MQTT et sur l'API : étape de production, documentée, non activée en
  POC local.

## 6. Roadmap — une phase à la fois

Travailler **une phase à la fois** ; ne pas pré-implémenter les suivantes.
Vérifier la « définition de terminé » avant d'avancer. Détail dans
`docs/roadmap.md`.

- **Phase 0 — Scaffolding** : le dépôt démarre. `docker compose up` lance le
  broker MQTT et la base. *Terminé quand* : broker et TimescaleDB tournent et
  sont joignables.
- **Phase 1 — Simulateur** : le device-simulator publie des mesures réalistes
  sur MQTT. *Terminé quand* : les messages arrivent sur le broker.
- **Phase 2 — Ingestion + persistance** : l'ingestion valide et écrit en base.
  *Terminé quand* : la télémétrie valide est stockée dans TimescaleDB.
- **Phase 3 — Moteur de qualité + alertes** : indice (exposition cumulée) et
  alertes. *Terminé quand* : indice et alertes sont calculés et stockés.
- **Phase 4 — API + dashboard** : FastAPI + dashboard React (live + historique).
  *Terminé quand* : le dashboard montre les consignations en temps réel.
- **Phase 5 — Durcissement sécurité + doc** : revue secure-by-design, doc finale.

## 7. Hors scope

- Programmation d'automate (PLC) et configuration de serveur OPC UA côté
  terrain : **hors scope** de ce POC et hors du hands-on du porteur. Si une
  évolution future touche ces sujets, le signaler explicitement.
- Validation scientifique de l'indice qualité : le POC prouve le **pipeline**,
  pas la chimie.

## 8. Instructions pour Claude Code

- Une phase à la fois ; ne pré-implémente pas les phases suivantes.
- Respecte les contrats de `docs/data-contract.md` — ne les change pas sans
  bumper `schema_version` et le noter au journal des décisions.
- Après toute décision d'architecture, ajoute une ligne au journal.
- Demande avant d'introduire une dépendance lourde absente de la stack du §3.

## 9. Journal des décisions

| Date       | Décision |
|------------|----------|
| 2026-05-25 | Architecture Option B (MQTT + base time-series + SPA) validée. |
| 2026-05-25 | Simulation logicielle ; pas d'ESP32 pour le moment. |
| 2026-05-25 | Moteur de qualité par règles (exposition cumulée), pas de ML. |
| 2026-05-25 | Code/commentaires en anglais, documentation humaine en français. |
| 2026-06-03 | Phase 3 livrée : intégration trapézoïdale, score [0-100], cooldown alertes 1h. `alerts` table standard (pas hypertable) — PK BIGSERIAL incompatible TimescaleDB. |
| 2026-06-03 | Phase 4 livrée : FastAPI + React feature-based (pas MVC — non idiomatique React). Nginx reverse proxy `/api/*` → FastAPI. Token baked dans bundle React via build arg Docker. |
| 2026-06-03 | Phase 5 livrée : ACL MQTT activée (moindre privilège), revue sécurité complète dans `docs/security-review.md`. POC complet — toutes phases terminées. |
| 2026-06-07 | Fenêtre glissante `QUALITY_WINDOW_DAYS=1` (défaut) : moteur calcule sur les dernières 24h au lieu de l'historique complet. Évite le score figé à 0 sur démo longue durée. |
| 2026-06-07 | Recalibration poids lumineux `QUALITY_LIGHT_WEIGHT=0.005` (était 0.1) : un incident `sun_exposure` ne détruit plus le score instantanément. Probabilité incidents simulateur réduite à 0.5%. |
| 2026-06-07 | Injection manuelle (`/inject`) : service `manual-injector` à cheval iot/backend, publie sur MQTT (pas d'écriture directe en base — respect du contrat device-agnostique). 2ᵉ pont après l'ingestion, assumé comme affordance de démo. Scénarios horodatés dans le passé pour faire bouger le score cumulé. |
