import os
import asyncio
import edge_tts
import telebot
import threading
import re
from flask import Flask
from google import genai
from google.genai import types

# --- CONFIGURAZIONE MULTI-KEY ---
# Recuperiamo le 3 chiavi da Render
CHIAVI_DISPONIBILI = [
    os.environ.get("GOOGLE_API_KEY"),
    os.environ.get("GOOGLE_API_KEY_2"),
    os.environ.get("GOOGLE_API_KEY_3")
]
# Filtriamo solo quelle effettivamente inserite
CHIAVI_VALIDE = [k for k in CHIAVI_DISPONIBILI if k]

TOKEN_TELEGRAM = os.environ.get("TELEGRAM_TOKEN")
ID_AMMINISTRATORE = 123456789  # <--- METTI IL TUO ID QUI

# Inizializziamo i client per ogni chiave
clients = [genai.Client(api_key=k) for k in CHIAVI_VALIDE]
indice_chiave_attuale = 0

bot = telebot.TeleBot(TOKEN_TELEGRAM)
sessioni_utenti = {}

def crea_nuova_sessione(client_scelto):
    config = types.GenerateContentConfig(
        system_instruction="Sei J.A.R.V.I.S. Rispondi in italiano, formale e conciso. Non usare emoji.",
        tools=[types.Tool(google_search=types.GoogleSearch())]
    )
    return client_scelto.chats.create(model="models/gemini-1.5-flash", config=config)

def ottieni_sessione(chat_id):
    global indice_chiave_attuale
    if chat_id not in sessioni_utenti:
        client_attuale = clients[indice_chiave_attuale]
        sessioni_utenti[chat_id] = crea_nuova_sessione(client_attuale)
    return sessioni_utenti[chat_id]

def genera_audio_jarvis(testo, nome_file):
    voce = "it-IT-DiegoNeural"
    comunicate = edge_tts.Communicate(testo, voce)
    asyncio.run(comunicate.save(nome_file))

# --- SERVER FLASK PER RENDER ---
app = Flask(__name__)
@app.route('/')
def index(): return "J.A.R.V.I.S. Multi-Key: Online"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
threading.Thread(target=run_web, daemon=True).start()

# --- LOGICA DI ROTAZIONE CHIAVI ---
def invia_messaggio_con_rotazione(chat_id, messaggio_payload):
    global indice_chiave_attuale
    tentativi = 0
    max_tentativi = len(clients)

    while tentativi < max_tentativi:
        try:
            chat = ottieni_sessione(chat_id)
            return chat.send_message(messaggio_payload)
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                # Chiave esaurita! Passiamo alla prossima
                indice_chiave_attuale = (indice_chiave_attuale + 1) % len(clients)
                # Reset della sessione per l'utente con la nuova chiave
                sessioni_utenti[chat_id] = crea_nuova_sessione(clients[indice_chiave_attuale])
                tentativi += 1
                print(f"🔄 Switch alla chiave {indice_chiave_attuale + 1} per l'utente {chat_id}")
            else:
                raise e # Errore diverso (es. 404), lo lanciamo per gestirlo dopo
    
    raise Exception("Tutte le API Key sono esaurite per oggi.")

# --- TELEGRAM HANDLERS ---
@bot.message_handler(commands=['start', 'reset'])
def welcome(message):
    chat_id = message.chat.id
    sessioni_utenti[chat_id] = crea_nuova_sessione(clients[indice_chiave_attuale])
    bot.send_message(chat_id, "Sistemi J.A.R.V.I.S. ricaricati con Multi-Key. Collegamento stabilito.")

@bot.message_handler(content_types=['text', 'voice', 'audio'])
def handle_all(message):
    chat_id = message.chat.id
    try:
        bot.send_chat_action(chat_id, 'record_voice')
        
        # Gestione Input (Testo o Audio)
        if message.content_type in ['voice', 'audio']:
            ext = ".ogg" if message.content_type == 'voice' else ".mp3"
            f_info = message.voice if message.content_type == 'voice' else message.audio
            nome_f = f"rec_{chat_id}{ext}"
            with open(nome_f, 'wb') as f:
                f.write(bot.download_file(bot.get_file(f_info.file_id).file_path))
            
            # Carichiamo il file usando il client attuale
            u_file = clients[indice_chiave_attuale].files.upload(file=nome_f)
            risposta = invia_messaggio_con_rotazione(chat_id, [u_file, "Rispondi a questo audio."])
            os.remove(nome_f)
        else:
            risposta = invia_messaggio_con_rotazione(chat_id, message.text)

        # Generazione Audio Risposta
        txt = risposta.text
        f_voc = f"v_{chat_id}.mp3"
        genera_audio_jarvis(re.sub(r'```.*?```', '', txt, flags=re.DOTALL).strip() or "Ricevuto.", f_voc)
        bot.send_voice(chat_id, open(f_voc, 'rb'), caption=txt[:1000])
        os.remove(f_voc)

    except Exception as e:
        if "esaurite" in str(e):
            bot.send_message(chat_id, "🛑 Protocollo 'Blackout': Tutte le chiavi sono esaurite per oggi.")
        else:
            bot.send_message(chat_id, f"⚠️ Errore: {str(e)[:50]}")

bot.infinity_polling()
