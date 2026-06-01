# Architecture

## Vue d'ensemble

Architecture de référence IoT fondée sur un bus de messages pub/sub.

    [device simulé] --MQTT--> [broker] --> [ingestion] --> [TimescaleDB]
                                                               |
                                                  [moteur de qualité]
                                                               |
                                        [API] <--REST/WS--> [dashboard]

## Composants

- **Device simulator** — émule des consignations d'huile (camion, entrepôt)
  et publie des mesures température / luminosité / humidité.
- **Broker MQTT (Mosquitto)** — bus de messages. Découple totalement les
  devices du back-end : un device ne connaît que le broker et un topic.
- **Service d'ingestion** — s'abonne, valide chaque payload, écrit en base.
  C'est la frontière de confiance du système.
- **TimescaleDB** — stockage time-series (PostgreSQL + extension).
- **Moteur de qualité** — calcule l'indice de qualité et les alertes.
- **API (FastAPI)** — expose les données au dashboard.
- **Dashboard (React)** — visualisation live et historique.

## Flux de données et frontières de confiance

device -> [broker, authentifié] -> ingestion -> [validation : rejet des
payloads malformés] -> TimescaleDB -> moteur de qualité -> API ->
[authentification API] -> dashboard.

Deux frontières de confiance explicites : l'authentification du broker, et la
validation de schéma à l'ingestion. La donnée device est non fiable tant
qu'elle n'a pas franchi la validation.

## Segmentation réseau

Deux réseaux Docker :

- `iot-net` — devices + broker.
- `backend-net` — base + services métier.

Le service d'ingestion est **le seul** composant connecté aux deux réseaux :
c'est le point de passage contrôlé entre la zone « terrain » et la zone
back-end. Le dashboard ne parle jamais MQTT directement.

## Décision structurante : contrat device-agnostique

Le contrat de données (`data-contract.md`) est un payload JSON versionné.
Tant qu'un émetteur respecte ce contrat, il est interchangeable sans toucher
au back-end — c'est ce qui rend le POC réutilisable et non jetable.

## POC vs production

| Aspect    | POC                        | Production |
|-----------|----------------------------|------------|
| Broker    | Mosquitto unique, local    | Broker clusterisé ou managé |
| Transport | MQTT en clair (localhost)  | MQTT sur TLS, certificats par device |
| Ingestion | Un process                 | Plusieurs workers (shared subscriptions) |
| Base      | TimescaleDB conteneurisée  | TimescaleDB managée, rétention/agrégats |
| API       | Token statique             | SSO / OAuth |
| Qualité   | Règles déterministes       | Modèle affiné, éventuellement ML |

Aucune de ces évolutions n'impose de réécrire : les contrats restent les mêmes.
