# Image de base pour un service Python du POC.
# À affiner lors de la phase qui implémente ce service.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# TODO : définir le vrai entrypoint à l'implémentation du service.
CMD ["python", "-m", "src.main"]
