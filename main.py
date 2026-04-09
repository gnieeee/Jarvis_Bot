import os
import telebot
import requests
import json
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def chiedi_a_jarvis(prompt):
    try:
        # Usiamo il modello search per navigazione reale 2026
        url = f"https://text.pollinations.ai/{prompt}?model=search&system=Sei%20JARVIS.%20Oggi%20è%20il%209%20Aprile%202026.%20Rispondi%20solo%20con%20il%20testo%20finale%20in%20italiano."
        response = requests.get(url, timeout=30)
        
        testo_grezzo = response.text
        
        # Se il server ci manda un JSON tecnico, proviamo a estrarre solo il messaggio
        try:
            dati = json.loads(testo_grezzo)
            if 'choices' in dati:
                return dati['choices'][0]['message']['content']
            elif 'content' in dati:
                return dati['content']
        except:
            # Se non è un JSON, puliamo il testo da eventuali residui di codice
            return testo_grezzo.split('"content":')[-1].replace('}', '').replace('"', '').strip()
            
        return testo_grezzo
    except:
        return "Sistemi in ricalibrazione, Signore. La connessione web è instabile."

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "J.A.R.V.I.S. Online. Protocolli di pulizia dati attivati. Come posso aiutarla?")

@bot.message_handler(func=lambda m: True)
def chat(message):
    bot.send_chat_action(message.chat.id, 'typing')
    risposta = chiedi_a_jarvis(message.text)
    bot.reply_to(message, risposta)

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
