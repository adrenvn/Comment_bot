"""
Конфигурация Instagram Automation Bot v2.0
ОБНОВЛЕННЫЙ ФАЙЛ config.py
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

# === КОНСТАНТЫ УЛУЧШЕННОЙ АВТОРИЗАЦИИ ===
# Быстрые попытки авторизации
FAST_RETRY_DELAY = int(os.getenv("FAST_RETRY_DELAY", 120))  # 2 минуты
MAX_FAST_ATTEMPTS = int(os.getenv("MAX_FAST_ATTEMPTS", 3))  # 3 быстрые попытки
SLOW_RETRY_DELAY = int(os.getenv("SLOW_RETRY_DELAY", 420))  # 7 минут для медленных

# Таймауты для разных типов проверок
CHALLENGE_TIMEOUT = int(os.getenv("CHALLENGE_TIMEOUT", 1800))  # 30 минут
SMS_CODE_TIMEOUT = int(os.getenv("SMS_CODE_TIMEOUT", 300))     # 5 минут
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", 600))           # 10 минут

# Интерактивные возможности
ENABLE_SMS_INPUT = os.getenv("ENABLE_SMS_INPUT", "true").lower() == "true"
ENABLE_QUICK_RETRY = os.getenv("ENABLE_QUICK_RETRY", "true").lower() == "true"
ENABLE_AUTO_PROXY_SWITCH = os.getenv("ENABLE_AUTO_PROXY_SWITCH", "true").lower() == "true"
ENABLE_SAFE_MODE = os.getenv("ENABLE_SAFE_MODE", "true").lower() == "true"

# Детектор типов проверок
CHALLENGE_DETECTION = {
    'phone_keywords': ['phone', 'sms', 'mobile', 'текст', 'смс'],
    'email_keywords': ['email', 'mail', 'почта', 'письмо'],
    'device_keywords': ['device', 'устройство', 'телефон', 'приложение'],
    'photo_keywords': ['photo', 'selfie', 'фото', 'селфи', 'снимок']
}

# Антидетект улучшения
RANDOM_DELAYS = {
    'before_login': (3, 8),      # Задержка перед входом
    'after_challenge': (5, 15),  # Задержка после challenge
    'between_attempts': (2, 5),  # Задержка между действиями
}

# Настройки уведомлений
AUTH_NOTIFICATIONS = {
    'send_progress': True,        # Отправлять прогресс авторизации
    'send_challenges': True,      # Уведомления о проверках
    'send_success': True,         # Уведомления об успехе
    'send_failures': True,        # Уведомления о неудачах
}

# Статистика и мониторинг
AUTH_MONITORING = {
    'track_attempts': True,       # Отслеживать попытки
    'track_challenge_types': True, # Отслеживать типы проверок
    'track_proxy_performance': True, # Производительность прокси
    'auto_alert_threshold': 0.7,  # Порог автоуведомлений (70% неудач)
}

# === ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ===
instabots = {}  # Хранение сессий Instagram
tasks = {}      # Активные задачи
captcha_confirmed = {}  # Подтверждения капчи

# Глобальные переменные для улучшенной авторизации
auth_sessions = {}     # Активные сессии авторизации
auth_callbacks = {}    # Callback данные для авторизации
sms_codes = {}         # Временное хранение SMS кодов

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