import os
import telebot
import requests
from flask import Flask, request

# --- CONFIGURAZIONE ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- MOTORE CEREBRALE CON TRIPLA RIDONDANZA ---
def chiedi_a_jarvis(prompt):
    """
    Tenta di ottenere una risposta usando diversi endpoint gratuiti.
    Se uno fallisce (es. 502 Bad Gateway), passa automaticamente al successivo.
    """
    # Endpoint 1: OpenAI Large (Tunnel)
    # Endpoint 2: Search Optimized (Per news e attualità)
    # Endpoint 3: Mistral (Backup stabile)
    motori = [
    f"https://text.pollinations.ai/{prompt}?model=openai&system=Sei%20JARVIS.%20Rispondi%20formale.%20Se%20non%20conosci%20una%20risposta%20o%20non%20hai%20dati%20reali%20aggiornati,%20ammettilo%20e%20non%20inventare%20mai%20nomi%20o%20date.",
    f"https://text.pollinations.ai/{prompt}?model=search",
    f"https://text.pollinations.ai/{prompt}?model=mistral"
    ]
    
    for url in motori:
        try:
            response = requests.get(url, timeout=15)
            # Verifica che la risposta sia valida e non un errore di gateway
            if response.status_code == 200 and "Bad Gateway" not in response.text and len(response.text) > 5:
                return response.text
        except Exception:
            continue
            
    return "Sistemi critici, Signore. I database esterni sono saturi. Riprovi tra 30 secondi."

def genera_immagine(descrizione):
    p = descrizione.replace(' ', '%20')
    return f"https://image.pollinations.ai/prompt/{p}?width=1024&height=1024&nologo=true"

# --- GESTIONE TELEGRAM ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "J.A.R.V.I.S. Online. Tripla ridondanza attiva. Come posso aiutarla?")

@bot.message_handler(commands=['imm'])
def img(message):
    prompt = message.text.replace('/imm', '').strip()
    if not prompt:
        bot.reply_to(message, "Descrizione mancante, Signore.")
        return
    bot.send_chat_action(message.chat.id, 'upload_photo')
    bot.send_photo(message.chat.id, genera_immagine(prompt))

@bot.message_handler(content_types=['document', 'text'])
def handle_all(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    if message.content_type == 'document':
        try:
            file_info = bot.get_file(message.document.file_id)
            data = bot.download_file(file_info.file_path)
            content = data.decode('utf-8')
            bot.reply_to(message, chiedi_a_jarvis(f"Analizza questo file:\n\n{content}"))
        except:
            bot.reply_to(message, "Formato file non supportato.")
    else:
        bot.reply_to(message, chiedi_a_jarvis(message.text))

# --- WEBHOOK SERVER ---

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
