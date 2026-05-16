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

threading.Thread(target=run_dummy_server, daemon=True).start()

# ==========================================
# 🤖 НАСТРОЙКИ БОТА
# ==========================================
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
API_KEY = os.environ.get("DEEPSEEK_API_KEY")
WATCH_CHANNEL_ID = os.environ.get("WATCH_CHANNEL_ID")
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID")

if WATCH_CHANNEL_ID: WATCH_CHANNEL_ID = int(WATCH_CHANNEL_ID)
if LOG_CHANNEL_ID: LOG_CHANNEL_ID = int(LOG_CHANNEL_ID)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🤖 ИИ-Судья успешно запущен как {bot.user}!")
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send("🟢 **ИИ-Судья успешно запущен и готов к тесту DeepSeek!**")

# === ОБЩЕНИЕ С DEEPSEEK НАПРЯМУЮ ===
@bot.command(name="тест")
async def test_deepseek(ctx, *, question: str):
    """Команда для прямого разговора с ИИ: !тест [твой вопрос]"""
    await ctx.send("🤖 *Посылаю запрос в DeepSeek...*")
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Ты — ИИ-помощник майнкрафт сервера. Отвечай кратко и емко."},
            {"role": "user", "content": question}
        ],
        "temperature": 0.7
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post("https://api.deepseek.com/v1/chat/completions", json=payload, headers=headers)
        if response.status_code == 200:
            result = response.json()['choices'][0]['message']['content']
            await ctx.send(f"💬 **Ответ от DeepSeek:**\n{result}")
        else:
            await ctx.send(f"❌ Ошибка DeepSeek! Код ответа сервера: {response.status_code}\nПроверь баланс или API ключ.")
    except Exception as e:
        await ctx.send(f"❌ Произошла ошибка: {e}")

# === АВТО-АНАЛИЗ ИГРОВОГО ЧАТА ===
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Проверяем игровой чат
    if message.channel.id == WATCH_CHANNEL_ID:
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Ты — скрытый ИИ-модератор Майнкрафт сервера. Анализируй сообщения игроков. Если игрок замышляет гриферство, кражу, поджог привата, заговор против админа или жестко токсичит, отвечай строго в формате: [ПОДОЗРИТЕЛЬНО: причина]. Если все в порядке, пиши [БЕЗОПАСНО]."},
                {"role": "user", "content": message.content}
            ],
            "temperature": 0.2
        }
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post("https://api.deepseek.com/v1/chat/completions", json=payload, headers=headers)
            if response.status_code == 200:
                result = response.json()['choices'][0]['message']['content']
                if "ПОДОЗРИТЕЛЬНО" in result.upper():
                    log_channel = bot.get_channel(LOG_CHANNEL_ID)
                    if log_channel:
                        embed = discord.Embed(title="🚨 Судья обнаружил угрозу на сервере!", color=discord.Color.red())
                        embed.add_field(name="Нарушитель", value=message.author.name, inline=True)
                        embed.add_field(name="Что написано", value=message.content, inline=False)
                        embed.add_field(name="Анализ Судьи", value=result, inline=False)
                        await log_channel.send(embed=embed)
        except Exception as e:
            print(f"Ошибка анализа чата: {e}")

    await bot.process_commands(message)

if __name__ == "__main__":
    bot.run(TOKEN)
