import os
import re
import discord
import requests
from flask import Flask
import threading

app = Flask(__name__)

# ==========================================
# 🤖 НАСТРОЙКИ И ПОДГОТОВКА ID КАНАЛОВ
# ==========================================
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
API_KEY = os.environ.get("DEEPSEEK_API_KEY")

# 1. Канал, который бот слушает (сырая-консоль)
WATCH_CHANNEL_ID = os.environ.get("WATCH_CHANNEL_ID")
# 2. Канал для вердиктов ИИ (ии-логи)
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID")
# 3. Канал для чистых входов/выходов с IP (входы-выходы)
JOIN_LEAVE_CHANNEL_ID = os.environ.get("JOIN_LEAVE_CHANNEL_ID")
# 4. Канал с заметками админа (кабинет-судьи)
SECRET_CHAT_ID = os.environ.get("SECRET_CHAT_ID")

def clean_id(val):
    try:
        return int(str(val).strip()) if val else None
    except:
        return None

WATCH_CHANNEL_ID = clean_id(WATCH_CHANNEL_ID)
LOG_CHANNEL_ID = clean_id(LOG_CHANNEL_ID)
JOIN_LEAVE_CHANNEL_ID = clean_id(JOIN_LEAVE_CHANNEL_ID)
SECRET_CHAT_ID = clean_id(SECRET_CHAT_ID)

# Включаем интенты шлюза Дискорда
intents = discord.Intents.all()
client = discord.Client(intents=intents)
MODEL_NAME = "llama-3.1-8b-instant"

@app.route('/', methods=['GET', 'HEAD'])
def index():
    return "ИИ-Судья активно слушает DiscordSRV мост сервера!", 200

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
            print(f"⚠️ Ошибка секретного чата (Кабинет Судьи): {e}", flush=True)

    system_prompt = (
        "Ты — скрытый ИИ-модератор сервера DigitalMine. Твоя задача — анализировать чат.\n"
        "If the player is planning griefing, resource theft, a conspiracy against admins, or shows aggression, "
        "respond strictly in the format: [ПОДОЗРИТЕЛЬНО: причина].\n"
        "Если сообщение обычное и безопасное, пиши [БЕЗОПАСНО].\n"
        "Отвечай только на русском языке.\n\n"
        f"Заметки админа из Кабинета Судьи:\n{player_notes}"
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
                # Угрозы отправляются СТРОГО в канал ии-логи (LOG_CHANNEL_ID)
                log_ch = client.get_channel(LOG_CHANNEL_ID)
                if log_ch:
                    emb = discord.Embed(title="🚨 Фиксация угрозы в чате!", color=discord.Color.red())
                    emb.add_field(name="Игрок", value=author, inline=True)
                    emb.add_field(name="Фраза", value=text, inline=False)
                    emb.add_field(name="Судейский вердикт", value=verdict, inline=False)
                    await log_ch.send(embed=emb)
                    print(f"🔴 Эмбед угрозы от {author} отправлен в ии-логи!", flush=True)
        else:
            print(f"❌ Ошибка Groq API: {res.status_code} | {res.text}", flush=True)
    except Exception as err:
        print(f"❌ Ошибка сети с ИИ: {err}", flush=True)

# ==========================================
# 📡 ДВОЙНОЙ ПЕРЕХВАТ СООБЩЕНИЙ ИЗ КОНСОЛИ
# ==========================================

@client.event
async def on_message(message):
    if WATCH_CHANNEL_ID and message.channel.id == WATCH_CHANNEL_ID:
        if message.embeds and any("Фиксация угрозы" in (e.title or "") for e in message.embeds):
            return
        await process_discord_msg(message)

@client.event
async def on_raw_message_create(payload):
    if WATCH_CHANNEL_ID and payload.channel_id == WATCH_CHANNEL_ID:
        try:
            channel = client.get_channel(payload.channel_id) or await client.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            if message.embeds and any("Фиксация угрозы" in (e.title or "") for e in message.embeds):
                return
            await process_discord_msg(message)
        except Exception as e:
            print(f"⚠️ Ошибка разбора сырого пакета: {e}", flush=True)

# ==========================================
# 📊 ПОСТРОЧНЫЙ ПЕРЕХВАТ, ОЧИСТКА И АНАЛИЗ ЧАТА
# ==========================================
async def process_discord_msg(message):
    content = message.content
    author_name = message.author.display_name

    if content and content.strip():
        # Разбиваем сообщение из консоли на отдельные строки на случай склейки
        lines = content.split('\n')
        is_console_log = False

        for line in lines:
            if not line.strip():
                continue

            # 1. Перехват входа игрока + парсинг IP
            if "logged in with entity id" in line:
                is_console_log = True
                match = re.search(r"\[\w+\s+(\d{2}:\d{2}:\d{2})\s+INFO.*?\]\s+(\w+)\[\/(.*?):\d+\]\s+logged\s+in", line)
                if match:
                    time_str, username, ip_address = match.group(1), match.group(2), match.group(3)
                    clean_msg = f"⏰ `[{time_str}]` | 🟢 **{username}** зашёл на server | 🌐 `[IP: {ip_address}]`"
                    
                    # Отправляем КРАСИВЫЙ лог строго в канал входы-выходы
                    target_ch_id = JOIN_LEAVE_CHANNEL_ID or LOG_CHANNEL_ID
                    ch = client.get_channel(target_ch_id)
                    if ch:
                        await ch.send(clean_msg)

            # 2. Перехват выхода игрока
            elif "lost connection:" in line:
                is_console_log = True
                match = re.search(r"\[\w+\s+(\d{2}:\d{2}:\d{2})\s+INFO.*?\]\s+(\w+)\s+lost\s+connection", line)
                if match:
                    time_str, username = match.group(1), match.group(2)
                    clean_msg = f"⏰ `[{time_str}]` | 🔴 **{username}** вышел с сервера"
                    
                    # Отправляем строго в канал входы-выходы
                    target_ch_id = JOIN_LEAVE_CHANNEL_ID or LOG_CHANNEL_ID
                    ch = client.get_channel(target_ch_id)
                    if ch:
                        await ch.send(clean_msg)

        # Если сообщение полностью состояло из системных логов входа/выхода — прерываемся, ИИ его не читает
        if is_console_log:
            return

    # Если DiscordSRV прислал обычное сообщение игрока "Ник: текст"
    if content and content.strip():
        if ":" in content:
            parts = content.split(":", 1)
            raw_author = parts[0].strip()
            if "]" in raw_author:
                raw_author = raw_author.split("]")[-1].strip()
            
            author_name = raw_author
            content = parts[1].strip()

    # Разбор структуры, если DiscordSRV упаковал текст чата в Embed
    if not content and message.embeds:
        emb = message.embeds[0]
        if emb.author:
            author_name = emb.author.name
        elif emb.title and ":" in emb.title:
            author_name = emb.title.split(":")[0].strip()
            
        content = emb.description or emb.title or ""
        if not content and emb.fields:
            content = " ".join([f.value for f in emb.fields if f.value])

    # Запуск ИИ-Судьи для анализа обычного игрового чата
    if content and content.strip():
        content = content.replace("`", "").strip()
        await analyze_text(author_name, content)

# ==========================================
# 🟢 СТАРТ СИСТЕМЫ
# ==========================================
@client.event
async def on_ready():
    print(f"🟢 БОТ ПОЛНОСТЬЮ ГОТОВ! Наблюдение за консолью: {WATCH_CHANNEL_ID}", flush=True)
    if LOG_CHANNEL_ID:
        try:
            ch = client.get_channel(LOG_CHANNEL_ID)
            if ch:
                await ch.send("🤖 **ИИ-Судья подключился к мосту DiscordSRV! Построчный анализ логов запущен.**")
        except:
            pass

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    print(f"🚀 СТАРТ СКИПТА! Наблюдение за каналом ID: {WATCH_CHANNEL_ID}", flush=True)
    threading.Thread(target=run_flask, daemon=True).start()
    client.run(TOKEN)
