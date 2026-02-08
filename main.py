import asyncio
from flask import Flask
from threading import Thread
# Импортируем данные из твоих файлов
from bott import dp as dp1, bot as bot1
from botfiv import dp as dp5, bot as bot5

# Настройка сервера для Render
app = Flask('')

@app.route('/')
def home():
    return "OK. Bots are running!"

def run_flask():
    # Порт 8080 — стандарт для Render
    app.run(host='0.0.0.0', port=8080)

async def start_everything():
    # 1. Запуск "анти-сна" в отдельном потоке
    Thread(target=run_flask).start()
    print("🚀 Мониторинг запущен!")

    # 2. Запуск обоих ботов одновременно
    print("🚀 Боты запускаются...")
    await asyncio.gather(
        dp1.start_polling(bot1),
        dp5.start_polling(bot5)
    )

if __name__ == "__main__":
    try:
        asyncio.run(start_everything())
    except KeyboardInterrupt:
        print("Остановка системы...")
