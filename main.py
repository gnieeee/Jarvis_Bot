import os
import telebot
import requests
from bs4 import BeautifulSoup
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def ricerca_web_reale(query):
    try:
        # Headers potenziati per sembrare un vero computer Stark
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}
        url = f"https://www.google.com/search?q={query}+date+2026"
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Cerchiamo nei vari snippet di Google
        snippets = soup.find_all(['span', 'div'], class_=['VwiC3b', 'MUwY0b', 'lyLwCc'])
        testo = " ".join([s.get_text() for s in snippets[:5]])
        
        return testo if len(testo) > 10 else "Nessun dato live disponibile."
    except:
        return "Errore di scansione satellitare."

def chiedi_a_jarvis(prompt):
    # Attivazione automatica ricerca per parole chiave
    keywords = ["quando", "partita", "sinner", "milan", "meteo", "risultato", "serie a"]
    info_web = ""
    
    if any(k in prompt.lower() for k in keywords):
        info_web = ricerca_web_reale(prompt)

    try:
        # Il prompt ora obbliga l'IA a usare i dati trovati
        context = f"DATA ATTUALE: 9 Aprile 2026. DATI REALI DAL WEB: {info_web}. DOMANDA: {prompt}"
        url = f"https://text.pollinations.ai/{context}?model=openai&system=Sei%20JARVIS.%20Usa%20i%20DATI%20REALI%20per%20dare%20date%20e%20orari%20precisi.%20Non%20inventare%20nulla."
        return requests.get(url, timeout=20).text
    except:
        return "Sistemi offline, Signore."

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Protocolli 2026 attivi, Signore. La ricerca web è operativa.")

@bot.message_handler(func=lambda m: True)
def chat(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.reply_to(message, chiedi_a_jarvis(message.text))

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
    
