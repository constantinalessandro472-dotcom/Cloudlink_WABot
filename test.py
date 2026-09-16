import requests

# L'URL pubblico del tuo tunnel + l'endpoint del server
url = "https://95hwwd0c-5000.euw.devtunnels.ms/webhook/prenotazione"

# I dati della prenotazione che simuliamo dal sito
dati_prenotazione = {
    "nome": "Alessandro",
    "telefono": "393274914212", # Metti il TUO numero con il 39 davanti (es. 393331234567)
    "coperti": 4,
    "data": "Stasera",
    "ora": "21:30"
}

print("Sparando i dati al server...")
risposta = requests.post(url, json=dati_prenotazione)

print(f"Risposta del server: {risposta.status_code}")
print(risposta.text)