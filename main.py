import os
import asyncio
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN", "8968356151:AAHPbdJbRJEeC4MbBEWCzIe7u_F1A39Zvxo")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

status_data = {
    "home": {"status": "Неизвестно", "time": "—"},
    "danya": {"status": "Неизвестно", "time": "—"}
}

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🏠 Дом"), KeyboardButton(text="🎮 Даня")],
        [KeyboardButton(text="📊 Проверить всё")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Выбери адрес для проверки:", reply_markup=keyboard)

@dp.message(lambda msg: msg.text == "🏠 Дом")
async def check_home(message: types.Message):
    info = status_data["home"]
    emoji = "🟢" if info["status"] == "Есть" else "🔴" if info["status"] == "Нет" else "⚪"
    await message.answer(f"{emoji} **Дом:** {info['status']}\n🕒 Смена статуса: {info['time']}", parse_mode="Markdown")

@dp.message(lambda msg: msg.text == "🎮 Даня")
async def check_danya(message: types.Message):
    info = status_data["danya"]
    emoji = "🟢" if info["status"] == "Есть" else "🔴" if info["status"] == "Нет" else "⚪"
    await message.answer(f"{emoji} **Даня:** {info['status']}\n🕒 Смена статуса: {info['time']}", parse_mode="Markdown")

@dp.message(lambda msg: msg.text == "📊 Проверить всё")
async def check_all(message: types.Message):
    h = status_data["home"]
    d = status_data["danya"]
    h_em = "🟢" if h["status"] == "Есть" else "🔴" if h["status"] == "Нет" else "⚪"
    d_em = "🟢" if d["status"] == "Есть" else "🔴" if d["status"] == "Нет" else "⚪"
    await message.answer(
        f"📊 **Сводка по точкам:**\n\n"
        f"{h_em} **Дом:** {h['status']} ({h['time']})\n"
        f"{d_em} **Даня:** {d['status']} ({d['time']})",
        parse_mode="Markdown"
    )

async def handle_ping(request):
    place = request.query.get("place")
    state = request.query.get("state")

    if place in status_data and state in ("on", "off"):
        status_data[place]["status"] = "Есть" if state == "on" else "Нет"
        status_data[place]["time"] = datetime.now().strftime("%H:%M:%S")
        return web.Response(text="OK")
    return web.Response(text="Ping alive", status=200)

async def on_startup(app):
    # Запускаем поллинг сообщений бота в фоне
    asyncio.create_task(dp.start_polling(bot))

async def on_shutdown(app):
    await bot.session.close()

def init_app():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/ping", handle_ping)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    web.run_app(init_app(), host="0.0.0.
    0", port=port)
