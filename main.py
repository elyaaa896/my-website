import asyncio
from flask import Flask
from threading import Thread
from bott import dp as dp1, bot as bot1
from botfiv import dp as dp5, bot as bot5

app = Flask('')

@app.route('/')
def home():
    return "Bots are Alive!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

async def start_everything():
    Thread(target=run_flask).start()
    print("🚀 Система запущена!")
    await asyncio.gather(
        dp1.start_polling(bot1),
        dp5.start_polling(bot5)
    )

if __name__ == "__main__":
    asyncio.run(start_everything())

