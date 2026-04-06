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
    # Render assegna una porta dinamica, la leggiamo e la usiamo
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Avviamo il finto sito web in background (Multithreading!)
threading.Thread(target=run_web, daemon=True).start()
# -----------------------------------------------

# 2. LOGICA DI TELEGRAM
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
# Avviamo il bot (questo terrà il programma acceso in attesa di messaggi)
bot.infinity_polling()
