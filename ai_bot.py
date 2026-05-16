import os
import discord
import requests
import http.server
import socketserver
import threading

# ==========================================
# 🛠️ ВЕБ-СЕРВЕР ДЛЯ РЕНДЕРА (МГНОВЕННЫЙ ВЫВОД)
# ==========================================
def run_dummy_server():
    handler = http.server.SimpleHTTPRequestHandler
    port = int(os.environ.get("PORT", 10000))
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"🌍 Веб-заглушка работает на порту {port}", flush=True)
            httpd.serve_forever()
    except Exception as e:
        print(f"⚠️ Ошибка веб-сервера: {e}", flush=True)

threading.Thread(target=run_dummy_server, daemon=True).start()

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

# Включаем абсолютно все интенты шлюза
intents = discord.Intents.all()
client = discord.Client(intents=intents)

MODEL_NAME = "llama-3.1-8b-instant"

print(f"🚀 СТАРТ СКИПТА! Наблюдение за: {WATCH_CHANNEL_ID} | Логи в: {LOG_CHANNEL_ID}", flush=True)

# ==========================================
# ⚡ МГНОВЕННЫЕ ЭВЕНТЫ ПОДКЛЮЧЕНИЯ
# ==========================================
@client.event
async def on_connect():
    print("🔌 Подключено к шлюзу Discord! Ждем готовности...", flush=True)

@client.event
async def on_ready():
    print(f"🟢 БОТ ПОЛНОСТЬЮ ГОТОВ! Имя в сети: {client.user}", flush=True)
    # Сразу шлем сигнал в лог-канал, чтобы проверить отправку сообщений
    if LOG_CHANNEL_ID:
        try:
            ch = client.get_channel(LOG_CHANNEL_ID)
            if ch:
                await ch.send("🤖 **ИИ-Судья успешно вошёл в сеть и готов к тестам чата!**")
                print("🟢 Тестовое сообщение отправлено в Дискорд!", flush=True)
        except Exception as log_err:
            print(f"❌ Не удалось отправить старт-сообщение в канал: {log_err}", flush=True)

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
            print(f"⚠️ Ошибка досье: {e}", flush=True)

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
            print(f"🤖 Вердикт Groq: {verdict}", flush=True)
            
            # Логируем в Дискорд, только если нашли реальную угрозу
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
# 🛑 УЛЬТРА-ПЕРЕХВАТ СЫРЫХ СОБЫТИЙ (С ПОЛНЫМ ДЕБАГОМ)
# ==========================================
@client.event
async def on_raw_message_create(payload):
    if WATCH_CHANNEL_ID and payload.channel_id == WATCH_CHANNEL_ID:
        
        try:
            channel = client.get_channel(payload.channel_id) or await client.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
        except Exception as fetch_err:
            print(f"⚠️ Не удалось прочесть сырое сообщение: {fetch_err}", flush=True)
            return

        if message.author.id == client.user.id:
            return

        print(f"\n📥 [ПЕРЕХВАТ] КТО-ТО НАПИСАЛ! Автор: {message.author} (Бот/Вебхук: {message.author.bot})", flush=True)
        
        content = ""
        author_name = message.author.display_name

        # 🕵️‍♂️ ДЕБАГ ПОЛЯ: Распечатываем всё, что прилетело от DiscordSRV
        print(f"📋 Сырой контент (content): '{message.content}'", flush=True)
        print(f"📋 Кол-во эмбедов (embeds): {len(message.embeds)}", flush=True)

        # 1. Проверяем обычный текст
        if message.content and message.content.strip():
            content = message.content

        # 2. Проверяем сложные эмбеды от вебхуков плагина
        if not content and message.embeds:
            emb = message.embeds[0]
            print(f"📊 Свойства эмбеда -> Title: '{emb.title}', Desc: '{emb.description}'", flush=True)
            if emb.author:
                print(f"📊 Автор эмбеда -> Name: '{emb.author.name}'", flush=True)
                author_name = emb.author.name
            
            # Собираем текст из любого доступного стандартного поля
            content = emb.description or emb.title or ""
            
            # Если DiscordSRV засунул текст в блоки полей (fields)
            if not content and emb.fields:
                print(f"📊 Найдены поля в эмбеде! Fields: {emb.fields}", flush=True)
                content = " ".join([f.value for f in emb.fields if f.value])

        print(f"📝 ИТОГОВЫЙ РАСПОЗНАННЫЙ ТЕКСТ: '{content}' от {author_name}\n", flush=True)

        # Если текст вытащили — отправляем в Groq ИИ
        if content and content.strip():
            await analyze_text(author_name, content)
        else:
            print("⚠️ Робот не смог извлечь текст. Проверь логи дебага выше!", flush=True)

if __name__ == "__main__":
    client.run(TOKEN)
