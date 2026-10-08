import os, asyncio
import os, asyncio
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message

BOT_TOKEN = "8968356151:AAHPbdJbRJEeC4MbBEWCzIe7u_F1A39Zvxo"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Данные по точкам
data = {
    "home": {"name": "Хата", "s": "Неизвестно", "t": "—"},
    "danya": {"name": "Даня", "s": "Неизвестно", "t": "—"}
}

# Подписки пользователей: {user_id: {"home": True, "danya": True}}
subs = {}

def get_reply_kb(user_id):
    user_sub = subs.setdefault(user_id, {"home": True, "danya": True})
    h_text = f"🏠 Хата: {'🔔 ВКЛ' if user_sub['home'] else '🔕 ВЫКЛ'}"
    d_text = f"🎮 Даня: {'🔔 ВКЛ' if user_sub['danya'] else '🔕 ВЫКЛ'}"
    
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=h_text), KeyboardButton(text=d_text)],
            [KeyboardButton(text="📊 Проверить статус")]
        ],
        resize_keyboard=True,
        persistent=True
    )

@dp.message(Command("start"))
async def start_cmd(m: Message):
    subs.setdefault(m.chat.id, {"home": True, "danya": True})
    await m.answer(
        "Панель мониторинга готова! Кнопки всегда внизу экрана 👇",
        reply_markup=get_reply_kb(m.chat.id)
    )

# Переключение Хаты
@dp.message(F.text.startswith("🏠 Хата:"))
async def toggle_home(m: Message):
    user_sub = subs.setdefault(m.chat.id, {"home": True, "danya": True})
    user_sub["home"] = not user_sub["home"]
    state_str = "ВКЛЮЧЕНЫ 🔔" if user_sub["home"] else "ВЫКЛЮЧЕНЫ 🔕"
    await m.answer(f"Уведомления по Хате {state_str}", reply_markup=get_reply_kb(m.chat.id))

# Переключение Дани
@dp.message(F.text.startswith("🎮 Даня:"))
async def toggle_danya(m: Message):
    user_sub = subs.setdefault(m.chat.id, {"home": True, "danya": True})
    user_sub["danya"] = not user_sub["danya"]
    state_str = "ВКЛЮЧЕНЫ 🔔" if user_sub["danya"] else "ВЫКЛЮЧЕНЫ 🔕"
    await m.answer(f"Уведомления по Дане {state_str}", reply_markup=get_reply_kb(m.chat.id))

# Проверка статуса
@dp.message(F.text == "📊 Проверить статус")
async def check_status(m: Message):
    h = data["home"]
    d = data["danya"]
    h_ico = "🟢" if h["s"] == "Есть" else "🔴" if h["s"] == "Нет" else "⚪"
    d_ico = "🟢" if d["s"] == "Есть" else "🔴" if d["s"] == "Нет" else "⚪"
    
    text = (
        f"📊 **Текущее состояние:**\n\n"
        f"{h_ico} **Хата:** {h['s']} (с {h['t']})\n"
        f"{d_ico} **Даня:** {d['s']} (с {d['t']})"
    )
    await m.answer(text, parse_mode="Markdown", reply_markup=get_reply_kb(m.chat.id))

# Прием сигналов от MacroDroid
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
    web.run_app(app, port=10000)

