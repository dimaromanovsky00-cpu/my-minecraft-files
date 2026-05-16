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

if WATCH_CHANNEL_ID: WATCH_CHANNEL_ID = int(WATCH_CHANNEL_ID)
if LOG_CHANNEL_ID: LOG_CHANNEL_ID = int(LOG_CHANNEL_ID)
if SECRET_CHAT_ID: SECRET_CHAT_ID = int(SECRET_CHAT_ID)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

MODEL_NAME = "llama-3.1-8b-instant"

@bot.event
async def on_ready():
    print(f"🤖 ИИ-Судья успешно запущен как {bot.user}!")
    print(f"🔍 Наблюдение за каналом: {WATCH_CHANNEL_ID}")

# ==========================================
# 🧠 ФУНКЦИЯ ОБРАБОТКИ И ОТПРАВКИ В ИИ
# ==========================================
async def process_game_message(author_name, message_content):
    if not message_content or not message_content.strip():
        return

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
            print(f"📥 Лог ИИ для {author_name}: {result}")
            
            # Фильтруем: шлём в логи ТОЛЬКО подозрительные моменты, чтобы не спамить!
            if "ПОДОЗРИТЕЛЬНО" in result.upper():
                log_channel = bot.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    embed = discord.Embed(title="🚨 ИИ-Судья зафиксировал угрозу!", color=discord.Color.red())
                    embed.add_field(name="Подозреваемый игрок", value=author_name, inline=True)
                    embed.add_field(name="Текст сообщения из игры", value=message_content, inline=False)
                    embed.add_field(name="Анализ и вердикт Судьи", value=result, inline=False)
                    await log_channel.send(embed=embed)
    except Exception as e:
        print(f"❌ Ошибка отправки в ИИ: {e}")

# ==========================================
# ⚡ ПЕРЕХВАТ ОБЫЧНЫХ СООБЩЕНИЙ И ВЕБХУКОВ
# ==========================================
@bot.event
async def on_message(message):
    # Если сообщение в нужном канале (неважно, от вебхука, бота или игрока)
    if WATCH_CHANNEL_ID and message.channel.id == WATCH_CHANNEL_ID:
        if message.author == bot.user:
            return
            
        # Получаем чистый текст сообщения
        content = message.content
        
        # Если DiscordSRV отправляет сообщения через Embeds (карточки)
        if not content and message.embeds:
            embed = message.embeds[0]
            author_name = embed.author.name if embed.author else "Игрок"
            content = embed.description or ""
        else:
            author_name = message.author.display_name

        # Запускаем ИИ-анализ
        await process_game_message(author_name, content)

    else:
        # Для остальных каналов игнорируем ботов и обрабатываем префиксы (!тест)
        if message.author.bot:
            return
        await bot.process_commands(message)

# ==========================================
# 💬 КОМАНДА ДЛЯ ПРОВЕРКИ (!тест)
# ==========================================
@bot.command(name="тест")
async def test_ai(ctx, *, question: str):
    await ctx.send("🤖 *Запрос в Groq отправлен...*")
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Ты — ИИ-помощник. Отвечай кратко на русском."},
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
