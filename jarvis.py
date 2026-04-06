import os
import telebot
import edge_tts
import asyncio
import threading
import re
from flask import Flask
from google import genai
from google.genai import types

# --- CONFIGURAZIONE ---
TOKEN_TELEGRAM = os.environ.get("TELEGRAM_TOKEN")
# Recuperiamo le 3 chiavi dalle variabili d'ambiente di Render
CHIAVI = [
    os.environ.get("GOOGLE_API_KEY"),
    os.environ.get("GOOGLE_API_KEY_2"),
    os.environ.get("GOOGLE_API_KEY_3")
]
CHIAVI_VALIDE = [k for k in CHIAVI if k]

# IMPORTANTE: Inserisci qui il tuo ID Telegram numerico
ID_AMMINISTRATORE = 1386073388  # <--- CAMBIA QUESTO NUMERO

# Disabilitiamo il threading interno di telebot per uccidere l'errore 409 Conflict
bot = telebot.TeleBot(TOKEN_TELEGRAM, threaded=False)
clients = [genai.Client(api_key=k) for k in CHIAVI_VALIDE]
indice_chiave = 0
sessioni = {}

# --- FUNZIONI CORE GEMINI ---
def crea_chat(client_scelto):
    config = types.GenerateContentConfig(
        system_instruction="Sei J.A.R.V.I.S. Rispondi in italiano, in modo formale, conciso e senza usare emoji.",
        tools=[types.Tool(google_search=types.GoogleSearch())]
    )
    # Usiamo il modello 'latest' per la massima compatibilità ed evitare il 404
    return client_scelto.chats.create(model="models/gemini-1.5-flash", config=config)

def chiedi_a_gemini(chat_id, prompt):
    global indice_chiave
    for _ in range(len(clients)):
        try:
            if chat_id not in sessioni:
                sessioni[chat_id] = crea_chat(clients[indice_chiave])
            return sessioni[chat_id].send_message(prompt)
        except Exception as e:
            # Se la chiave è esaurita (Errore 429), passiamo alla prossima
            if "429" in str(e) or "quota" in str(e).lower():
                indice_chiave = (indice_chiave + 1) % len(clients)
                sessioni[chat_id] = crea_chat(clients[indice_chiave])
                continue
            raise e
    raise Exception("Tutte le API Key sono esaurite per oggi.")

# --- HANDLERS TELEGRAM ---
@bot.message_handler(commands=['start', 'reset'])
def send_welcome(message):
    chat_id = message.chat.id
    sessioni[chat_id] = crea_chat(clients[indice_chiave])
    bot.reply_to(message, "Sistemi J.A.R.V.I.S. Online. Multi-Key e Notifiche attive.")

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_message(message):
    chat_id = message.chat.id
    nome_utente = message.from_user.first_name or "Utente"
    
    # --- NOTIFICA PER TE ---
    if chat_id != ID_AMMINISTRATORE:
        try:
            bot.send_message(ID_AMMINISTRATORE, f"👀 J.A.R.V.I.S. ALERT: {nome_utente} ({chat_id}) ha inviato un messaggio.")
        except:
            pass # Evita blocchi se la notifica fallisce

    try:
        bot.send_chat_action(chat_id, 'record_voice')
        
        # Chiediamo risposta a Gemini con rotazione chiavi
        risposta_gemini = chiedi_a_gemini(chat_id, message.text)
        testo_risposta = risposta_gemini.text
        
        # Generazione Audio con Edge-TTS
        audio_file = f"jarvis_{chat_id}.mp3"
        asyncio.run(edge_tts.Communicate(testo_risposta, "it-IT-DiegoNeural").save(audio_file))
        
        # Invio vocale su Telegram
        with open(audio_file, 'rb') as voice:
            bot.send_voice(chat_id, voice, caption=testo_risposta[:1000])
        
        # Pulizia file temporaneo
        if os.path.exists(audio_file):
            os.remove(audio_file)
            
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Errore di sistema: {str(e)[:100]}")

# --- SERVER FLASK PER MANTENERE RENDER ATTIVO ---
app = Flask(__name__)
@app.route('/')
def health_check(): return "J.A.R.V.I.S. Multi-Key Status: ACTIVE", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- AVVIO ---
if __name__ == "__main__":
    # Avviamo Flask in un thread separato
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Avviamo il polling del bot (modalità singola per evitare il 409)
    print("Inizializzazione J.A.R.V.I.S. in corso...")
    bot.polling(none_stop=True, interval=0, timeout=20)
