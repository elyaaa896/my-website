import subprocess
import time
import sys

# Запускаем ботов (файлы должны называться bott.py и botfiv.py)
p1 = subprocess.Popen([sys.executable, 'bott.py'])
p2 = subprocess.Popen([sys.executable, 'botfiv.py'])

print("🚀 Боты запущены! )) я буду следить за ними...")

try:
    while True:
        time.sleep(10) # Проверяем каждые 10 секунд

        # Если первый бот упал — включаем снова
        if p1.poll() is not None:
            print("⚠️ Первый бот упал, воскрешаю...")
            p1 = subprocess.Popen([sys.executable, 'bott.py'])

        # Если второй бот упал — включаем снова
        if p2.poll() is not None:
            print("⚠️ Второй бот упал, воскрешаю...")
            p2 = subprocess.Popen([sys.executable, 'botfiv.py'])
except KeyboardInterrupt:
    p1.terminate()
    p2.terminate()
