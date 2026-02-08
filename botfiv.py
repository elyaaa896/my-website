import asyncio
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

API_TOKEN = '8344514218:AAFlAbVAc1VdcqPZ9jlTL5DYSXcBAdZlyrI'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Настройка Google Таблиц
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet_u = client.open("moviesbot_base").worksheet("users")

class Form(StatesGroup):
    waiting_for_series = State()
    waiting_for_custom_status = State()

def load_user_movies(user_id):
    try:
        all_r = sheet_u.get_all_records()
        # Возвращаем (номер_строки_в_таблице, данные)
        return [(i + 2, r) for i, r in enumerate(all_r) if str(r.get('user_id')) == str(user_id)]
    except:
        return []

def get_movie_list_text(user_id, page=1):
    user_movies = load_user_movies(user_id)
    if not user_movies: return "🎬 Ваш список пуст."
    
    start = (page-1)*10
    end = start + 10
    text = f"🍿 Твой список (Стр. {page}):\n\n"
    for _, m in user_movies[start:end]:
        series = f" | {m.get('series')}" if m.get('series') else ""
        text += f"• {m['name']} — {m['status']}{series}\n"
    return text

def get_main_keyboard(user_id, page=1):
    user_movies = load_user_movies(user_id)
    builder = InlineKeyboardBuilder()
    start = (page-1)*10
    end = start + 10
    
    for row_idx, m in user_movies[start:end]:
        builder.button(text=f"⚙️ {m['name']}", callback_data=f"uedit_{row_idx}_{page}")
    
    builder.adjust(1)
    nav_buttons = []
    if page > 1: nav_buttons.append(types.InlineKeyboardButton(text="⬅️", callback_data=f"upage_{page-1}"))
    if end < len(user_movies): nav_buttons.append(types.InlineKeyboardButton(text="➡️", callback_data=f"upage_{page+1}"))
    if nav_buttons: builder.row(*nav_buttons)
    
    builder.row(types.InlineKeyboardButton(text="➕ Добавить фильм", callback_data=f"uadd_{page}"))
    return builder.as_markup()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(get_movie_list_text(message.from_user.id), reply_markup=get_main_keyboard(message.from_user.id))

@dp.callback_query(F.data.startswith("upage_"))
async def change_page(call: types.CallbackQuery):
    page = int(call.data.split("_")[1])
    await call.message.edit_text(get_movie_list_text(call.from_user.id, page), reply_markup=get_main_keyboard(call.from_user.id, page))

@dp.callback_query(F.data.startswith("uedit_"))
async def edit_movie(call: types.CallbackQuery):
    _, row_idx, page = call.data.split("_")
    all_r = sheet_u.get_all_records()
    # Индекс в all_records на 2 меньше, чем номер строки
    movie_data = all_r[int(row_idx)-2]
    
    builder = InlineKeyboardBuilder()
    # Твои смайлики + новый ⏭️
    for emo in ["✅", "▶️", "⏳", "⏭️", "➖"]:
        builder.button(text=emo, callback_data=f"uset_{row_idx}_{emo}_{page}")
    
    # Кнопки как в bott.py
    builder.button(text="📝 +Текст", callback_data=f"ucust_{row_idx}_{page}")
    builder.button(text="🔢 Серия", callback_data=f"useries_{row_idx}_{page}")
    builder.button(text="🗑 Удалить", callback_data=f"udel_{row_idx}_{page}")
    builder.button(text="🔙 Назад", callback_data=f"upage_{page}")
    
    builder.adjust(5, 2, 2)
    await call.message.edit_text(f"Управление: {movie_data['name']}", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("uset_"))
async def set_status(call: types.CallbackQuery):
    _, row_idx, emo, page = call.data.split("_")
    sheet_u.update_cell(int(row_idx), 3, emo)
    await call.message.edit_text(get_movie_list_text(call.from_user.id, int(page)), 
                                 reply_markup=get_main_keyboard(call.from_user.id, int(page)))

# Логика для +Текст
@dp.callback_query(F.data.startswith("ucust_"))
async def ask_custom_status(call: types.CallbackQuery, state: FSMContext):
    _, row_idx, page = call.data.split("_")
    await state.update_data(row_idx=row_idx, page=page)
    await state.set_state(Form.waiting_for_custom_status)
    await call.message.answer("Введите свой статус (например: Жду 2 сезон):")
    await call.answer()

@dp.message(Form.waiting_for_custom_status)
async def process_custom_status(message: types.Message, state: FSMContext):
    data = await state.get_data()
    row_idx = int(data['row_idx'])
    # Берем первый символ (смайлик) текущего статуса и добавляем текст
    current_status = sheet_u.cell(row_idx, 3).value
    emoji = current_status[0] if current_status else "⏳"
    new_status = f"{emoji} {message.text}"
    sheet_u.update_cell(row_idx, 3, new_status)
    await state.clear()
    await message.answer("Статус обновлен!", reply_markup=get_main_keyboard(message.from_user.id, int(data['page'])))

# Логика для Серии
@dp.callback_query(F.data.startswith("useries_"))
async def ask_series(call: types.CallbackQuery, state: FSMContext):
    _, row_idx, page = call.data.split("_")
    await state.update_data(row_idx=row_idx, page=page)
    await state.set_state(Form.waiting_for_series)
    await call.message.answer("На какой серии остановились?")
    await call.answer()

@dp.message(Form.waiting_for_series)
async def process_series(message: types.Message, state: FSMContext):
    data = await state.get_data()
    sheet_u.update_cell(int(data['row_idx']), 4, message.text)
    await state.clear()
    await message.answer("Серия сохранена!", reply_markup=get_main_keyboard(message.from_user.id, int(data['page'])))

@dp.callback_query(F.data.startswith("udel_"))
async def delete_movie(call: types.CallbackQuery):
    _, row_idx, page = call.data.split("_")
    sheet_u.delete_rows(int(row_idx))
    await call.message.edit_text(get_movie_list_text(call.from_user.id, int(page)), 
                                 reply_markup=get_main_keyboard(call.from_user.id, int(page)))

# Добавление нового фильма
@dp.callback_query(F.data.startswith("uadd_"))
async def add_movie_start(call: types.CallbackQuery):
    await call.message.answer("Напишите название фильма:")
    await call.answer()

@dp.message()
async def save_new_movie(message: types.Message):
    # Если мы не ждем серию или статус, значит это название нового фильма
    if not await dp.storage.get_state(bot, message.from_user.id):
        sheet_u.append_row([str(message.from_user.id), message.text, "⏳", ""])
        await message.answer(f"✅ Добавлено: {message.text}", reply_markup=get_main_keyboard(message.from_user.id))

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
