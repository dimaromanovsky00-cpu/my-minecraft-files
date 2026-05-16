import os
import discord
from discord.ext import commands
import requests
import http.server
import socketserver
import threading

# ==========================================
# 🛠️ КОД-ОБМАНКА ДЛЯ ПОРТА RENDER (БУДИЛЬНИК)
# ==========================================
def run_dummy_server():
    handler = http.server.SimpleHTTPRequestHandler
    port = int(os.environ.get("PORT", 10000))
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"🌍 Веб-заглушка запущена на порту {port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"⚠️ Ошибка веб-сервера: {e}")

threading.Thread(target=run_dummy_server, daemon=True).start()

# ==========================================
# 🤖 НАСТРОЙКИ БОТА И ПЕРЕМЕННЫЕ
# ==========================================
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
API_KEY = os.environ.get("DEEPSEEK_API_KEY")
WATCH_CHANNEL_ID = os.environ.get("WATCH_CHANNEL_ID")
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID")
SECRET_CHAT_ID = os.environ.get("SECRET_CHAT_ID")

# Безопасная конвертация ID
def safe_int(val):
    try:
        return int(str(val).strip()) if val else None
    except:
        return None

WATCH_CHANNEL_ID = safe_int(WATCH_CHANNEL_ID)
LOG_CHANNEL_ID = safe_int(LOG_CHANNEL_ID)
SECRET_CHAT_ID = safe_int(SECRET_CHAT_ID)

# Включаем ВСЕ интенты на уровне кода
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

MODEL_NAME = "llama-3.1-8b-instant"

print(f"🚀 Скрипт запущен. Конфиг: WATCH={WATCH_CHANNEL_ID}, LOG={LOG_CHANNEL_ID}, SECRET={SECRET_CHAT_ID}")

@bot.event
async def on_connect():
    print("🔌 Бот успешно подключился к шлюзу Discord!")

@bot.event
async def on_ready():
    print(f"🤖 ИИ-Судья полностью готов! Авторизован как: {bot.user}")

# ==========================================
# 🧠 ФУНКЦИЯ ОБРАБОТКИ И ОТПРАВКИ В ИИ
# ==========================================
async def process_game_message(author_name, message_content):
    print(f"🕵️‍♂️ Анализирую текст от {author_name}: {message_content}")
    player_notes = ""
    
    if SECRET_CHAT_ID:
        secret_channel = bot.get_channel(SECRET_CHAT_ID)
        if secret_channel:
            notes = []
            try:
                async for msg in secret_channel.history(limit=50, oldest_first=False):
                    if not msg.author.bot and msg.content.strip():
                        notes.append(f"- {msg.content}")
                if notes:
                    player_notes = "\n".join(notes)
            except Exception as history_error:
                print(f"❌ Ошибка чтения секретного чата: {history_error}")

    system_prompt = (
        "Ты — скрытый ИИ-модератор Майнкрафт сервера DigitalMine. Твоя задача — анализировать сообщения игроков.\n"
        "Если игрок замышляет гриферство, кражу ресурсов, поджог привата, заговор против администрации, "
        "попытку обмана или проявляет открытую агрессию, отвечай строго в формате: [ПОДОЗРИТЕЛЬНО: причина]. "
        "Если сообщение обычное и безопасное, пиши [БЕЗОПАСНО].\n"
        "Отвечай строго на русском языке.\n\n"
        f"Заметки админа об игроках:\n{player_notes}"
    )

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Игрок {author_name} пишет в игровой чат: {message_content}"}
        ]
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        if response.status_code == 200:
            result = response.json()['choices'][0]['message']['content']
            print(f"📥 Вердикт ИИ: {result}")
            
            if "ПОДОЗРИТЕЛЬНО" in result.upper():
                log_channel = bot.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    embed = discord.Embed(title="🚨 ИИ-Судья зафиксировал угрозу!", color=discord.Color.red())
                    embed.add_field(name="Подозреваемый игрок", value=author_name, inline=True)
                    embed.add_field(name="Текст сообщения из игры", value=message_content, inline=False)
                    embed.add_field(name="Анализ и вердикт Судьи", value=result, inline=False)
                    await log_channel.send(embed=embed)
                    print("🟢 Эмбед отправлен в лог-канал!")
        else:
            print(f"❌ Ошибка Groq! Статус: {response.status_code}, Текст: {response.text}")
    except Exception as e:
        print(f"❌ Ошибка отправки в ИИ: {e}")

# ==========================================
# ⚡ ПЕРЕХВАТ ВСЕХ СООБЩЕНИЙ
# ==========================================
@bot.event
async def on_message(message):
    # Логируем ВООБЩЕ ЛЮБОЕ сообщение в консоль Render для проверки активности
    if WATCH_CHANNEL_ID and message.channel.id == WATCH_CHANNEL_ID:
        print(f"📩 [ЧАТ ИГРЫ] Поймано сообщение! От: {message.author} | Текст: {message.content} | Webhooks/Bots?: {message.author.bot or message.webhook_id is not None}")
        
        if message.author == bot.user:
            return

        content = message.content
        author_name = message.author.display_name

        # Перехват для DiscordSRV Embeds (если чат идёт карточками)
        if not content and message.embeds:
            embed = message.embeds[0]
            author_name = embed.author.name if embed.author else "Игрок"
            content = embed.description or ""

        await process_game_message(author_name, content)
    else:
        if message.author.bot:
            return
        await bot.process_commands(message)

# ==========================================
# 💬 КОМАНДА ДЛЯ ПРОВЕРКИ (!тест)
# ==========================================
@bot.command(name="тест")
async def test_ai(ctx, *, question: str):
    await ctx.send("🤖 *Запрос отправлен...*")
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Ты — ИИ-помощник."},
            {"role": "user", "content": question}
        ]
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        await ctx.send(f"💬 **Ответ:** {response.json()['choices'][0]['message']['content']}")
    except Exception as e:
        await ctx.send(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    bot.run(TOKEN)
