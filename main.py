import os
import telebot
import requests
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def chiedi_a_jarvis(prompt):
    """Bypass per ricerca in tempo reale 2026"""
    try:
        # Forziamo il modello 'search' che ignora la data di addestramento e usa il web
        url = f"https://text.pollinations.ai/{prompt}?model=search&system=Sei%20JARVIS.%20Oggi%20è%20il%209%20Aprile%202026.%20Usa%20sempre%20i%20dati%20web%20più%20recenti."
        response = requests.get(url, timeout=20)
        
        if response.status_code == 200:
            return response.text
        return "Sistemi lenti, Signore. Riprovi tra un istante."
    except:
        return "Connessione neurale interrotta. Riprovo..."

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "J.A.R.V.I.S. Online. Sensori attivati. Come posso aiutarla?")

@bot.message_handler(commands=['imm'])
def img(message):
    desc = message.text.replace('/imm', '').strip()
    if desc:
        bot.send_photo(message.chat.id, f"https://image.pollinations.ai/prompt/{desc.replace(' ','%20')}")

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
    return "ONLINE", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 8080)))
