import os, asyncio, time, logging
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

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

data = {
    "home": {"name": "Хата", "icon": "🏠", "s": None, "t": "—", "last": 0, "watch": True},
    "danya": {"name": "Даня", "icon": "👺", "s": None, "t": "—", "last": 0, "watch": False},
}

subs = {}

def now_str():
    return datetime.now(TZ).strftime("%H:%M")

def user(uid):
    return subs.setdefault(uid, {"home": True, "danya": True})

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
        "Я пишу, коли зникає або з'являється світло.\n"
        "🔔 — сповіщення увімкнені, 🔕 — вимкнені. Натисни на кнопку, щоб перемкнути.",
        reply_markup=kb(m.chat.id),
    )

async def toggle(m: Message, p: str):
    u = user(m.chat.id)
    u[p] = not u[p]
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
    if status:
        msg = f"⚡ {d['name']}: світло з'явилось"
    else:
        msg = f"❌ {d['name']}: світло зникло"
    for uid, prefs in list(subs.items()):
        if prefs.get(p, False):
            try:
                await bot.send_message(chat_id=uid, text=msg)
            except Exception:
                logging.exception("send_message failed")

async def ping(r):
    p = r.query.get("place")
    s = r.query.get("state")
    if p not in data:
        return web.Response(text="ALIVE")

    if s in ("alive", "on", "off"):
        data[p]["last"] = time.time()
        new = False if s == "off" else True
        if data[p]["s"] is None and s == "alive":
            data[p]["s"] = True
            data[p]["t"] = now_str()
        elif data[p]["s"] != new:
            await notify(p, new)
        return web.Response(text="OK")

    return web.Response(text="ALIVE")

async def watchdog():
    while True:
        await asyncio.sleep(15)
        try:
            for p, d in data.items():
                if d["watch"] and d["s"] is True and time.time() - d["last"] > TIMEOUT:
                    await notify(p, False)
        except Exception:
            logging.exception("watchdog error")

async def run_polling():
    try:
        await dp.start_polling(bot)
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
