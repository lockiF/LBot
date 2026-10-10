import os, asyncio, time
from datetime import datetime
from zoneinfo import ZoneInfo
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message

TZ = ZoneInfo("Europe/Kyiv")
TIMEOUT = 150  # секунд без alive = света нет

def now_str():
    return datetime.now(TZ).strftime("%H:%M:%S")

# добавь в data поле last и watch:
data = {
    "home": {"name": "Хата", "s": "Неизвестно", "t": "—", "last": 0, "watch": True},
    "danya": {"name": "Даня", "s": "Неизвестно", "t": "—", "last": 0, "watch": False}
}

async def notify(p, status):
    data[p]["s"] = status
    data[p]["t"] = now_str()
    ico = "⚡" if status == "Есть" else "❌"
    msg = f"{ico} **{data[p]['name']}:** Свет {status.lower()}! ({data[p]['t']})"
    for user_id, prefs in subs.items():
        if prefs.get(p, False):
            try:
                await bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")
            except Exception:
                pass

async def ping(r):
    p = r.query.get("place")
    s = r.query.get("state")
    if p not in data:
        return web.Response(text="ALIVE")

    if s == "alive":
        data[p]["last"] = time.time()
        # свет вернулся, а "on" мы пропустили
        if data[p]["s"] == "Нет":
            await notify(p, "Есть")
        elif data[p]["s"] == "Неизвестно":
            data[p]["s"] = "Есть"
            data[p]["t"] = now_str()
        return web.Response(text="OK")

    if s in ("on", "off"):
        data[p]["last"] = time.time()
        new_status = "Есть" if s == "on" else "Нет"
        if data[p]["s"] != new_status:
            await notify(p, new_status)
        return web.Response(text="OK")

    return web.Response(text="ALIVE")

async def watchdog():
    while True:
        await asyncio.sleep(15)
        for p, d in data.items():
            if d["watch"] and d["s"] == "Есть" and time.time() - d["last"] > TIMEOUT:
                await notify(p, "Нет")

async def start_bot(app):
    asyncio.create_task(dp.start_polling(bot))
    asyncio.create_task(watchdog())

app = web.Application()
app.router.add_get("/", ping)
app.router.add_get("/ping", ping)
app.on_startup.append(start_bot)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=10000)
