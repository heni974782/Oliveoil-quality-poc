# Revue sécurité — POC Monitoring Huile d'Olive

Revue effectuée en Phase 5. Chaque item est classé **OK** (en place),
**MITIGÉ** (atténué pour le POC, chemin vers prod documenté), ou
**ACTION** (doit être corrigé avant tout déploiement réel).

---

## 1. Authentification MQTT

| Item | Statut | Détail |
|------|--------|--------|
| Connexions anonymes | **OK** | `allow_anonymous false` dans `mosquitto.conf` |
| Credentials par service | **OK** | Users distincts : `simulator`, `ingestion` |
| ACL par user | **OK** | `simulator` → write only, `ingestion` → read only |
| Rotation des credentials | **ACTION** | Changer les passwords MQTT avant tout déploiement non-local |

### ACL en place

```
user simulator
topic write oliveoil/#       # peut publier, ne peut pas lire

user ingestion
topic read oliveoil/#        # peut s'abonner, ne peut pas publier
```

Principe : un device compromis ne peut pas lire la télémétrie des autres
devices, et ne peut pas se faire passer pour l'ingestion.

---

## 2. Validation des données

| Item | Statut | Détail |
|------|--------|--------|
| Validation payload ingestion | **OK** | Pydantic v2 — rejet strict des payloads malformés |
| Inconnu `schema_version` | **OK** | Ingestion refuse tout payload dont `schema_version` est inconnu |
| Idempotence | **OK** | `ON CONFLICT (consignment_id, time) DO NOTHING` |
| Injection SQL | **OK** | Requêtes paramétrées psycopg — pas de formatage de chaîne |

---

## 3. API FastAPI

| Item | Statut | Détail |
|------|--------|--------|
| Authentification | **OK** | Bearer token sur tous les endpoints REST |
| WebSocket auth | **OK** | Token passé en query param `?token=` |
| Force du token | **OK** | `API_AUTH_TOKEN` roté vers un token aléatoire 64 hex chars (2026-06-07) |
| CORS | **MITIGÉ** | `allow_origins=["*"]` acceptable derrière Nginx sur réseau interne. En prod : restreindre à l'origine du dashboard |
| TLS (HTTPS) | **MITIGÉ** | Non activé en POC local. En prod : Nginx termine TLS, certificat Let's Encrypt ou CA interne |
| Rate limiting | **MITIGÉ** | Non implémenté. En prod : Nginx `limit_req_zone` ou middleware FastAPI |
| Exposition port | **MITIGÉ** | Port 8000 exposé sur l'hôte pour tests Postman. En prod : supprimer l'exposition, seul Nginx parle à l'API |

---

## 4. Dashboard React

| Item | Statut | Détail |
|------|--------|--------|
| Token baked dans le bundle | **MITIGÉ** | `VITE_API_TOKEN` injecté à la compilation via build arg Docker. Acceptable pour dashboard interne salle de contrôle (réseau isolé). Inacceptable pour tout accès internet |
| Pas de login utilisateur | **MITIGÉ** | Un seul token partagé. En prod multi-utilisateur : SSO / OAuth |

---

## 5. Segmentation réseau Docker

| Item | Statut | Détail |
|------|--------|--------|
| Réseau `iot-net` | **OK** | Devices + broker uniquement |
| Réseau `backend-net` | **OK** | Base + services métier uniquement |
| Ingestion seul pont | **OK** | Seul service connecté aux deux réseaux |
| Dashboard → MQTT | **OK** | Impossible — dashboard sur `backend-net` uniquement |

---

## 6. Secrets et Git

| Item | Statut | Détail |
|------|--------|--------|
| `.env` gitignore | **OK** | Secrets hors Git |
| `broker/.../passwd` gitignore | **OK** | Hashes MQTT hors Git |
| `admin.txt` gitignore | **OK** | Notes d'administration hors Git |
| Secrets dans le code | **OK** | Aucun — tout via variables d'environnement |
| `.env.example` documenté | **OK** | Variables documentées sans valeurs sensibles |

---

## 7. TLS — chemin vers la production

Non activé en POC (réseau Docker local). Étapes pour la production :

**MQTT :**
```
# mosquitto.conf
listener 8883
certfile  /mosquitto/certs/server.crt
keyfile   /mosquitto/certs/server.key
cafile    /mosquitto/certs/ca.crt
require_certificate false  # ou true pour mTLS device
tls_version tlsv1.2
```

**API :**
Nginx termine TLS en amont de FastAPI :
```nginx
server {
    listen 443 ssl;
    ssl_certificate     /etc/nginx/certs/server.crt;
    ssl_certificate_key /etc/nginx/certs/server.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
}
```

---

## 8. Résumé — actions obligatoires avant déploiement réel

| Priorité | Action |
|----------|--------|
| ~~CRITIQUE~~ | ~~Changer `API_AUTH_TOKEN`~~ — **DONE 2026-06-07** |
| CRITIQUE | Changer les passwords MQTT (`simulator`, `ingestion`) |
| HAUTE | Activer TLS sur MQTT (port 8883) |
| HAUTE | Activer TLS sur l'API (Nginx + certificat) |
| HAUTE | Restreindre CORS à l'origine du dashboard |
| MOYENNE | Retirer l'exposition du port 8000 sur l'hôte |
| MOYENNE | Implémenter rate limiting sur l'API |
| FAIBLE | Envisager SSO/OAuth si accès multi-utilisateur |
