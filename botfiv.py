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

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet_u = client.open("moviesbot_base").worksheet("users")

class Form(StatesGroup):
    waiting_for_series = State()
    waiting_for_custom_text = State()

def load_user_movies(user_id):
    try:
        all_r = sheet_u.get_all_records()
        return [(i, r) for i, r in enumerate(all_r) if str(r.get('user_id')) == str(user_id)]
    except: return []

def get_movie_list_text(user_id, page=1):
    user_movies = load_user_movies(user_id)
    if not user_movies: return "🎬 Список пуст."
    items_per_page = 30
    start = (page - 1) * items_per_page
    current = user_movies[start:start+items_per_page]
    text = f"🎬 **ВАШ СПИСОК (Стр. {page}):**\n\n"
    for i, (orig_idx, m) in enumerate(current, 1):
        v, st, comm = m.get('series', ''), m.get('status', '⏳'), m.get('comment', '')
        text += f"{i}. {m['name']} ({v}) — {st} {comm}\n"
    return text

def get_main_keyboard(user_id, page=1):
    user_movies = load_user_movies(user_id)
    builder = InlineKeyboardBuilder()
    items_per_page = 30
    start = (page - 1) * items_per_page
    current = user_movies[start:start+items_per_page]
    for i, (orig_idx, m) in enumerate(current, 1):
        builder.button(text=str(i), callback_data=f"uselect_{orig_idx}_{page}")
    nav = []
    if page > 1: nav.append(types.InlineKeyboardButton(text="⬅️", callback_data=f"upage_{page-1}"))
    if start + items_per_page < len(user_movies): nav.append(types.InlineKeyboardButton(text="➡️", callback_data=f"upage_{page+1}"))
    builder.row(*nav)
    builder.adjust(5)
    return builder.as_markup()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(get_movie_list_text(message.from_user.id, 1), reply_markup=get_main_keyboard(message.from_user.id, 1))

@dp.callback_query(F.data.startswith("upage_"))
async def change_page(call: types.CallbackQuery):
    page = int(call.data.split("_")[1])
    await call.message.edit_text(get_movie_list_text(call.from_user.id, page), reply_markup=get_main_keyboard(call.from_user.id, page))

@dp.callback_query(F.data.startswith("uselect_"))
async def select_movie(call: types.CallbackQuery):
    idx, page = int(call.data.split("_")[1]), int(call.data.split("_")[2])
    all_r = sheet_u.get_all_records()
    builder = InlineKeyboardBuilder()
    # Добавляем кнопку ⏮️ в список статусов
    for emo in ["✅", "▶️", "⏳", "➖", "⏮️"]:  # Добавил ⏮️
        builder.button(text=emo, callback_data=f"uset_{idx}_{emo}_{page}")
    builder.button(text="➕ Текст", callback_data=f"utxt_{idx}_{page}")
    builder.button(text="📝 Серия", callback_data=f"user_{idx}_{page}")
    builder.button(text="🗑 Удалить", callback_data=f"udel_{idx}_{page}")
    builder.button(text="🔙 Назад", callback_data=f"upage_{page}")
    builder.adjust(5, 2, 2)  # Изменил на 5 в первой строке
    await call.message.edit_text(f"Фильм: {all_r[idx]['name']}", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("user_"))
async def ask_ser(call: types.CallbackQuery, state: FSMContext):
    _, idx, page = call.data.split("_")
    await state.update_data(row=int(idx) + 2, page=page)
    await state.set_state(Form.waiting_for_series)
    await call.message.answer("Введите серию (любой формат, например: 2/2, Сезон 2 серия 2, 2 сезон 2 серия и т.д.):")

@dp.message(Form.waiting_for_series)
async def upd_ser(message: types.Message, state: FSMContext):
    data = await state.get_data()
    sheet_u.update_cell(data['row'], 4, message.text) # D - серия
    await state.clear()
    await message.answer(get_movie_list_text(message.from_user.id, int(data['page'])), reply_markup=get_main_keyboard(message.from_user.id, int(data['page'])))

@dp.callback_query(F.data.startswith("utxt_"))
async def ask_txt(call: types.CallbackQuery, state: FSMContext):
    _, idx, page = call.data.split("_")
    await state.update_data(row=int(idx) + 2, page=page)
    await state.set_state(Form.waiting_for_custom_text)
    await call.message.answer("Введите текст (любой текст, например: жду новых серий, выходит 25.12.2024 и т.д.):")

@dp.message(Form.waiting_for_custom_text)
async def upd_txt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    sheet_u.update_cell(data['row'], 5, message.text) # E - комментарий
    await state.clear()
    await message.answer(get_movie_list_text(message.from_user.id, int(data['page'])), reply_markup=get_main_keyboard(message.from_user.id, int(data['page'])))

@dp.callback_query(F.data.startswith("uset_"))
async def set_st(call: types.CallbackQuery):
    _, idx, emo, page = call.data.split("_")
    sheet_u.update_cell(int(idx) + 2, 3, emo) # C - статус
    await call.message.edit_text(get_movie_list_text(call.from_user.id, int(page)), reply_markup=get_main_keyboard(call.from_user.id, int(page)))

@dp.callback_query(F.data.startswith("udel_"))
async def del_mov(call: types.CallbackQuery):
    _, idx, page = call.data.split("_")
    sheet_u.delete_rows(int(idx) + 2)
    await call.message.edit_text(get_movie_list_text(call.from_user.id, int(page)), reply_markup=get_main_keyboard(call.from_user.id, int(page)))

# ФИКС: Добавляем фильтр для добавления новых фильмов
@dp.message(F.text & ~F.text.startswith('/'))
async def add_mov(message: types.Message, state: FSMContext):
    # Проверяем, не находимся ли мы в состоянии ожидания ввода
    current_state = await state.get_state()
    
    # Если есть активное состояние (ожидание серии или текста), НЕ добавляем новый фильм
    if current_state in [Form.waiting_for_series, Form.waiting_for_custom_text]:
        return
    
    # Если нет активного состояния и это не команда - добавляем новый фильм
    sheet_u.append_row([str(message.from_user.id), message.text, "⏳", "", ""])
    await message.answer(get_movie_list_text(message.from_user.id, 1), reply_markup=get_main_keyboard(message.from_user.id, 1))

async def main(): 
    await dp.start_polling(bot)

if __name__ == "__main__": 
    asyncio.run(main())
