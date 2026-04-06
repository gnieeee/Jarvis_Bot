import os
import telebot
import google.generativeai as genai
import requests
from flask import Flask
from threading import Thread

# --- CARICAMENTO SISTEMI (Variabili Render) ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

# Moduli Google Gemini (Ridondanza Tripla)
GEMINI_KEYS = [
    os.environ.get('GOOGLE_API_KEY'),
    os.environ.get('GOOGLE_API_KEY_2'),
    os.environ.get('GOOGLE_API_KEY_3')
]
CHIAVI_VALIDE = [k for k in GEMINI_KEYS if k]

# Modulo Ricerca Globale (Corretto come richiesto)
GOOGLE_SEARCH_KEY = os.environ.get('Google_Search_KEY') 
SEARCH_ENGINE_ID = '37500e21f32e94d06'

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask('')

# Direttiva Primaria (Personalità)
SYSTEM_PROMPT = "Agisci come JARVIS, l'assistente AI di Tony Stark. Sii formale, chiama l'utente 'Signore', usa un tono sofisticato e ironico. Sei un esperto onnisciente."

@app.route('/')
def home():
    return "J.A.R.V.I.S. STATUS: OPERATIONAL"

def comunica_con_gemini(testo_utente):
    """Gestione intelligente delle chiavi Gemini"""
    for chiave in CHIAVI_VALIDE:
        try:
            genai.configure(api_key=chiave)
            model = genai.GenerativeModel('gemini-1.5-flash')
            # Integriamo il sistema nel prompt
            prompt_completo = f"{SYSTEM_PROMPT}\n\nUtente: {testo_utente}\nJarvis:"
            response = model.generate_content(prompt_completo)
            return response.text
        except Exception:
            continue # Prova la chiave successiva se questa fallisce
    return "Sistemi critici, Signore. Non riesco a stabilire una connessione stabile con i server neurali."

# --- PROTOCOLLI DI COMUNICAZIONE ---

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "Sistemi online, Signore. J.A.R.V.I.S. è configurato e pronto all'azione. Come posso servirla?")

@bot.message_handler(commands=['cerca'])
def search(message):
    # Estrazione query
    query = message.text.replace('/cerca ', '').strip()
    if not query or query == "/cerca":
        bot.reply_to(message, "Mi indichi l'oggetto della ricerca, Signore.")
        return
    
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={GOOGLE_SEARCH_KEY}&cx={SEARCH_ENGINE_ID}"
        res = requests.get(url).json()
        
        if 'items' in res:
            info = res['items'][0]['snippet']
            link = res['items'][0]['link']
            bot.reply_to(message, f"Risultati della scansione, Signore:\n\n{info}\n\nFonte: {link}")
        else:
            bot.reply_to(message, "Nessun dato rilevante nei database pubblici, Signore.")
    except Exception:
        bot.reply_to(message, "Il modulo di ricerca ha riscontrato un'interferenza esterna.")

@bot.message_handler(func=lambda m: True)
def chat(message):
    bot.send_chat_action(message.chat.id, 'typing')
    risposta = comunica_con_gemini(message.text)
    bot.reply_to(message, risposta)

# --- AVVIO SISTEMI ---
def run():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    t = Thread(target=run)
    t.start()
    print("Accensione reattore Arc... J.A.R.V.I.S. è attivo.")
    bot.infinity_polling()
