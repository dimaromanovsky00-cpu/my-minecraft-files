import os
import discord
import requests
from flask import Flask, request, jsonify
import threading

# ==========================================
# 🌐 ВЕБ-СЕРВЕР ДЛЯ ПРЯМОГО ПРИЁМА ИЗ МАЙНА
# ==========================================
app = Flask(__name__)

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
API_KEY = os.environ.get("DEEPSEEK_API_KEY")
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID")
SECRET_CHAT_ID = os.environ.get("SECRET_CHAT_ID")

def clean_id(val):
    try:
        return int(str(val).strip()) if val else None
    except:
        return None

LOG_CHANNEL_ID = clean_id(LOG_CHANNEL_ID)
SECRET_CHAT_ID = clean_id(SECRET_CHAT_ID)

# Настройка Discord клиента (теперь только для отправки)
intents = discord.Intents.default()
client = discord.Client(intents=intents)
MODEL_NAME = "llama-3.1-8b-instant"

@app.route('/', methods=['GET', 'HEAD'])
def index():
    return "ИИ-Судья работает!", 200

# Сюда будут прилетать сообщения из Майнкрафта
@app.route('/webhook', methods=['POST'])
def minecraft_webhook():
    data = request.json
    if not data:
        return jsonify({"status": "no_data"}), 400
    
    # Извлекаем игрока и его текст (подстроим под плагин)
    author = data.get("username", "Игрок")
    text = data.get("content", "")
    
    if text.strip():
        print(f"\n📥 [ПРЯМОЙ ПЕРЕХВАТ ИЗ ИГРЫ] {author}: {text}", flush=True)
        # Запускаем анализ ИИ в фоновом потоке, чтобы сервер игры не лагал, ждал ответа
        threading.Thread(target=async_analyze_bridge, args=(author, text)).start()
        
    return jsonify({"status": "received"}), 200

def async_analyze_bridge(author, text):
    # Мост для запуска асинхронного анализа из обычного Flask
    client.loop.create_task(analyze_text(author, text))

# ==========================================
# 🧠 ОБРАБОТКА ТЕКСТА ЧЕРЕЗ ИИ
# ==========================================
async def analyze_text(author, text):
    player_notes = ""
    if SECRET_CHAT_ID:
        try:
            sec_ch = client.get_channel(SECRET_CHAT_ID)
            if sec_ch:
                notes = []
                async for msg in sec_ch.history(limit=30, oldest_first=False):
                    if not msg.author.bot and msg.content.strip():
                        notes.append(f"- {msg.content}")
                if notes:
                    player_notes = "\n".join(notes)
        except Exception as e:
            print(f"⚠️ Ошибка чтения секретного чата: {e}", flush=True)

    system_prompt = (
        "Ты — скрытый ИИ-модератор сервера DigitalMine. Твоя задача — анализировать чат.\n"
        "Если игрок замышляет гриферство, кражу ресурсов, заговор против админов или проявляет агрессию, "
        "отвечай строго в формате: [ПОДОЗРИТЕЛЬНО: причина].\n"
        "Если сообщение обычное и безопасное, пиши [БЕЗОПАСНО].\n"
        "Отвечай только на русском языке.\n\n"
        f"Заметки админа:\n{player_notes}"
    )

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Игрок {author} пишет: {text}"}
        ]
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        if res.status_code == 200:
            verdict = res.json()['choices'][0]['message']['content']
            print(f"🤖 Вердикт ИИ для {author}: {verdict}", flush=True)
            
            if "ПОДОЗРИТЕЛЬНО" in verdict.upper():
                log_ch = client.get_channel(LOG_CHANNEL_ID)
                if log_ch:
                    emb = discord.Embed(title="🚨 Фиксация угрозы в игре!", color=discord.Color.red())
                    emb.add_field(name="Нарушитель", value=author, inline=True)
                    emb.add_field(name="Фраза в чате", value=text, inline=False)
                    emb.add_field(name="Анализ Судьи", value=verdict, inline=False)
                    await log_ch.send(embed=emb)
                    print(f"🔴 Эмбед угрозы игрока {author} отправлен в Дискорд!", flush=True)
        else:
            print(f"❌ Ошибка Groq API: {res.status_code}", flush=True)
    except Exception as err:
        print(f"❌ Ошибка сети с ИИ: {err}", flush=True)

@client.event
async def on_ready():
    print(f"🟢 БОТ ДЛЯ ОТПРАВКИ ЛОГОВ ГОТОВ! Сеть: {client.user}", flush=True)

# Запуск веб-сервера Flask в отдельном потоке
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    client.run(TOKEN)
