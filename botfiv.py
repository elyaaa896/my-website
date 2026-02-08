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

# ТВОЙ ТОКЕН ИЗ !botfiv.ру
API_TOKEN = '8344514218:AAFlAbVAc1VdcqPZ9jlTL5DYSXcBAdZlyrI'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- НАДЕЖНОЕ ПОДКЛЮЧЕНИЕ К GOOGLE ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def get_creds():
    # Сначала ищем в переменных окружения Render
    creds_json = os.environ.get("G_CREDS")
    if creds_json:
        info = json.loads(creds_json)
        return ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
    # Если нет — берем из локального файла
    return ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)

creds = get_creds()
client = gspread.authorize(creds)
sheet_u = client.open("moviesbot_base").worksheet("users")

class Form(StatesGroup):
    waiting_for_series = State()
    waiting_for_custom_status = State()

def load_user_movies(user_id):
    try:
        all_r = sheet_u.get_all_records()
        # Возвращаем (номер строки в таблице, данные фильма) для конкретного пользователя
        return [(i + 2, r) for i, r in enumerate(all_r) if str(r.get('user_id')) == str(user_id)]
    except:
        return []

def get_movie_list_text(user_id, page=1):
    user_movies = load_user_movies(user_id)
    if not user_movies:
        return "🎬 Ваш личный список пуст. Просто напишите название фильма."

    items_per_page = 30
    start = (page - 1) * items_per_page
    current = user_movies[start:start+items_per_page]

    text = f"🎬 **МОЙ СПИСОК (Стр. {page}):**\n\n"
    for i, (row_idx, m) in enumerate(current, 1):
        v = m.get('series', '')
        s_text = f" ({v} )" if v else ""
        text += f"{i}. {m['name']}{s_text} — {m.get('status', '⏳')}\n"

    total = len(user_movies)
    watched = sum(1 for _, m in user_movies if '✅' in str(m.get('status', '')))
    text += f"\n📊 {watched}/{total}"
    return text

def get_main_keyboard(user_id, page=1):
    user_movies = load_user_movies(user_id)
    builder = InlineKeyboardBuilder()
    items_per_page = 30
    start = (page - 1) * items_per_page
    current = user_movies[start:start+items_per_page]

    for i, (row_idx, m) in enumerate(current, 1):
        # row_idx — это реальный номер строки в Google Таблице
        builder.button(text=str(i), callback_data=f"select_{row_idx}_{page}")
    
    nav = []
    if page > 1: nav.append(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{page-1}"))
    if start + items_per_page < len(user_movies): 
        nav.append(types.InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page_{page+1}"))
    
    if nav: builder.row(*nav)
    builder.adjust(5)
    return builder.as_markup()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    # ПРИВЕТСТВИЕ ОДИН В ОДИН ИЗ ТВОЕГО !botfiv.ру
    welcome_text = (
        "👋 Привет! Это твой личный трекер фильмов.\n\n"
        "**Значения статусов:**\n"
        "✅ — просмотрено\n"
        "▶️ — пауза\n"
        "⏭️ — следующий\n"
        "⏳ — ожидание\n"
        "➖ — не смотрел\n"
        "➕ — дата выхода"
    )
    await message.answer(welcome_text, parse_mode="Markdown")
    await message.answer(get_movie_list_text(message.from_user.id, 1),
                         reply_markup=get_main_keyboard(message.from_user.id, 1))

@dp.callback_query(F.data.startswith("select_"))
async def select_movie(call: types.CallbackQuery):
    row_idx, page = int(call.data.split("_")[1]), int(call.data.split("_")[2])
    # Получаем данные напрямую из таблицы, чтобы кнопка управления знала имя фильма
    all_records = sheet_u.get_all_records()
    movie_data = all_records[row_idx - 2]
    
    builder = InlineKeyboardBuilder()
    # ТВОИ КНОПКИ ИЗ !botfiv.ру
    for emo in ["✅", "▶️", "⏭️", "⏳", "➖"]:
        builder.button(text=emo, callback_data=f"set_{row_idx}_{emo}_{page}")

    builder.button(text="➕ Текст", callback_data=f"custom_{row_idx}_{page}")
    builder.button(text="📝 Серия", callback_data=f"ser_{row_idx}_{page}")
    builder.button(text="🗑 Удалить", callback_data=f"del_{row_idx}_{page}")
    builder.button(text="🔙 Назад", callback_data=f"page_{page}")
    builder.adjust(5, 2, 2)
    await call.message.edit_text(f"Управление: {movie_data['name']}", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("set_"))
async def set_status(call: types.CallbackQuery):
    _, row_idx, emo, page = call.data.split("_")
    sheet_u.update_cell(int(row_idx), 3, emo) # Колонка C (status)
    await call.message.edit_text(get_movie_list_text(call.from_user.id, int(page)),
                                 reply_markup=get_main_keyboard(call.from_user.id, int(page)))

@dp.callback_query(F.data.startswith("del_"))
async def delete_movie(call: types.CallbackQuery):
    _, row_idx, page = call.data.split("_")
    sheet_u.delete_rows(int(row_idx))
    await call.message.edit_text(get_movie_list_text(call.from_user.id, int(page)),
                                 reply_markup=get_main_keyboard(call.from_user.id, int(page)))

@dp.message(F.text)
async def add_movie(message: types.Message):
    if not message.text.startswith('/'):
        user_id = str(message.from_user.id)
        sheet_u.append_row([user_id, message.text, "⏳", ""])
        await message.answer(get_movie_list_text(message.from_user.id, 1),
                             reply_markup=get_main_keyboard(message.from_user.id, 1))

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
