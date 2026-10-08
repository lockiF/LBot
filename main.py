import os, asyncio
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

bot = Bot(token="8968356151:AAHPbdJbRJEeC4MbBEWCzIe7u_F1A39Zvxo")
dp = Dispatcher()

data = {
    "home": {"s": "Неизвестно", "t": "—"},
    "danya": {"s": "Неизвестно", "t": "—"}
}

kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🏠 Дом"), KeyboardButton(text="🎮 Даня")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start(m):
    await m.answer("Выбери точку:", reply_markup=kb)

@dp.message(F.text == "🏠 Дом")
async def h(m):
    ico = "🟢" if data["home"]["s"] == "Есть" else "🔴"
    await m.answer(f"{ico} Дом: {data['home']['s']}\nВремя: {data['home']['t']}")

@dp.message(F.text == "🎮 Даня")
async def d(m):
    ico = "🟢" if data["danya"]["s"] == "Есть" else "🔴"
    await m.answer(f"{ico} Даня: {data['danya']['s']}\nВремя: {data['danya']['t']}")

async def ping(r):
    p = r.query.get("place")
    s = r.query.get("state")
    if p in data and s in ("on", "off"):
        data[p]["s"] = "Есть" if s == "on" else "Нет"
        data[p]["t"] = datetime.now().strftime("%H:%M:%S")
        return web.Response(text="OK")
    return web.Response(text="ALIVE")

async def start_bot(app):
    asyncio.create_task(dp.start_polling(bot))

app = web.Application()
app.router.add_get("/", ping)
app.router.add_get("/ping", ping)
app.on_startup.append(start_bot)

if __name__ == "__main__":
    web.run_app(app, port=int(os.getenv("PORT", 10000)))
