import asyncio
import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# [span_0](start_span)Ваш токен остается прежним[span_0](end_span)
API_TOKEN = '8523485807:AAGku_LElg2d7imUPitL4T_icTXgcUJ5bkA'

URL = 'https://docs.google.com/spreadsheets/d/1-NrRTjCIGOLIGpcy5Kixk6K6CbzHzycrm0kL9nAoh8A/export?format=csv&gid=0'

# [span_1](start_span)Настройки прокси удалены, так как они не нужны на Render[span_1](end_span)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class Form(StatesGroup):
    waiting_for_series = State()
    waiting_for_custom_status = State()

DB_FILE = "movies_db.json"

def load_movies():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_movies():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        [span_2](start_span)json.dump(movies, f, ensure_ascii=False, indent=4)[span_2](end_span)

movies = load_movies()

def get_movie_list_text(page=1):
    if not movies:
        return "🎬 Список пуст."
    [span_3](start_span)items_per_page = 30[span_3](end_span)
    start = (page - 1) * items_per_page
    end = start + items_per_page
    current_movies = movies[start:end]
    text = f"🎬 **МОЙ СПИСОК (Стр. {page}):**\n\n"
    for i, m in enumerate(current_movies, start + 1):
        v = m.get('series', '')
        s_text = f" ({v} )" if v else ""
        text += f"{i}. {m['name']}{s_text} — {m.get('status', '⏳')}\n"
    [span_4](start_span)text += f"\n📊 {sum(1 for m in movies if '✅' in str(m.get('status', '')))}/{len(movies)}"[span_4](end_span)
    return text

def get_main_keyboard(page=1):
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
    [span_5](start_span)await message.answer(get_movie_list_text(1), reply_markup=get_main_keyboard(1))[span_5](end_span)

@dp.callback_query(F.data.startswith("page_"))
async def change_page(call: types.CallbackQuery):
    page = int(call.data.split("_")[1])
    await call.message.edit_text(get_movie_list_text(page), reply_markup=get_main_keyboard(page))

@dp.callback_query(F.data.startswith("select_"))
async def select_movie(call: types.CallbackQuery):
    data = call.data.split("_")
    idx, page = int(data[1]), int(data[2])
    builder = InlineKeyboardBuilder()
    for emo in ["✅", "💋", "⏳", "📛", "➖"]:
        builder.button(text=emo, callback_data=f"set_{idx}_{emo}_{page}")
    builder.button(text="➕ Текст", callback_data=f"custom_{idx}_{page}")
    builder.button(text="📝 Серия", callback_data=f"ser_{idx}_{page}")
    builder.button(text="🗑 Удалить", callback_data=f"del_{idx}_{page}")
    builder.button(text="🔙 Назад", callback_data=f"page_{page}")
    builder.adjust(5, 2, 2)
    [span_6](start_span)await call.message.edit_text(f"Управление: {movies[int(idx)]['name']}", reply_markup=builder.as_markup())[span_6](end_span)

@dp.callback_query(F.data.startswith("set_"))
async def set_status(call: types.CallbackQuery):
    _, idx, emo, page = call.data.split("_")
    movies[int(idx)]['status'] = emo
    save_movies()
    await call.message.edit_text(get_movie_list_text(int(page)), reply_markup=get_main_keyboard(int(page)))

@dp.callback_query(F.data.startswith("custom_"))
async def ask_custom(call: types.CallbackQuery, state: FSMContext):
    _, idx, page = call.data.split("_")
    await state.update_data(m_idx=int(idx), page=int(page))
    await state.set_state(Form.waiting_for_custom_status)
    await call.answer()

@dp.message(Form.waiting_for_custom_status)
async def process_custom(message: types.Message, state: FSMContext):
    data = await state.get_data()
    m_idx = data['m_idx']
    current_s = str(movies[m_idx].get('status', '⏳'))
    emoji_part = current_s[0] if current_s else "⏳"
    [span_7](start_span)movies[m_idx]['status'] = f"{emoji_part} {message.text}"[span_7](end_span)
    save_movies()
    await state.clear()
    await message.answer(get_movie_list_text(data['page']), reply_markup=get_main_keyboard(data['page']))

@dp.callback_query(F.data.startswith("del_"))
async def delete_movie(call: types.CallbackQuery):
    _, idx, page = call.data.split("_")
    movies.pop(int(idx))
    save_movies()
    await call.message.edit_text(get_movie_list_text(int(page)), reply_markup=get_main_keyboard(int(page)))

@dp.callback_query(F.data.startswith("ser_"))
async def ask_series(call: types.CallbackQuery, state: FSMContext):
    _, idx, page = call.data.split("_")
    await state.update_data(m_idx=int(idx), page=int(page))
    await state.set_state(Form.waiting_for_series)
    await call.answer()

@dp.message(Form.waiting_for_series)
async def process_series(message: types.Message, state: FSMContext):
    data = await state.get_data()
    movies[data['m_idx']]['series'] = message.text
    save_movies()
    await state.clear()
    [span_8](start_span)await message.answer(get_movie_list_text(data['page']), reply_markup=get_main_keyboard(data['page']))[span_8](end_span)

@dp.message(F.text)
async def add_movie(message: types.Message):
    movies.append({"name": message.text, "status": "⏳", "series": ""})
    save_movies()
    await message.answer(get_movie_list_text(1), reply_markup=get_main_keyboard(1))

async def main():
    [span_9](start_span)print("🚀 Бот запущен! (Статусы + Текст работают)")[span_9](end_span)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
