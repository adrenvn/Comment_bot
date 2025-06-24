"""
Базовый TikTok сервис с использованием Playwright
services/tiktok_service.py - НОВЫЙ ФАЙЛ
"""

import asyncio
import logging
import random
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, Playwright

from database.models import TikTokScenario, TikTokSentMessage, TikTokPendingMessage, TikTokAuthenticationLog
from database.connection import Session
from services.encryption import EncryptionService
from services.proxy_manager import ProxyManager

logger = logging.getLogger(__name__)

class TikTokService:
    """Базовый сервис для работы с TikTok через Playwright"""
    
    def __init__(self, scenario: TikTokScenario):
        self.scenario = scenario
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.session = Session()
        
        # Состояние сессии
        self.is_authenticated = False
        self.last_activity = datetime.now()
        self.video_id = None
        
        # Настройки безопасности
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        self.viewports = [
            {'width': 1366, 'height': 768},
            {'width': 1920, 'height': 1080},
            {'width': 1440, 'height': 900},
            {'width': 1536, 'height': 864}
        ]
    
    async def init_browser(self) -> bool:
        """Инициализация браузера с антидетект настройками"""
        try:
            logger.info(f"Инициализация браузера для TikTok сценария {self.scenario.id}")
            
            self.playwright = await async_playwright().start()
            
            # Настройки браузера для обхода детекции
            browser_args = [
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions-except',
                '--disable-extensions',
                '--disable-plugins-discovery',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-field-trial-config',
                '--disable-back-forward-cache',
                '--disable-ipc-flooding-protection'
            ]
            
            # Настройка прокси
            proxy_config = None
            if self.scenario.proxy_server:
                proxy_dict = ProxyManager.get_proxy_dict(self.scenario.proxy_server)
                if proxy_dict:
                    proxy_url = proxy_dict['http']
                    logger.info(f"Использование прокси: {self.scenario.proxy_server.name}")
                    
                    # Парсим URL прокси
                    if '@' in proxy_url:
                        auth_part, server_part = proxy_url.split('://', 1)[1].split('@')
                        username, password = auth_part.split(':')
                        server = server_part
                    else:
                        username = self.scenario.proxy_server.username
                        password = ProxyManager.decrypt_password(
                            self.scenario.proxy_server.password_encrypted
                        ) if self.scenario.proxy_server.password_encrypted else None
                        server = f"{self.scenario.proxy_server.host}:{self.scenario.proxy_server.port}"
                    
                    proxy_config = {
                        'server': f"{self.scenario.proxy_server.proxy_type}://{server}",
                        'username': username,
                        'password': password
                    }
            
            # Запуск браузера
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=browser_args,
                proxy=proxy_config
            )
            
            # Случайный выбор user agent и viewport
            user_agent = random.choice(self.user_agents)
            viewport = random.choice(self.viewports)
            
            # Создание контекста с реалистичными настройками
            self.context = await self.browser.new_context(
                viewport=viewport,
                user_agent=user_agent,
                locale='en-US',
                timezone_id='America/New_York',
                permissions=['geolocation'],
                geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # New York
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            
            # Блокируем ненужные ресурсы для ускорения
            await self.context.route('**/*.{png,jpg,jpeg,gif,svg,woff,woff2,mp4,webm}', 
                                   lambda route: route.abort())
            
            # Создание страницы
            self.page = await self.context.new_page()
            
            # Антидетект скрипты
            await self.page.add_init_script("""
                // Переопределяем webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Переопределяем languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                // Переопределяем plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // Переопределяем chrome object
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
                
                // Переопределяем permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            logger.info(f"Браузер успешно инициализирован для сценария {self.scenario.id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка инициализации браузера TikTok: {e}")
            await self.cleanup()
            return False
    
    async def authenticate(self) -> bool:
        """Базовая авторизация в TikTok"""
        auth_start_time = time.time()
        
        try:
            logger.info(f"Начало авторизации TikTok для сценария {self.scenario.id}")
            
            # Запись попытки авторизации
            auth_log = TikTokAuthenticationLog(
                scenario_id=self.scenario.id,
                attempt_number=self.scenario.auth_attempt,
                auth_method='playwright',
                proxy_used=self.scenario.proxy_server.name if self.scenario.proxy_server else None,
                success=False,
                user_agent_used=await self.page.evaluate('navigator.userAgent')
            )
            
            # Имитация реального поведения пользователя
            await self._simulate_user_behavior()
            
            # Переход на TikTok
            await self.page.goto('https://www.tiktok.com', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(random.uniform(2, 4))
            
            # Переход на страницу входа
            await self.page.goto('https://www.tiktok.com/login', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(random.uniform(3, 6))
            
            # Выбор метода входа (Phone/Email/Username)
            await self._select_login_method()
            
            # Заполнение формы входа
            success = await self._fill_login_form()
            if not success:
                auth_log.error_message = "Ошибка заполнения формы входа"
                self.session.add(auth_log)
                self.session.commit()
                return False
            
            # Ожидание результата авторизации
            auth_success = await self._wait_for_auth_result()
            
            # Обновление лога авторизации
            auth_log.success = auth_success
            auth_log.duration_seconds = int(time.time() - auth_start_time)
            
            if auth_success:
                logger.info(f"Успешная авторизация TikTok для сценария {self.scenario.id}")
                self.is_authenticated = True
                self.scenario.auth_status = 'success'
                self.scenario.error_message = None
            else:
                logger.warning(f"Неудачная авторизация TikTok для сценария {self.scenario.id}")
                self.scenario.auth_status = 'failed'
                auth_log.error_message = "Неудачная авторизация"
            
            self.session.add(auth_log)
            self.session.merge(self.scenario)
            self.session.commit()
            
            return auth_success
            
        except Exception as e:
            logger.error(f"Ошибка авторизации TikTok для сценария {self.scenario.id}: {e}")
            
            # Запись ошибки в лог
            if 'auth_log' in locals():
                auth_log.success = False
                auth_log.error_message = str(e)
                auth_log.duration_seconds = int(time.time() - auth_start_time)
                self.session.add(auth_log)
            
            self.scenario.auth_status = 'failed'
            self.scenario.error_message = str(e)[:500]
            self.session.merge(self.scenario)
            self.session.commit()
            
            return False
    
    async def _simulate_user_behavior(self):
        """Имитация поведения реального пользователя"""
        # Случайные движения мыши
        for _ in range(random.randint(2, 4)):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            await self.page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Случайная задержка
        await asyncio.sleep(random.uniform(1, 3))
    
    async def _select_login_method(self):
        """Выбор метода входа"""
        try:
            # Ищем различные варианты кнопок входа
            login_selectors = [
                'a[href*="login"]',
                'button:has-text("Log in")',
                'button:has-text("Login")',
                '[data-e2e="top-login-button"]',
                '[data-e2e="header-login-button"]'
            ]
            
            for selector in login_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        await element.click()
                        await asyncio.sleep(random.uniform(1, 2))
                        break
                except:
                    continue
            
            # Ждем появления формы входа
            await asyncio.sleep(random.uniform(2, 4))
            
            # Выбираем метод входа по email/username
            method_selectors = [
                'a:has-text("Use phone / email / username")',
                'a:has-text("Use email or username")',
                '[data-e2e="login-method-email"]',
                'div:has-text("Email or username")'
            ]
            
            for selector in method_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        await element.click()
                        await asyncio.sleep(random.uniform(1, 2))
                        break
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"Не удалось выбрать метод входа: {e}")
    
    async def _fill_login_form(self) -> bool:
        """Заполнение формы входа"""
        try:
            # Ждем появления полей ввода
            await asyncio.sleep(random.uniform(2, 4))
            
            # Поиск поля username/email
            username_selectors = [
                'input[name="username"]',
                'input[placeholder*="email"]',
                'input[placeholder*="username"]',
                'input[type="text"]',
                'input[data-e2e="email-input"]'
            ]
            
            username_input = None
            for selector in username_selectors:
                try:
                    username_input = await self.page.wait_for_selector(selector, timeout=3000)
                    if username_input:
                        break
                except:
                    continue
            
            if not username_input:
                logger.error("Не найдено поле для ввода username")
                return False
            
            # Ввод username с имитацией человеческого поведения
            await self._human_type(username_input, self.scenario.tiktok_username)
            await asyncio.sleep(random.uniform(1, 2))
            
            # Поиск поля пароля
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[placeholder*="password"]',
                'input[data-e2e="password-input"]'
            ]
            
            password_input = None
            for selector in password_selectors:
                try:
                    password_input = await self.page.wait_for_selector(selector, timeout=3000)
                    if password_input:
                        break
                except:
                    continue
            
            if not password_input:
                logger.error("Не найдено поле для ввода пароля")
                return False
            
            # Ввод пароля
            password = EncryptionService.decrypt_password(self.scenario.tiktok_password_encrypted)
            await self._human_type(password_input, password)
            await asyncio.sleep(random.uniform(1, 2))
            
            # Поиск и нажатие кнопки входа
            login_button_selectors = [
                'button[type="submit"]',
                'button:has-text("Log in")',
                'button:has-text("Login")',
                '[data-e2e="login-button"]',
                'button[data-e2e="login-submit-button"]'
            ]
            
            login_button = None
            for selector in login_button_selectors:
                try:
                    login_button = await self.page.wait_for_selector(selector, timeout=3000)
                    if login_button:
                        break
                except:
                    continue
            
            if not login_button:
                logger.error("Не найдена кнопка входа")
                return False
            
            # Случайная задержка перед нажатием
            await asyncio.sleep(random.uniform(1, 3))
            
            # Нажатие кнопки входа
            await login_button.click()
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка заполнения формы входа: {e}")
            return False
    
    async def _human_type(self, element, text: str):
        """Имитация человеческого набора текста"""
        await element.click()
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Очищаем поле
        await element.fill('')
        
        # Набираем текст посимвольно
        for char in text:
            await element.type(char)
            # Случайная задержка между символами
            await asyncio.sleep(random.uniform(0.08, 0.2))
    
    async def _wait_for_auth_result(self) -> bool:
        """Ожидание результата авторизации"""
        try:
            # Ждем либо успешного перенаправления, либо ошибки
            start_time = time.time()
            timeout = 30  # 30 секунд
            
            while time.time() - start_time < timeout:
                current_url = self.page.url
                
                # Проверяем успешный вход
                if any(path in current_url for path in ['/foryou', '/following', '/explore']):
                    logger.info(f"Успешный вход в TikTok, URL: {current_url}")
                    return True
                
                # Проверяем наличие ошибок
                error_selectors = [
                    '.error-message',
                    '[data-e2e="login-error"]',
                    'div:has-text("Incorrect username or password")',
                    'div:has-text("Please check your email")',
                    '.login-error'
                ]
                
                for selector in error_selectors:
                    try:
                        error_element = await self.page.wait_for_selector(selector, timeout=1000)
                        if error_element:
                            error_text = await error_element.text_content()
                            logger.warning(f"Ошибка авторизации TikTok: {error_text}")
                            return False
                    except:
                        continue
                
                # Проверяем наличие captcha или challenge
                challenge_selectors = [
                    '[data-e2e="captcha"]',
                    '.captcha',
                    'iframe[src*="captcha"]',
                    'div:has-text("Verify")',
                    'div:has-text("Security check")'
                ]
                
                for selector in challenge_selectors:
                    try:
                        challenge_element = await self.page.wait_for_selector(selector, timeout=1000)
                        if challenge_element:
                            logger.warning(f"TikTok требует прохождение проверки безопасности")
                            # Здесь можно добавить обработку challenge
                            return False
                    except:
                        continue
                
                await asyncio.sleep(1)
            
            logger.warning("Таймаут ожидания результата авторизации TikTok")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при ожидании результата авторизации: {e}")
            return False
    
    async def extract_video_id(self, video_url: str) -> Optional[str]:
        """Извлечение ID видео из ссылки TikTok"""
        try:
            logger.info(f"Извлечение ID видео из URL: {video_url}")
            
            # Переходим на страницу видео
            await self.page.goto(video_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(random.uniform(3, 6))
            
            # Получаем текущий URL после редиректов
            current_url = self.page.url
            logger.info(f"Текущий URL после перехода: {current_url}")
            
            # Извлекаем ID видео из URL
            # Форматы TikTok URLs:
            # https://www.tiktok.com/@username/video/1234567890
            # https://vm.tiktok.com/ZMxxx/ (короткие ссылки)
            
            if '/video/' in current_url:
                video_id = current_url.split('/video/')[-1].split('?')[0].split('/')[0]
                self.video_id = video_id
                logger.info(f"Извлечен ID видео: {video_id}")
                return video_id
            
            # Попытка извлечь из мета-тегов
            try:
                video_id_meta = await self.page.get_attribute('meta[property="og:url"]', 'content')
                if video_id_meta and '/video/' in video_id_meta:
                    video_id = video_id_meta.split('/video/')[-1].split('?')[0].split('/')[0]
                    self.video_id = video_id
                    logger.info(f"Извлечен ID видео из мета-тегов: {video_id}")
                    return video_id
            except:
                pass
            
            logger.warning(f"Не удалось извлечь ID видео из URL: {current_url}")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка извлечения ID видео TikTok: {e}")
            return None
    
    async def get_comments(self, limit: int = 50) -> List[Dict]:
        """Получение комментариев к текущему видео"""
        try:
            logger.info(f"Начало извлечения комментариев (лимит: {limit})")
            
            comments = []
            
            # Прокручиваем страницу для загрузки комментариев
            await self._scroll_to_load_comments()
            
            # Селекторы для комментариев
            comment_selectors = [
                '[data-e2e="comment-item"]',
                '.comment-item',
                '[class*="comment"]',
                '[class*="Comment"]'
            ]
            
            comment_elements = []
            for selector in comment_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        comment_elements = elements
                        logger.info(f"Найдено {len(elements)} элементов комментариев с селектором: {selector}")
                        break
                except:
                    continue
            
            if not comment_elements:
                logger.warning("Не найдено элементов комментариев")
                return comments
            
            # Обработка каждого комментария
            processed_count = 0
            for element in comment_elements[:limit]:
                try:
                    comment_data = await self._extract_comment_data(element)
                    if comment_data:
                        comments.append(comment_data)
                        processed_count += 1
                        
                        # Проверяем триггерное слово
                        if self.scenario.trigger_word.lower() in comment_data['text'].lower():
                            logger.info(f"Найден комментарий с триггером от {comment_data['username']}")
                        
                except Exception as e:
                    logger.warning(f"Ошибка обработки комментария: {e}")
                    continue
            
            logger.info(f"Обработано {processed_count} комментариев из {len(comment_elements)}")
            return comments
            
        except Exception as e:
            logger.error(f"Ошибка получения комментариев TikTok: {e}")
            return []
    
    async def _scroll_to_load_comments(self):
        """Прокрутка страницы для загрузки комментариев"""
        try:
            # Прокручиваем до раздела комментариев
            await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
            await asyncio.sleep(random.uniform(2, 3))
            
            # Дополнительная прокрутка для загрузки большего количества комментариев
            for _ in range(3):
                await self.page.evaluate('window.scrollBy(0, 500)')
                await asyncio.sleep(random.uniform(1, 2))
                
        except Exception as e:
            logger.warning(f"Ошибка прокрутки для загрузки комментариев: {e}")
    
    async def _extract_comment_data(self, element) -> Optional[Dict]:
        """Извлечение данных из элемента комментария"""
        try:
            # Различные селекторы для извлечения данных комментария
            text_selectors = [
                '[data-e2e="comment-level-1"] span',
                '.comment-text',
                '[class*="comment-text"]',
                'span[data-e2e*="comment"]'
            ]
            
            username_selectors = [
                '[data-e2e="comment-username"]',
                '.comment-username',
                '[class*="username"]',
                'a[href*="@"]'
            ]
            
            # Извлекаем текст комментария
            comment_text = None
            for selector in text_selectors:
                try:
                    text_element = await element.query_selector(selector)
                    if text_element:
                        comment_text = await text_element.text_content()
                        if comment_text and comment_text.strip():
                            break
                except:
                    continue
            
            # Извлекаем имя пользователя
            username = None
            user_id = None
            for selector in username_selectors:
                try:
                    username_element = await element.query_selector(selector)
                    if username_element:
                        username = await username_element.text_content()
                        
                        # Пытаемся получить ссылку на профиль для ID
                        user_link = await username_element.get_attribute('href')
                        if user_link and '/@' in user_link:
                            user_id = user_link.split('/@')[-1].split('?')[0]
                        
                        if username and username.strip():
                            break
                except:
                    continue
            
            # Валидация данных
            if not comment_text or not username:
                return None
            
            # Очистка данных
            comment_text = comment_text.strip()
            username = username.strip().replace('@', '')
            
            if not user_id:
                user_id = username
            
            return {
                'user_id': user_id,
                'username': username,
                'text': comment_text,
                'timestamp': datetime.now(),
                'platform': 'tiktok'
            }
            
        except Exception as e:
            logger.warning(f"Ошибка извлечения данных комментария: {e}")
            return None
    
    async def cleanup(self):
        """Очистка ресурсов браузера"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
                
            logger.info(f"Ресурсы браузера очищены для сценария {self.scenario.id}")
            
        except Exception as e:
            logger.error(f"Ошибка очистки ресурсов браузера: {e}")
        finally:
            if self.session:
                self.session.close()
    
    def __del__(self):
        """Деструктор для автоматической очистки"""
        try:
            if hasattr(self, 'session') and self.session:
                self.session.close()
        except:
            pass

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

async def test_tiktok_connection(proxy_server=None) -> bool:
    """Тестирование подключения к TikTok"""
    try:
        # Создаем временный сценарий для тестирования
        test_scenario = type('TestScenario', (), {
            'id': 'test',
            'proxy_server': proxy_server,
            'tiktok_username': 'test',
            'tiktok_password_encrypted': EncryptionService.encrypt_password('test')
        })()
        
        service = TikTokService(test_scenario)
        
        # Инициализируем браузер
        if not await service.init_browser():
            return False
        
        # Пробуем зайти на TikTok
        await service.page.goto('https://www.tiktok.com', timeout=15000)
        
        # Проверяем успешность загрузки
        title = await service.page.title()
        success = 'tiktok' in title.lower()
        
        await service.cleanup()
        return success
        
    except Exception as e:
        logger.error(f"Ошибка тестирования подключения к TikTok: {e}")
        return False

def validate_tiktok_video_url(url: str) -> bool:
    """Валидация URL TikTok видео"""
    valid_patterns = [
        'tiktok.com/@',
        'vm.tiktok.com/',
        'm.tiktok.com/@'
    ]
    
    return any(pattern in url for pattern in valid_patterns)

# === КОНФИГУРАЦИЯ ===

TIKTOK_CONFIG = {
    'max_comments_per_check': 50,
    'scroll_delay': (1, 3),
    'comment_processing_delay': (0.1, 0.3),
    'page_load_timeout': 30000,
    'auth_timeout': 30000,
    'retry_delay': (60, 180),
    'user_agent_rotation': True,
    'viewport_randomization': True
}