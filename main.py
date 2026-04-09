import os
import telebot
import requests
from flask import Flask, request

# --- CONFIGURAZIONE ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- FUNZIONE IA (Utilizza API Gratuite Aperte) ---
def chiedi_a_jarvis(prompt):
    try:
        # Usiamo un endpoint gratuito che non richiede chiavi API
        url = f"https://text.pollinations.ai/{prompt}?model=openai"
        response = requests.get(url, timeout=15)
        return response.text
    except:
        return "Sistemi in sovraccarico, Signore. Sto ricalibrando i server gratuiti."

# --- FUNZIONE IMMAGINI (Gratis) ---
def genera_immagine(descrizione):
    return f"https://image.pollinations.ai/prompt/{descrizione.replace(' ', '%20')}"

# --- GESTIONE MESSAGGI ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "J.A.R.V.I.S. Online. Sistemi gratuiti attivati. Come posso servirla?")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    bot.reply_to(message, "Analisi file in corso...")
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    testo_file = downloaded_file.decode('utf-8') # Funziona per .txt, .py, .csv
    risposta = chiedi_a_jarvis(f"Analizza questo codice o file e lavoralo: {testo_file}")
    bot.reply_to(message, risposta)

@bot.message_handler(func=lambda m: m.text.startswith('/imm'))
def img_gen(message):
    prompt = message.text.replace('/imm', '')
    bot.send_photo(message.chat.id, genera_immagine(prompt))

@bot.message_handler(func=lambda m: True)
def chat(message):
    bot.send_chat_action(message.chat.id, 'typing')
    risposta = chiedi_a_jarvis(message.text)
    bot.reply_to(message, risposta)

# --- SERVER WEBHOOK ---
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
