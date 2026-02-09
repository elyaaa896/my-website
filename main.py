import subprocess
import time
import sys
import http.server
import threading

# Функция для создания фиктивного веб-сервера (чтобы Render не ругался)
def run_dummy_server():
    server_address = ('', 10000) # Render использует порт 10000 по умолчанию
    httpd = http.server.HTTPServer(server_address, http.server.SimpleHTTPRequestHandler)
    print("🌍 Фиктивный веб-сервер запущен на порту 10000")
    httpd.serve_forever()

def start_all():
    # Запускаем "сайт" в отдельном потоке
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    # Запускаем твоих ботов
    p1 = subprocess.Popen([sys.executable, 'bott.py'])
    p2 = subprocess.Popen([sys.executable, 'botfiv.py'])
    
    print("✅ БОТЫ ЗАПУЩЕНЫ!")
    
    try:
        while True:
            time.sleep(20)
            if p1.poll() is not None:
                p1 = subprocess.Popen([sys.executable, 'bott.py'])
            if p2.poll() is not None:
                p2 = subprocess.Popen([sys.executable, 'botfiv.py'])
    except:
        p1.terminate()
        p2.terminate()

if __name__ == "__main__":
    start_all()
