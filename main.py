import os, asyncio, time, logging, json
from datetime import datetime, timezone, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("НЕМАЄ BOT_TOKEN в Environment!")

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Kyiv")
except Exception:
    TZ = timezone(timedelta(hours=3))

TIMEOUT = 40  # 40 секунд без пінгів = світла немає
SUBS_FILE = "subs.json"
STATE_FILE = "state.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Базові дані
data = {
    "home": {"name": "Хата", "icon": "🏠", "s": None, "t": "—", "last": 0, "watch": True},
    "danya": {"name": "Даня", "icon": "👺", "s": None, "t": "—", "last": 0, "watch": False},
}

def load_json(filename, default):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Помилка читання {filename}: {e}")
    return default

def save_json(filename, content):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Помилка запису {filename}: {e}")

subs = {int(k): v for k, v in load_json(SUBS_FILE, {}).items()}

# Відновлюємо стан з файлу, щоб не спамити при рестарті
saved_state = load_json(STATE_FILE, {})
for k, v in saved_state.items():
    if k in data:
        data[k]["s"] = v.get("s")
        data[k]["t"] = v.get("t", "—")

def save_current_state():
    to_save = {k: {"s": v["s"], "t": v["t"]} for k, v in data.items()}
    save_json(STATE_FILE, to_save)

def now_str():
    return datetime.now(TZ).strftime("%H:%M")

def user(uid):
    if uid not in subs:
        subs[uid] = {"home": True, "danya": True}
        save_json(SUBS_FILE, subs)
    return subs[uid]

def kb(uid):
    u = user(uid)
    bell = lambda p: "🔔" if u.get(p, True) else "🔕"
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f"🏠 Хата: {bell('home')}"),
             KeyboardButton(text=f"👺 Даня: {bell('danya')}")],
            [KeyboardButton(text="📊 Статус світла")],
        ],
        resize_keyboard=True,
        persistent=True,
    )

@dp.message(Command("start"))
async def start_cmd(m: Message):
    user(m.chat.id)
    await m.answer("🔔 — сповіщення увімкнені, 🔕 — вимкнені.", reply_markup=kb(m.chat.id))

async def toggle(m: Message, p: str):
    u = user(m.chat.id)
    u[p] = not u.get(p, True)
    save_json(SUBS_FILE, subs)
    name = data[p]["name"]
    text = f"🔔 Сповіщення по {name}: увімкнено" if u[p] else f"🔕 Сповіщення по {name}: вимкнено"
    await m.answer(text, reply_markup=kb(m.chat.id))

@dp.message(F.text.startswith("🏠"))
async def toggle_home(m: Message):
    await toggle(m, "home")

@dp.message(F.text.startswith("👺"))
async def toggle_danya(m: Message):
    await toggle(m, "danya")

@dp.message(F.text == "📊 Статус світла")
async def check_status(m: Message):
    lines = []
    for d in data.values():
        if d["s"] is None:
            lines.append(f"⚪ {d['name']}: невідомо")
        elif d["s"]:
            lines.append(f"🟢 {d['name']}: світло є (з {d['t']})")
        else:
            lines.append(f"🔴 {d['name']}: світла нема (з {d['t']})")
        await m.answer("\n".join(lines), reply_markup=kb(m.chat.id))

async def notify(p, status):
    d = data[p]
    d["s"] = status
    d["t"] = now_str()
    save_current_state()
    
    msg = f"⚡ {d['name']}: світло з'явилось ({d['t']})" if status else f"❌ {d['name']}: світло зникло ({d['t']})"
    
    for uid, prefs in list(subs.items()):
        if prefs.get(p, True):
            try:
                await bot.send_message(chat_id=uid, text=msg)
            except Exception:
                pass

async def ping(r):
    p = r.query.get("place")
    s = r.query.get("state")
    if p not in data:
        return web.Response(text="UNKNOWN_PLACE")

    data[p]["last"] = time.time()
    new_status = False if s == "off" else True

    # Перший пінг після старту бота (якщо раніше стан був невідомий)
    if data[p]["s"] is None:
        data[p]["s"] = new_status
        data[p]["t"] = now_str()
        save_current_state()
        # НЕ ВІДПРАВЛЯЄМО NOTIFY — тихо зафіксували стан!
        return web.Response(text="INITIALIZED")

    # Стан дійсно змінився
    if data[p]["s"] != new_status:
        await notify(p, new_status)

    return web.Response(text="OK")

async def watchdog():
    while True:
        await asyncio.sleep(10)
        now = time.time()
        for p, d in data.items():
            # Перевіряємо тільки якщо вважали, що світло Є, і пінгів немає довго
            if d["watch"] and d["s"] is True and d["last"] > 0 and (now - d["last"] > TIMEOUT):
                await notify(p, False)

async def start_bot(app):
    asyncio.create_task(dp.start_polling(bot, handle_signals=False))
    asyncio.create_task(watchdog())

app = web.Application()
app.router.add_get("/", ping)
app.router.add_get("/ping", ping)
app.on_startup.append(start_bot)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
