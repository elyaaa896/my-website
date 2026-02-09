import asyncio
import pandas as pd
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

API_TOKEN = '8523485807:AAGku_LElg2d7imUPitL4T_icTXgcUJ5bkA'
# Ссылка на твой основной лист (main)
URL = 'https://docs.google.com/spreadsheets/d/1-NrRTjCIGOLIGpcy5Kixk6K6CbzHzycrm0kL9nAoh8A/export?format=csv&gid=0'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def load_data():
    try:
        df = pd.read_csv(URL)
        return df.fillna('').to_dict('records')
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        return []

def get_text(m, p=1):
    if not m: return "🎬 Список пуст или таблица недоступна."
    start, end = (p-1)*30, p*30
    curr = m[start:end]
    txt = f"🎬 **МОЙ СПИСОК (Стр. {p}):**\n\n"
    for i, x in enumerate(curr, start + 1):
        ser = f" ({x['series']})" if x.get('series') else ""
        txt += f"{i}. {x.get('name','')} {ser} — {x.get('status','⏳')}\n"
    watched = sum(1 for x in m if '✅' in str(x.get('status','')))
    txt += f"\n📊 {watched}/{len(m)}"
    return txt

def get_kb(m, p=1):
    builder = InlineKeyboardBuilder()
    start, end = (p-1)*30, min(p*30, len(m))
    for i in range(start, end):
        builder.button(text=str(i+1), callback_data="none")
    nav = []
    if p > 1: nav.append(types.InlineKeyboardButton(text="⬅️", callback_data=f"p_{p-1}"))
    if end < len(m): nav.append(types.InlineKeyboardButton(text="➡️", callback_data=f"p_{p+1}"))
    if nav: builder.row(*nav)
    builder.adjust(5)
    return builder.as_markup()

@dp.message(Command("start"))
async def s_cmd(msg: types.Message):
    data = load_data()
    await msg.answer(get_text(data, 1), reply_markup=get_kb(data, 1))

@dp.callback_query(F.data.startswith("p_"))
async def p_callback(call: types.CallbackQuery):
    p = int(call.data.split("_")[1])
    data = load_data()
    await call.message.edit_text(get_text(data, p), reply_markup=get_kb(data, p))

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
