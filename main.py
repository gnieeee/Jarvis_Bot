import os
import telebot
import requests
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def chiedi_a_jarvis(prompt):
    try:
        # Passiamo al modello 'openai' che è il più compatibile, 
        # chiedendo esplicitamente dati aggiornati nel prompt
        url = f"https://text.pollinations.ai/{prompt}?model=openai&system=Sei%20JARVIS.%20Oggi%20è%20il%209%20Aprile%202026.%20Fornisci%20informazioni%20aggiornate%20sullo%20sport%20e%20sulle%20partite.%20Rispondi%20solo%20in%20italiano."
        response = requests.get(url, timeout=20)
        
        if response.status_code == 200:
            return response.text
        else:
            # Se l'API ha problemi, proviamo il modello 'mistral' come backup
            url_backup = f"https://text.pollinations.ai/{prompt}?model=mistral"
            return requests.get(url_backup, timeout=20).text
    except:
        return "Sistemi in ricalibrazione, Signore. Il server gratuito è sotto pressione."

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "J.A.R.V.I.S. Online. Protocollo Flux attivato. Come posso aiutarla?")

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
