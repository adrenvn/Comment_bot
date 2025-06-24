"""
Функции валидации и проверки доступа
"""

import logging
from database.models import Admin, User
from database.connection import Session

logger = logging.getLogger(__name__)

def is_admin(telegram_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    session = Session()
    try:
        admin = session.query(Admin).filter_by(telegram_id=telegram_id).first()
        return admin is not None
    except Exception as e:
        logger.error(f"Ошибка проверки админа: {e}")
        return False
    finally:
        session.close()

def is_user(telegram_id: int) -> bool:
    """Проверка, является ли пользователь зарегистрированным"""
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        return user is not None
    except Exception as e:
        logger.error(f"Ошибка проверки пользователя: {e}")
        return False
    finally:
        session.close()

def validate_instagram_credentials(username: str, password: str) -> bool:
    """Валидация учетных данных Instagram"""
    if not username or not password:
        return False
    if len(username) < 1 or len(password) < 6:
        return False
    return True

def validate_instagram_post_link(link: str) -> bool:
    """Валидация ссылки на пост Instagram"""
    if not link or 'instagram.com' not in link:
        return False
    if '/p/' not in link and '/reel/' not in link:
        return False
    return True

def validate_proxy_data(proxy_type: str, host: str, port: int) -> bool:
    """Валидация данных прокси"""
    # Проверка типа прокси
    if proxy_type not in ['http', 'https', 'socks5']:
        return False
    
    # Проверка хоста
    if not host or len(host) < 3 or '.' not in host:
        return False
    
    # Проверка порта
    if not isinstance(port, int) or port < 1 or port > 65535:
        return False
    
    return True

def validate_trigger_word(word: str) -> bool:
    """Валидация триггерного слова"""
    if not word or len(word) < 2:
        return False
    # Проверяем, что нет недопустимых символов
    forbidden_chars = ['<', '>', '&', '"', "'"]
    return not any(char in word for char in forbidden_chars)

def validate_dm_message(message: str) -> bool:
    """Валидация DM сообщения"""
    if not message or len(message) < 10:
        return False
    if len(message) > 1000:  # Instagram limit
        return False
    return True

def validate_telegram_id(telegram_id: str) -> bool:
    """Валидация Telegram ID"""
    try:
        user_id = int(telegram_id)
        return user_id > 0
    except ValueError:
        return False