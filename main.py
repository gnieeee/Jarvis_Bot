import os
import telebot
import requests
from bs4 import BeautifulSoup
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def ricerca_web_reale(query):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}
        # Aggiungiamo '2026' alla query per forzare Google
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}+2026"
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Cerchiamo di prendere gli snippet più rilevanti
        snippets = soup.find_all(['span', 'div'], class_=['VwiC3b', 'MUwY0b', 'lyLwCc'])
        info = " ".join([s.get_text() for s in snippets[:3]])
        return info if len(info) > 20 else None
    except:
        return None

def chiedi_a_jarvis(prompt):
    info_web = ricerca_web_reale(prompt)
    
    # Se abbiamo trovato dati reali, li passiamo all'IA con un ordine perentorio
    try:
        if info_web:
            system_msg = "Sei JARVIS. USA QUESTI DATI PER RISPONDERE ORA: " + info_web
        else:
            system_msg = "Sei JARVIS, l'assistente di Tony Stark. Rispondi in modo formale."

        url = f"https://text.pollinations.ai/{prompt}?model=openai&system={system_msg.replace(' ', '%20')}"
        risposta = requests.get(url, timeout=20).text
        
        # Se l'IA continua a scusarsi nonostante i dati, forziamo l'output dei dati grezzi
        if "Mi dispiace" in risposta or "non ho accesso" in risposta:
            if info_web:
                return f"Signore, i database riportano quanto segue: {info_web}"
        
        return risposta
    except:
        return "Sistemi offline. Riprovi, Signore."

@bot.message_handler(func=lambda m: True)
def chat(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.reply_to(message, chiedi_a_jarvis(message.text))

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://' + os.getenv("RENDER_EXTERNAL_HOSTNAME") + '/' + TOKEN)
    return "JARVIS ONLINE", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 8080)))
