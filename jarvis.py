import os
import asyncio
import edge_tts
import telebot
import threading
from flask import Flask
from google import genai
from google.genai import types

# 1. CONFIGURAZIONE CHIAVI
API_KEY_GOOGLE = os.environ.get("GOOGLE_API_KEY")
TOKEN_TELEGRAM = os.environ.get("TELEGRAM_TOKEN")

client = genai.Client(api_key=API_KEY_GOOGLE)
bot = telebot.TeleBot(TOKEN_TELEGRAM)

# Istruzioni di sistema aggiornate per gestire anche l'udito
config = types.GenerateContentConfig(
    system_instruction="""Sei J.A.R.V.I.S. Rispondi in italiano, formale e conciso. 
    Se nell'audio o nel testo l'utente ti chiede esplicitamente di 'trascrivere', fornisci il testo integrale di ciò che è stato detto. 
    Altrimenti, rispondi al contenuto del messaggio in modo intelligente. Non usare emoji o formattazioni strane.""",
    tools=[types.Tool(google_search=types.GoogleSearch())]
)

chat = client.chats.create(model="gemini-2.5-flash", config=config)

def genera_audio_jarvis(testo, nome_file):
    voce = "it-IT-DiegoNeural"
    comunicate = edge_tts.Communicate(testo, voce)
    asyncio.run(comunicate.save(nome_file))

# --- SERVER WEB PER RENDER ---
app = Flask(__name__)
@app.route('/')
def index(): return "J.A.R.V.I.S. Online"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()

# --- NUOVO MODULO: UDITO (GESTIONE VOCALI) ---
@bot.message_handler(content_types=['voice'])
def gestisci_vocale(message):
    chat_id = message.chat.id
    nome_vocale = f"vocale_{chat_id}.ogg"
    try:
        bot.send_chat_action(chat_id, 'record_voice')
        
        # 1. Scarica il vocale da Telegram
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(nome_vocale, 'wb') as f:
            f.write(downloaded_file)
            
        # 2. Carica l'audio su Google Gemini
        # Gemini supporta nativamente il formato .ogg di Telegram
        audio_caricato = client.files.upload(file=nome_vocale)
        
        # 3. Chiedi a Gemini di ascoltare e rispondere
        risposta = chat.send_message([audio_caricato, "Ascolta questo audio e rispondi secondo le tue istruzioni di sistema."])
        testo_risposta = risposta.text
        
        # 4. Genera risposta audio (o solo testo se è una trascrizione lunga)
        print(f"Jarvis ha ascoltato: {testo_risposta}")
        
        file_risposta_audio = f"jarvis_voce_{chat_id}.mp3"
        genera_audio_jarvis(testo_risposta, file_risposta_audio)
        
        with open(file_risposta_audio, 'rb') as audio:
            bot.send_voice(chat_id, audio, caption=testo_risposta)
            
        # 5. Pulizia
        os.remove(nome_vocale)
        os.remove(file_risposta_audio)
        
    except Exception as e:
        bot.send_message(chat_id, f"Signore, ho avuto difficoltà ad ascoltare il messaggio: {e}")
        if os.path.exists(nome_vocale): os.remove(nome_vocale)

# --- MODULO DOCUMENTI ---
@bot.message_handler(content_types=['document'])
def gestisci_documento(message):
    chat_id = message.chat.id
    nome_file = message.document.file_name
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(nome_file, 'wb') as f: f.write(downloaded_file)
        
        file_caricato = client.files.upload(file=nome_file)
        risposta = chat.send_message([file_caricato, f"Analizza il file {nome_file} e riassumilo."])
        
        file_audio = f"risposta_doc_{chat_id}.mp3"
        genera_audio_jarvis(risposta.text, file_audio)
        with open(file_audio, 'rb') as audio:
            bot.send_voice(chat_id, audio, caption=risposta.text)
        
        os.remove(nome_file)
        os.remove(file_audio)
    except Exception as e:
        bot.send_message(chat_id, f"Errore analisi documento: {e}")

# --- MODULO TESTO ---
@bot.message_handler(func=lambda message: True)
def rispondi_testo(message):
    chat_id = message.chat.id
    try:
        bot.send_chat_action(chat_id, 'record_voice')
        risposta = chat.send_message(message.text)
        file_audio = f"risposta_{chat_id}.mp3"
        genera_audio_jarvis(risposta.text, file_audio)
        with open(file_audio, 'rb') as audio:
            bot.send_voice(chat_id, audio, caption=risposta.text)
        os.remove(file_audio)
    except Exception as e:
        bot.send_message(chat_id, f"Errore: {e}")

print("J.A.R.V.I.S. ONLINE")
bot.infinity_polling()
