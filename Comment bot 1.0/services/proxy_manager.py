"""
Сервис управления прокси серверами
"""

import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from config import cipher, PROXY_CHECK_TIMEOUT, PROXY_CHECK_URL, PROXY_RECHECK_INTERVAL
from database.models import ProxyServer
from database.connection import Session

logger = logging.getLogger(__name__)

class ProxyManager:
    """Менеджер прокси серверов"""
    
    @staticmethod
    def encrypt_password(password: str) -> str:
        """Шифрование пароля прокси"""
        return cipher.encrypt(password.encode()).decode()

    @staticmethod
    def decrypt_password(encrypted_password: str) -> str:
        """Расшифровка пароля прокси"""
        return cipher.decrypt(encrypted_password.encode()).decode()

    @staticmethod
    def get_proxy_dict(proxy: ProxyServer) -> Optional[Dict[str, str]]:
        """Получение словаря прокси для requests/instagrapi"""
        if not proxy:
            return None
        
        auth = ""
        if proxy.username and proxy.password_encrypted:
            try:
                password = ProxyManager.decrypt_password(proxy.password_encrypted)
                auth = f"{proxy.username}:{password}@"
            except Exception as e:
                logger.error(f"Ошибка расшифровки пароля прокси {proxy.id}: {e}")
                return None
        
        proxy_url = f"{proxy.proxy_type}://{auth}{proxy.host}:{proxy.port}"
        
        return {
            'http': proxy_url,
            'https': proxy_url
        }

    @staticmethod
    def check_proxy_health(proxy: ProxyServer) -> bool:
        """Проверка работоспособности прокси"""
        try:
            proxy_dict = ProxyManager.get_proxy_dict(proxy)
            if not proxy_dict:
                logger.warning(f"Не удалось получить настройки прокси {proxy.id}")
                return False
                
            # Проверяем через HTTP запрос
            response = requests.get(
                PROXY_CHECK_URL, 
                proxies=proxy_dict,
                timeout=PROXY_CHECK_TIMEOUT
            )
            
            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"Прокси {proxy.name} работает. IP: {response_data.get('origin', 'unknown')}")
                return True
            else:
                logger.warning(f"Прокси {proxy.name} вернул статус {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            logger.warning(f"Таймаут при проверке прокси {proxy.name}")
            return False
        except requests.exceptions.ProxyError:
            logger.warning(f"Ошибка подключения к прокси {proxy.name}")
            return False
        except Exception as e:
            logger.error(f"Ошибка проверки прокси {proxy.name}: {e}")
            return False

    @staticmethod
    def get_best_proxy() -> Optional[ProxyServer]:
        """Получение лучшего доступного прокси"""
        session = Session()
        try:
            # Получаем активные прокси, отсортированные по использованию
            proxies = session.query(ProxyServer).filter_by(
                is_active=True, 
                is_working=True
            ).order_by(ProxyServer.usage_count.asc()).all()
            
            if not proxies:
                logger.warning("Нет доступных прокси серверов")
                return None
                
            # Проверяем первый прокси (с наименьшим использованием)
            best_proxy = proxies[0]
            
            # Проверяем, давно ли проверялся прокси
            if (not best_proxy.last_check or 
                datetime.now() - best_proxy.last_check > timedelta(minutes=PROXY_RECHECK_INTERVAL)):
                
                is_working = ProxyManager.check_proxy_health(best_proxy)
                best_proxy.is_working = is_working
                best_proxy.last_check = datetime.now()
                session.commit()
                
                if not is_working:
                    logger.warning(f"Прокси {best_proxy.name} не работает, ищем следующий")
                    # Рекурсивно ищем следующий рабочий прокси
                    return ProxyManager.get_best_proxy()
            
            # Увеличиваем счетчик использования
            best_proxy.usage_count += 1
            session.commit()
            
            logger.info(f"Выбран прокси: {best_proxy.name} (использований: {best_proxy.usage_count})")
            return best_proxy
            
        except Exception as e:
            logger.error(f"Ошибка получения прокси: {e}")
            return None
        finally:
            session.close()

    @staticmethod
    def check_all_proxies() -> Dict[str, int]:
        """Проверка всех активных прокси"""
        session = Session()
        try:
            proxies = session.query(ProxyServer).filter_by(is_active=True).all()
            
            working_count = 0
            failed_count = 0
            results = []
            
            for proxy in proxies:
                is_working = ProxyManager.check_proxy_health(proxy)
                proxy.is_working = is_working
                proxy.last_check = datetime.now()
                
                if is_working:
                    working_count += 1
                    results.append(f"✅ {proxy.name}")
                else:
                    failed_count += 1
                    results.append(f"❌ {proxy.name}")
            
            session.commit()
            
            logger.info(f"Проверено прокси: {working_count} работают, {failed_count} не работают")
            
            return {
                'working': working_count,
                'failed': failed_count,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Ошибка проверки всех прокси: {e}")
            return {'working': 0, 'failed': 0, 'results': []}
        finally:
            session.close()

    @staticmethod
    def get_proxy_stats() -> Dict:
        """Получение статистики прокси"""
        session = Session()
        try:
            # Общая статистика
            total_proxies = session.query(ProxyServer).count()
            active_proxies = session.query(ProxyServer).filter_by(is_active=True).count()
            working_proxies = session.query(ProxyServer).filter_by(is_active=True, is_working=True).count()
            
            # Статистика по типам
            type_stats = {}
            for proxy_type in ['http', 'https', 'socks5']:
                count = session.query(ProxyServer).filter_by(proxy_type=proxy_type).count()
                type_stats[proxy_type] = count
            
            # Общее использование
            total_usage = session.query(ProxyServer).with_entities(
                session.query(ProxyServer.usage_count).scalar_subquery()
            ).scalar() or 0
            
            return {
                'total': total_proxies,
                'active': active_proxies,
                'working': working_proxies,
                'types': type_stats,
                'usage': total_usage
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики прокси: {e}")
            return {}
        finally:
            session.close()

    @staticmethod
    def create_proxy(name: str, proxy_type: str, host: str, port: int, 
                    username: str = None, password: str = None) -> Optional[ProxyServer]:
        """Создание нового прокси сервера"""
        session = Session()
        try:
            # Шифрование пароля если есть
            encrypted_password = None
            if password:
                encrypted_password = ProxyManager.encrypt_password(password)
            
            # Создание прокси
            proxy = ProxyServer(
                name=name,
                proxy_type=proxy_type,
                host=host,
                port=port,
                username=username,
                password_encrypted=encrypted_password
            )
            
            session.add(proxy)
            session.commit()
            
            logger.info(f"Создан прокси {proxy.id}: {name}")
            return proxy
            
        except Exception as e:
            logger.error(f"Ошибка создания прокси: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    @staticmethod
    def delete_proxy(proxy_id: int) -> bool:
        """Удаление прокси сервера"""
        session = Session()
        try:
            proxy = session.query(ProxyServer).filter_by(id=proxy_id).first()
            if not proxy:
                logger.warning(f"Прокси {proxy_id} не найден")
                return False
            
            # Проверяем, используется ли прокси в сценариях
            from database.models import Scenario
            scenarios_count = session.query(Scenario).filter_by(proxy_id=proxy_id).count()
            
            if scenarios_count > 0:
                logger.warning(f"Прокси {proxy_id} используется в {scenarios_count} сценариях")
                return False
            
            proxy_name = proxy.name
            session.delete(proxy)
            session.commit()
            
            logger.info(f"Удален прокси {proxy_id}: {proxy_name}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления прокси {proxy_id}: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    @staticmethod
    def get_proxy_list() -> List[ProxyServer]:
        """Получение списка всех прокси"""
        session = Session()
        try:
            return session.query(ProxyServer).order_by(ProxyServer.created_at.desc()).all()
        except Exception as e:
            logger.error(f"Ошибка получения списка прокси: {e}")
            return []
        finally:
            session.close()

    @staticmethod
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