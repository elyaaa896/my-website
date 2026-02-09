import asyncio
import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# [span_10](start_span)Ваш токен[span_10](end_span)
API_TOKEN = '8344514218:AAFlAbVAc1VdcqPZ9jlTL5DYSXcBAdZlyrI'

USERS_URL = 'https://docs.google.com/spreadsheets/d/1-NrRTjCIGOLIGpcy5Kixk6K6CbzHzycrm0kL9nAoh8A/export?format=csv&gid=0'

# [span_11](start_span)Убрали прокси-сессию[span_11](end_span)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class Form(StatesGroup):
    waiting_for_series = State()
    waiting_for_custom_status = State()

DATA_FOLDER = "user_data_storage"
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

def get_user_file(user_id):
    return os.path.join(DATA_FOLDER, f"list_{user_id}.json")

def load_movies(user_id):
    path = get_user_file(user_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_movies(user_id, data):
    path = get_user_file(user_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_movie_list_text(user_id, page=1):
    movies = load_movies(user_id)
    if not movies:
       return "🎬 Ваш личный список пуст. Просто напишите название фильма, чтобы добавить его."

    items_per_page = 30
    start = (page - 1) * items_per_page
    end = start + items_per_page
    current_movies = movies[start:end]

    text = f"🎬 **МОЙ СПИСОК (Стр. {page}):**\n\n"
    for i, m in enumerate(current_movies, start + 1):
        v = m.get('series', '')
        s_text = f" ({v} )" if v else ""
        text += f"{i}. {m['name']}{s_text} — {m.get('status', '⏳')}\n"

    total = len(movies)
    watched = sum(1 for m in movies if '✅' in str(m.get('status', '')))
    text += f"\n📊 {watched}/{total}"
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
    [span_15](start_span)if page > 1: nav.append(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{page-1}"))[span_15](end_span)
    if end < len(movies): nav.append(types.InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page_{page+1}"))
    if nav: builder.row(*nav)
    builder.adjust(5)
    return builder.as_markup()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    welcome_text = (
        [span_16](start_span)"👋 Привет! Это твой личный трекер фильмов и сериалов.\n\n"[span_16](end_span)
        "**Значения статусов:**\n"
        "✅ — просмотрено\n"
        "▶️ — пауза, отложил просмотр\n"
        "⏭️ — следующий фильм\n"
        "⏳ — ожидание новых серий\n"
        "➖ — не смотрел\n"
        "➕ — добавить дату выхода фильма\n\n"
        "Ниже твой личный список:"
    )
    [span_17](start_span)await message.answer(welcome_text, parse_mode="Markdown")[span_17](end_span)
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

@dp.callback_query(F.data.startswith("custom_"))
async def ask_custom(call: types.CallbackQuery, state: FSMContext):
    _, idx, page = call.data.split("_")
    await state.update_data(m_idx=int(idx), page=int(page))
    await state.set_state(Form.waiting_for_custom_status)
    await call.answer()

@dp.message(Form.waiting_for_custom_status)
async def process_custom(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    movies = load_movies(user_id)
    m_idx = data['m_idx']
    current_s = str(movies[m_idx].get('status', '⏳'))
    emoji_part = current_s[0] if current_s else "⏳"
    movies[m_idx]['status'] = f"{emoji_part} {message.text}"
    save_movies(user_id, movies)
    await state.clear()
    await message.answer(get_movie_list_text(user_id, data['page']),
                         reply_markup=get_main_keyboard(user_id, data['page']))

@dp.callback_query(F.data.startswith("del_"))
async def delete_movie(call: types.CallbackQuery):
    _, idx, page = call.data.split("_")
    user_id = call.from_user.id
    movies = load_movies(user_id)
    movies.pop(int(idx))
    save_movies(user_id, movies)
    await call.message.edit_text(get_movie_list_text(user_id, int(page)),
                                 reply_markup=get_main_keyboard(user_id, int(page)))

@dp.callback_query(F.data.startswith("ser_"))
async def ask_series(call: types.CallbackQuery, state: FSMContext):
    _, idx, page = call.data.split("_")
    await state.update_data(m_idx=int(idx), page=int(page))
    await state.set_state(Form.waiting_for_series)
    await call.answer()

@dp.message(Form.waiting_for_series)
async def process_series(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    movies = load_movies(user_id)
    movies[data['m_idx']]['series'] = message.text
    save_movies(user_id, movies)
    await state.clear()
    await message.answer(get_movie_list_text(user_id, data['page']),
                         reply_markup=get_main_keyboard(user_id, data['page']))

@dp.message(F.text)
async def add_movie(message: types.Message):
    user_id = message.from_user.id
    movies = load_movies(user_id)
    movies.append({"name": message.text, "status": "⏳", "series": ""})
    save_movies(user_id, movies)
    await message.answer(get_movie_list_text(user_id, 1), reply_markup=get_main_keyboard(user_id, 1))

async def main():
    print("🚀 Бот запущен! Статусы обновлены.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
