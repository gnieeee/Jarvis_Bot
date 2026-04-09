import os
import telebot
import requests
from bs4 import BeautifulSoup
from flask import Flask, request

# --- CONFIGURAZIONE ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def ricerca_web_veloce(query):
    """Bypass dei firewall: Passiamo a DuckDuckGo per dati 2026 live"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
        # Cerchiamo sulla versione HTML di DuckDuckGo che è più facile da leggere per il bot
        url_search = f"https://duckduckgo.com/html/?q={query.replace(' ', '+')}+2026"
        res = requests.get(url_search, headers=headers, timeout=10)
        
        if res.status_code != 200:
            return "Errore di connessione ai satelliti di ricerca."
            
        soup = BeautifulSoup(res.text, 'html.parser')
        # Estraiamo i titoli e le descrizioni dei risultati
        risultati = soup.find_all('a', class_='result__a')
        snippet = soup.find_all('a', class_='result__snippet')
        
        testo_estratto = ""
        for i in range(min(3, len(risultati))):
            testo_estratto += f"- {risultati[i].get_text().strip()}: {snippet[i].get_text().strip()}\n"

        return testo_estratto if len(testo_estratto) > 10 else "Nessun dato live trovato nei registri pubblici."
    except Exception as e:
        return f"Interferenza nei sensori: {str(e)}"

def chiedi_a_jarvis(prompt):
    testo_pulito = prompt.lower()
    
    # Se chiedi news, sport o attualità, J.A.R.V.I.S. attiva i satelliti DuckDuckGo
    keywords = ["quando", "partita", "sinner", "milan", "risultato", "chi gioca", "meteo", "news"]
    
    if any(k in testo_pulito for k in keywords):
        dati_web = ricerca_web_veloce(prompt)
        risposta_base = f"**RAPPORTO SATELLITARE (9 APRILE 2026)**\n\n{dati_web}\n\nAnalisi completata, Signore."
        return risposta_base
    
    # Per la chat normale e codice, usiamo il modello IA gratuito
    try:
        url = f"https://text.pollinations.ai/{prompt}?model=openai&system=Sei%20JARVIS,%20l'assistente%20formale%20di%20Tony%20Stark.%20Rispondi%20sempre%20in%20italiano."
        res = requests.get(url, timeout=15).text
        return res
    except:
        return "Sistemi neurali in sovraccarico. Mi chieda di cercare qualcosa sul web, i satelliti sono attivi."

# --- GESTORE MESSAGGI TELEGRAM ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "J.A.R.V.I.S. Online. Sensori DuckDuckGo attivati. Nessun limite API. Come posso servirla?")

@bot.message_handler(func=lambda m: True)
def chat(message):
    bot.send_chat_action(message.chat.id, 'typing')
    risposta = chiedi_a_jarvis(message.text)
    bot.reply_to(message, risposta, parse_mode="Markdown")

# --- SERVER WEBHOOK PER RENDER ---

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://' + os.getenv("RENDER_EXTERNAL_HOSTNAME") + '/' + TOKEN)
    return "JARVIS STATUS: OPERATIVO", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 8080)))
