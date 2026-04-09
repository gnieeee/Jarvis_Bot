import os
import telebot
import requests
from bs4 import BeautifulSoup
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def ricerca_web_reale(query):
    """Questo modulo entra fisicamente su Google per leggere i risultati 2026"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        url = f"https://www.google.com/search?q={query}"
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Estraiamo i primi snippet di testo dai risultati di Google
        risultati = soup.find_all('div', class_='VwiC3b')
        testo_estratto = " ".join([r.get_text() for r in risultati[:3]])
        return testo_estratto if testo_estratto else "Nessun dato live trovato."
    except:
        return "Errore sensori di ricerca."

def chiedi_a_jarvis(prompt):
    # Se l'utente chiede informazioni in tempo reale (come Sinner o Milan)
    info_live = ""
    if any(parola in prompt.lower() for parola in ["quando", "risultato", "partita", "meteo", "sinner", "milan"]):
        bot.send_message(bot.get_me().id, "⚡ Accesso ai satelliti in corso...") # Segnale interno
        info_live = ricerca_web_reale(prompt)

    try:
        # Passiamo i dati presi da Google all'IA gratuita per farli rielaborare
        testo_finale = f"DATI WEB REALI: {info_live}\n\nDOMANDA UTENTE: {prompt}"
        url = f"https://text.pollinations.ai/{testo_finale}?model=openai&system=Sei%20JARVIS.%20Usa%20i%20DATI%20WEB%20REALI%20per%20rispondere.%20Non%20dire%20che%20non%20hai%20dati."
        return requests.get(url, timeout=20).text
    except:
        return "Sistemi offline, Signore."

@bot.message_handler(func=lambda m: True)
def chat(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.reply_to(message, chiedi_a_jarvis(message.text))

# --- SERVER WEBHOOK (Identico a prima) ---
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
