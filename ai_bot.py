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
# 🤖 НАСТРОЙКИ БОТА И ПЕРЕМЕННЫЕ
# ==========================================
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
API_KEY = os.environ.get("DEEPSEEK_API_KEY") # Твой рабочий ключ Groq (gsk_...)
WATCH_CHANNEL_ID = os.environ.get("WATCH_CHANNEL_ID")
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID")
SECRET_CHAT_ID = os.environ.get("SECRET_CHAT_ID") # Наш секретный кабинет досье

if WATCH_CHANNEL_ID: WATCH_CHANNEL_ID = int(WATCH_CHANNEL_ID)
if LOG_CHANNEL_ID: LOG_CHANNEL_ID = int(LOG_CHANNEL_ID)
if SECRET_CHAT_ID: SECRET_CHAT_ID = int(SECRET_CHAT_ID)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Сверхбыстрая актуальная модель Groq
MODEL_NAME = "llama-3.1-8b-instant"

@bot.event
async def on_ready():
    print(f"🤖 ИИ-Судья запущен как {bot.user}!")
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send("🟢 **ИИ-Судья успешно обновлён! Секретный кабинет досье подключён к системе.**")

# === ОБЩЕНИЕ НАПРЯМУЮ ЧЕРЕЗ КОМАНДУ ===
@bot.command(name="тест")
async def test_ai(ctx, *, question: str):
    await ctx.send("🤖 *Посылаю сверхбыстрый запрос в Groq...*")
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Ты — ИИ-помощник майнкрафт сервера DigitalMine. Отвечай кратко, емко и строго на русском языке."},
            {"role": "user", "content": question}
        ]
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        if response.status_code == 200:
            result = response.json()['choices'][0]['message']['content']
            await ctx.send(f"💬 **Ответ ИИ:**\n{result}")
        else:
            await ctx.send(f"❌ Ошибка Groq! Код ответа: {response.status_code}")
    except Exception as e:
        await ctx.send(f"❌ Произошла ошибка: {e}")

# === АВТО-АНАЛИЗ ИГРОВОГО ЧАТА С УЧЁТОМ ДОСЬЕ ИЗ СЕКРЕТНОГО ЧАТА ===
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Проверяем, пришло ли сообщение из канала, транслирующего чат Майнкрафта
    if message.channel.id == WATCH_CHANNEL_ID:
        
        player_notes = ""
        # Динамически вытаскиваем историю сообщений из секретного кабинета админа
        if SECRET_CHAT_ID:
            secret_channel = bot.get_channel(SECRET_CHAT_ID)
            if secret_channel:
                notes = []
                try:
                    # Читаем последние 50 записей в канале, игнорируя сообщения самого бота
                    async for msg in secret_channel.history(limit=50, oldest_first=False):
                        if not msg.author.bot and msg.content.strip():
                            notes.append(f"- {msg.content}")
                    if notes:
                        player_notes = "\n".join(notes)
                except Exception as history_error:
                    print(f"Не удалось прочитать секретный чат: {history_error}")

        # Формируем расширенную инструкцию для ИИ-Судьи
        system_prompt = (
            "Ты — скрытый ИИ-модератор Майнкрафт сервера DigitalMine. Твоя задача — анализировать сообщения игроков.\n"
            "Если игрок замышляет гриферство, кражу ресурсов, поджог привата, заговор против администрации, "
            "попытку обмана или проявляет открытую агрессию, отвечай строго в формате: [ПОДОЗРИТЕЛЬНО: причина]. "
            "Если сообщение обычное и безопасное, пиши [БЕЗОПАСНО].\n"
            "Отвечай строго на русском языке.\n\n"
            "⚠️ ВАЖНО: Ниже приведены актуальные секретные досье и заметки об игроках от Администратора. "
            "Обязательно учитывай эти характеры, контекст прошлых отношений и предупреждения при оценке фраз:\n"
            f"{player_notes if player_notes else 'Особых примечаний по игрокам пока нет. Суди по стандартным правилам.'}"
        )

        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Игрок {message.author.name} пишет в игровой чат: {message.content}"}
            ]
        }
        headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
        
        try:
            response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
            if response.status_code == 200:
                result = response.json()['choices'][0]['message']['content']
                
                # Если ИИ вынес вердикт подозрительности
                if "ПОДОЗРИТЕЛЬНО" in result.upper():
                    log_channel = bot.get_channel(LOG_CHANNEL_ID)
                    if log_channel:
                        embed = discord.Embed(title="🚨 ИИ-Судья зафиксировал угрозу!", color=discord.Color.red())
                        embed.add_field(name="Подозреваемый игрок", value=message.author.name, inline=True)
                        embed.add_field(name="Текст сообщения из игры", value=message.content, inline=False)
                        embed.add_field(name="Анализ и вердикт Судьи", value=result, inline=False)
                        await log_channel.send(embed=embed)
        except Exception as e:
            print(f"Ошибка автоматического анализа чата: {e}")

    await bot.process_commands(message)

if __name__ == "__main__":
    bot.run(TOKEN)
