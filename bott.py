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

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("moviesbot_base").worksheet("main")

class Form(StatesGroup):
    waiting_for_series = State()
    waiting_for_custom_text = State()

def load_movies():
    try: return sheet.get_all_records()
    except: return []

def get_movie_list_text(page=1):
    movies = load_movies()
    if not movies: return "🎬 Список пуст."
    items_per_page = 30
    start = (page - 1) * items_per_page
    current_movies = movies[start:start + items_per_page]
    text = f"🎬 МОЙ СПИСОК (Стр. {page}):\n\n"
    for i, m in enumerate(current_movies, start + 1):
        # Формат: Название (Серия) — Статус Текст
        s = m.get('series', '')
        st = m.get('status', '⏳')
        txt = m.get('comment', '')
        text += f"{i}. {m.get('name', '???')} ({s}) — {st} {txt}\n"
    text += f"\n📊 {len(movies)}"
    return text

def get_main_keyboard(page=1):
    movies = load_movies()
    builder = InlineKeyboardBuilder()
    items_per_page = 30
    start = (page - 1) * items_per_page
    for i in range(start, min(start + items_per_page, len(movies))):
        builder.button(text=str(i+1), callback_data=f"select_{i}_{page}")
    nav = []
    if page > 1: nav.append(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{page-1}"))
    if start + items_per_page < len(movies): nav.append(types.InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page_{page+1}"))
    builder.row(*nav)
    builder.adjust(5)
    return builder.as_markup()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(get_movie_list_text(1), reply_markup=get_main_keyboard(1))

@dp.callback_query(F.data.startswith("page_"))
async def change_page(call: types.CallbackQuery):
    page = int(call.data.split("_")[1])
    await call.message.edit_text(get_movie_list_text(page), reply_markup=get_main_keyboard(page))

@dp.callback_query(F.data.startswith("select_"))
async def select_movie(call: types.CallbackQuery):
    idx, page = int(call.data.split("_")[1]), int(call.data.split("_")[2])
    movies = load_movies()
    builder = InlineKeyboardBuilder()
    for emo in ["✅", "💋", "⏳", "📛", "➖"]:
        builder.button(text=emo, callback_data=f"set_{idx}_{emo}_{page}")
    builder.button(text="➕ Текст", callback_data=f"txt_{idx}_{page}")
    builder.button(text="📝 Серия", callback_data=f"ser_{idx}_{page}")
    builder.button(text="🗑 Удалить", callback_data=f"del_{idx}_{page}")
    builder.button(text="🔙 Назад", callback_data=f"page_{page}")
    builder.adjust(5, 2, 2)
    await call.message.edit_text(f"Управление: {movies[idx]['name']}", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("ser_"))
async def ask_series(call: types.CallbackQuery, state: FSMContext):
    _, idx, page = call.data.split("_")
    await state.update_data(row=int(idx) + 2, page=page)
    await state.set_state(Form.waiting_for_series)
    await call.message.answer("Введите серию:")

@dp.message(Form.waiting_for_series)
async def update_series(message: types.Message, state: FSMContext):
    data = await state.get_data()
    sheet.update_cell(data['row'], 3, message.text) # Столбец C
    await state.clear()
    await message.answer(get_movie_list_text(int(data['page'])), reply_markup=get_main_keyboard(int(data['page'])))

@dp.callback_query(F.data.startswith("txt_"))
async def ask_text(call: types.CallbackQuery, state: FSMContext):
    _, idx, page = call.data.split("_")
    await state.update_data(row=int(idx) + 2, page=page)
    await state.set_state(Form.waiting_for_custom_text)
    await call.message.answer("Введите текст:")

@dp.message(Form.waiting_for_custom_text)
async def update_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    sheet.update_cell(data['row'], 4, message.text) # Столбец D
    await state.clear()
    await message.answer(get_movie_list_text(int(data['page'])), reply_markup=get_main_keyboard(int(data['page'])))

@dp.callback_query(F.data.startswith("set_"))
async def set_status(call: types.CallbackQuery):
    _, idx, emo, page = call.data.split("_")
    sheet.update_cell(int(idx) + 2, 2, emo) # Столбец B
    await call.message.edit_text(get_movie_list_text(int(page)), reply_markup=get_main_keyboard(int(page)))

@dp.callback_query(F.data.startswith("del_"))
async def delete_movie(call: types.CallbackQuery):
    _, idx, page = call.data.split("_")
    sheet.delete_rows(int(idx) + 2)
    await call.message.edit_text(get_movie_list_text(int(page)), reply_markup=get_main_keyboard(int(page)))

# ЭТА ФУНКЦИЯ БОЛЬШЕ НЕ СРАБОТАЕТ, ЕСЛИ МЫ ЖДЕМ СЕРИЮ ИЛИ ТЕКСТ
@dp.message(F.text)
async def add_movie(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None and not message.text.startswith('/'):
        sheet.append_row([message.text, "⏳", "", ""])
        await message.answer(get_movie_list_text(1), reply_markup=get_main_keyboard(1))

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
