# Webhook prenotazioni → WhatsApp

Server Flask che riceve i dati di un form di prenotazione e invia una
notifica su WhatsApp tramite le **WhatsApp Cloud API** di Meta.

## 1. Setup

```bash
python -m venv venv
source venv/bin/activate  # su Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Compila `.env` con i tuoi valori (vedi sezione 2).

Avvio in locale:

```bash
python app.py
```

## 2. Dove trovare le credenziali WhatsApp

1. Crea un'app su [developers.facebook.com](https://developers.facebook.com/),
   aggiungi il prodotto **WhatsApp**.
2. Nella dashboard "WhatsApp > Erogazione API" trovi:
   - **Token di accesso temporaneo** (24h, utile per i test) — per la
     produzione serve un token permanente generato tramite un
     System User in Meta Business Suite.
   - **Phone number ID** del numero mittente di test.
3. `NOTIFY_PHONE_NUMBER` è il numero che riceverà le notifiche (il tuo
   cellulare o quello del ristorante), in formato E.164 senza il `+`
   (es. `393331234567`).
4. In modalità test, il numero destinatario deve essere aggiunto alla
   lista dei "numeri di test" nella dashboard, altrimenti l'invio fallisce.

## 3. Come chiamarlo dal form

```bash
curl -X POST http://localhost:5000/webhook/prenotazione \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Mario Rossi",
    "telefono": "3331234567",
    "coperti": 4,
    "data": "20/09/2026",
    "ora": "20:30",
    "note": "Tavolo vicino alla finestra"
  }'
```

Funziona anche con `application/x-www-form-urlencoded` (form HTML
classico): basta che i campi si chiamino `nome`, `telefono`, `coperti`,
`data`, `ora`, `note`.

## 4. Nota importante: finestra delle 24 ore

Le Cloud API distinguono tra:
- **messaggi di testo liberi** (quelli usati qui): inviabili solo se il
  numero destinatario ha avuto un'interazione con il tuo numero
  WhatsApp Business nelle ultime 24 ore;
- **messaggi template**: pre-approvati da Meta, unico modo per iniziare
  una conversazione fuori dalla finestra delle 24 ore.

Per il caso d'uso "notifica al gestore/staff" spesso basta far
scrivere una volta il numero dello staff al numero WhatsApp Business
per aprire la finestra. Se invece vuoi notificare il *cliente* che ha
prenotato (fuori dalla finestra), dovrai creare un template su Meta e
sostituire il payload in `invia_messaggio_whatsapp` con uno di tipo
`"type": "template"`.

## 5. Sicurezza — cose da sistemare prima di andare in produzione

- **HTTPS obbligatorio**: esponi l'endpoint solo dietro TLS (es. dietro
  un reverse proxy Nginx con certificato, o su un hosting che lo
  fornisce già).
- **Autenticazione dell'endpoint**: è già presente il supporto a una
  chiave condivisa (`BOOKING_API_KEY` + header `X-API-Key`); attivala
  impostando la variabile e facendola inviare dal form.
- **Segreti**: non committare mai `.env`; in produzione usa i secret
  manager della piattaforma di hosting invece del file.
- **Rate limiting**: valuta `flask-limiter` per evitare abusi
  dell'endpoint pubblico.
- **CORS**: se il form gira su un dominio diverso dal server, aggiungi
  `flask-cors` e limita l'origine consentita.
- **Log**: il numero di telefono del cliente finisce nei log; se ti
  serve conformità GDPR, valuta di mascherarlo o di limitarne la
  retention.

## 6. Struttura del progetto

```
whatsapp-prenotazioni/
├── app.py            # server Flask
├── requirements.txt  # dipendenze
├── .env.example       # template variabili d'ambiente
└── README.md
```
