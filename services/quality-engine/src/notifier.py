"""
Webhook notifier for quality alerts.

NOTIFICATION_WEBHOOK_URL   — target URL; empty = disabled (no-op).
NOTIFICATION_WEBHOOK_FORMAT — generic (default) | teams | slack
NOTIFICATION_ALERT_TYPES   — comma-separated alert_type values to forward;
                              default: high_temperature,high_light,high_humidity
"""

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

log = logging.getLogger(__name__)

WEBHOOK_URL    = os.getenv("NOTIFICATION_WEBHOOK_URL", "").strip()
WEBHOOK_FORMAT = os.getenv("NOTIFICATION_WEBHOOK_FORMAT", "generic").lower()

_raw = os.getenv("NOTIFICATION_ALERT_TYPES", "high_temperature,high_light,high_humidity")
ALERT_TYPES = {t.strip() for t in _raw.split(",") if t.strip()}


# ---------------------------------------------------------------------------
# Payload builders — one per format
# ---------------------------------------------------------------------------

def _generic(alert_type, severity, consignment_id, value, threshold, message):
    return {
        "event":          "iot_alert",
        "alert_type":     alert_type,
        "severity":       severity,
        "consignment_id": consignment_id,
        "value":          value,
        "threshold":      threshold,
        "message":        message,
        "timestamp":      datetime.now(timezone.utc).isoformat(),
    }


def _teams(alert_type, severity, consignment_id, value, threshold, message):
    icon  = "🚨" if severity == "critical" else "⚠️"
    color = "FF0000" if severity == "critical" else "FF8C00"
    return {
        "@type":     "MessageCard",
        "@context":  "https://schema.org/extensions",
        "summary":    f"Alerte IoT — {alert_type}",
        "themeColor": color,
        "title":      f"{icon} {alert_type} — {consignment_id}",
        "sections": [{
            "facts": [
                {"name": "Consignation", "value": consignment_id},
                {"name": "Valeur",       "value": str(value)},
                {"name": "Seuil",        "value": str(threshold)},
                {"name": "Sévérité",     "value": severity},
                {"name": "Message",      "value": message},
            ],
        }],
    }


def _slack(alert_type, severity, consignment_id, value, threshold, message):
    icon = "🚨" if severity == "critical" else "⚠️"
    return {
        "text": f"{icon} Alerte IoT — {alert_type} sur {consignment_id}",
        "blocks": [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{icon} {alert_type}* — `{consignment_id}`\n"
                    f"Valeur : *{value}* | Seuil : {threshold}\n"
                    f"_{message}_"
                ),
            },
        }],
    }


_BUILDERS = {"teams": _teams, "slack": _slack}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def notify(
    alert_type: str,
    severity: str,
    consignment_id: str,
    value: float,
    threshold: float,
    message: str,
) -> None:
    """Post a webhook notification. Silent no-op if URL not configured or type not in scope."""
    if not WEBHOOK_URL or alert_type not in ALERT_TYPES:
        return

    builder = _BUILDERS.get(WEBHOOK_FORMAT, _generic)
    payload = builder(alert_type, severity, consignment_id, value, threshold, message)

    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            log.info("Webhook sent: alert_type=%s status=%d", alert_type, resp.status)
    except (urllib.error.URLError, OSError) as exc:
        # Never crash the engine loop on notification failure.
        log.warning("Webhook failed (alert_type=%s): %s", alert_type, exc)
