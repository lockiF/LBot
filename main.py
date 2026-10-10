import os, asyncio, time, logging, json
from datetime import datetime, timezone, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("НЕМАЄ BOT_TOKEN в Environment на Render!")

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Kiev")
except Exception:
    TZ = timezone(timedelta(hours=3))

TIMEOUT = 150  # секунд без alive = світла нема
SUBS_FILE = "subs.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

data = {
    "home": {"name": "Хата", "icon": "🏠", "s": None, "t": "—", "last": 0, "watch": True},
    "danya": {"name": "Даня", "icon": "👺", "s": None, "t": "—", "last": 0, "watch": False},
}

# Завантаження та збереження підписників у файл, щоб Render не зкидав їх при рестарті
def load_subs():
    if os.path.exists(SUBS_FILE):
        try:
            with open(SUBS_FILE, "r", encoding="utf-8") as f:
                data_loaded = json.load(f)
                return {int(k): v for k, v in data_loaded.items()}
        except Exception as e:
            logging.error(f"Помилка читання subs.json: {e}")
    return {}

def save_subs():
    try:
        with open(SUBS_FILE, "w", encoding="utf-8") as f:
            json.dump(subs, f, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Помилка запису subs.json: {e}")

subs = load_subs()

def now_str():
    return datetime.now(TZ).strftime("%H:%M")

def user(uid):
    if uid not in subs:
        subs[uid] = {"home": True, "danya": True}
        save_subs()
    return subs[uid]

def kb(uid):
    u = user(uid)
    bell = lambda p: "🔔" if u[p] else "🔕"
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
    await m.answer(
        "🔔 — сповіщення увімкнені, 🔕 — вимкнені.",
        reply_markup=kb(m.chat.id),
    )

async def toggle(m: Message, p: str):
    u = user(m.chat.id)
    u[p] = not u[p]
    save_subs()
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
    msg = f"⚡ {d['name']}: світло з'явилось" if status else f"❌ {d['name']}: світло зникло"
    
    for uid, prefs in list(subs.items()):
        if prefs.get(p, False):
            try:
                await bot.send_message(chat_id=uid, text=msg)
            except Exception:
                logging.exception(f"Не вдалося відправити повідомлення користувачу {uid}")

async def ping(r):
    p = r.query.get("place")
    s = r.query.get("state")
    if p not in data:
        return web.Response(text="ALIVE")

    if s in ("alive", "on", "off"):
        data[p]["last"] = time.time()
        new = False if s == "off" else True
        
        # Якщо статус у пам'яті ще не встановлений (після рестарту бота)
        if data[p]["s"] is None:
            data[p]["s"] = new
            data[p]["t"] = now_str()
            # Якщо світло є — шлемо сповіщення
            if new:
                await notify(p, True)
        elif data[p]["s"] != new:
            await notify(p, new)
            
        return web.Response(text="OK")

    return web.Response(text="ALIVE")

async def watchdog():
    while True:
        await asyncio.sleep(15)
        try:
            for p, d in data.items():
                if d["watch"] and d["s"] is True and (time.time() - d["last"] > TIMEOUT):
                    await notify(p, False)
        except Exception:
            logging.exception("watchdog error")

async def run_polling():
    try:
        # Отключаем перехват сигналов, чтобы aiogram не падал внутри aiohttp
        await dp.start_polling(bot, handle_signals=False)
    except Exception:
        logging.exception("POLLING CRASHED")

async def start_bot(app):
    asyncio.create_task(run_polling())
    asyncio.create_task(watchdog())

app = web.Application()
app.router.add_get("/", ping)
app.router.add_get("/ping", ping)
app.on_startup.append(start_bot)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
