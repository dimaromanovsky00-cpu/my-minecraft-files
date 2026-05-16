import discord
import requests
import json
import os

# ============== НАСТРОЙКА КЛЮЧЕЙ (Берутся из облака) ==============
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
CHANNELS_TO_WATCH = [123456789012345678]  # ID канала #игровой-чат
LOG_CHANNEL_ID = 876543210987654321      # ID канала #ии-логи
# =================================================================

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

SYSTEM_PROMPT = (
    "Ты — ИИ-Аналитик безопасности Minecraft-сервера 'DigitalMine'. Ты следишь за логами игроков (входы, чат). "
    "Твоя задача — выявлять угрозы: подозрительную смену IP (взлом), скрытую токсичность, планирование гриферства. "
    "Будь умным, отличай дружеские шутки игроков от реальной агрессии. "
    "Если строка безопасна — ИГНОРИРУЙ её. Если видишь угрозу — кратко аргументируй, почему это опасно."
)

def analyze_with_ai(text):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Проанализируй действие на сервере: {text}"}
        ],
        "temperature": 0.3
    }
    try:
        response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()['choices'][0]['message']['content'].strip()
            return result
        return None
    except Exception as e:
        print(f"Ошибка ИИ: {e}")
        return None

@client.event
async def on_ready():
    print(f"🤖 ИИ-Судья {client.user} запущен в облаке и готов к защите 24/7!")

@client.event
async def on_message(message):
    # Проверяем, что сообщение пришло из игрового чата и это не сам бот
    if message.channel.id in CHANNELS_TO_WATCH and message.author != client.user:
        analysis = analyze_with_ai(message.content)
        
        # Если ИИ нашел угрозу и что-то ответил, отправляем в админский канал
        if analysis and len(analysis) > 5:
            log_channel = client.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(f"⚠️ **[ИИ-АНАЛИЗ]**: {analysis}\n*Контекст: {message.content}*")

client.run(TOKEN)


# Код-обманка для Render, чтобы он думал, что это сайт
import http.server
import socketserver
import threading

def run_dummy_server():
    handler = http.server.SimpleHTTPRequestHandler
    # Render автоматически передает порт в переменные окружения, мы его читаем
    import os
    port = int(os.environ.get("PORT", 10000))
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

# Запускаем сайт-заглушку в отдельном потоке, чтобы он не мешал Дискорд-боту
threading.Thread(target=run_dummy_server, daemon=True).start()
