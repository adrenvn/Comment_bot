"""
Интеграция с 922Proxy.com
Автоматическое управление прокси через их API
"""

import logging
import requests
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from config import cipher
from database.models import ProxyServer
from database.connection import Session
from services.proxy_manager import ProxyManager

logger = logging.getLogger(__name__)

class Proxy922Manager:
    """Менеджер для работы с 922Proxy"""
    
    def __init__(self, api_key: str = None, username: str = None, password: str = None):
        """
        Инициализация менеджера 922Proxy
        
        Args:
            api_key: API ключ от 922Proxy (если есть)
            username: Имя пользователя
            password: Пароль
        """
        self.api_key = api_key
        self.username = username
        self.password = password
        self.base_url = "https://www.922s5.com/api"  # Примерный URL API
        
    @staticmethod
    def parse_proxy_list(proxy_list_text: str) -> List[Dict]:
        """
        Парсинг списка прокси из текста
        Поддерживает различные форматы:
        - IP:PORT:USER:PASS
        - IP:PORT@USER:PASS
        - USER:PASS@IP:PORT
        """
        proxies = []
        
        for line in proxy_list_text.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            try:
                # Формат: IP:PORT:USER:PASS
                if line.count(':') == 3:
                    parts = line.split(':')
                    ip, port, user, password = parts
                    
                # Формат: IP:PORT@USER:PASS
                elif '@' in line and ':' in line:
                    if line.count('@') == 1:
                        ip_port, user_pass = line.split('@')
                        ip, port = ip_port.split(':')
                        user, password = user_pass.split(':')
                    else:
                        # Формат: USER:PASS@IP:PORT
                        user_pass, ip_port = line.split('@')
                        user, password = user_pass.split(':')
                        ip, port = ip_port.split(':')
                
                # Формат: IP:PORT (без авторизации)
                elif line.count(':') == 1:
                    ip, port = line.split(':')
                    user, password = None, None
                
                else:
                    logger.warning(f"Неизвестный формат прокси: {line}")
                    continue
                
                proxies.append({
                    'host': ip.strip(),
                    'port': int(port.strip()),
                    'username': user.strip() if user else None,
                    'password': password.strip() if password else None
                })
                
            except Exception as e:
                logger.error(f"Ошибка парсинга строки '{line}': {e}")
                continue
        
        return proxies
    
    def get_proxy_list_from_api(self) -> List[Dict]:
        """
        Получение списка прокси через API (если доступно)
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}' if self.api_key else None,
                'Content-Type': 'application/json'
            }
            
            # Примерный запрос к API
            response = requests.get(
                f"{self.base_url}/proxies",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('proxies', [])
            else:
                logger.error(f"Ошибка API 922Proxy: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Ошибка получения прокси через API: {e}")
            return []
    
    @staticmethod
    def import_proxies_to_database(proxies: List[Dict], proxy_type: str = 'http', 
                                  name_prefix: str = '922Proxy') -> int:
        """
        Импорт прокси в базу данных
        
        Args:
            proxies: Список прокси для импорта
            proxy_type: Тип прокси (http, https, socks5)
            name_prefix: Префикс для названий прокси
            
        Returns:
            Количество успешно импортированных прокси
        """
        session = Session()
        imported_count = 0
        
        try:
            for i, proxy_data in enumerate(proxies, 1):
                try:
                    # Проверка, есть ли уже такой прокси
                    existing_proxy = session.query(ProxyServer).filter_by(
                        host=proxy_data['host'],
                        port=proxy_data['port']
                    ).first()
                    
                    if existing_proxy:
                        logger.info(f"Прокси {proxy_data['host']}:{proxy_data['port']} уже существует")
                        continue
                    
                    # Шифрование пароля если есть
                    encrypted_password = None
                    if proxy_data.get('password'):
                        encrypted_password = ProxyManager.encrypt_password(proxy_data['password'])
                    
                    # Создание прокси
                    proxy = ProxyServer(
                        name=f"{name_prefix} #{i}",
                        proxy_type=proxy_type,
                        host=proxy_data['host'],
                        port=proxy_data['port'],
                        username=proxy_data.get('username'),
                        password_encrypted=encrypted_password,
                        is_active=True,
                        is_working=True  # Предполагаем, что новые прокси работают
                    )
                    
                    session.add(proxy)
                    imported_count += 1
                    
                except Exception as e:
                    logger.error(f"Ошибка импорта прокси {proxy_data}: {e}")
                    continue
            
            session.commit()
            logger.info(f"Импортировано {imported_count} прокси из {len(proxies)}")
            
        except Exception as e:
            logger.error(f"Ошибка импорта прокси: {e}")
            session.rollback()
        finally:
            session.close()
        
        return imported_count
    
    @staticmethod
    def bulk_check_proxies(batch_size: int = 10) -> Dict:
        """
        Массовая проверка прокси небольшими партиями
        
        Args:
            batch_size: Размер партии для проверки
            
        Returns:
            Статистика проверки
        """
        session = Session()
        results = {'checked': 0, 'working': 0, 'failed': 0, 'errors': []}
        
        try:
            # Получаем прокси, которые давно не проверялись
            old_check_time = datetime.now() - timedelta(hours=1)
            proxies = session.query(ProxyServer).filter_by(is_active=True).filter(
                ProxyServer.last_check < old_check_time
            ).limit(batch_size).all()
            
            for proxy in proxies:
                try:
                    is_working = ProxyManager.check_proxy_health(proxy)
                    proxy.is_working = is_working
                    proxy.last_check = datetime.now()
                    
                    results['checked'] += 1
                    if is_working:
                        results['working'] += 1
                    else:
                        results['failed'] += 1
                        
                except Exception as e:
                    results['errors'].append(f"Прокси {proxy.id}: {str(e)}")
                    logger.error(f"Ошибка проверки прокси {proxy.id}: {e}")
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Ошибка массовой проверки прокси: {e}")
            session.rollback()
        finally:
            session.close()
        
        return results
    
    @staticmethod
    def auto_rotate_proxies():
        """
        Автоматическая ротация прокси - деактивация неработающих
        """
        session = Session()
        
        try:
            # Деактивируем прокси, которые не работают более 24 часов
            failed_time = datetime.now() - timedelta(hours=24)
            
            failed_proxies = session.query(ProxyServer).filter(
                ProxyServer.is_working == False,
                ProxyServer.last_check < failed_time,
                ProxyServer.is_active == True
            ).all()
            
            deactivated_count = 0
            for proxy in failed_proxies:
                proxy.is_active = False
                deactivated_count += 1
                logger.info(f"Деактивирован неработающий прокси: {proxy.name}")
            
            session.commit()
            
            if deactivated_count > 0:
                logger.info(f"Автоматически деактивировано {deactivated_count} прокси")
            
            return deactivated_count
            
        except Exception as e:
            logger.error(f"Ошибка автоматической ротации прокси: {e}")
            session.rollback()
            return 0
        finally:
            session.close()


class Proxy922ConfigManager:
    """Менеджер конфигурации для 922Proxy"""
    
    @staticmethod
    def save_922_config(api_key: str = None, username: str = None, password: str = None):
        """Сохранение конфигурации 922Proxy в зашифрованном виде"""
        import os
        from config import ENCRYPTION_KEY
        
        config_data = {
            'api_key': api_key,
            'username': username,
            'password': password,
            'updated_at': datetime.now().isoformat()
        }
        
        try:
            # Шифруем конфигурацию
            encrypted_config = cipher.encrypt(json.dumps(config_data).encode()).decode()
            
            # Сохраняем в файл
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', '922_config.enc')
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, 'w') as f:
                f.write(encrypted_config)
            
            logger.info("Конфигурация 922Proxy сохранена")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации 922Proxy: {e}")
            return False
    
    @staticmethod
    def load_922_config() -> Dict:
        """Загрузка конфигурации 922Proxy"""
        import os
        
        config_path = os.path.join(os.path.dirname(__file__), '..', 'data', '922_config.enc')
        
        if not os.path.exists(config_path):
            return {}
        
        try:
            with open(config_path, 'r') as f:
                encrypted_config = f.read()
            
            # Расшифровываем
            decrypted_data = cipher.decrypt(encrypted_config.encode()).decode()
            config_data = json.loads(decrypted_data)
            
            return config_data
            
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации 922Proxy: {e}")
            return {}


# === ГОТОВЫЕ КОНФИГУРАЦИИ ДЛЯ ПОПУЛЯРНЫХ ПРОКСИ ПРОВАЙДЕРОВ ===

PROXY_PROVIDERS_CONFIG = {
    '922proxy': {
        'name': '922Proxy',
        'formats': [
            'IP:PORT:USER:PASS',
            'USER:PASS@IP:PORT',
            'IP:PORT@USER:PASS'
        ],
        'default_type': 'socks5',
        'api_url': 'https://www.922s5.com/api',
        'check_url': 'http://httpbin.org/ip'
    },
    'brightdata': {
        'name': 'Bright Data',
        'formats': [
            'USER:PASS@IP:PORT'
        ],
        'default_type': 'http',
        'api_url': None,
        'check_url': 'http://httpbin.org/ip'
    },
    'oxylabs': {
        'name': 'Oxylabs',
        'formats': [
            'USER:PASS@IP:PORT'
        ],
        'default_type': 'http',
        'api_url': None,
        'check_url': 'http://httpbin.org/ip'
    },
    'smartproxy': {
        'name': 'SmartProxy',
        'formats': [
            'USER:PASS@IP:PORT',
            'IP:PORT:USER:PASS'
        ],
        'default_type': 'http',
        'api_url': None,
        'check_url': 'http://httpbin.org/ip'
    }
}


class UniversalProxyImporter:
    """Универсальный импортер прокси для разных провайдеров"""
    
    @staticmethod
    def detect_proxy_format(proxy_text: str) -> str:
        """Автоматическое определение формата прокси"""
        lines = [line.strip() for line in proxy_text.strip().split('\n') 
                if line.strip() and not line.startswith('#')]
        
        if not lines:
            return 'unknown'
        
        sample_line = lines[0]
        
        # IP:PORT:USER:PASS
        if sample_line.count(':') == 3:
            return 'ip_port_user_pass'
        
        # USER:PASS@IP:PORT
        elif '@' in sample_line and sample_line.count(':') >= 2:
            if sample_line.find('@') < sample_line.rfind(':'):
                return 'user_pass_at_ip_port'
            else:
                return 'ip_port_at_user_pass'
        
        # IP:PORT
        elif sample_line.count(':') == 1:
            return 'ip_port_only'
        
        return 'unknown'
    
    @staticmethod
    def import_from_text(proxy_text: str, provider: str = '922proxy', 
                        proxy_type: str = None) -> Dict:
        """
        Универсальный импорт прокси из текста
        
        Args:
            proxy_text: Текст со списком прокси
            provider: Провайдер прокси
            proxy_type: Тип прокси (если None, используется default из конфига)
            
        Returns:
            Результат импорта
        """
        if provider in PROXY_PROVIDERS_CONFIG:
            config = PROXY_PROVIDERS_CONFIG[provider]
            if not proxy_type:
                proxy_type = config['default_type']
            name_prefix = config['name']
        else:
            proxy_type = proxy_type or 'http'
            name_prefix = provider.title()
        
        # Парсинг прокси
        proxies = Proxy922Manager.parse_proxy_list(proxy_text)
        
        if not proxies:
            return {'success': False, 'message': 'Не удалось распарсить прокси'}
        
        # Импорт в базу данных
        imported_count = Proxy922Manager.import_proxies_to_database(
            proxies, proxy_type, name_prefix
        )
        
        return {
            'success': True,
            'imported': imported_count,
            'total': len(proxies),
            'message': f'Импортировано {imported_count} из {len(proxies)} прокси'
        }
    
    @staticmethod
    def get_import_instructions(provider: str) -> str:
        """Получение инструкций по импорту для провайдера"""
        if provider not in PROXY_PROVIDERS_CONFIG:
            return "Поддерживаемые форматы:\n• IP:PORT:USER:PASS\n• USER:PASS@IP:PORT\n• IP:PORT (без авторизации)"
        
        config = PROXY_PROVIDERS_CONFIG[provider]
        formats = '\n'.join([f"• {fmt}" for fmt in config['formats']])
        
        return f"Инструкции для {config['name']}:\n\nПоддерживаемые форматы:\n{formats}\n\nТип прокси по умолчанию: {config['default_type'].upper()}"