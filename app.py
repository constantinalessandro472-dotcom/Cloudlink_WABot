"""
Webhook Flask per prenotazioni -> notifica WhatsApp (Meta Cloud API)
=====================================================================

Riceve i dati di un form di prenotazione (nome, telefono, coperti, ecc.)
via POST e inoltra una notifica come messaggio WhatsApp usando le
WhatsApp Cloud API di Meta.

Configurazione richiesta (vedi .env.example):
- WHATSAPP_TOKEN            token di accesso (permanente o temporaneo)
- WHATSAPP_PHONE_NUMBER_ID  ID del numero mittente configurato su Meta
- NOTIFY_PHONE_NUMBER       numero (formato E.164 senza "+") a cui
                             inviare la notifica di nuova prenotazione
- WHATSAPP_API_VERSION      versione API Graph (default: v20.0)
"""

import logging
import os
from datetime import datetime

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
load_dotenv()

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("prenotazioni-webhook")

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
NOTIFY_PHONE_NUMBER = os.environ.get("NOTIFY_PHONE_NUMBER")
API_VERSION = os.environ.get("WHATSAPP_API_VERSION", "v20.0")

# Chiave opzionale per proteggere l'endpoint: se impostata, il chiamante
# deve inviarla nell'header "X-API-Key". Consigliata in produzione.
API_KEY = os.environ.get("BOOKING_API_KEY")

REQUIRED_FIELDS = ["nome", "telefono", "coperti"]


class ConfigError(Exception):
    """Sollevata quando mancano variabili d'ambiente obbligatorie."""


def _check_config():
    missing = [
        var
        for var in ("WHATSAPP_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "NOTIFY_PHONE_NUMBER")
        if not os.environ.get(var)
    ]
    if missing:
        raise ConfigError(f"Variabili d'ambiente mancanti: {', '.join(missing)}")


def valida_dati(dati: dict) -> list[str]:
    """Controlla i campi obbligatori e la coerenza dei valori. Ritorna una lista di errori (vuota se tutto ok)."""
    errori = []

    for campo in REQUIRED_FIELDS:
        if not str(dati.get(campo, "")).strip():
            errori.append(f"Campo obbligatorio mancante: {campo}")

    coperti = dati.get("coperti")
    if coperti not in (None, ""):
        try:
            n = int(coperti)
            if n <= 0:
                errori.append("Il numero di coperti deve essere maggiore di zero")
        except (TypeError, ValueError):
            errori.append("Il numero di coperti deve essere un numero intero")

    return errori


def componi_messaggio(dati: dict) -> str:
    """Costruisce il testo del messaggio WhatsApp a partire dai dati del form."""
    nome = dati.get("nome")
    telefono = dati.get("telefono")
    coperti = dati.get("coperti")
    data_prenotazione = dati.get("data", "non specificata")
    ora = dati.get("ora", "non specificata")
    note = dati.get("note") or "-"

    return (
        "📅 *Nuova prenotazione*\n\n"
        f"👤 Nome: {nome}\n"
        f"📞 Telefono: {telefono}\n"
        f"🍽️ Coperti: {coperti}\n"
        f"📆 Data: {data_prenotazione}\n"
        f"🕒 Ora: {ora}\n"
        f"📝 Note: {note}\n\n"
        f"Ricevuta il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}"
    )


def invia_messaggio_whatsapp(numero_destinatario: str, testo: str) -> dict:
    """Invia un messaggio di testo tramite le WhatsApp Cloud API. Solleva HTTPError in caso di risposta non 2xx."""
    url = f"https://graph.facebook.com/{API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero_destinatario,
        "type": "text",
        "text": {"body": testo},
    }

    risposta = requests.post(url, headers=headers, json=payload, timeout=10)
    risposta.raise_for_status()
    return risposta.json()


@app.route("/webhook/prenotazione", methods=["POST"])
def ricevi_prenotazione():
    # Protezione opzionale con chiave condivisa
    if API_KEY and request.headers.get("X-API-Key") != API_KEY:
        return jsonify({"successo": False, "errore": "Non autorizzato"}), 401

    try:
        _check_config()
    except ConfigError as exc:
        logger.error(str(exc))
        return jsonify({"successo": False, "errore": "Configurazione server incompleta"}), 500

    dati = request.get_json(silent=True) if request.is_json else request.form.to_dict()
    dati = dati or {}

    if not dati:
        return jsonify({"successo": False, "errore": "Nessun dato ricevuto"}), 400

    errori = valida_dati(dati)
    if errori:
        return jsonify({"successo": False, "errori": errori}), 400

    testo = componi_messaggio(dati)

    try:
        risultato = invia_messaggio_whatsapp(NOTIFY_PHONE_NUMBER, testo)
    except requests.exceptions.HTTPError as exc:
        dettaglio = exc.response.json() if exc.response is not None else str(exc)
        logger.error("Errore API WhatsApp: %s", dettaglio)
        return jsonify({
            "successo": False,
            "errore": "Invio messaggio WhatsApp fallito",
            "dettaglio": dettaglio,
        }), 502
    except requests.exceptions.RequestException as exc:
        logger.error("Errore di rete verso WhatsApp: %s", exc)
        return jsonify({"successo": False, "errore": "Errore di rete verso WhatsApp"}), 502

    message_id = risultato.get("messages", [{}])[0].get("id")
    logger.info("Prenotazione notificata (message_id=%s): %s", message_id, dati)
    return jsonify({"successo": True, "whatsapp_message_id": message_id}), 200


@app.route("/salute", methods=["GET"])
def salute():
    return jsonify({"stato": "ok"}), 200


if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=porta, debug=False)
