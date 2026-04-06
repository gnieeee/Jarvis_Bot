import os
import asyncio
import edge_tts
import telebot
import threading
from flask import Flask
from google import genai
from google.genai import types

# 1. LETTURA CHIAVI DAL CLOUD
API_KEY_GOOGLE = os.environ.get("GOOGLE_API_KEY")
TOKEN_TELEGRAM = os.environ.get("TELEGRAM_TOKEN")

# Inizializzazione
client = genai.Client(api_key=API_KEY_GOOGLE)
bot = telebot.TeleBot(TOKEN_TELEGRAM)

config = types.GenerateContentConfig(
    system_instruction="Da ora in poi sei J.A.R.V.I.S. Rispondi in italiano in modo formale e conciso. Non usare emoji o asterischi.",
    tools=[types.Tool(google_search=types.GoogleSearch())]
)

# Questa è la sessione di chat che ricorderà la cronologia
chat = client.chats.create(model="gemini-2.5-flash", config=config)

def genera_audio_jarvis(testo, nome_file):
    voce = "it-IT-DiegoNeural"
    comunicate = edge_tts.Communicate(testo, voce)
    asyncio.run(comunicate.save(nome_file))

# --- IL TRUCCO PER RENDER (Dummy Web Server) ---
app = Flask(__name__)

@app.route('/')
def index():
    return "J.A.R.V.I.S. Sistemi Online. Server Operativo."

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()
# -----------------------------------------------

# --- NUOVO MODULO: GESTIONE DEI DOCUMENTI ---
@bot.message_handler(content_types=['document'])
def gestisci_documento(message):
    chat_id = message.chat.id
    try:
        bot.send_message(chat_id, "Documento ricevuto, Signore. Download in corso...")
        
        # 1. Scarica il file da Telegram
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        nome_file = message.document.file_name
        
        # Salva temporaneamente il file sul server Render
        with open(nome_file, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        bot.send_message(chat_id, "Lettura e analisi dei dati completata. Elaborazione riassunto...")
        
        # 2. Carica il file su Google Gemini
        file_caricato = client.files.upload(file=nome_file)
        
        # 3. Chiedi a Jarvis di presentare il file
        prompt = f"Ho appena caricato il file {nome_file}. Fammi un riassunto formale, brillante e conciso del suo contenuto per capire di cosa tratta, poi chiedimi se voglio approfondire qualche capitolo o concetto in particolare."
        risposta = chat.send_message([file_caricato, prompt])
        testo_pulito = risposta.text
        
        # 4. Genera e invia l'audio
        file_audio = f"risposta_doc_{chat_id}.mp3"
        genera_audio_jarvis(testo_pulito, file_audio)
        
        with open(file_audio, 'rb') as audio:
            bot.send_voice(chat_id, audio, caption=testo_pulito)
            
        # 5. Pulizia di sistema (Vitale per non intasare il server)
        os.remove(nome_file)
        os.remove(file_audio)
        
    except Exception as e:
        bot.send_message(chat_id, f"Mi scusi Signore, c'è stato un errore nell'analisi del documento: {e}")

# --- MODULO CLASSICO: MESSAGGI DI TESTO ---
@bot.message_handler(func=lambda message: True)
def rispondi_a_messaggio(message):
    comando_utente = message.text
    chat_id = message.chat.id
    
    try:
        bot.send_chat_action(chat_id, 'record_voice')
        
        risposta = chat.send_message(comando_utente)
        testo_pulito = risposta.text
        
        file_audio = f"risposta_{chat_id}.mp3"
        genera_audio_jarvis(testo_pulito, file_audio)
        
        with open(file_audio, 'rb') as audio:
            bot.send_voice(chat_id, audio, caption=testo_pulito)
            
        os.remove(file_audio)
        
    except Exception as e:
        bot.send_message(chat_id, f"Mi scusi Signore, errore di sistema: {e}")

print("-" * 50)
print("SISTEMA J.A.R.V.I.S. IN ASCOLTO SU TELEGRAM E SUL WEB...")
print("-" * 50)

# Avviamo il bot
bot.infinity_polling()
