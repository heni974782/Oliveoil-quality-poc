# Broker MQTT — Mosquitto

Le broker exige une authentification (`allow_anonymous false`). Le fichier de
mots de passe doit être créé **avant le premier `docker compose up`**, sinon
le conteneur ne démarrera pas.

## Créer les identifiants

Depuis la racine du dépôt, en utilisant l'image Mosquitto :

    docker run --rm -it \
      -v "$(pwd)/broker/mosquitto/config:/mosquitto/config" \
      eclipse-mosquitto:2 \
      mosquitto_passwd -c -b /mosquitto/config/passwd ingestion <mot_de_passe>

Ajouter d'autres utilisateurs (un par device) en retirant l'option `-c` :

    docker run --rm -it \
      -v "$(pwd)/broker/mosquitto/config:/mosquitto/config" \
      eclipse-mosquitto:2 \
      mosquitto_passwd -b /mosquitto/config/passwd device-001 <mot_de_passe>

Le fichier `passwd` est gitignoré : il ne doit jamais être commité. Les mots
de passe choisis ici doivent correspondre à ceux du fichier `.env`.

## ACL (Phase 5)

Activer `acl_file` dans `mosquitto.conf` et fournir un `aclfile` pour
restreindre chaque device à ses propres topics.
