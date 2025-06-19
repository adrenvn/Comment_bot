"""
Конфигурация Instagram Automation Bot v2.0
"""

import os
from cryptography.fernet import Fernet

# === ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не установлен в .env файле")

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # Генерируем ключ если его нет
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print(f"Сгенерирован новый ключ шифрования: {ENCRYPTION_KEY}")
    print("Добавьте его в .env файл: ENCRYPTION_KEY=" + ENCRYPTION_KEY)

ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID")
DATABASE_PATH = os.getenv("DATABASE_PATH", "sqlite:///./data/bot_database.db")

# === КОНСТАНТЫ INSTAGRAM ===
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", 5))
DELAY_BETWEEN_ATTEMPTS = int(os.getenv("DELAY_BETWEEN_ATTEMPTS", 420))  # 7 минут
CAPTCHA_TIMEOUT = int(os.getenv("CAPTCHA_TIMEOUT", 1800))  # 30 минут
MAX_REQUESTS_PER_HOUR = int(os.getenv("MAX_REQUESTS_PER_HOUR", 200))
MAX_ACTIVE_SCENARIOS = int(os.getenv("MAX_ACTIVE_SCENARIOS", 2))
MIN_ACTION_DELAY = int(os.getenv("MIN_ACTION_DELAY", 15))
MAX_ACTION_DELAY = int(os.getenv("MAX_ACTION_DELAY", 30))

# === КОНСТАНТЫ ПРОКСИ ===
PROXY_CHECK_TIMEOUT = 10  # Таймаут проверки прокси в секундах
PROXY_CHECK_URL = "http://httpbin.org/ip"  # URL для проверки прокси
PROXY_RECHECK_INTERVAL = 30  # Интервал перепроверки прокси в минутах

# === ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ===
instabots = {}  # Хранение сессий Instagram
tasks = {}      # Активные задачи
captcha_confirmed = {}  # Подтверждения капчи

# === ИНИЦИАЛИЗАЦИЯ ШИФРОВАНИЯ ===
cipher = Fernet(ENCRYPTION_KEY.encode())

# === НАСТРОЙКИ АНТИДЕТЕКТ ===
INSTAGRAM_USER_AGENTS = [
    "Instagram 219.0.0.12.117 Android",
    "Instagram 250.0.0.16.109 Android",
    "Instagram 243.0.0.15.119 Android"
]

DEVICE_SETTINGS = [
    {
        'manufacturer': 'Samsung',
        'model': 'SM-G973F',
        'android_version': 29,
        'android_release': '10'
    },
    {
        'manufacturer': 'Xiaomi',
        'model': 'Mi 10',
        'android_version': 30,
        'android_release': '11'
    },
    {
        'manufacturer': 'OnePlus',
        'model': 'OnePlus 8',
        'android_version': 29,
        'android_release': '10'
    }
]