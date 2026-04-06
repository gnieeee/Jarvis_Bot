import os
import telebot
import google.generativeai as genai
from flask import Flask, request

# --- SISTEMI CORE ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.0-pro')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- RISPOSTA IA ---
def genera_risposta(testo):
    try:
        prompt = f"Sei J.A.R.V.I.S., assistente di Tony Stark. Rispondi in modo formale e conciso. Utente: {testo}"
        return model.generate_content(prompt).text
    except:
        return "Sistemi critici, Signore. Verifichi la chiave neurale (API Key) su Render."

# --- COMANDI BOT ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Sistemi online, Signore. Come posso servirla?")

@bot.message_handler(func=lambda m: True)
def chat(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.reply_to(message, genera_risposta(message.text))

# --- SERVER WEBHOOK ---
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://' + os.getenv("RENDER_EXTERNAL_HOSTNAME") + '/' + TOKEN)
    return "J.A.R.V.I.S. ONLINE", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 8080)))
