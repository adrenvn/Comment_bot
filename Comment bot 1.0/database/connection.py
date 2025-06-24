"""
Подключение к базе данных
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

# Создание движка БД
engine = create_engine(DATABASE_PATH, echo=False)
Session = sessionmaker(bind=engine)

def init_database():
    """Инициализация базы данных"""
    try:
        Base.metadata.create_all(engine)
        logger.info("База данных инициализирована успешно")
        return True
    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}")
        raise

def get_session():
    """Получение сессии БД"""
    return Session()

def check_database_health():
    """Проверка состояния базы данных"""
    try:
        session = Session()
        # Простой запрос для проверки
        session.execute("SELECT 1")
        session.close()
        return True
    except Exception as e:
        logger.error(f"Проблемы с базой данных: {e}")
        return False