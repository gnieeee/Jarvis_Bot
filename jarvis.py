import os
import asyncio
import edge_tts
import telebot
import threading
import re
from flask import Flask
from google import genai
from google.genai import types

# --- CONFIGURAZIONE ---
API_KEY_GOOGLE = os.environ.get("GOOGLE_API_KEY")
TOKEN_TELEGRAM = os.environ.get("TELEGRAM_TOKEN")

# INSERISCI QUI IL TUO ID TELEGRAM
ID_AMMINISTRATORE = 123456789  

utenti_noti = set()      
utenti_bloccati = set()  

client = genai.Client(api_key=API_KEY_GOOGLE)
bot = telebot.TeleBot(TOKEN_TELEGRAM)
sessioni_utenti = {}

def crea_nuova_sessione():
    config = types.GenerateContentConfig(
        system_instruction="Sei J.A.R.V.I.S. Rispondi in italiano, formale e conciso. Non usare emoji.",
        tools=[types.Tool(google_search=types.GoogleSearch())]
    )
    # MODELLO STABILE 1.5 FLASH
    return client.chats.create(model="models/gemini-1.5-flash", config=config)

def ottieni_sessione(chat_id):
    if chat_id not in sessioni_utenti:
        sessioni_utenti[chat_id] = crea_nuova_sessione()
    return sessioni_utenti[chat_id]

def genera_audio_jarvis(testo, nome_file):
    # Rimosse indentazioni extra per evitare SyntaxError
    voce = "it-IT-DiegoNeural"
    comunicate = edge_tts.Communicate(testo, voce)
    asyncio.run(comunicate.save(nome_file))

# --- SERVER FLASK ---
app = Flask(__name__)
@app.route('/')
def index(): return "J.A.R.V.I.S. Status: Online"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
threading.Thread(target=run_web, daemon=True).start()

# --- SECURITY CHECK ---
def verifica_e_notifica(message):
    chat_id = message.chat.id
    nome = message.from_user.first_name
    if chat_id == ID_AMMINISTRATORE: return True
    if chat_id in utenti_bloccati:
        bot.send_message(chat_id, "⛔ Accesso negato.")
        return False
    if chat_id not in utenti_noti:
        utenti_noti.add(chat_id)
        avviso = f"👀 UTENTE RILEVATO: {nome} (ID: `{chat_id}`)\nBlocca: /blocca {chat_id}"
        bot.send_message(ID_AMMINISTRATORE, avviso)
    return True

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['blocca', 'sblocca'])
def gestisci_admin(message):
    if message.chat.id != ID_AMMINISTRATORE: return
    cmd = message.text.split()
    if len(cmd) < 2: return
    id_t = int(cmd[1])
    if cmd[0] == "/blocca":
        utenti_bloccati.add(id_t)
        bot.send_message(ID_AMMINISTRATORE, f"🛑 ID {id_t} bloccato.")
    else:
        if id_t in utenti_bloccati: utenti_bloccati.remove(id_t)
        bot.send_message(ID_AMMINISTRATORE, f"✅ ID {id_t} sbloccato.")

# --- CORE LOGIC ---
@bot.message_handler(commands=['start', 'reset', 'clear'])
def welcome(message):
    if not verifica_e_notifica(message): return
    chat_id = message.chat.id
    sessioni_utenti[chat_id] = crea_nuova_sessione()
    bot.send_message(chat_id, "Sistemi J.A.R.V.I.S. ricaricati. Collegamento stabilito.")

@bot.message_handler(content_types=['text', 'voice', 'audio'])
def handle_all(message):
    if not verifica_e_notifica(message): return
    chat_id = message.chat.id
    chat = ottieni_sessione(chat_id)
    
    try:
        bot.send_chat_action(chat_id, 'record_voice')
        
        if message.content_type in ['voice', 'audio']:
            ext = ".ogg" if message.content_type == 'voice' else ".mp3"
            f_info = message.voice if message.content_type == 'voice' else message.audio
            nome_f = f"rec_{chat_id}{ext}"
            with open(nome_f, 'wb') as f:
                f.write(bot.download_file(bot.get_file(f_info.file_id).file_path))
            u_file = client.files.upload(file=nome_f)
            risposta = chat.send_message([u_file, "Rispondi a questo audio."])
            os.remove(nome_f)
        else:
            risposta = chat.send_message(message.text)

        txt = risposta.text
        f_voc = f"v_{chat_id}.mp3"
        genera_audio_jarvis(re.sub(r'```.*?```', '', txt, flags=re.DOTALL).strip() or "Messaggio ricevuto.", f_voc)
        bot.send_voice(chat_id, open(f_voc, 'rb'), caption=txt[:1000])
        os.remove(f_voc)

    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg:
            bot.send_message(chat_id, "⚠️ Limite Google raggiunto. Attendi 60 secondi.")
        elif "404" in err_msg:
            bot.send_message(chat_id, "❌ Modello non trovato. Verifica la tua API KEY su Google AI Studio.")
        else:
            bot.send_message(chat_id, f"⚙️ Errore tecnico: {err_msg[:50]}")

bot.infinity_polling()
