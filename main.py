import os, asyncio
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

BOT_TOKEN = "8968356151:AAHPbdJbRJEeC4MbBEWCzIe7u_F1A39Zvxo"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Данные по точкам
data = {
    "home": {"name": "Дом", "s": "Неизвестно", "t": "—"},
    "danya": {"name": "Даня", "s": "Неизвестно", "t": "—"}
}

# Подписки пользователей: {user_id: {"home": True, "danya": False}}
subs = {}

def get_kb(user_id):
    user_sub = subs.setdefault(user_id, {"home": True, "danya": True})
    h_ico = "🔔" if user_sub["home"] else "🔕"
    d_ico = "🔔" if user_sub["danya"] else "🔕"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"🏠 Хата {h_ico}", callback_data="toggle_home"),
            InlineKeyboardButton(text=f"👺 Даня {d_ico}", callback_data="toggle_danya")
        ],
        [
            InlineKeyboardButton(text="📊 Статус", callback_data="check_status")
        ]
    ])

@dp.message(Command("start"))
async def start_cmd(m: Message):
    subs.setdefault(m.chat.id, {"home": True, "danya": True})
    await m.answer(
        "👋 **Панель мониторинга света**\n\n"
        "Нажимай на кнопки ниже, чтобы включить (🔔) или выключить (🔕) пуши по конкретной точке:",
        reply_markup=get_kb(m.chat.id),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("toggle_"))
async def toggle_sub(call: CallbackQuery):
    place = call.data.replace("toggle_", "")
    user_sub = subs.setdefault(call.from_user.id, {"home": True, "danya": True})
    user_sub[place] = not user_sub[place]
    
    await call.message.edit_reply_markup(reply_markup=get_kb(call.from_user.id))
    await call.answer("Настройки обновлены!")

@dp.callback_query(F.data == "check_status")
async def check_now(call: CallbackQuery):
    h = data["home"]
    d = data["danya"]
    h_ico = "🟢" if h["s"] == "Есть" else "🔴" if h["s"] == "Нет" else "⚪"
    d_ico = "🟢" if d["s"] == "Есть" else "🔴" if d["s"] == "Нет" else "⚪"
    
    text = (
        f"📊 **Текущее состояние:**\n\n"
        f"{h_ico} **Дом:** {h['s']} (с {h['t']})\n"
        f"{d_ico} **Даня:** {d['s']} (с {d['t']})"
    )
    await call.answer()
    await call.message.answer(text, parse_mode="Markdown")

# Сервер для приёма сигналов от MacroDroid
async def ping(r):
    p = r.query.get("place")
    s = r.query.get("state")
    if p in data and s in ("on", "off"):
        new_status = "Есть" if s == "on" else "Нет"
        time_now = datetime.now().strftime("%H:%M:%S")
        
        data[p]["s"] = new_status
        data[p]["t"] = time_now
        
        ico = "⚡" if s == "on" else "❌"
        msg = f"{ico} **{data[p]['name']}:** Свет {new_status.lower()}! ({time_now})"
        
        # Шлем пуш только тем, у кого включен колокольчик на эту точку
        for user_id, user_prefs in subs.items():
            if user_prefs.get(p, False):
                try:
                    await bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")
                except Exception:
                    pass
                    
        return web.Response(text="OK")
    return web.Response(text="ALIVE")

async def start_bot(app):
    asyncio.create_task(dp.start_polling(bot))

app = web.Application()
app.router.add_get("/", ping)
app.router.add_get("/ping", ping)
app.on_startup.append(start_bot)

if __name__ == "__main__":
    web.run_app(app, 
                port=10000)
