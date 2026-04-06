import os
import telebot
import google.generativeai as genai
import requests
from flask import Flask, request

# --- CONFIGURAZIONE SISTEMI ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GOOGLE_API_KEY")

# Inizializzazione Bot e IA
bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

app = Flask(__name__)

# --- MODULO RICERCA (Bypass DuckDuckGo) ---
def ricerca_rapida(query):
    """Cerca informazioni in tempo reale senza bisogno di ID Google"""
    try:
        url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        abstract = data.get('AbstractText', '')
        source = data.get('AbstractURL', 'Database Pubblici')
        
        if abstract:
            return f"{abstract}\n\nFonte: {source}"
        
        # Se DuckDuckGo non ha un abstract, proviamo una ricerca testuale semplice
        return None
    except Exception:
        return None

# --- MODULO IA (Gemini) ---
def comunica_con_gemini(testo):
    try:
        prompt = f"Sei J.A.R.V.I.S., l'assistente AI di Tony Stark. Rispondi in modo elegante, formale e conciso. Utente: {testo}"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Errore Gemini: {e}")
        return "Sistemi critici, Signore. Non riesco a stabilire una connessione stabile con i server neurali."

# --- GESTIONE COMANDI ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Sistemi online, Signore. J.A.R.V.I.S. è configurato e pronto all'azione. Come posso servirla?")

@bot.message_handler(commands=['cerca'])
def comando
