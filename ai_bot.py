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
    print(f"🔍 Параметры: WATCH={WATCH_CHANNEL_ID}, LOG={LOG_CHANNEL_ID}, SECRET={SECRET_CHAT_ID}")

@bot.event
async def on_message(message):
    # ПРОВЕРКА 1: Видит ли бот вообще хоть какие-то сообщения в целевом канале?
    if WATCH_CHANNEL_ID and message.channel.id == WATCH_CHANNEL_ID:
        print(f"📥 [ОТЛАДКА] Бот поймал сообщение в игровом канале!")
        print(f"👤 Автор: {message.author} (Бот? {message.author.bot})")
        print(f"📝 Текст: {message.content}")

        if message.author == bot.user:
            print("🚫 Это собственное сообщение бота, игнорируем.")
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
            f"Заметки админа:\n{player_notes}"
        )

        author_name = message.author.display_name

        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Игрок {author_name} пишет в игровой чат: {message.content}"}
            ]
        }
        headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
        
        try:
            print("🧠 Отправляю запрос в Groq...")
            response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
            if response.status_code == 200:
                result = response.json()['choices'][0]['message']['content']
                print(f"🤖 Ответ ИИ: {result}")
                
                # ВРЕМЕННО: Слём ВСЕ вердикты в логи, чтобы понять, работает ли отправка!
                log_channel = bot.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    color = discord.Color.red() if "ПОДОЗРИТЕЛЬНО" in result.upper() else discord.Color.green()
                    embed = discord.Embed(title="🔍 Тестовый анализ Судьи", color=color)
                    embed.add_field(name="Игрок", value=author_name, inline=True)
                    embed.add_field(name="Сообщение", value=message.content, inline=False)
                    embed.add_field(name="Вердикт", value=result, inline=False)
                    await log_channel.send(embed=embed)
                    print("🟢 Эмбед успешно отправлен в лог-канал!")
            else:
                print(f"❌ Ошибка Groq! Статус: {response.status_code}, Текст: {response.text}")
        except Exception as e:
            print(f"❌ Ошибка во время анализа: {e}")

    else:
        if message.author.bot:
            return
        await bot.process_commands(message)

# === КОМАНДА !тест ===
@bot.command(name="тест")
async def test_ai(ctx, *, question: str):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Ты — ИИ-помощник. Отвечай кратко."},
            {"role": "user", "content": question}
        ]
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        await ctx.send(f"💬 {response.json()['choices'][0]['message']['content']}")
    except Exception as e:
        await ctx.send(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    bot.run(TOKEN)
