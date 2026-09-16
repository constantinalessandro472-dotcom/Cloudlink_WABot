"""
Webhook Flask per prenotazioni -> notifica WhatsApp (Meta Cloud API)
====================================================================
"""

import logging
import os
from datetime import datetime

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

# Carica le variabili d'ambiente
load_dotenv()

# Inizializza l'app Flask
app = Flask(__name__)
CORS(app)

# Configura il logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("prenotazioni-webhook")

# Variabili WhatsApp
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
NOTIFY_PHONE_NUMBER = os.environ.get("NOTIFY_PHONE_NUMBER")
API_VERSION = os.environ.get("WHATSAPP_API_VERSION", "v20.0")


# ==========================================
# ROTTE PRINCIPALI
# ==========================================

@app.route('/')
def home():
    # Questa è la rotta che fa caricare la tua pagina del Pink Cadillac
    return render_template('Index.html')


@app.route("/salute", methods=["GET"])
def salute():
    # Rotta di test per vedere se il server è vivo
    return jsonify({"stato": "ok"}), 200


@app.route('/webhook', methods=['POST'])
def webhook():
    # Riceve i dati dal form e li manda a WhatsApp
    dati = request.json
    if not dati:
        return jsonify({"successo": False, "errore": "Nessun dato ricevuto"}), 400
    
    url = f"https://graph.facebook.com/{API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Formatta il messaggio
    testo_messaggio = f"Nuova prenotazione dal sito!\nDettagli: {dati}"
    
    payload = {
        "messaging_product": "whatsapp",
        "to": NOTIFY_PHONE_NUMBER,
        "type": "text",
        "text": {"body": testo_messaggio}
    }
    
    try:
        risposta = requests.post(url, json=payload, headers=headers)
        risultato = risposta.json()
        
        if risposta.status_code in [200, 201]:
            message_id = risultato.get("messages", [{}])[0].get("id", "sconosciuto")
            logger.info("Prenotazione notificata (message_id=%s): %s", message_id, dati)
            return jsonify({"successo": True, "whatsapp_message_id": message_id}), 200
        else:
            logger.error("Errore da WhatsApp: %s", risultato)
            return jsonify({"successo": False, "errore": risultato}), 502
            
    except requests.exceptions.RequestException as exc:
        logger.error("Errore di rete verso WhatsApp: %s", exc)
        return jsonify({"successo": False, "errore": "Errore di rete verso WhatsApp"}), 502


# ==========================================
# AVVIO DEL SERVER
# ==========================================
if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=porta, debug=False)
