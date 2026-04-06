import os
import asyncio
import edge_tts
import telebot
from google import genai
from google.genai import types

# Usiamo os.environ.get() per leggere le chiavi dal server in modo sicuro!
API_KEY_GOOGLE = os.environ.get("GOOGLE_API_KEY")
TOKEN_TELEGRAM = os.environ.get("TELEGRAM_TOKEN")


# Inizializziamo i sistemi
client = genai.Client(api_key=API_KEY_GOOGLE)
bot = telebot.TeleBot(TOKEN_TELEGRAM)

# Configurazione di J.A.R.V.I.S. con Ricerca Google integrata
config = types.GenerateContentConfig(
    system_instruction="Da ora in poi sei J.A.R.V.I.S. Rispondi in italiano in modo formale e conciso. Non usare emoji o asterischi.",
    tools=[types.Tool(google_search=types.GoogleSearch())]
)

chat = client.chats.create(model="gemini-2.5-flash", config=config)

def genera_audio_jarvis(testo, nome_file):
    """Genera l'audio neurale e lo salva su disco"""
    voce = "it-IT-DiegoNeural"
    comunicate = edge_tts.Communicate(testo, voce)
    asyncio.run(comunicate.save(nome_file))

print("-" * 50)
print("SISTEMA J.A.R.V.I.S. IN ASCOLTO SU TELEGRAM...")
print("-" * 50)

# 2. IL "RICEVITORE" DI TELEGRAM
# Questa funzione scatta ogni volta che scrivi qualcosa al tuo Bot su Telegram
@bot.message_handler(func=lambda message: True)
def rispondi_a_messaggio(message):
    comando_utente = message.text
    chat_id = message.chat.id
    
    print(f"Messaggio ricevuto su Telegram: {comando_utente}")
    
    try:
        # Avvisiamo l'utente su Telegram che Jarvis sta scrivendo/registrando
        bot.send_chat_action(chat_id, 'record_voice')
        
        # Chiediamo la risposta a Gemini
        risposta = chat.send_message(comando_utente)
        testo_pulito = risposta.text
        
        # Generiamo il file audio
        file_audio = f"risposta_{chat_id}.mp3"
        genera_audio_jarvis(testo_pulito, file_audio)
        
        # Inviamo l'audio su Telegram come Nota Vocale!
        with open(file_audio, 'rb') as audio:
            bot.send_voice(chat_id, audio, caption=testo_pulito)
            
        # Pulizia: cancelliamo il file audio dal PC dopo averlo inviato
        os.remove(file_audio)
        
    except Exception as e:
        errore = f"Mi scusi Signore, c'è stato un errore di sistema: {e}"
        bot.send_message(chat_id, errore)

# Avviamo il bot (questo terrà il programma acceso in attesa di messaggi)
bot.infinity_polling()