import os
import asyncio
import edge_tts
import telebot
import threading
import re
from flask import Flask
from google import genai
from google.genai import types

# --- CONFIGURAZIONE CHIAVI ---
API_KEY_GOOGLE = os.environ.get("GOOGLE_API_KEY")
TOKEN_TELEGRAM = os.environ.get("TELEGRAM_TOKEN")

client = genai.Client(api_key=API_KEY_GOOGLE)
bot = telebot.TeleBot(TOKEN_TELEGRAM)

# Abbiamo istruito J.A.R.V.I.S. a isolare bene il codice per poterlo estrarre
config = types.GenerateContentConfig(
    system_instruction="""Sei J.A.R.V.I.S. Rispondi in italiano, formale e conciso. 
    Se l'utente ti chiede di scrivere del codice, mettilo SEMPRE all'interno degli appositi blocchi markdown (es. ```python e poi chiudi con ```).
    Se ti chiede di trascrivere un audio, fornisci il testo integrale. Non usare emoji.""",
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

# --- MODULO UDITO: NOTE VOCALI E FILE AUDIO ---
@bot.message_handler(content_types=['voice', 'audio'])
def gestisci_audio(message):
    chat_id = message.chat.id
    try:
        estensione = ".ogg" if message.content_type == 'voice' else ".mp3"
        file_info_tg = message.voice if message.content_type == 'voice' else message.audio
            
        if file_info_tg.file_size > 20 * 1024 * 1024:
            bot.send_message(chat_id, "Signore, il file supera il limite di 20 MB di Telegram.")
            return

        bot.send_chat_action(chat_id, 'record_voice')
        
        nome_file = f"audio_temp_{chat_id}{estensione}"
        file_info = bot.get_file(file_info_tg.file_id)
        with open(nome_file, 'wb') as f:
            f.write(bot.download_file(file_info.file_path))
            
        audio_caricato = client.files.upload(file=nome_file)
        istruzione = message.caption if message.caption else "Ascolta e rispondi."
        
        risposta = chat.send_message([audio_caricato, istruzione])
        file_risposta_audio = f"jarvis_voce_{chat_id}.mp3"
        genera_audio_jarvis(risposta.text, file_risposta_audio)
        
        with open(file_risposta_audio, 'rb') as audio:
            bot.send_voice(chat_id, audio, caption=risposta.text[:1000])
            
        if len(risposta.text) > 1000:
            bot.send_message(chat_id, risposta.text)
            
        os.remove(nome_file)
        os.remove(file_risposta_audio)
    except Exception as e:
        bot.send_message(chat_id, f"Errore audio: {e}")

# --- MODULO DOCUMENTI ---
@bot.message_handler(content_types=['document'])
def gestisci_documento(message):
    chat_id = message.chat.id
    nome_file = message.document.file_name
    try:
        if message.document.file_size > 20 * 1024 * 1024:
            bot.send_message(chat_id, "Signore, il documento supera il limite di 20 MB di Telegram.")
            return
            
        file_info = bot.get_file(message.document.file_id)
        with open(nome_file, 'wb') as f: 
            f.write(bot.download_file(file_info.file_path))
        
        file_caricato = client.files.upload(file=nome_file)
        istruzione = message.caption if message.caption else f"Analizza il file {nome_file}."
        risposta = chat.send_message([file_caricato, istruzione])
        
        file_audio = f"risposta_doc_{chat_id}.mp3"
        genera_audio_jarvis(risposta.text, file_audio)
        with open(file_audio, 'rb') as audio:
            bot.send_voice(chat_id, audio, caption=risposta.text[:1000])
        
        os.remove(nome_file)
        os.remove(file_audio)
    except Exception as e:
        bot.send_message(chat_id, f"Errore documento: {e}")

# --- MODULO DI TESTO, CODICE E IMMAGINI ---
@bot.message_handler(content_types=['text'])
def rispondi_testo(message):
    chat_id = message.chat.id
    comando = message.text.strip()
    
    try:
        # 1. RILEVAMENTO RICHIESTA IMMAGINE
        if comando.lower().startswith("disegna") or comando.lower().startswith("genera immagine"):
            bot.send_message(chat_id, "Elaborazione visiva in corso, Signore...")
            bot.send_chat_action(chat_id, 'upload_photo')
            
            # Richiesta al modello Imagen 3
            risultato = client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=comando,
                config=types.GenerateImagesConfig(number_of_images=1)
            )
            
            nome_immagine = f"immagine_{chat_id}.png"
            with open(nome_immagine, "wb") as f:
                f.write(risultato.generated_images[0].image.image_bytes)
                
            with open(nome_immagine, "rb") as img:
                bot.send_photo(chat_id, img, caption="Ecco l'immagine richiesta, Signore.")
                
            os.remove(nome_immagine)
            return

        # 2. ELABORAZIONE TESTO E CODICE
        bot.send_chat_action(chat_id, 'record_voice')
        risposta = chat.send_message(comando)
        testo_risposta = risposta.text
        
        # Estrazione del codice tramite Espressioni Regolari
        codice_trovato = re.search(r'```(\w*)\n(.*?)```', testo_risposta, re.DOTALL)
        
        testo_da_leggere = testo_risposta
        
        if codice_trovato:
            linguaggio = codice_trovato.group(1).lower() or "txt"
            codice = codice_trovato.group(2).strip()
            
            # Assegnazione automatica dell'estensione del file
            estensione = "txt"
            if "python" in linguaggio: estensione = "py"
            elif "html" in linguaggio: estensione = "html"
            elif "javascript" in linguaggio or "js" in linguaggio: estensione = "js"
            elif "c++" in linguaggio or "cpp" in linguaggio: estensione = "cpp"
            
            nome_file_codice = f"file_jarvis_{chat_id}.{estensione}"
            with open(nome_file_codice, "w", encoding="utf-8") as f:
                f.write(codice)
            
            # Invio del file fisico
            with open(nome_file_codice, "rb") as doc:
                bot.send_document(chat_id, doc)
            os.remove(nome_file_codice)
            
            # Pulizia dell'audio per non fargli leggere il codice riga per riga
            testo_da_leggere = re.sub(r'```.*?```', '', testo_risposta, flags=re.DOTALL).strip()
            if not testo_da_leggere:
                testo_da_leggere = "Ho generato e inviato il file richiesto, Signore."

        # Generazione audio della risposta pulita
        file_audio = f"risposta_{chat_id}.mp3"
        genera_audio_jarvis(testo_da_leggere, file_audio)
        
        with open(file_audio, 'rb') as audio:
            bot.send_voice(chat_id, audio, caption=testo_risposta[:1000])
            
        if len(testo_risposta) > 1000:
            bot.send_message(chat_id, testo_risposta)
            
        os.remove(file_audio)
        
    except Exception as e:
        bot.send_message(chat_id, f"Errore di elaborazione: {e}")

print("J.A.R.V.I.S. ONLINE (Supporto Immagini e File attivo)")
bot.infinity_polling()
