# Roadmap

Développement par phases. Travailler **une phase à la fois** ; ne pas
pré-implémenter les suivantes. Vérifier la « définition de terminé » avant
d'avancer.

## Phase 0 — Scaffolding
Le dépôt démarre.
- `cp .env.example .env` et valeurs renseignées.
- Identifiants du broker créés (voir `broker/mosquitto/README.md`).
- `docker compose up` démarre Mosquitto et TimescaleDB.
**Terminé quand** : les deux conteneurs tournent, le broker accepte une
connexion authentifiée, la base répond.

## Phase 1 — Simulateur de devices
- Modèle de consignation (profil de transport / stockage).
- Génération de mesures réalistes ; incidents injectables.
- Publication MQTT conforme au contrat de données.
**Terminé quand** : les messages sont visibles sur le broker.

## Phase 2 — Ingestion + persistance
- Abonnement MQTT authentifié.
- Validation Pydantic de chaque payload ; rejet et log des malformés.
- Schéma TimescaleDB (hypertable) et écriture de la télémétrie.
**Terminé quand** : la télémétrie valide est stockée en base.

## Phase 3 — Moteur de qualité + alertes
- Calcul de l'exposition cumulée (degré-heures, lux-heures).
- Indice de qualité par consignation.
- Génération et persistance des alertes sur dépassement de seuil.
**Terminé quand** : indice et alertes sont calculés et stockés.

## Phase 4 — API + dashboard
- API FastAPI : REST (historique, config) + WebSocket (live), avec token.
- Dashboard React : liste des consignations, jauges, courbes, alertes.
**Terminé quand** : le dashboard affiche les consignations en temps réel.

## Phase 5 — Durcissement sécurité + documentation
- Revue secure-by-design (auth, ACL MQTT, TLS, secrets, exposition).
- Documentation finale et préparation de la présentation.
**Terminé quand** : la revue de sécurité est passée et la doc est à jour.
