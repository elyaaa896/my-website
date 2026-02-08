import asyncio
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

API_TOKEN = '8523485807:AAGku_LElg2d7imUPitL4T_icTXgcUJ5bkA'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Настройка Google Таблиц
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("moviesbot_base").worksheet("main")

class Form(StatesGroup):
    waiting_for_series = State()
    waiting_for_custom_status = State()

def load_movies():
    try:
        return sheet.get_all_records()
    except:
        return []

def get_movie_list_text(page=1):
    movies = load_movies()
    if not movies: return "🎬 Список пуст."
    items_per_page = 30
    start = (page - 1) * items_per_page
    current_movies = movies[start:start + items_per_page]
    text = f"🎬 МОЙ СПИСОК (Стр. {page}):\n\n"
    for i, movie in enumerate(current_movies, start=start + 1):
        status = movie.get('status', '⏳')
        series = f" | {movie['series']}" if movie.get('series') else ""
        text += f"{i}. {movie['name']} — {status}{series}\n"
    return text

def get_main_keyboard(page=1):
    movies = load_movies()
    builder = InlineKeyboardBuilder()
    items_per_page = 30
    start = (page - 1) * items_per_page
    current_movies = movies[start:start + items_per_page]
    
    for i, _ in enumerate(current_movies, start=start):
        builder.button(text=str(i + 1), callback_data=f"edit_{i}_{page}")
    
    builder.adjust(5)
    nav_buttons = []
    if page > 1:
        nav_buttons.append(types.InlineKeyboardButton(text="⬅️", callback_data=f"page_{page-1}"))
    if start + items_per_page < len(movies):
        nav_buttons.append(types.InlineKeyboardButton(text="➡️", callback_data=f"page_{page+1}"))
    if nav_buttons:
        builder.row(*nav_buttons)
    return builder.as_markup()

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(get_movie_list_text(1), reply_markup=get_main_keyboard(1))

@dp.callback_query(F.data.startswith("page_"))
async def change_page(call: types.CallbackQuery):
    page = int(call.data.split("_")[1])
    await call.message.edit_text(get_movie_list_text(page), reply_markup=get_main_keyboard(page))

@dp.callback_query(F.data.startswith("edit_"))
async def select_movie(call: types.CallbackQuery):
    movies = load_movies()
    idx, page = int(call.data.split("_")[1]), int(call.data.split("_")[2])
    builder = InlineKeyboardBuilder()
    # Твои оригинальные смайлики
    for emo in ["✅", "💋", "⏳", "📛", "➖"]:
        builder.button(text=emo, callback_data=f"set_{idx}_{emo}_{page}")
    
    # Кнопки как были в bott(1).py
    builder.button(text="➕ Текст", callback_data=f"custom_{idx}_{page}")
    builder.button(text="📝 Серия", callback_data=f"ser_{idx}_{page}")
    builder.button(text="🗑 Удалить", callback_data=f"del_{idx}_{page}")
    builder.button(text="🔙 Назад", callback_data=f"page_{page}")
    
    builder.adjust(5, 2, 2)
    await call.message.edit_text(f"Управление: {movies[idx]['name']}", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("set_"))
async def set_status(call: types.CallbackQuery):
    _, idx, emo, page = call.data.split("_")
    row_idx = int(idx) + 2
    sheet.update_cell(row_idx, 2, emo)
    await call.message.edit_text(get_movie_list_text(int(page)), reply_markup=get_main_keyboard(int(page)))

# --- ЛОГИКА С ПОДСКАЗКАМИ ---

@dp.callback_query(F.data.startswith("custom_"))
async def ask_custom(call: types.CallbackQuery, state: FSMContext):
    _, idx, page = call.data.split("_")
    await state.update_data(m_idx=int(idx), page=int(page))
    await state.set_state(Form.waiting_for_custom_status)
    await call.message.answer("Введите текст для статуса:") # ТВОЯ ПОДСКАЗКА
    await call.answer()

@dp.message(Form.waiting_for_custom_status)
async def process_custom(message: types.Message, state: FSMContext):
    data = await state.get_data()
    row_idx = data['m_idx'] + 2
    current_s = sheet.cell(row_idx, 2).value
    emoji_part = current_s[0] if current_s else "⏳"
    sheet.update_cell(row_idx, 2, f"{emoji_part} {message.text}")
    await state.clear()
    await message.answer("Статус обновлен!", reply_markup=get_main_keyboard(data['page']))

@dp.callback_query(F.data.startswith("ser_"))
async def ask_series(call: types.CallbackQuery, state: FSMContext):
    _, idx, page = call.data.split("_")
    await state.update_data(m_idx=int(idx), page=int(page))
    await state.set_state(Form.waiting_for_series)
    await call.message.answer("Какая серия?") # ТВОЯ ПОДСКАЗКА
    await call.answer()

@dp.message(Form.waiting_for_series)
async def process_series(message: types.Message, state: FSMContext):
    data = await state.get_data()
    sheet.update_cell(data['m_idx'] + 2, 3, message.text)
    await state.clear()
    await message.answer("Серия сохранена!", reply_markup=get_main_keyboard(data['page']))

@dp.callback_query(F.data.startswith("del_"))
async def delete_movie(call: types.CallbackQuery):
    _, idx, page = call.data.split("_")
    sheet.delete_rows(int(idx) + 2)
    await call.message.edit_text(get_movie_list_text(int(page)), reply_markup=get_main_keyboard(int(page)))

@dp.message()
async def add_movie(message: types.Message, state: FSMContext):
    # Добавление фильма текстом
    cur_state = await state.get_state()
    if cur_state is None and not message.text.startswith('/'):
        sheet.append_row([message.text, "⏳", ""])
        await message.answer(f"✅ Добавлено: {message.text}", reply_markup=get_main_keyboard(1))

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
