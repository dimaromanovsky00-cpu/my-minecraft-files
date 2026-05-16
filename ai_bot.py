import os
import discord
import requests
from flask import Flask
import threading

app = Flask(__name__)

# ==========================================
# 🤖 НАСТРОЙКИ И ПОДГОТОВКА ID
# ==========================================
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
API_KEY = os.environ.get("DEEPSEEK_API_KEY")
WATCH_CHANNEL_ID = os.environ.get("WATCH_CHANNEL_ID")
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID")
SECRET_CHAT_ID = os.environ.get("SECRET_CHAT_ID")

def clean_id(val):
    try:
        return int(str(val).strip()) if val else None
    except:
        return None

WATCH_CHANNEL_ID = clean_id(WATCH_CHANNEL_ID)
LOG_CHANNEL_ID = clean_id(LOG_CHANNEL_ID)
SECRET_CHAT_ID = clean_id(SECRET_CHAT_ID)

# Включаем ВСЕ интенты шлюза
intents = discord.Intents.all()
client = discord.Client(intents=intents)
MODEL_NAME = "llama-3.1-8b-instant"

@app.route('/', methods=['GET', 'HEAD'])
def index():
    return "ИИ-Судья слушает Дискорд!", 200

# ==========================================
# 🧠 ОБРАБОТКА ТЕКСТА ЧЕРЕЗ ИИ
# ==========================================
async def analyze_text(author, text):
    print(f"🔍 ИИ анализирует фразу от [{author}]: {text}", flush=True)
    
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
            print(f"⚠️ Ошибка секретного чата: {e}", flush=True)

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
            print(f"🤖 Вердикт ИИ: {verdict}", flush=True)
            
            if "ПОДОЗРИТЕЛЬНО" in verdict.upper():
                log_ch = client.get_channel(LOG_CHANNEL_ID)
                if log_ch:
                    emb = discord.Embed(title="🚨 Фиксация угрозы в чате!", color=discord.Color.red())
                    emb.add_field(name="Игрок", value=author, inline=True)
                    emb.add_field(name="Фраза", value=text, inline=False)
                    emb.add_field(name="Судейский вердикт", value=verdict, inline=False)
                    await log_ch.send(embed=emb)
                    print("🔴 Эмбед угрозы отправлен в Дискорд!", flush=True)
        else:
            print(f"❌ Ошибка Groq API: {res.status_code} | {res.text}", flush=True)
    except Exception as err:
        print(f"❌ Ошибка сети с ИИ: {err}", flush=True)

# ==========================================
# 📡 ДВОЙНОЙ ПЕРЕХВАТ ИЗ ТЕКСТОВОГО КАНАЛА
# ==========================================

# Способ 1: Стандартный обработчик сообщений
@client.event
async def on_message(message):
    if WATCH_CHANNEL_ID and message.channel.id == WATCH_CHANNEL_ID:
        if message.author.id == client.user.id:
            return
        print(f"📥 [on_message] Поймано от {message.author}: {message.content[:30]}...", flush=True)
        await process_discord_msg(message)

# Способ 2: Сырой низкоуровневый перехват пакетов шлюза
@client.event
async def on_raw_message_create(payload):
    if WATCH_CHANNEL_ID and payload.channel_id == WATCH_CHANNEL_ID:
        if payload.message_id and payload.author_id == client.user.id:
            return
        print(f"📥 [on_raw_message] Шлюз зафиксировал активность в канале!", flush=True)
        try:
            channel = client.get_channel(payload.channel_id) or await client.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            await process_discord_msg(message)
        except Exception as e:
            print(f"⚠️ Ошибка разбора сырого пакета: {e}", flush=True)

# Общая логика вытаскивания текста
async def process_discord_msg(message):
    content = message.content
    author_name = message.author.display_name

    # Если DiscordSRV прячет текст в Эмбед
    if not content and message.embeds:
        emb = message.embeds[0]
        author_name = emb.author.name if emb.author else "Игрок сервера"
        content = emb.description or emb.title or ""
        if not content and emb.fields:
            content = " ".join([f.value for f in emb.fields if f.value])

    if content and content.strip():
        await analyze_text(author_name, content)

# ==========================================
# 🟢 СТАРТ БОТА
# ==========================================
@client.event
async def on_ready():
    print(f"🟢 БОТ ПОЛНОСТЬЮ ГОТОВ! Наблюдение за каналом: {WATCH_CHANNEL_ID}", flush=True)
    if LOG_CHANNEL_ID:
        try:
            ch = client.get_channel(LOG_CHANNEL_ID)
            if ch:
                await ch.send("🤖 **ИИ-Судья вернулся на прослушку Дискорд-канала! Жду сообщений.**")
        except:
            pass

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    print(f"🚀 СТАРТ СКИПТА! Наблюдение за: {WATCH_CHANNEL_ID}", flush=True)
    threading.Thread(target=run_flask, daemon=True).start()
    client.run(TOKEN)
