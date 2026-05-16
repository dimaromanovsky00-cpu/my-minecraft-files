import os
import discord
from discord.ext import commands
import requests
import http.server
import socketserver
import threading

# ==========================================
# 🛠️ КОД-ОБМАНКА ДЛЯ ПОРТА RENDER
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

# Запускаем сайт-заглушку в отдельном потоке, чтобы он не мешал Дискорд-боту
threading.Thread(target=run_dummy_server, daemon=True).start()

# ==========================================
# 🤖 ОСНОВНОЙ КОД ДИСКОРД-БОТА
# ==========================================
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
API_KEY = os.environ.get("DEEPSEEK_API_KEY")
WATCH_CHANNEL_ID = os.environ.get("WATCH_CHANNEL_ID")
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID")

# Превращаем ID каналов в числа, если они заданы
if WATCH_CHANNEL_ID: WATCH_CHANNEL_ID = int(WATCH_CHANNEL_ID)
if LOG_CHANNEL_ID: LOG_CHANNEL_ID = int(LOG_CHANNEL_ID)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🤖 ИИ-Судья успешно запущен под именем {bot.user}!")
    # Отправляем тестовое сообщение в лог-канал при запуске
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send("🟢 **ИИ-Судья успешно запущен в облаке и готов к защите сервера!**")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Проверяем только нужный игровой чат
    if message.channel.id == WATCH_CHANNEL_ID:
        # Простой пример анализа текста через DeepSeek (базовый запрос)
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Ты — администратор Майнкрафт сервера. Твоя задача — оценивать сообщения игроков на токсичность, угрозы гриферства или подготовку заговоров. Отвечай строго в формате: [БЕЗОПАСНО] или [ПОДОЗРИТЕЛЬНО: причина]."},
                {"role": "user", "content": message.content}
            ],
            "temperature": 0.3
        }
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post("https://api.deepseek.com/v1/chat/completions", json=payload, headers=headers)
            if response.status_code == 200:
                result = response.json()['choices'][0]['message']['content']
                if "[ПОДОЗРИТЕЛЬНО]" in result.upper() or "ПОДОЗРИТЕЛЬНО" in result.upper():
                    log_channel = bot.get_channel(LOG_CHANNEL_ID)
                    if log_channel:
                        embed = discord.Embed(title="🚨 Обнаружена подозрительная активность!", color=discord.Color.red())
                        embed.add_field(name="Игрок", value=message.author.name, inline=True)
                        embed.add_field(name="Сообщение", value=message.content, inline=False)
                        embed.add_field(name="Вердикт ИИ", value=result, inline=False)
                        await log_channel.send(embed=embed)
        except Exception as e:
            print(f"Ошибка обращения к API DeepSeek: {e}")

    await bot.process_commands(message)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ ОШИБКА: DISCORD_BOT_TOKEN не найден в переменных окружения!")
    else:
        bot.run(TOKEN)
