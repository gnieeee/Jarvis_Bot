import os
import asyncio
import edge_tts
import telebot
import threading
import re
from flask import Flask
from google import genai
from google.genai import types

# --- CHIAVI E SICUREZZA ---
API_KEY_GOOGLE = os.environ.get("GOOGLE_API_KEY")
TOKEN_TELEGRAM = os.environ.get("TELEGRAM_TOKEN")

# INSERISCI QUI IL TUO ID (Senza virgolette)
ID_AMMINISTRATORE = 1386073388  

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
    # PASSAGGIO A GEMINI 1.5 FLASH PER MAGGIORE STABILITÀ
    return client.chats.create(model="gemini-1.5-flash", config=config)
    
def ottieni_sessione(chat_id):
    if chat_id not in sessioni_utenti:
        sessioni_utenti[chat_id] = crea_nuova_sessione()
    return sessioni_utenti[chat_id]

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

# --- SISTEMA DI SORVEGLIANZA & FILTRO ERRORI ---
def verifica_e_notifica(message):
    chat_id = message.chat.id
    nome_utente = message.from_user.first_name
    if chat_id == ID_AMMINISTRATORE: return True
    if chat_id in utenti_bloccati:
        bot.send_message(chat_id, "⛔ Accesso negato. Protocolli di sicurezza attivi.")
        return False
    if chat_id not in utenti_noti:
        utenti_noti.add(chat_id)
        avviso = f"👀 NUOVO UTENTE: {nome_utente}\nID: `{chat_id}`\nBlocca con: /blocca {chat_id}"
        bot.send_message(ID_AMMINISTRATORE, avviso)
    return True

def gestisci_errore_quota(chat_id, e):
    # FILTRO PROFESSIONALE PER ERRORE 429
    if "429" in str(e) or "Resource" in str(e):
        bot.send_message(chat_id, "⚠️ Sistemi in sovraccarico. J.A.R.V.I.S. ha bisogno di 60 secondi per ricaricare i condensatori. Riprovi a breve.")
    else:
        bot.send_message(chat_id, f"❌ Errore di sistema: {str(e)[:100]}")

# --- COMANDI ADMIN ---
@bot.message_handler(commands=['blocca', 'sblocca'])
def gestisci_blacklist(message):
    if message.chat.id != ID_AMMINISTRATORE: return
    comando = message.text.split()
    if len(comando) < 2: return
    id_t = int(comando[1])
    if comando[0] == "/blocca":
        utenti_bloccati.add(id_t)
        bot.send_message(ID_AMMINISTRATORE, f"🛑 ID {id_t} rimosso dai sistemi.")
    else:
        if id_t in utenti_bloccati: utenti_bloccati.remove(id_t)
        bot.send_message(ID_AMMINISTRATORE, f"✅ ID {id_t} riabilitato.")

# --- FUNZIONI OPERATIVE ---
@bot.message_handler(commands=['clear', 'reset', 'start'])
def reset_cronologia(message):
    if not verifica_e_notifica(message): return
    chat_id = message.chat.id
    sessioni_utenti[chat_id] = crea_nuova_sessione()
    bot.send_message(chat_id, "Sistemi resettati. Collegamento stabilito.")

@bot.message_handler(content_types=['voice', 'audio'])
def gestisci_audio(message):
    if not verifica_e_notifica(message): return
    chat_id = message.chat.id
    chat = ottieni_sessione(chat_id)
    try:
        ext = ".ogg" if message.content_type == 'voice' else ".mp3"
        f_info = message.voice if message.content_type == 'voice' else message.audio
        nome_f = f"audio_{chat_id}{ext}"
        with open(nome_f, 'wb') as f:
            f.write(bot.download_file(bot.get_file(f_info.file_id).file_path))
        audio_up = client.files.upload(file=nome_f)
        risp = chat.send_message([audio_up, "Analizza questo audio."])
        f_res = f"res_{chat_id}.mp3"
        genera_audio_jarvis(risp.text, f_res)
        bot.send_voice(chat_id, open(f_res, 'rb'), caption=risp.text[:1000])
        os.remove(nome_f); os.remove(f_res)
    except Exception as e: gestisci_errore_quota(chat_id, e)

@bot.message_handler(content_types=['text'])
def rispondi_testo(message):
    if not verifica_e_notifica(message): return
    chat_id = message.chat.id
    chat = ottieni_sessione(chat_id)
    try:
        bot.send_chat_action(chat_id, 'record_voice')
        risp = chat.send_message(message.text)
        txt = risp.text
        code = re.search(r'```(\w*)\n(.*?)```', txt, re.DOTALL)
        if code:
            with open(f"f_{chat_id}.txt", "w") as f: f.write(code.group(2).strip())
            bot.send_document(chat_id, open(f"f_{chat_id}.txt", "rb"))
            os.remove(f"f_{chat_id}.txt")
        f_audio = f"voc_{chat_id}.mp3"
        genera_audio_jarvis(re.sub(r'```.*?```', '', txt, flags=re.DOTALL).strip() or "File generato.", f_audio)
        bot.send_voice(chat_id, open(f_audio, 'rb'), caption=txt[:1000])
        os.remove(f_audio)
    except Exception as e: gestisci_errore_quota(chat_id, e)

bot.infinity_polling()
