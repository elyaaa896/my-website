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
        return [(i, r) for i, r in enumerate(all_r) if str(r.get('user_id')) == str(user_id)]
    except:
        return []

def get_movie_list_text(user_id, page=1):
    user_movies = load_user_movies(user_id)
    if not user_movies: return "🎬 Ваш список пуст."
    start = (page-1)*10
    end = start + 10
    text = f"🍿 Твой список (Стр. {page}):\n\n"
    for i, (idx, m) in enumerate(user_movies[start:end], start=1):
        ser = f" | {m.get('series')}" if m.get('series') else ""
        text += f"{i}. {m['name']} — {m['status']}{ser}\n"
    return text

def get_main_keyboard(user_id, page=1):
    user_movies = load_user_movies(user_id)
    builder = InlineKeyboardBuilder()
    start = (page-1)*10
    end = start + 10
    
    # ВОЗВРАЩАЕМ ЦИФРЫ (1, 2, 3...)
    for i, (idx, m) in enumerate(user_movies[start:end], start=1):
        builder.button(text=str(i), callback_data=f"uedit_{idx}_{page}")
    
    builder.adjust(5)
    nav = []
    if page > 1: nav.append(types.InlineKeyboardButton(text="⬅️", callback_data=f"upage_{page-1}"))
    if end < len(user_movies): nav.append(types.InlineKeyboardButton(text="➡️", callback_data=f"upage_{page+1}"))
    if nav: builder.row(*nav)
    
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
    _, idx, page = call.data.split("_")
    all_r = sheet_u.get_all_records()
    movie = all_r[int(idx)]
    
    builder = InlineKeyboardBuilder()
    # 5 смайликов в ряд (добавлен ⏭️)
    for emo in ["✅", "▶️", "⏳", "⏭️", "➖"]:
        builder.button(text=emo, callback_data=f"uset_{idx}_{emo}_{page}")
    
    # ТРИ НОВЫЕ КНОПКИ
    builder.button(text="📝 +Текст", callback_data=f"ucust_{idx}_{page}")
    builder.button(text="🔢 Серия", callback_data=f"useries_{idx}_{page}")
    builder.button(text="🗑 Удалить", callback_data=f"udel_{idx}_{page}")
    builder.button(text="🔙 Назад", callback_data=f"upage_{page}")
    
    builder.adjust(5, 2, 2)
    await call.message.edit_text(f"Фильм: {movie['name']}", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("uset_"))
async def set_status(call: types.CallbackQuery):
    _, idx, emo, page = call.data.split("_")
    sheet_u.update_cell(int(idx) + 2, 3, emo)
    await call.message.edit_text(get_movie_list_text(call.from_user.id, int(page)), 
                                 reply_markup=get_main_keyboard(call.from_user.id, int(page)))

@dp.callback_query(F.data.startswith("ucust_"))
async def ask_custom(call: types.CallbackQuery, state: FSMContext):
    _, idx, page = call.data.split("_")
    await state.update_data(idx=idx, page=page)
    await state.set_state(Form.waiting_for_custom_status)
    await call.message.answer("Введите текст статуса:")

@dp.message(Form.waiting_for_custom_status)
async def proc_custom(message: types.Message, state: FSMContext):
    data = await state.get_data()
    idx = int(data['idx'])
    # Сохраняем смайлик, меняем текст
    curr = sheet_u.cell(idx + 2, 3).value
    emo = curr[0] if curr else "⏳"
    sheet_u.update_cell(idx + 2, 3, f"{emo} {message.text}")
    await state.clear()
    await message.answer("Обновлено!", reply_markup=get_main_keyboard(message.from_user.id, int(data['page'])))

@dp.callback_query(F.data.startswith("useries_"))
async def ask_ser(call: types.CallbackQuery, state: FSMContext):
    _, idx, page = call.data.split("_")
    await state.update_data(idx=idx, page=page)
    await state.set_state(Form.waiting_for_series)
    await call.message.answer("Какая серия?")

@dp.message(Form.waiting_for_series)
async def proc_ser(message: types.Message, state: FSMContext):
    data = await state.get_data()
    sheet_u.update_cell(int(data['idx']) + 2, 4, message.text)
    await state.clear()
    await message.answer("Серия записана!", reply_markup=get_main_keyboard(message.from_user.id, int(data['page'])))

@dp.callback_query(F.data.startswith("udel_"))
async def delete_movie(call: types.CallbackQuery):
    _, idx, page = call.data.split("_")
    sheet_u.delete_rows(int(idx) + 2)
    await call.message.edit_text(get_movie_list_text(call.from_user.id, int(page)), 
                                 reply_markup=get_main_keyboard(call.from_user.id, int(page)))

@dp.callback_query(F.data.startswith("uadd_"))
async def add_start(call: types.CallbackQuery):
    await call.message.answer("Напишите название:")

@dp.message()
async def save_new(message: types.Message):
    if not await dp.storage.get_state(bot, message.from_user.id):
        sheet_u.append_row([str(message.from_user.id), message.text, "⏳", ""])
        await message.answer(f"✅ Добавлено: {message.text}", reply_markup=get_main_keyboard(message.from_user.id))

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
