import asyncio
import gspread
import json
import os
from oauth2client.service_account import ServiceAccountCredentials
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

API_TOKEN = '8523485807:AAGku_LElg2d7imUPitL4T_icTXgcUJ5bkA'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- СУПЕР-НАДЕЖНОЕ ПОДКЛЮЧЕНИЕ ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def get_creds():
    # Сначала пытаемся взять из переменных окружения (для Render)
    creds_json = os.environ.get("G_CREDS")
    if creds_json:
        info = json.loads(creds_json)
        return ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
    # Если нет в переменных, берем из файла
    return ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)

creds = get_creds()
client = gspread.authorize(creds)
sheet = client.open("moviesbot_base").worksheet("main")

class Form(StatesGroup):
    waiting_for_series = State()
    waiting_for_custom_status = State()

def load_movies():
    try: return sheet.get_all_records()
    except: return []

def get_movie_list_text(page=1):
    movies = load_movies()
    if not movies: return "🎬 Список пуст."
    items_per_page = 30
    start = (page - 1) * items_per_page
    current = movies[start:start+items_per_page]
    text = f"🎬 **МОЙ СПИСОК (Стр. {page}):**\n\n"
    for i, m in enumerate(current, start + 1):
        v = m.get('series', '')
        text += f"{i}. {m['name']}{f' ({v})' if v else ''} — {m.get('status', '⏳')}\n"
    text += f"\n📊 {sum(1 for m in movies if '✅' in str(m.get('status', '')))}/{len(movies)}"
    return text

def get_main_keyboard(page=1):
    movies = load_movies()
    builder = InlineKeyboardBuilder()
    start = (page - 1) * 30
    for i in range(start, min(start + 30, len(movies))):
        builder.button(text=str(i+1), callback_data=f"select_{i}_{page}")
    nav = []
    if page > 1: nav.append(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{page-1}"))
    if start + 30 < len(movies): nav.append(types.InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page_{page+1}"))
    if nav: builder.row(*nav)
    builder.adjust(5)
    return builder.as_markup()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(get_movie_list_text(1), reply_markup=get_main_keyboard(1))

@dp.callback_query(F.data.startswith("select_"))
async def select_movie(call: types.CallbackQuery):
    idx, page = int(call.data.split("_")[1]), int(call.data.split("_")[2])
    all_m = load_movies()
    builder = InlineKeyboardBuilder()
    # ТВОИ КНОПКИ
    for emo in ["✅", "💋", "⏳", "📛", "➖"]:
        builder.button(text=emo, callback_data=f"set_{idx}_{emo}_{page}")
    builder.button(text="➕ Текст", callback_data=f"custom_{idx}_{page}")
    builder.button(text="📝 Серия", callback_data=f"ser_{idx}_{page}")
    builder.button(text="🗑 Удалить", callback_data=f"del_{idx}_{page}")
    builder.button(text="🔙 Назад", callback_data=f"page_{page}")
    builder.adjust(5, 2, 2)
    await call.message.edit_text(f"Управление: {all_m[idx]['name']}", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("set_"))
async def set_status(call: types.CallbackQuery):
    _, idx, emo, page = call.data.split("_")
    sheet.update_cell(int(idx) + 2, 2, emo)
    await call.message.edit_text(get_movie_list_text(int(page)), reply_markup=get_main_keyboard(int(page)))

@dp.callback_query(F.data.startswith("del_"))
async def delete_movie(call: types.CallbackQuery):
    _, idx, page = call.data.split("_")
    sheet.delete_rows(int(idx) + 2)
    await call.message.edit_text(get_movie_list_text(int(page)), reply_markup=get_main_keyboard(int(page)))

@dp.message(F.text)
async def add_movie(message: types.Message):
    if not message.text.startswith('/'):
        sheet.append_row([message.text, "⏳", ""])
        await message.answer(get_movie_list_text(1), reply_markup=get_main_keyboard(1))

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
