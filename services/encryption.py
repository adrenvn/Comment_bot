"""
Сервис для шифрования и расшифровки данных
"""

import logging
from config import cipher

logger = logging.getLogger(__name__)

class EncryptionService:
    """Сервис шифрования"""
    
    @staticmethod
    def encrypt_password(password: str) -> str:
        """Шифрование пароля"""
        try:
            return cipher.encrypt(password.encode()).decode()
        except Exception as e:
            logger.error(f"Ошибка шифрования пароля: {e}")
            raise

    @staticmethod
    def decrypt_password(encrypted_password: str) -> str:
        """Расшифровка пароля"""
        try:
            return cipher.decrypt(encrypted_password.encode()).decode()
        except Exception as e:
            logger.error(f"Ошибка расшифровки пароля: {e}")
            raise

    @staticmethod
    def encrypt_data(data: str) -> str:
        """Шифрование произвольных данных"""
        try:
            return cipher.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Ошибка шифрования данных: {e}")
            raise

    @staticmethod
    def decrypt_data(encrypted_data: str) -> str:
        """Расшифровка произвольных данных"""
        try:
            return cipher.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Ошибка расшифровки данных: {e}")
            raise