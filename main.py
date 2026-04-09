import os
import telebot
import requests
from flask import Flask, request

# --- CONFIGURAZIONE CORE ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- MOTORE CEREBRALE (Gratuito e Senza API Key) ---
def chiedi_a_jarvis(prompt):
    """Bypass totale: utilizza tunnel gratuiti verso modelli GPT-4/Search"""
    try:
        # Tentativo 1: Motore ad alte prestazioni (Ottimo per codice e logica)
        url = f"https://text.pollinations.ai/{prompt}?model=openai&system=Sei%20JARVIS%20l'assistente%20di%20Tony%20Stark.%20Rispondi%20sempre%20in%20italiano%20in%20modo%20formale."
        response = requests.get(url, timeout=15)
        if response.status_code == 200 and len(response.text) > 2:
            return response.text
        
        # Tentativo 2: Motore di riserva con capacità di ricerca web
        url_alt = f"https://text.pollinations.ai/{prompt}?model=search"
        response_alt = requests.get(url_alt, timeout=15)
        return response_alt.text

    except Exception:
        return "Sistemi in ricalibrazione, Signore. Il flusso dati è momentaneamente instabile. Riprovi tra pochi istanti."

# --- GENERATORE IMMAGINI (Gratuito) ---
def genera_immagine(descrizione):
    # Converte il testo in URL valido per il generatore AI
    prompt_pulito = descrizione.replace(' ', '%20')
    return f"https://image.pollinations.ai/prompt/{prompt_pulito}?width=1024&height=1024&nologo=true"

# --- LOGICA DEL BOT TELEGRAM ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "J.A.R.V.I.S. Online, Signore. Protocolli gratuiti attivati. Nessuna chiave API richiesta. Come posso aiutarla?")

@bot.message_handler(commands=['imm'])
def comando_foto(message):
    descrizione = message.text.replace('/imm', '').strip()
    if not descrizione:
        bot.reply_to(message, "Signore, deve fornirmi una descrizione per la generazione dell'immagine.")
        return
    bot.send_chat_action(message.chat.id, 'upload_photo')
    bot.send_photo(message.chat.id, genera_immagine(descrizione), caption=f"Ecco il risultato per: {descrizione}")

@bot.message_handler(content_types=['document', 'text'])
def gestore_universale(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    # Se l'utente invia un file (es. .py, .txt, .js)
    if message.content_type == 'document':
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            contenuto = downloaded_file.decode('utf-8')
            quesito = f"Analizza e lavora questo codice/testo:\n\n{contenuto}"
            risposta = chiedi_a_jarvis(quesito)
            bot.reply_to(message, risposta)
        except:
            bot.reply_to(message, "Non riesco a leggere questo tipo di file, Signore. Si assicuri che sia un file di testo o codice.")
    
    # Se l'utente invia un messaggio di testo normale
    else:
        risposta = chiedi_a_jarvis(message.text)
        bot.reply_to(message, risposta)

# --- CONFIGURAZIONE SERVER RENDER (WEBHOOK) ---

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://' + os.getenv("RENDER_EXTERNAL_HOSTNAME") + '/' + TOKEN)
    return "JARVIS STATUS: OPERATIVO", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 8080)))
