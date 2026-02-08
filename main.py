import asyncio
from flask import Flask
from threading import Thread
from bott import dp as dp1, bot as bot1
from botfiv import dp as dp5, bot as bot5

# Создаем веб-сервер, чтобы Render видел активность
app = Flask('')

@app.route('/')
def home():
    return "OK. Bots are running!"

def run_flask():
    # Порт 8080 стандартный для большинства облачных хостингов
    app.run(host='0.0.0.0', port=8080)

async def start_everything():
    # 1. Запускаем "анти-сон" в фоновом потоке
    Thread(target=run_flask).start()
    print("🚀 Мониторинг для Render запущен!")

    # 2. Запускаем обоих ботов одновременно
    # Если один упадет, Render перезапустит весь скрипт
    print("🚀 Боты запускаются...")
    await asyncio.gather(
        dp1.start_polling(bot1),
        dp5.start_polling(bot5)
    )

if __name__ == "__main__":
    try:
        asyncio.run(start_everything())
    except KeyboardInterrupt:
        print("Система остановлена пользователем.")