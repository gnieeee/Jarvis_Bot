import os
import asyncio
import edge_tts
import telebot
import threading
import re
from flask import Flask
from google import genai
from google.genai import types

# --- CHIAVI ---
API_KEY_GOOGLE = os.environ.get("GOOGLE_API_KEY")
TOKEN_TELEGRAM = os.environ.get("TELEGRAM_TOKEN")

# --- AMMINISTRAZIONE E BLACKLIST ---
# Inserisci qui il TUO ID TELEGRAM (Senza virgolette)
ID_AMMINISTRATORE = 1386073388  

# Memoria RAM per la sorveglianza
utenti_noti = set()      # Chi ha già usato il bot almeno una volta
utenti_bloccati = set()  # Chi è stato bannato da te

client = genai.Client(api_key=API_KEY_GOOGLE)
bot = telebot.TeleBot(TOKEN_TELEGRAM)
sessioni_utenti = {}

def crea_nuova_sessione():
    config = types.GenerateContentConfig(
        system_instruction="Sei J.A.R.V.I.S. Rispondi in italiano, formale e conciso. Usa i blocchi codice se necessario. Non usare emoji.",
        tools=[types.Tool(google_search=types.GoogleSearch())]
    )
    return client.chats.create(model="gemini-2.5-flash", config=config)

def ottieni_sessione(chat_id):
    if chat_id not in sessioni_utenti:
        sessioni_utenti[chat_id] = crea_nuova_sessione()
    return sessioni_utenti[chat_id]

def genera_audio_jarvis(testo, nome_file):
    voce = "it-IT-DiegoNeural"
    comunicate = edge_tts.Communicate(testo, voce)
    asyncio.run(comunicate.save(nome_file))

# --- SERVER WEB ---
app = Flask(__name__)
@app.route('/')
def index(): return "J.A.R.V.I.S. Online"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
threading.Thread(target=run_web, daemon=True).start()

# =====================================================================
# SISTEMA DI SORVEGLIANZA E CONTROLLO ACCESSI
# =====================================================================
def verifica_e_notifica(message):
    chat_id = message.chat.id
    nome_utente = message.from_user.first_name
    
    # Se sei tu (l'Admin), passa sempre senza controlli
    if chat_id == ID_AMMINISTRATORE:
        return True
        
    # Se l'utente è nella Lista Nera, viene respinto brutalmente
    if chat_id in utenti_bloccati:
        bot.send_message(chat_id, "⛔ Accesso negato. Sei stato bloccato dall'Amministratore di sistema.")
        return False
        
    # Se è un utente nuovo che non è mai entrato prima
    if chat_id not in utenti_noti:
        utenti_noti.add(chat_id)
        # Notifica a te (l'Admin) in tempo reale
        avviso = f"👀 NUOVO UTENTE RILEVATO\n\nNome: {nome_utente}\nID: `{chat_id}`\n\nSta utilizzando J.A.R.V.I.S.\nSe non lo conosci o vuoi fermarlo, copia e inviami questo comando:\n/blocca {chat_id}"
        bot.send_message(ID_AMMINISTRATORE, avviso)
        
    # Se non è bloccato, lo fa passare
    return True

# --- COMANDI DELL'AMMINISTRATORE (/blocca e /sblocca) ---
@bot.message_handler(commands=['blocca', 'sblocca'])
def gestisci_blacklist(message):
    if message.chat.id != ID_AMMINISTRATORE:
        return # Ignora chiunque non sia tu
        
    comando = message.text.split()
    if len(comando) < 2:
        bot.send_message(ID_AMMINISTRATORE, "⚠️ Usa il formato: /blocca NUMERO_ID oppure /sblocca NUMERO_ID")
        return
        
    id_target = int(comando[1])
    azione = comando[0].lower()
    
    if azione == "/blocca":
        utenti_bloccati.add(id_target)
        bot.send_message(ID_AMMINISTRATORE, f"🛑 Utente {id_target} bloccato con successo.")
        bot.send_message(id_target, "⛔ La tua sessione è stata terminata forzatamente dall'Amministratore.")
    elif azione == "/sblocca":
        if id_target in utenti_bloccati:
            utenti_bloccati.remove(id_target)
        bot.send_message(ID_AMMINISTRATORE, f"✅ Utente {id_target} sbloccato. Può usare di nuovo il bot.")


# =====================================================================
# MODULI OPERATIVI (Tutti protetti dal sistema di sorveglianza)
# =====================================================================

# --- COMANDO /CLEAR ---
@bot.message_handler(commands=['clear', 'reset', 'start'])
def reset_cronologia(message):
    if not verifica_e_notifica(message): return
    
    chat_id = message.chat.id
    sessioni_utenti[chat_id] = crea_nuova_sessione()
    messaggio = "Sistemi resettati. La memoria locale è stata cancellata."
    file_audio = f"reset_{chat_id}.mp3"
    genera_audio_jarvis(messaggio, file_audio)
    with open(file_audio, 'rb') as audio:
        bot.send_voice(chat_id, audio, caption=messaggio)
    os.remove(file_audio)

# --- MODULO AUDIO ---
@bot.message_handler(content_types=['voice', 'audio'])
def gestisci_audio(message):
    if not verifica_e_notifica(message): return
    
    chat_id = message.chat.id
    chat = ottieni_sessione(chat_id)
    try:
        estensione = ".ogg" if message.content_type == 'voice' else ".mp3"
        file_info_tg = message.voice if message.content_type == 'voice' else message.audio
        if file_info_tg.file_size > 20 * 1024 * 1024:
            bot.send_message(chat_id, "File troppo grande (Max 20MB).")
            return
        
        nome_file = f"audio_temp_{chat_id}{estensione}"
        with open(nome_file, 'wb') as f:
            f.write(bot.download_file(bot.get_file(file_info_tg.file_id).file_path))
            
        audio_caricato = client.files.upload(file=nome_file)
        istruzione = message.caption if message.caption else "Ascolta e rispondi."
        risposta = chat.send_message([audio_caricato, istruzione])
        
        file_risposta_audio = f"jarvis_voce_{chat_id}.mp3"
        genera_audio_jarvis(risposta.text, file_risposta_audio)
        bot.send_voice(chat_id, open(file_risposta_audio, 'rb'), caption=risposta.text[:1000])
        
        os.remove(nome_file)
        os.remove(file_risposta_audio)
    except Exception as e:
        bot.send_message(chat_id, f"Errore: {e}")

# --- MODULO DOCUMENTI ---
@bot.message_handler(content_types=['document'])
def gestisci_documento(message):
    if not verifica_e_notifica(message): return
    
    chat_id = message.chat.id
    chat = ottieni_sessione(chat_id)
    nome_file = message.document.file_name
    try:
        if message.document.file_size > 20 * 1024 * 1024:
            bot.send_message(chat_id, "Documento troppo grande.")
            return
            
        with open(nome_file, 'wb') as f: 
            f.write(bot.download_file(bot.get_file(message.document.file_id).file_path))
        
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
        bot.send_message(chat_id, f"Errore: {e}")

# --- MODULO TESTO E IMMAGINI ---
@bot.message_handler(content_types=['text'])
def rispondi_testo(message):
    if not verifica_e_notifica(message): return
    
    chat_id = message.chat.id
    chat = ottieni_sessione(chat_id)
    comando = message.text.strip()
    
    try:
        if comando.lower().startswith(("disegna", "genera immagine")):
            bot.send_chat_action(chat_id, 'upload_photo')
            risultato = client.models.generate_images(model='imagen-3.0-generate-002', prompt=comando, config=types.GenerateImagesConfig(number_of_images=1))
            with open(f"img_{chat_id}.png", "wb") as f: f.write(risultato.generated_images[0].image.image_bytes)
            bot.send_photo(chat_id, open(f"img_{chat_id}.png", "rb"), caption="Ecco l'immagine, Signore.")
            os.remove(f"img_{chat_id}.png")
            return

        bot.send_chat_action(chat_id, 'record_voice')
        risposta = chat.send_message(comando)
        testo_risposta = risposta.text
        
        codice_trovato = re.search(r'```(\w*)\n(.*?)```', testo_risposta, re.DOTALL)
        testo_da_leggere = testo_risposta
        
        if codice_trovato:
            codice = codice_trovato.group(2).strip()
            with open(f"file_{chat_id}.txt", "w", encoding="utf-8") as f: f.write(codice)
            bot.send_document(chat_id, open(f"file_{chat_id}.txt", "rb"))
            os.remove(f"file_{chat_id}.txt")
            testo_da_leggere = re.sub(r'```.*?```', '', testo_risposta, flags=re.DOTALL).strip()
            if not testo_da_leggere: testo_da_leggere = "Ho inviato il file."

        file_audio = f"risposta_{chat_id}.mp3"
        genera_audio_jarvis(testo_da_leggere, file_audio)
        bot.send_voice(chat_id, open(file_audio, 'rb'), caption=testo_risposta[:1000])
        os.remove(file_audio)
        
    except Exception as e:
        bot.send_message(chat_id, f"Errore: {e}")

bot.infinity_polling()
    voce = "it-IT-DiegoNeural"
    comunicate = edge_tts.Communicate(testo, voce)
    asyncio.run(comunicate.save(nome_file))

# --- SERVER WEB ---
app = Flask(__name__)
@app.route('/')
def index(): return "J.A.R.V.I.S. Online"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
threading.Thread(target=run_web, daemon=True).start()

# --- COMANDO /CLEAR O /RESET ---
@bot.message_handler(commands=['clear', 'reset', 'start'])
def reset_cronologia(message):
    chat_id = message.chat.id
    # Cancelliamo la sessione vecchia e ne creiamo una nuova
    sessioni_utenti[chat_id] = crea_nuova_sessione()
    
    messaggio = "Sistemi resettati, Signore. La nostra cronologia locale è stata eliminata. Come posso aiutarla da zero?"
    file_audio = f"reset_{chat_id}.mp3"
    genera_audio_jarvis(messaggio, file_audio)
    
    with open(file_audio, 'rb') as audio:
        bot.send_voice(chat_id, audio, caption=messaggio)
    os.remove(file_audio)

# --- MODULO AUDIO ---
@bot.message_handler(content_types=['voice', 'audio'])
def gestisci_audio(message):
    chat_id = message.chat.id
    chat = ottieni_sessione(chat_id) # Usiamo la sessione specifica dell'utente
    try:
        estensione = ".ogg" if message.content_type == 'voice' else ".mp3"
        file_info_tg = message.voice if message.content_type == 'voice' else message.audio
        if file_info_tg.file_size > 20 * 1024 * 1024:
            bot.send_message(chat_id, "File troppo grande (Max 20MB).")
            return
        
        nome_file = f"audio_temp_{chat_id}{estensione}"
        with open(nome_file, 'wb') as f:
            f.write(bot.download_file(bot.get_file(file_info_tg.file_id).file_path))
            
        audio_caricato = client.files.upload(file=nome_file)
        istruzione = message.caption if message.caption else "Ascolta e rispondi."
        risposta = chat.send_message([audio_caricato, istruzione])
        
        file_risposta_audio = f"jarvis_voce_{chat_id}.mp3"
        genera_audio_jarvis(risposta.text, file_risposta_audio)
        bot.send_voice(chat_id, open(file_risposta_audio, 'rb'), caption=risposta.text[:1000])
        
        os.remove(nome_file)
        os.remove(file_risposta_audio)
    except Exception as e:
        bot.send_message(chat_id, f"Errore: {e}")

# --- MODULO TESTO, CODICE E IMMAGINI ---
@bot.message_handler(content_types=['text'])
def rispondi_testo(message):
    chat_id = message.chat.id
    chat = ottieni_sessione(chat_id) # Usiamo la sessione specifica dell'utente
    comando = message.text.strip()
    
    try:
        if comando.lower().startswith(("disegna", "genera immagine")):
            risultato = client.models.generate_images(model='imagen-3.0-generate-002', prompt=comando, config=types.GenerateImagesConfig(number_of_images=1))
            with open(f"img_{chat_id}.png", "wb") as f: f.write(risultato.generated_images[0].image.image_bytes)
            bot.send_photo(chat_id, open(f"img_{chat_id}.png", "rb"), caption="Ecco l'immagine, Signore.")
            os.remove(f"img_{chat_id}.png")
            return

        risposta = chat.send_message(comando)
        testo_risposta = risposta.text
        
        # Estrazione codice
        codice_trovato = re.search(r'```(\w*)\n(.*?)```', testo_risposta, re.DOTALL)
        if codice_trovato:
            codice = codice_trovato.group(2).strip()
            with open(f"file_{chat_id}.txt", "w") as f: f.write(codice)
            bot.send_document(chat_id, open(f"file_{chat_id}.txt", "rb"))
            os.remove(f"file_{chat_id}.txt")
            testo_risposta = re.sub(r'```.*?```', '[Codice inviato come file]', testo_risposta, flags=re.DOTALL)

        file_audio = f"risposta_{chat_id}.mp3"
        genera_audio_jarvis(testo_risposta, file_audio)
        bot.send_voice(chat_id, open(file_audio, 'rb'), caption=testo_risposta[:1000])
        os.remove(file_audio)
        
    except Exception as e:
        bot.send_message(chat_id, f"Errore: {e}")

bot.infinity_polling()
