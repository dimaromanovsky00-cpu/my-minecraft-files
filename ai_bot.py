import os
import discord
from discord.ext import commands
import http.server
import socketserver
import threading

# Веб-заглушка для Render
def run_dummy_server():
    handler = http.server.SimpleHTTPRequestHandler
    port = int(os.environ.get("PORT", 10000))
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"🌍 ВЕБ-ЗАГЛУШКА: Работает на порту {port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"⚠️ ВЕБ-ЗАГЛУШКА ОШИБКА: {e}")

threading.Thread(target=run_dummy_server, daemon=True).start()

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
WATCH_CHANNEL_ID = os.environ.get("WATCH_CHANNEL_ID")
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"⚙️ ЛОГ ЗАПУСКА: Бот успешно авторизован как {bot.user}")
    print(f"⚙️ НАСТРОЙКИ ИЗ RENDER:")
    print(f"   - Игровой чат (WATCH_CHANNEL_ID): {WATCH_CHANNEL_ID}")
    print(f"   - Лог чат (LOG_CHANNEL_ID): {LOG_CHANNEL_ID}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # ЭТОТ ЛОГ ПОКАЖЕТ, ВИДИТ ЛИ БОТ ЧАТ ВООБЩЕ
    print(f"📩 НОВОЕ СООБЩЕНИЕ!")
    print(f"   - Автор: {message.author.name}")
    print(f"   - Канал (где написали): {message.channel.name} (ID: {message.channel.id})")
    print(f"   - Текст: {message.content}")

    await bot.process_commands(message)

@bot.command(name="тест")
async def test(ctx):
    print("🎯 СРАБОТАЛА КОМАНДА !тест В ЛОГАХ")
    await ctx.send("🤖 Бот видит команды!")

if __name__ == "__main__":
    bot.run(TOKEN)
