"""
Улучшенная система авторизации Instagram с интерактивными элементами
services/enhanced_auth.py - НОВЫЙ ФАЙЛ
"""

import asyncio
import logging
import time
import random
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired, ChallengeRequired, TwoFactorRequired, 
    BadPassword, UserNotFound, RateLimitError, FeedbackRequired
)

from database.models import Scenario, ProxyServer
from database.connection import Session
from services.encryption import EncryptionService
from services.proxy_manager import ProxyManager
from config import instabots, captcha_confirmed, TELEGRAM_TOKEN

logger = logging.getLogger(__name__)

class ChallengeType(Enum):
    """Типы проверок Instagram"""
    UNKNOWN = "unknown"
    PHONE_SMS = "phone_sms"
    EMAIL = "email"
    DEVICE_CONFIRMATION = "device_confirmation"
    PHOTO_VERIFICATION = "photo_verification"
    SUSPICIOUS_LOGIN = "suspicious_login"

class AuthAttemptResult(Enum):
    """Результаты попыток авторизации"""
    SUCCESS = "success"
    CHALLENGE_REQUIRED = "challenge_required"
    TWO_FACTOR_REQUIRED = "two_factor_required"
    BAD_CREDENTIALS = "bad_credentials"
    RATE_LIMITED = "rate_limited"
    PROXY_ERROR = "proxy_error"
    UNKNOWN_ERROR = "unknown_error"

class AuthConfig:
    """Конфигурация авторизации"""
    FAST_RETRY_DELAY = 120  # 2 минуты вместо 7
    MAX_FAST_ATTEMPTS = 3   # Быстрые попытки
    SLOW_RETRY_DELAY = 420  # 7 минут для медленных попыток
    CHALLENGE_TIMEOUT = 1800  # 30 минут на решение challenge
    SMS_CODE_TIMEOUT = 300   # 5 минут на ввод SMS
    
    # Антидетект настройки
    WAIT_BEFORE_LOGIN = (3, 8)  # Случайная задержка перед входом
    WAIT_AFTER_CHALLENGE = (5, 15)  # Задержка после challenge
    
    # Прокси настройки
    AUTO_SWITCH_PROXY = True
    SAFE_MODE_NO_PROXY = True

class EnhancedInstagramAuth:
    """Улучшенная система авторизации Instagram"""
    
    def __init__(self, scenario: Scenario, bot, chat_id: int):
        self.scenario = scenario
        self.bot = bot
        self.chat_id = chat_id
        self.session = Session()
        
        # Состояние авторизации
        self.current_attempt = 0
        self.challenge_type = ChallengeType.UNKNOWN
        self.current_proxy = scenario.proxy_server
        self.ig_client = None
        self.message_id = None
        
        # Временные данные
        self.temp_data = {}
        
    async def authenticate(self) -> bool:
        """Главный метод авторизации с улучшенной логикой"""
        try:
            await self._send_auth_start_message()
            
            # Получаем пароль
            password = EncryptionService.decrypt_password(self.scenario.ig_password_encrypted)
            
            # Основной цикл авторизации
            for attempt in range(1, AuthConfig.MAX_FAST_ATTEMPTS + 1):
                self.current_attempt = attempt
                
                result = await self._attempt_login(password, attempt)
                
                if result == AuthAttemptResult.SUCCESS:
                    await self._handle_auth_success()
                    return True
                    
                elif result == AuthAttemptResult.CHALLENGE_REQUIRED:
                    challenge_result = await self._handle_challenge()
                    if challenge_result:
                        return True
                    # Если challenge не решен, пробуем с другим прокси
                    if not await self._try_switch_proxy():
                        break
                        
                elif result == AuthAttemptResult.TWO_FACTOR_REQUIRED:
                    await self._handle_2fa_error()
                    return False
                    
                elif result == AuthAttemptResult.BAD_CREDENTIALS:
                    await self._handle_bad_credentials()
                    return False
                    
                elif result == AuthAttemptResult.PROXY_ERROR:
                    if not await self._try_switch_proxy():
                        break
                    continue  # Пробуем сразу с новым прокси
                    
                elif result == AuthAttemptResult.RATE_LIMITED:
                    await self._handle_rate_limit()
                    break
                
                # Задержка между попытками
                if attempt < AuthConfig.MAX_FAST_ATTEMPTS:
                    await self._wait_with_options(attempt)
            
            # Если быстрые попытки не помогли, предлагаем медленный режим
            return await self._try_slow_mode(password)
            
        except Exception as e:
            logger.error(f"Критическая ошибка авторизации: {e}")
            await self._handle_critical_error(str(e))
            return False
            
        finally:
            self.session.close()
    
    async def _attempt_login(self, password: str, attempt: int) -> AuthAttemptResult:
        """Попытка входа в Instagram"""
        try:
            # Создаем/обновляем клиент
            self.ig_client = self._create_instagram_client()
            
            # Обновляем статус
            await self._update_auth_status(f"Попытка {attempt}/{AuthConfig.MAX_FAST_ATTEMPTS}")
            
            # Антидетект задержка
            wait_time = random.uniform(*AuthConfig.WAIT_BEFORE_LOGIN)
            await asyncio.sleep(wait_time)
            
            # Попытка входа
            self.ig_client.login(
                username=self.scenario.ig_username, 
                password=password
            )
            
            return AuthAttemptResult.SUCCESS
            
        except ChallengeRequired as e:
            logger.info(f"Challenge Required для сценария {self.scenario.id}")
            self.challenge_type = self._detect_challenge_type(str(e))
            return AuthAttemptResult.CHALLENGE_REQUIRED
            
        except TwoFactorRequired:
            return AuthAttemptResult.TWO_FACTOR_REQUIRED
            
        except (BadPassword, UserNotFound):
            return AuthAttemptResult.BAD_CREDENTIALS
            
        except RateLimitError:
            return AuthAttemptResult.RATE_LIMITED
            
        except Exception as e:
            error_str = str(e).lower()
            if 'proxy' in error_str or 'connection' in error_str:
                return AuthAttemptResult.PROXY_ERROR
            return AuthAttemptResult.UNKNOWN_ERROR
    
    async def _handle_2fa_error(self):
        """Обработка ошибки двухфакторной аутентификации"""
        self.scenario.auth_status = 'failed'
        self.scenario.error_message = "Требуется отключить 2FA"
        self.session.merge(self.scenario)
        self.session.commit()
        
        await self._update_message(
            f"🔐 <b>Двухфакторная аутентификация</b>\n\n"
            f"📱 Сценарий: #{self.scenario.id}\n"
            f"👤 Аккаунт: @{self.scenario.ig_username}\n\n"
            f"❌ Для работы бота необходимо отключить 2FA в настройках Instagram.\n\n"
            f"<b>Как отключить:</b>\n"
            f"1. Откройте Instagram → Настройки\n"
            f"2. Конфиденциальность → Двухфакторная аутентификация\n"
            f"3. Отключите все методы\n"
            f"4. Перезапустите сценарий",
            InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Перезапустить", callback_data=f'restart_{self.scenario.id}')
            ]])
        )
    
    async def _handle_bad_credentials(self):
        """Обработка неверных учетных данных"""
        self.scenario.auth_status = 'failed'
        self.scenario.error_message = "Неверный логин или пароль"
        self.scenario.status = 'stopped'
        self.session.merge(self.scenario)
        self.session.commit()
        
        await self._update_message(
            f"🚫 <b>Неверные учетные данные</b>\n\n"
            f"📱 Сценарий: #{self.scenario.id}\n"
            f"👤 Аккаунт: @{self.scenario.ig_username}\n\n"
            f"❌ Проверьте правильность логина и пароля.\n"
            f"Возможно, пароль был изменен.",
            InlineKeyboardMarkup([[
                InlineKeyboardButton("✏️ Изменить данные", callback_data=f'edit_credentials_{self.scenario.id}')
            ]])
        )
    
    async def _handle_rate_limit(self):
        """Обработка ограничения скорости"""
        self.scenario.auth_status = 'failed'
        self.scenario.error_message = "Превышен лимит запросов"
        self.session.merge(self.scenario)
        self.session.commit()
        
        await self._update_message(
            f"⚠️ <b>Превышен лимит запросов</b>\n\n"
            f"📱 Сценарий: #{self.scenario.id}\n"
            f"👤 Аккаунт: @{self.scenario.ig_username}\n\n"
            f"Instagram временно ограничил доступ.\n"
            f"Попробуйте позже или смените прокси.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Сменить прокси", callback_data=f'switch_proxy_{self.scenario.id}')],
                [InlineKeyboardButton("🛡️ Безопасный режим", callback_data=f'safe_mode_{self.scenario.id}')],
                [InlineKeyboardButton("⏰ Попробовать через час", callback_data=f'retry_later_{self.scenario.id}')]
            ])
        )
    
    async def _handle_challenge_timeout(self):
        """Обработка таймаута challenge"""
        await self._update_message(
            f"⏰ <b>Время ожидания истекло</b>\n\n"
            f"📱 Сценарий: #{self.scenario.id}\n"
            f"👤 Аккаунт: @{self.scenario.ig_username}\n\n"
            f"Проверка безопасности не была завершена вовремя.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data=f'restart_{self.scenario.id}')],
                [InlineKeyboardButton("🛡️ Безопасный режим", callback_data=f'safe_mode_{self.scenario.id}')]
            ])
        )
    
    async def _handle_critical_error(self, error: str):
        """Обработка критической ошибки"""
        self.scenario.auth_status = 'failed'
        self.scenario.error_message = error[:500]
        self.scenario.status = 'stopped'
        self.session.merge(self.scenario)
        self.session.commit()
        
        await self._update_message(
            f"💥 <b>Критическая ошибка</b>\n\n"
            f"📱 Сценарий: #{self.scenario.id}\n"
            f"👤 Аккаунт: @{self.scenario.ig_username}\n\n"
            f"❌ {error[:200]}...\n\n"
            f"Обратитесь к администратору.",
            InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Перезапустить", callback_data=f'restart_{self.scenario.id}')
            ]])
        )


# === ОБРАБОТЧИКИ CALLBACK'ов ===

async def handle_enhanced_auth_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback'ов для улучшенной авторизации"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    try:
        # Challenge подтверждения
        if data.startswith('challenge_confirmed_'):
            scenario_id = int(data.split('_')[-1])
            captcha_confirmed[f"challenge_{scenario_id}"] = True
            
        # SMS код запрос
        elif data.startswith('sms_requested_'):
            scenario_id = int(data.split('_')[-1])
            captcha_confirmed[f"sms_requested_{scenario_id}"] = True
            
        # Быстрый retry
        elif data.startswith('retry_now_'):
            scenario_id = int(data.split('_')[-1])
            captcha_confirmed[f"retry_now_{scenario_id}"] = True
            
        # Смена прокси
        elif data.startswith('switch_proxy_'):
            scenario_id = int(data.split('_')[-1])
            captcha_confirmed[f"switch_proxy_{scenario_id}"] = True
            
        # Безопасный режим
        elif data.startswith('safe_mode_'):
            scenario_id = int(data.split('_')[-1])
            captcha_confirmed[f"safe_mode_{scenario_id}"] = True
            
        # Медленный режим
        elif data.startswith('slow_mode_continue_'):
            scenario_id = int(data.split('_')[-1])
            captcha_confirmed[f"slow_mode_continue_{scenario_id}"] = True
            
        elif data.startswith('slow_mode_stop_'):
            scenario_id = int(data.split('_')[-1])
            captcha_confirmed[f"slow_mode_stop_{scenario_id}"] = True
            
        # Отмена SMS
        elif data.startswith('cancel_sms_'):
            scenario_id = int(data.split('_')[-1])
            await query.edit_message_text(
                "❌ Ввод SMS кода отменен.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад к challenge", callback_data=f'back_to_challenge_{scenario_id}')
                ]])
            )
            
    except Exception as e:
        logger.error(f"Ошибка обработки callback авторизации: {e}")
        await query.edit_message_text("❌ Ошибка обработки команды.")


# === ОБРАБОТЧИК SMS КОДОВ ===

async def handle_sms_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода SMS кодов"""
    if not update.message or not update.message.text:
        return
    
    # Проверяем, ожидается ли SMS код
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Проверяем формат SMS кода (обычно 6 цифр)
    if text.isdigit() and len(text) in [4, 5, 6, 8]:
        # Ищем активные сценарии пользователя, ожидающие SMS
        session = Session()
        try:
            from database.models import User, Scenario
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if user:
                active_scenarios = session.query(Scenario).filter_by(
                    user_id=user.id,
                    auth_status='waiting'
                ).all()
                
                # Если есть только один активный сценарий, применяем код к нему
                if len(active_scenarios) == 1:
                    scenario_id = active_scenarios[0].id
                    captcha_confirmed[f"sms_code_{scenario_id}"] = text
                    
                    await update.message.reply_text(
                        f"📱 SMS код <code>{text}</code> принят для сценария #{scenario_id}",
                        parse_mode='HTML'
                    )
                    return
                    
        finally:
            session.close()


# === ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА ===

async def run_enhanced_instagram_scenario(scenario_id: int, chat_id: int):
    """Запуск сценария с улучшенной авторизацией"""
    session = Session()
    try:
        scenario = session.query(Scenario).filter_by(id=scenario_id).first()
        if not scenario:
            logger.error(f"Сценарий {scenario_id} не найден")
            return
        
        # Получаем бот из приложения
        from telegram.ext import Application
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        bot = app.bot
        
        # Создаем экземпляр улучшенной авторизации
        auth_handler = EnhancedInstagramAuth(scenario, bot, chat_id)
        
        # Выполняем авторизацию
        auth_success = await auth_handler.authenticate()
        
        if auth_success:
            logger.info(f"Сценарий {scenario_id} успешно авторизован с улучшенной системой")
            # Здесь можно продолжить с основной логикой сценария
        else:
            logger.warning(f"Улучшенная авторизация сценария {scenario_id} не удалась")
            
    except Exception as e:
        logger.error(f"Ошибка запуска улучшенного сценария {scenario_id}: {e}")
    finally:
        session.close()


# === КОНФИГУРАЦИОННЫЕ ФУНКЦИИ ===

def set_auth_config(**kwargs):
    """Настройка параметров авторизации"""
    for key, value in kwargs.items():
        if hasattr(AuthConfig, key.upper()):
            setattr(AuthConfig, key.upper(), value)
            logger.info(f"Обновлен параметр авторизации: {key.upper()} = {value}")

def get_auth_config() -> dict:
    """Получение текущей конфигурации авторизации"""
    return {
        'fast_retry_delay': AuthConfig.FAST_RETRY_DELAY,
        'max_fast_attempts': AuthConfig.MAX_FAST_ATTEMPTS,
        'slow_retry_delay': AuthConfig.SLOW_RETRY_DELAY,
        'challenge_timeout': AuthConfig.CHALLENGE_TIMEOUT,
        'sms_code_timeout': AuthConfig.SMS_CODE_TIMEOUT,
        'auto_switch_proxy': AuthConfig.AUTO_SWITCH_PROXY,
        'safe_mode_no_proxy': AuthConfig.SAFE_MODE_NO_PROXY
    }


# === ПРЕДУСТАНОВКИ ===

PRESET_CONFIGS = {
    'aggressive': {
        'fast_retry_delay': 60,      # 1 минута
        'max_fast_attempts': 5,      # 5 быстрых попыток
        'auto_switch_proxy': True,
        'safe_mode_no_proxy': True
    },
    'balanced': {
        'fast_retry_delay': 120,     # 2 минуты (по умолчанию)
        'max_fast_attempts': 3,
        'auto_switch_proxy': True,
        'safe_mode_no_proxy': True
    },
    'conservative': {
        'fast_retry_delay': 300,     # 5 минут
        'max_fast_attempts': 2,
        'auto_switch_proxy': False,
        'safe_mode_no_proxy': False
    },
    'stealth': {
        'fast_retry_delay': 600,     # 10 минут
        'max_fast_attempts': 1,
        'auto_switch_proxy': True,
        'safe_mode_no_proxy': False
    }
}

def apply_auth_preset(preset_name: str) -> bool:
    """Применение предустановленной конфигурации"""
    if preset_name not in PRESET_CONFIGS:
        return False
    
    config = PRESET_CONFIGS[preset_name]
    set_auth_config(**config)
    
    logger.info(f"Применена предустановка авторизации: {preset_name}")
    return True


# === АДМИНСКИЕ ФУНКЦИИ ===

async def admin_auth_settings_menu(query):
    """Меню настроек авторизации для администраторов"""
    config = get_auth_config()
    
    text = (
        f"⚙️ <b>Настройки авторизации</b>\n\n"
        f"⚡ Быстрые попытки: {config['max_fast_attempts']}\n"
        f"⏰ Задержка (быстро): {config['fast_retry_delay']//60} мин\n"
        f"🐌 Задержка (медленно): {config['slow_retry_delay']//60} мин\n"
        f"🔐 Таймаут challenge: {config['challenge_timeout']//60} мин\n"
        f"📱 Таймаут SMS: {config['sms_code_timeout']//60} мин\n\n"
        f"🔄 Автосмена прокси: {'✅' if config['auto_switch_proxy'] else '❌'}\n"
        f"🛡️ Безопасный режим: {'✅' if config['safe_mode_no_proxy'] else '❌'}"
    )
    
    keyboard = [
        [InlineKeyboardButton("⚡ Быстрая настройка", callback_data='auth_quick_setup')],
        [InlineKeyboardButton("🔧 Детальные настройки", callback_data='auth_detailed_setup')],
        [InlineKeyboardButton("📊 Статистика авторизации", callback_data='auth_statistics')],
        [InlineKeyboardButton("🔄 Сбросить по умолчанию", callback_data='auth_reset_defaults')],
        [InlineKeyboardButton("🔙 Назад", callback_data='admin_panel')]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )challenge(self) -> bool:
        """Обработка Challenge Required с интерактивным интерфейсом"""
        try:
            challenge_info = self._get_challenge_info()
            keyboard = self._create_challenge_keyboard()
            
            await self._update_message(
                f"🔐 <b>Требуется проверка безопасности</b>\n\n"
                f"📱 Сценарий: #{self.scenario.id} (@{self.scenario.ig_username})\n"
                f"🔍 Тип проверки: {challenge_info['description']}\n\n"
                f"<b>📋 Инструкции:</b>\n{challenge_info['instructions']}\n\n"
                f"⏰ Время: {AuthConfig.CHALLENGE_TIMEOUT//60} минут",
                keyboard
            )
            
            # Ожидание действий пользователя
            return await self._wait_for_challenge_resolution()
            
        except Exception as e:
            logger.error(f"Ошибка обработки challenge: {e}")
            return False
    
    async def _wait_for_challenge_resolution(self) -> bool:
        """Ожидание решения challenge с интерактивными опциями"""
        start_time = time.time()
        
        while time.time() - start_time < AuthConfig.CHALLENGE_TIMEOUT:
            # Проверяем флаги состояния
            if captcha_confirmed.get(f"challenge_{self.scenario.id}", False):
                captcha_confirmed.pop(f"challenge_{self.scenario.id}", False)
                
                # Попытка повторного входа
                try:
                    password = EncryptionService.decrypt_password(self.scenario.ig_password_encrypted)
                    self.ig_client.login(self.scenario.ig_username, password)
                    
                    await self._handle_auth_success()
                    return True
                    
                except ChallengeRequired:
                    # Challenge все еще активен
                    await self._update_message(
                        "⚠️ <b>Проверка еще не завершена</b>\n\n"
                        "Попробуйте еще раз или переключитесь на безопасный режим.",
                        self._create_challenge_keyboard()
                    )
                    continue
                    
                except Exception as e:
                    await self._update_message(f"❌ Ошибка: {str(e)[:100]}")
                    return False
            
            # Проверяем запрос SMS кода
            if captcha_confirmed.get(f"sms_requested_{self.scenario.id}", False):
                captcha_confirmed.pop(f"sms_requested_{self.scenario.id}", False)
                return await self._handle_sms_input()
            
            # Проверяем переключение на безопасный режим
            if captcha_confirmed.get(f"safe_mode_{self.scenario.id}", False):
                captcha_confirmed.pop(f"safe_mode_{self.scenario.id}", False)
                return await self._try_safe_mode()
            
            await asyncio.sleep(5)
        
        # Таймаут
        await self._handle_challenge_timeout()
        return False
    
    async def _handle_sms_input(self) -> bool:
        """Обработка ввода SMS кода"""
        await self._update_message(
            "📱 <b>Ввод SMS кода</b>\n\n"
            "Введите код, полученный по SMS:",
            InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отменить", callback_data=f'cancel_sms_{self.scenario.id}')
            ]])
        )
        
        # Ожидание ввода кода
        start_time = time.time()
        while time.time() - start_time < AuthConfig.SMS_CODE_TIMEOUT:
            sms_code = captcha_confirmed.get(f"sms_code_{self.scenario.id}")
            if sms_code:
                captcha_confirmed.pop(f"sms_code_{self.scenario.id}", False)
                
                try:
                    # Попытка ввода кода
                    self.ig_client.challenge_code_handler(sms_code)
                    
                    # Повторная попытка входа
                    password = EncryptionService.decrypt_password(self.scenario.ig_password_encrypted)
                    self.ig_client.login(self.scenario.ig_username, password)
                    
                    await self._handle_auth_success()
                    return True
                    
                except Exception as e:
                    await self._update_message(
                        f"❌ Неверный код или ошибка: {str(e)[:100]}\n\n"
                        "Попробуйте еще раз или переключитесь на безопасный режим.",
                        self._create_challenge_keyboard()
                    )
                    return False
            
            await asyncio.sleep(2)
        
        await self._update_message(
            "⏰ Время ввода SMS кода истекло.",
            self._create_challenge_keyboard()
        )
        return False
    
    async def _try_safe_mode(self) -> bool:
        """Попытка авторизации в безопасном режиме (без прокси)"""
        if not AuthConfig.SAFE_MODE_NO_PROXY:
            return False
            
        await self._update_message(
            "🛡️ <b>Безопасный режим</b>\n\n"
            "Попытка авторизации без прокси..."
        )
        
        try:
            # Сохраняем текущий прокси
            original_proxy = self.current_proxy
            self.current_proxy = None
            
            # Создаем клиент без прокси
            self.ig_client = self._create_instagram_client()
            
            # Попытка входа
            password = EncryptionService.decrypt_password(self.scenario.ig_password_encrypted)
            self.ig_client.login(self.scenario.ig_username, password)
            
            # Обновляем сценарий
            self.scenario.proxy_id = None
            self.session.merge(self.scenario)
            self.session.commit()
            
            await self._handle_auth_success()
            return True
            
        except Exception as e:
            # Восстанавливаем прокси
            self.current_proxy = original_proxy
            await self._update_message(
                f"❌ Безопасный режим не помог: {str(e)[:100]}"
            )
            return False
    
    async def _try_switch_proxy(self) -> bool:
        """Попытка переключения на другой прокси"""
        if not AuthConfig.AUTO_SWITCH_PROXY:
            return False
            
        new_proxy = ProxyManager.get_best_proxy()
        if not new_proxy or new_proxy.id == (self.current_proxy.id if self.current_proxy else None):
            return False
        
        self.current_proxy = new_proxy
        self.scenario.proxy_id = new_proxy.id
        self.session.merge(self.scenario)
        self.session.commit()
        
        await self._update_message(
            f"🔄 <b>Переключение прокси</b>\n\n"
            f"Новый прокси: {new_proxy.name}\n"
            f"Повторная попытка авторизации..."
        )
        
        return True
    
    async def _wait_with_options(self, attempt: int):
        """Ожидание между попытками с интерактивными опциями"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ Попробовать сейчас", callback_data=f'retry_now_{self.scenario.id}')],
            [InlineKeyboardButton("🌐 Сменить прокси", callback_data=f'switch_proxy_{self.scenario.id}')],
            [InlineKeyboardButton("🛡️ Безопасный режим", callback_data=f'safe_mode_{self.scenario.id}')]
        ])
        
        await self._update_message(
            f"⏳ <b>Ожидание перед попыткой {attempt + 1}</b>\n\n"
            f"⏰ Автоматически через: {AuthConfig.FAST_RETRY_DELAY//60} мин\n\n"
            f"Или выберите действие:",
            keyboard
        )
        
        # Ожидание с проверкой флагов
        start_time = time.time()
        while time.time() - start_time < AuthConfig.FAST_RETRY_DELAY:
            if captcha_confirmed.get(f"retry_now_{self.scenario.id}", False):
                captcha_confirmed.pop(f"retry_now_{self.scenario.id}", False)
                return
                
            if captcha_confirmed.get(f"switch_proxy_{self.scenario.id}", False):
                captcha_confirmed.pop(f"switch_proxy_{self.scenario.id}", False)
                await self._try_switch_proxy()
                return
                
            if captcha_confirmed.get(f"safe_mode_{self.scenario.id}", False):
                captcha_confirmed.pop(f"safe_mode_{self.scenario.id}", False)
                await self._try_safe_mode()
                return
            
            await asyncio.sleep(5)
    
    async def _try_slow_mode(self, password: str) -> bool:
        """Медленный режим авторизации"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Продолжить", callback_data=f'slow_mode_continue_{self.scenario.id}')],
            [InlineKeyboardButton("❌ Остановить", callback_data=f'slow_mode_stop_{self.scenario.id}')]
        ])
        
        await self._update_message(
            f"🐌 <b>Переход в медленный режим</b>\n\n"
            f"Быстрые попытки не помогли.\n"
            f"Продолжить с задержкой {AuthConfig.SLOW_RETRY_DELAY//60} минут между попытками?",
            keyboard
        )
        
        # Ожидание решения
        start_time = time.time()
        while time.time() - start_time < 300:  # 5 минут на решение
            if captcha_confirmed.get(f"slow_mode_continue_{self.scenario.id}", False):
                captcha_confirmed.pop(f"slow_mode_continue_{self.scenario.id}", False)
                return await self._slow_auth_attempts(password)
                
            if captcha_confirmed.get(f"slow_mode_stop_{self.scenario.id}", False):
                captcha_confirmed.pop(f"slow_mode_stop_{self.scenario.id}", False)
                await self._handle_auth_stopped()
                return False
            
            await asyncio.sleep(5)
        
        # Таймаут - останавливаем
        await self._handle_auth_stopped()
        return False
    
    async def _slow_auth_attempts(self, password: str) -> bool:
        """Медленные попытки авторизации"""
        for attempt in range(1, 4):  # Еще 3 медленные попытки
            await self._update_message(
                f"🐌 <b>Медленная попытка {attempt}/3</b>\n\n"
                f"Попытка через длинную задержку..."
            )
            
            result = await self._attempt_login(password, attempt + AuthConfig.MAX_FAST_ATTEMPTS)
            
            if result == AuthAttemptResult.SUCCESS:
                await self._handle_auth_success()
                return True
            
            if attempt < 3:
                await asyncio.sleep(AuthConfig.SLOW_RETRY_DELAY)
        
        await self._handle_auth_failed()
        return False
    
    def _create_instagram_client(self) -> Client:
        """Создание клиента Instagram с настройками"""
        ig_bot = Client()
        
        # Настройка прокси
        if self.current_proxy:
            proxy_dict = ProxyManager.get_proxy_dict(self.current_proxy)
            if proxy_dict:
                ig_bot.set_proxy(proxy_dict['http'])
        
        # Антидетект настройки
        from config import INSTAGRAM_USER_AGENTS, DEVICE_SETTINGS
        user_agent = random.choice(INSTAGRAM_USER_AGENTS)
        device = random.choice(DEVICE_SETTINGS)
        
        ig_bot.set_user_agent(user_agent)
        ig_bot.set_device(device)
        
        return ig_bot
    
    def _detect_challenge_type(self, error_message: str) -> ChallengeType:
        """Определение типа проверки по сообщению об ошибке"""
        error_lower = error_message.lower()
        
        if 'phone' in error_lower or 'sms' in error_lower:
            return ChallengeType.PHONE_SMS
        elif 'email' in error_lower:
            return ChallengeType.EMAIL
        elif 'device' in error_lower:
            return ChallengeType.DEVICE_CONFIRMATION
        elif 'photo' in error_lower or 'selfie' in error_lower:
            return ChallengeType.PHOTO_VERIFICATION
        elif 'suspicious' in error_lower:
            return ChallengeType.SUSPICIOUS_LOGIN
        
        return ChallengeType.UNKNOWN
    
    def _get_challenge_info(self) -> Dict[str, str]:
        """Получение информации о типе проверки"""
        challenge_info = {
            ChallengeType.PHONE_SMS: {
                "description": "📱 SMS подтверждение",
                "instructions": (
                    "1. Откройте Instagram в браузере или приложении\n"
                    "2. Войдите в аккаунт (будет запрошен SMS код)\n"
                    "3. Введите код из SMS\n"
                    "4. Нажмите 'Готово' ниже\n\n"
                    "💡 Или используйте кнопку 'SMS код' для ввода прямо здесь"
                )
            },
            ChallengeType.EMAIL: {
                "description": "📧 Email подтверждение",
                "instructions": (
                    "1. Проверьте почту (включая спам)\n"
                    "2. Откройте письмо от Instagram\n"
                    "3. Следуйте инструкциям в письме\n"
                    "4. Нажмите 'Готово' после подтверждения"
                )
            },
            ChallengeType.DEVICE_CONFIRMATION: {
                "description": "📱 Подтверждение устройства",
                "instructions": (
                    "1. Откройте Instagram на телефоне\n"
                    "2. Подтвердите вход с нового устройства\n"
                    "3. Нажмите 'Готово' после подтверждения"
                )
            },
            ChallengeType.PHOTO_VERIFICATION: {
                "description": "📸 Фото верификация",
                "instructions": (
                    "1. Откройте Instagram\n"
                    "2. Сделайте селфи согласно инструкциям\n"
                    "3. Дождитесь одобрения (может занять время)\n"
                    "4. Используйте безопасный режим или другой аккаунт"
                )
            }
        }
        
        return challenge_info.get(
            self.challenge_type,
            {
                "description": "🔐 Проверка безопасности",
                "instructions": (
                    "1. Откройте Instagram\n"
                    "2. Войдите в аккаунт и пройдите проверку\n"
                    "3. Нажмите 'Готово' после завершения"
                )
            }
        )
    
    def _create_challenge_keyboard(self) -> InlineKeyboardMarkup:
        """Создание клавиатуры для challenge"""
        keyboard = [
            [InlineKeyboardButton("✅ Готово", callback_data=f'challenge_confirmed_{self.scenario.id}')]
        ]
        
        # Добавляем специальные кнопки для SMS
        if self.challenge_type == ChallengeType.PHONE_SMS:
            keyboard.insert(0, [InlineKeyboardButton("📱 Ввести SMS код", callback_data=f'sms_requested_{self.scenario.id}')])
        
        keyboard.extend([
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data=f'retry_now_{self.scenario.id}')],
            [InlineKeyboardButton("🛡️ Безопасный режим", callback_data=f'safe_mode_{self.scenario.id}')],
            [InlineKeyboardButton("🌐 Сменить прокси", callback_data=f'switch_proxy_{self.scenario.id}')]
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    async def _send_auth_start_message(self):
        """Отправка стартового сообщения авторизации"""
        proxy_info = f"🌐 {self.current_proxy.name}" if self.current_proxy else "🌐 Прямое подключение"
        
        message = await self.bot.send_message(
            chat_id=self.chat_id,
            text=f"🚀 <b>Улучшенная авторизация v2.0</b>\n\n"
                 f"📱 Сценарий: #{self.scenario.id}\n"
                 f"👤 Аккаунт: @{self.scenario.ig_username}\n"
                 f"{proxy_info}\n\n"
                 f"⚡ Быстрый режим: {AuthConfig.MAX_FAST_ATTEMPTS} попытки × {AuthConfig.FAST_RETRY_DELAY//60} мин\n"
                 f"🔄 Автосмена прокси: {'✅' if AuthConfig.AUTO_SWITCH_PROXY else '❌'}\n"
                 f"🛡️ Безопасный режим: {'✅' if AuthConfig.SAFE_MODE_NO_PROXY else '❌'}",
            parse_mode='HTML'
        )
        self.message_id = message.message_id
    
    async def _update_message(self, text: str, keyboard: InlineKeyboardMarkup = None):
        """Обновление сообщения"""
        try:
            await self.bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=self.message_id,
                text=text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка обновления сообщения: {e}")
    
    async def _update_auth_status(self, status: str):
        """Обновление статуса авторизации"""
        proxy_info = f"🌐 {self.current_proxy.name}" if self.current_proxy else "🌐 Прямое подключение"
        
        await self._update_message(
            f"🔄 <b>{status}</b>\n\n"
            f"📱 Сценарий: #{self.scenario.id}\n"
            f"👤 Аккаунт: @{self.scenario.ig_username}\n"
            f"{proxy_info}\n\n"
            f"⏳ Выполняется вход в Instagram..."
        )
    
    async def _handle_auth_success(self):
        """Обработка успешной авторизации"""
        # Сохраняем клиент
        instabots[self.scenario.id] = self.ig_client
        
        # Обновляем статус в БД
        self.scenario.auth_status = 'success'
        self.scenario.error_message = None
        self.session.merge(self.scenario)
        self.session.commit()
        
        proxy_status = f"🌐 {self.current_proxy.name}" if self.current_proxy else "🌐 Прямое подключение"
        
        await self._update_message(
            f"✅ <b>Авторизация успешна!</b>\n\n"
            f"📱 Сценарий: #{self.scenario.id}\n"
            f"👤 Аккаунт: @{self.scenario.ig_username}\n"
            f"{proxy_status}\n"
            f"🎯 Триггер: <code>{self.scenario.trigger_word}</code>\n"
            f"🕐 Попытка: {self.current_attempt}\n\n"
            f"🚀 Сценарий готов к работе!"
        )
    
    async def _handle_auth_failed(self):
        """Обработка неудачной авторизации"""
        self.scenario.auth_status = 'failed'
        self.scenario.status = 'stopped'
        self.session.merge(self.scenario)
        self.session.commit()
        
        await self._update_message(
            f"❌ <b>Авторизация не удалась</b>\n\n"
            f"📱 Сценарий: #{self.scenario.id}\n"
            f"👤 Аккаунт: @{self.scenario.ig_username}\n\n"
            f"🔴 Все попытки исчерпаны.\n"
            f"Проверьте учетные данные и попробуйте позже.",
            InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Перезапустить", callback_data=f'restart_{self.scenario.id}')
            ]])
        )
    
    async def _handle_auth_stopped(self):
        """Обработка остановки авторизации пользователем"""
        self.scenario.auth_status = 'failed'
        self.scenario.status = 'stopped'
        self.scenario.error_message = "Остановлено пользователем"
        self.session.merge(self.scenario)
        self.session.commit()
        
        await self._update_message(
            f"⏹️ <b>Авторизация остановлена</b>\n\n"
            f"📱 Сценарий: #{self.scenario.id}\n"
            f"👤 Аккаунт: @{self.scenario.ig_username}\n\n"
            f"Сценарий приостановлен по запросу пользователя.",
            InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Перезапустить", callback_data=f'restart_{self.scenario.id}')
            ]])
        )
    
    async def _handle_