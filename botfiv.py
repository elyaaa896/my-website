import asyncio
import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

API_TOKEN = '8344514218:AAFlAbVAc1VdcqPZ9jlTL5DYSXcBAdZlyrI'
bot = Bot(token=API_TOKEN) # Прокси удалены
dp = Dispatcher()

class Form(StatesGroup):
    waiting_for_series = State()
    waiting_for_custom_status = State()

DATA_FOLDER = "user_data_storage"
if not os.path.exists(DATA_FOLDER): os.makedirs(DATA_FOLDER)

def get_user_file(user_id): return os.path.join(DATA_FOLDER, f"list_{user_id}.json")

def load_movies(user_id):
    path = get_user_file(user_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    return []

def save_movies(user_id, data):
    path = get_user_file(user_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_movie_list_text(user_id, page=1):
    movies = load_movies(user_id)
    if not movies: return "🎬 Ваш личный список пуст."
    items_per_page = 30
    start = (page - 1) * items_per_page
    end = start + items_per_page
    current_movies = movies[start:end]
    text = f"🎬 **МОЙ СПИСОК (Стр. {page}):**\n\n"
    for i, m in enumerate(current_movies, start + 1):
        v = m.get('series', '')
        s_text = f" ({v} сер.)" if v else ""
        text += f"{i}. {m['name']}{s_text} — {m.get('status', '⏳')}\n"
    text += f"\n📊 {sum(1 for m in movies if '✅' in str(m.get('status', '')))}/{len(movies)}"
    return text

def get_main_keyboard(user_id, page=1):
    movies = load_movies(user_id)
    builder = InlineKeyboardBuilder()
    items_per_page = 30
    start = (page - 1) * items_per_page
    end = start + items_per_page
    for i in range(start, min(end, len(movies))):
        builder.button(text=str(i+1), callback_data=f"select_{i}_{page}")
    nav = []
    if page > 1: nav.append(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{page-1}"))
    if end < len(movies): nav.append(types.InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page_{page+1}"))
    if nav: builder.row(*nav)
    builder.adjust(5)
    return builder.as_markup()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    welcome_text = "👋 Привет! Это твой личный трекер.\n\nСтатусы:\n✅ — просмотрено\n▶️ — пауза\n⏳ — ожидание\n➖ — не смотрел"
    await message.answer(welcome_text)
    await message.answer(get_movie_list_text(message.from_user.id, 1),
                         reply_markup=get_main_keyboard(message.from_user.id, 1))

@dp.callback_query(F.data.startswith("page_"))
async def change_page(call: types.CallbackQuery):
    page = int(call.data.split("_")[1])
    await call.message.edit_text(get_movie_list_text(call.from_user.id, page),
                                 reply_markup=get_main_keyboard(call.from_user.id, page))

@dp.callback_query(F.data.startswith("select_"))
async def select_movie(call: types.CallbackQuery):
    movies = load_movies(call.from_user.id)
    data = call.data.split("_")
    idx, page = int(data[1]), int(data[2])
    builder = InlineKeyboardBuilder()
    for emo in ["✅", "▶️", "⏭️", "⏳", "➖"]:
        builder.button(text=emo, callback_data=f"set_{idx}_{emo}_{page}")
    builder.button(text="➕", callback_data=f"custom_{idx}_{page}")
    builder.button(text="📝 Серия", callback_data=f"ser_{idx}_{page}")
    builder.button(text="🗑 Удалить", callback_data=f"del_{idx}_{page}")
    builder.button(text="🔙 Назад", callback_data=f"page_{page}")
    builder.adjust(5, 2, 2)
    await call.message.edit_text(f"Управление: {movies[idx]['name']}", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("set_"))
async def set_status(call: types.CallbackQuery):
    _, idx, emo, page = call.data.split("_")
    user_id = call.from_user.id
    movies = load_movies(user_id)
    movies[int(idx)]['status'] = emo
    save_movies(user_id, movies)
    await call.message.edit_text(get_movie_list_text(user_id, int(page)),
                                 reply_markup=get_main_keyboard(user_id, int(page)))

@dp.message(F.text)
async def add_movie(message: types.Message):
    user_id = message.from_user.id
    movies = load_movies(user_id)
    movies.append({"name": message.text, "status": "⏳", "series": ""})
    save_movies(user_id, movies)
    await message.answer(get_movie_list_text(user_id, 1),
                         reply_markup=get_main_keyboard(user_id, 1))
