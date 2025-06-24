"""
Сервис для работы с Instagram API через instagrapi
"""

import asyncio
import logging
import time
import random
from datetime import datetime, timedelta
from telegram.ext import Application

from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired, TwoFactorRequired

from database.models import Scenario, SentMessage, PendingMessage, RequestLog
from database.connection import Session
from services.encryption import EncryptionService
from services.proxy_manager import ProxyManager
from config import (
    TELEGRAM_TOKEN, MAX_ATTEMPTS, DELAY_BETWEEN_ATTEMPTS, CAPTCHA_TIMEOUT,
    MIN_ACTION_DELAY, MAX_ACTION_DELAY, INSTAGRAM_USER_AGENTS, DEVICE_SETTINGS,
    instabots, captcha_confirmed
)

logger = logging.getLogger(__name__)

class InstagramService:
    """Сервис для работы с Instagram"""
    
    @staticmethod
    def get_media_id_from_link(ig_bot: Client, link: str) -> str:
        """Извлечение ID поста из ссылки Instagram"""
        try:
            logger.info(f"Извлечение media_pk из ссылки: {link}")
            
            # Проверка формата ссылки
            if not link or 'instagram.com' not in link:
                raise ValueError("Некорректная ссылка Instagram")
            
            if '/p/' not in link and '/reel/' not in link:
                raise ValueError("Ссылка должна содержать /p/ или /reel/")
            
            media_pk = ig_bot.media_pk_from_url(link)
            logger.info(f"Успешно получен ID поста: {media_pk}")
            return media_pk
        except Exception as e:
            logger.error(f"Ошибка при получении ID поста: {e}")
            raise

    @staticmethod
    def setup_instagram_client(scenario: Scenario) -> Client:
        """Настройка клиента Instagram с прокси и антидетект"""
        ig_bot = Client()
        
        # Настройка прокси если назначен
        if scenario.proxy_server:
            proxy_dict = ProxyManager.get_proxy_dict(scenario.proxy_server)
            if proxy_dict:
                ig_bot.set_proxy(proxy_dict['http'])
                logger.info(f"Настроен прокси {scenario.proxy_server.name} для сценария {scenario.id}")
            else:
                logger.warning(f"Не удалось настроить прокси для сценария {scenario.id}")
        
        # Антидетект настройки
        user_agent = random.choice(INSTAGRAM_USER_AGENTS)
        device = random.choice(DEVICE_SETTINGS)
        
        ig_bot.set_user_agent(user_agent)
        ig_bot.set_device(device)
        
        return ig_bot

    @staticmethod
    async def authenticate_instagram(scenario: Scenario, bot, chat_id: int) -> bool:
        """Авторизация в Instagram с обработкой challenges"""
        session = Session()
        
        try:
            # Получение пароля
            password = EncryptionService.decrypt_password(scenario.ig_password_encrypted)
            
            # Создание клиента
            ig_bot = InstagramService.setup_instagram_client(scenario)
            
            # Попытки авторизации
            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    scenario.auth_attempt = attempt
                    session.merge(scenario)
                    session.commit()
                    
                    proxy_info = f" через {scenario.proxy_server.name}" if scenario.proxy_server else ""
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"🔄 <b>Авторизация {attempt}/{MAX_ATTEMPTS}</b>\n\n"
                             f"📱 Сценарий: #{scenario.id}\n"
                             f"👤 Аккаунт: @{scenario.ig_username}{proxy_info}",
                        parse_mode='HTML'
                    )
                    
                    logger.info(f"Попытка авторизации {attempt} для сценария {scenario.id}")
                    
                    # Попытка входа
                    ig_bot.login(username=scenario.ig_username, password=password)
                    
                    # Успешная авторизация
                    scenario.auth_status = 'success'
                    scenario.error_message = None
                    session.merge(scenario)
                    session.commit()
                    
                    instabots[scenario.id] = ig_bot
                    
                    proxy_status = f"🌐 Прокси: {scenario.proxy_server.name}" if scenario.proxy_server else "🌐 Прямое подключение"
                    
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"✅ <b>Авторизация успешна!</b>\n\n"
                             f"📱 Сценарий: #{scenario.id}\n"
                             f"👤 Аккаунт: @{scenario.ig_username}\n"
                             f"{proxy_status}\n"
                             f"🎯 Триггер: <code>{scenario.trigger_word}</code>\n\n"
                             f"🚀 Сценарий готов к работе!",
                        parse_mode='HTML'
                    )
                    
                    logger.info(f"Сценарий {scenario.id} успешно авторизован")
                    return True
                    
                except ChallengeRequired as e:
                    logger.warning(f"Challenge Required для сценария {scenario.id}")
                    scenario.error_message = "Требуется проверка безопасности Instagram"
                    session.merge(scenario)
                    session.commit()
                    
                    if attempt == 1:
                        # Показываем кнопку подтверждения
                        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                        keyboard = InlineKeyboardMarkup([[
                            InlineKeyboardButton(
                                "✅ Я прошел проверку", 
                                callback_data=f'captcha_confirmed_{scenario.id}'
                            )
                        ]])
                        
                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"🔐 <b>Требуется проверка безопасности</b>\n\n"
                                 f"📱 Сценарий: #{scenario.id} (@{scenario.ig_username})\n\n"
                                 f"<b>Что нужно сделать:</b>\n"
                                 f"1. Откройте Instagram в браузере или приложении\n"
                                 f"2. Войдите в аккаунт @{scenario.ig_username}\n"
                                 f"3. Пройдите проверку безопасности\n"
                                 f"4. Нажмите кнопку ниже\n\n"
                                 f"⏰ Время ожидания: {CAPTCHA_TIMEOUT//60} минут",
                            parse_mode='HTML',
                            reply_markup=keyboard
                        )
                        
                        # Ожидание подтверждения
                        start_time = time.time()
                        while time.time() - start_time < CAPTCHA_TIMEOUT:
                            if captcha_confirmed.get(scenario.id, False):
                                captcha_confirmed[scenario.id] = False
                                await bot.send_message(
                                    chat_id=chat_id,
                                    text=f"✅ Подтверждение получено. Повторная попытка входа..."
                                )
                                break
                            await asyncio.sleep(5)
                        
                        if not captcha_confirmed.get(scenario.id, False):
                            await bot.send_message(
                                chat_id=chat_id,
                                text=f"⏰ Время ожидания истекло для сценария #{scenario.id}.\n"
                                     "Сценарий остановлен. Попробуйте перезапустить позже."
                            )
                            scenario.status = 'stopped'
                            scenario.auth_status = 'failed'
                            session.merge(scenario)
                            session.commit()
                            return False
                    
                    elif attempt < MAX_ATTEMPTS:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"❌ Попытка {attempt} неудачна. Ожидание {DELAY_BETWEEN_ATTEMPTS//60} минут..."
                        )
                        await asyncio.sleep(DELAY_BETWEEN_ATTEMPTS)
                        
                except TwoFactorRequired as e:
                    logger.error(f"2FA требуется для сценария {scenario.id}")
                    scenario.auth_status = 'failed'
                    scenario.error_message = "Требуется двухфакторная аутентификация"
                    session.merge(scenario)
                    session.commit()
                    
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"❌ <b>Ошибка авторизации</b>\n\n"
                             f"📱 Сценарий: #{scenario.id}\n"
                             f"👤 Аккаунт: @{scenario.ig_username}\n\n"
                             f"🔐 Для аккаунта включена двухфакторная аутентификация.\n"
                             f"Отключите 2FA в настройках Instagram и перезапустите сценарий.",
                        parse_mode='HTML'
                    )
                    return False
                    
                except Exception as e:
                    logger.error(f"Ошибка авторизации {attempt} для сценария {scenario.id}: {e}")
                    scenario.error_message = str(e)[:500]  # Ограничиваем длину
                    session.merge(scenario)
                    session.commit()
                    
                    if attempt < MAX_ATTEMPTS:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"❌ <b>Ошибка авторизации</b>\n\n"
                                 f"📱 Сценарий: #{scenario.id}\n"
                                 f"⚠️ Ошибка: {str(e)[:100]}\n\n"
                                 f"🔄 Попытка {attempt + 1} через {DELAY_BETWEEN_ATTEMPTS//60} минут...",
                            parse_mode='HTML'
                        )
                        await asyncio.sleep(DELAY_BETWEEN_ATTEMPTS)
                    else:
                        scenario.auth_status = 'failed'
                        scenario.status = 'stopped'
                        session.merge(scenario)
                        session.commit()
                        
                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"❌ <b>Авторизация не удалась</b>\n\n"
                                 f"📱 Сценарий: #{scenario.id}\n"
                                 f"👤 Аккаунт: @{scenario.ig_username}\n\n"
                                 f"🔴 Все попытки исчерпаны.\n"
                                 f"Проверьте учетные данные и попробуйте позже.",
                            parse_mode='HTML'
                        )
                        return False
            
            return False
            
        finally:
            session.close()

    @staticmethod
    async def check_comments_for_scenario(scenario_id: int) -> dict:
        """Проверка комментариев для сценария"""
        session = Session()
        
        try:
            scenario = session.query(Scenario).filter_by(id=scenario_id).first()
            if not scenario or scenario.status != 'running':
                return {'success': False, 'message': 'Сценарий неактивен'}
                
            ig_bot = instabots.get(scenario_id)
            if not ig_bot:
                return {'success': False, 'message': 'Сессия Instagram неактивна'}
            
            # Проверка активности сессии
            try:
                ig_bot.user_id_from_username(scenario.ig_username)
            except LoginRequired:
                scenario.auth_status = 'failed'
                session.merge(scenario)
                session.commit()
                return {'success': False, 'message': 'Требуется повторная авторизация'}
                
            # Получ