import os
import telebot
import requests
from bs4 import BeautifulSoup
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def ricerca_web_veloce(query):
    """Cerca su Google e restituisce il testo pulito immediatamente"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}+2026"
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Estraiamo i dati principali (snippet di Google)
        snippets = soup.find_all(['span', 'div'], class_=['VwiC3b', 'MUwY0b', 'lyLwCc'])
        info = ". ".join([s.get_text() for s in snippets[:2]])
        return info if len(info) > 10 else "Nessun dato trovato."
    except:
        return "Errore di connessione ai satelliti."

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "J.A.R.V.I.S. Online. Protocollo di emergenza attivo. Sono pronto, Signore.")

@bot.message_handler(func=lambda m: True)
def chat(message):
    bot.send_chat_action(message.chat.id, 'typing')
    testo = message.text.lower()
    
    # Se chiedi news, sport o meteo, J.A.R.V.I.S. risponde DIRETTAMENTE con Google
    if any(k in testo for k in ["quando", "partita", "sinner", "milan", "risultato", "chi gioca"]):
        dati = ricerca_web_veloce(message.text)
        risposta = f"**Rapporto Satellitare 9 Aprile 2026:**\n\n{dati}\n\nSpero che queste informazioni le siano utili, Signore."
        bot.reply_to(message, risposta, parse_mode="Markdown")
    else:
        # Per la chat normale, usiamo un endpoint di backup molto più leggero
        try:
            url = f"https://text.pollinations.ai/{message.text}?model=mistral&system=Rispondi%20formale"
            res = requests.get(url, timeout=10).text
            bot.reply_to(message, res)
        except:
            bot.reply_to(message, "I sistemi neurali sono in attesa. Mi chieda pure delle ricerche web, quelle sono operative.")

# --- SERVER WEBHOOK (Identico) ---
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://' + os.getenv("RENDER_EXTERNAL_HOSTNAME") + '/' + TOKEN)
    return "JARVIS ONLINE", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 8080)))
