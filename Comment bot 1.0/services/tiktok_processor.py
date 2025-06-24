"""
Основной процессор для TikTok автоматизации
services/tiktok_processor.py - НОВЫЙ ФАЙЛ
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from telegram.ext import Application

from database.models import TikTokScenario, TikTokSentMessage, TikTokPendingMessage, TikTokAuthenticationLog
from database.connection import Session
from services.tiktok_service import TikTokService
from config import TELEGRAM_TOKEN, TIKTOK_MESSAGE_DELAY, tiktok_sessions, tiktok_tasks

logger = logging.getLogger(__name__)

async def process_tiktok_scenario(scenario_id: int, chat_id: int):
    """Основная функция обработки TikTok сценария"""
    session = Session()
    service = None
    
    try:
        # Получаем сценарий
        scenario = session.query(TikTokScenario).filter_by(id=scenario_id).first()
        if not scenario:
            logger.error(f"TikTok сценарий {scenario_id} не найден")
            return

        # Получаем бот
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        bot = app.bot

        logger.info(f"Запуск обработки TikTok сценария {scenario_id}")

        # Создаем сервис TikTok
        service = TikTokService(scenario)
        
        # Сохраняем сессию
        tiktok_sessions[scenario_id] = service

        # Отправляем уведомление о начале
        await bot.send_message(
            chat_id=chat_id,
            text=f"🎵 <b>Запуск TikTok сценария #{scenario_id}</b>\n\n"
                 f"📱 Аккаунт: @{scenario.tiktok_username}\n"
                 f"🎯 Триггер: <code>{scenario.trigger_word}</code>\n"
                 f"🌐 Прокси: {scenario.proxy_server.name if scenario.proxy_server else 'Без прокси'}\n\n"
                 f"⏳ Инициализация браузера...",
            parse_mode='HTML'
        )

        # Инициализация браузера
        if not await service.init_browser():
            scenario.auth_status = 'failed'
            scenario.error_message = 'Ошибка инициализации браузера'
            session.merge(scenario)
            session.commit()
            
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ <b>Ошибка TikTok сценария #{scenario_id}</b>\n\n"
                     f"Не удалось инициализировать браузер.\n"
                     f"Проверьте настройки Playwright.",
                parse_mode='HTML'
            )
            return

        # Авторизация
        await bot.send_message(
            chat_id=chat_id,
            text=f"🔐 <b>Авторизация в TikTok</b>\n\n"
                 f"📱 Аккаунт: @{scenario.tiktok_username}\n"
                 f"⏳ Выполняется вход...",
            parse_mode='HTML'
        )

        auth_success = await service.authenticate()
        
        if not auth_success:
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ <b>Ошибка авторизации TikTok #{scenario_id}</b>\n\n"
                     f"📱 Аккаунт: @{scenario.tiktok_username}\n"
                     f"🔴 Не удалось войти в аккаунт\n\n"
                     f"Возможные причины:\n"
                     f"• Неверный логин или пароль\n"
                     f"• Блокировка IP/прокси\n"
                     f"• Требуется проверка безопасности\n"
                     f"• Включена двухфакторная аутентификация",
                parse_mode='HTML'
            )
            return

        # Извлечение ID видео
        await bot.send_message(
            chat_id=chat_id,
            text=f"🎵 <b>Анализ TikTok видео</b>\n\n"
                 f"📱 Сценарий: #{scenario_id}\n"
                 f"🔗 Видео: {scenario.video_link[:50]}...\n"
                 f"⏳ Извлечение данных...",
            parse_mode='HTML'
        )

        video_id = await service.extract_video_id(scenario.video_link)
        if not video_id:
            scenario.error_message = 'Не удалось извлечь ID видео'
            session.merge(scenario)
            session.commit()
            
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ <b>Ошибка обработки видео</b>\n\n"
                     f"Не удалось извлечь ID из ссылки:\n"
                     f"{scenario.video_link}\n\n"
                     f"Проверьте корректность ссылки.",
                parse_mode='HTML'
            )
            return

        # Успешная инициализация
        await bot.send_message(
            chat_id=chat_id,
            text=f"✅ <b>TikTok сценарий #{scenario_id} запущен!</b>\n\n"
                 f"📱 Аккаунт: @{scenario.tiktok_username}\n"
                 f"🎵 Видео ID: {video_id}\n"
                 f"🎯 Триггер: <code>{scenario.trigger_word}</code>\n\n"
                 f"🔄 Начинается мониторинг комментариев...",
            parse_mode='HTML'
        )

        # Основной цикл мониторинга
        await run_tiktok_monitoring_loop(scenario, service, bot, chat_id)

    except asyncio.CancelledError:
        logger.info(f"TikTok сценарий {scenario_id} отменен")
    except Exception as e:
        logger.error(f"Критическая ошибка TikTok сценария {scenario_id}: {e}")
        
        try:
            app = Application.builder().token(TELEGRAM_TOKEN).build()
            bot = app.bot
            await bot.send_message(
                chat_id=chat_id,
                text=f"💥 <b>Критическая ошибка TikTok #{scenario_id}</b>\n\n"
                     f"Ошибка: {str(e)[:200]}\n\n"
                     f"Сценарий остановлен. Попробуйте перезапустить.",
                parse_mode='HTML'
            )
        except:
            pass
    finally:
        # Очистка ресурсов
        if service:
            await service.cleanup()
        
        if scenario_id in tiktok_sessions:
            del tiktok_sessions[scenario_id]
        
        if scenario_id in tiktok_tasks:
            del tiktok_tasks[scenario_id]
        
        session.close()

async def run_tiktok_monitoring_loop(scenario: TikTokScenario, service: TikTokService, bot, chat_id: int):
    """Основной цикл мониторинга TikTok комментариев"""
    check_count = 0
    
    while scenario.is_active and scenario.status == 'running':
        try:
            check_count += 1
            logger.info(f"TikTok проверка #{check_count} для сценария {scenario.id}")
            
            # Проверяем комментарии
            result = await check_tiktok_comments_internal(scenario, service)
            
            if result['success']:
                if result['new_messages'] > 0:
                    # Отправляем уведомление о новых триггерах
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"🎯 <b>Найдены новые триггеры!</b>\n\n"
                             f"📱 TikTok #{scenario.id}\n"
                             f"🔍 Найдено комментариев: {result['total_comments']}\n"
                             f"🎯 С триггером: {result['trigger_comments']}\n"
                             f"📩 Добавлено в очередь: {result['new_messages']}\n\n"
                             f"⏳ Начинается отправка сообщений...",
                        parse_mode='HTML'
                    )
                    
                    # Отправляем сообщения
                    send_result = await send_tiktok_messages_internal(scenario, service)
                    
                    if send_result['sent_count'] > 0:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"📩 <b>Сообщения отправлены!</b>\n\n"
                                 f"📱 TikTok #{scenario.id}\n"
                                 f"✅ Отправлено: {send_result['sent_count']}\n"
                                 f"❌ Ошибок: {send_result['failed_count']}\n"
                                 f"⏳ В очереди: {send_result['remaining_count']}",
                            parse_mode='HTML'
                        )
            
            # Обновляем время последней проверки
            scenario.last_comment_check = datetime.now()
            
            # Периодические уведомления о статусе (каждые 10 проверок)
            if check_count % 10 == 0:
                session = Session()
                try:
                    scenario = session.query(TikTokScenario).filter_by(id=scenario.id).first()
                    if scenario:
                        pending_count = session.query(TikTokPendingMessage).filter_by(scenario_id=scenario.id).count()
                        sent_count = session.query(TikTokSentMessage).filter_by(scenario_id=scenario.id).count()
                        
                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"📊 <b>Статус TikTok #{scenario.id}</b>\n\n"
                                 f"🔄 Проверок выполнено: {check_count}\n"
                                 f"📊 Обработано комментариев: {scenario.comments_processed}\n"
                                 f"📩 Отправлено сообщений: {sent_count}\n"
                                 f"⏳ В очереди: {pending_count}\n"
                                 f"🕐 Последняя проверка: {datetime.now().strftime('%H:%M:%S')}",
                            parse_mode='HTML'
                        )
                finally:
                    session.close()
            
            # Задержка между проверками (5-10 минут)
            delay = random.randint(300, 600)  
            logger.info(f"TikTok сценарий {scenario.id}: следующая проверка через {delay//60} минут")
            await asyncio.sleep(delay)
            
            # Обновляем сценарий из БД
            session = Session()
            try:
                scenario = session.query(TikTokScenario).filter_by(id=scenario.id).first()
                if not scenario or scenario.status != 'running':
                    logger.info(f"TikTok сценарий {scenario.id} остановлен или удален")
                    break
            finally:
                session.close()
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Ошибка в цикле мониторинга TikTok {scenario.id}: {e}")
            
            # Уведомляем об ошибке
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ <b>Ошибка мониторинга TikTok #{scenario.id}</b>\n\n"
                         f"Ошибка: {str(e)[:100]}\n"
                         f"Попытка восстановления через 10 минут...",
                    parse_mode='HTML'
                )
                
                # Задержка перед повторной попыткой
                await asyncio.sleep(600)  # 10 минут
                
            except:
                pass

async def check_tiktok_comments_internal(scenario: TikTokScenario, service: TikTokService) -> Dict:
    """Внутренняя функция проверки комментариев"""
    session = Session()
    
    try:
        logger.info(f"Проверка комментариев TikTok для сценария {scenario.id}")
        
        # Получаем комментарии
        comments = await service.get_comments(limit=50)
        
        if not comments:
            return {
                'success': True,
                'total_comments': 0,
                'trigger_comments': 0,
                'new_messages': 0
            }
        
        # Обрабатываем комментарии
        new_messages = 0
        trigger_comments = 0
        
        for comment in comments:
            # Проверяем триггерное слово
            if scenario.trigger_word.lower() in comment['text'].lower():
                trigger_comments += 1
                
                # Проверяем, не отправляли ли уже сообщение этому пользователю
                existing_message = session.query(TikTokSentMessage).filter_by(
                    scenario_id=scenario.id,
                    tiktok_user_id=comment['user_id']
                ).first()
                
                if not existing_message:
                    # Проверяем, нет ли уже в очереди
                    existing_pending = session.query(TikTokPendingMessage).filter_by(
                        scenario_id=scenario.id,
                        tiktok_user_id=comment['user_id']
                    ).first()
                    
                    if not existing_pending:
                        # Добавляем в очередь
                        pending_message = TikTokPendingMessage(
                            scenario_id=scenario.id,
                            tiktok_user_id=comment['user_id'],
                            tiktok_username=comment['username'],
                            message_text=scenario.dm_message,
                            comment_text=comment['text'][:500]  # Сохраняем оригинальный комментарий
                        )
                        session.add(pending_message)
                        new_messages += 1
                        
                        logger.info(f"Добавлен в очередь TikTok: {comment['username']} - {comment['text'][:50]}")
        
        # Обновляем статистику сценария
        scenario.comments_processed += len(comments)
        session.merge(scenario)
        session.commit()
        
        return {
            'success': True,
            'total_comments': len(comments),
            'trigger_comments': trigger_comments,
            'new_messages': new_messages
        }
        
    except Exception as e:
        logger.error(f"Ошибка проверки комментариев TikTok {scenario.id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'total_comments': 0,
            'trigger_comments': 0,
            'new_messages': 0
        }
    finally:
        session.close()

async def send_tiktok_messages_internal(scenario: TikTokScenario, service: TikTokService) -> Dict:
    """Внутренняя функция отправки сообщений"""
    session = Session()
    
    try:
        # Получаем сообщения из очереди (максимум 5 за раз)
        pending_messages = session.query(TikTokPendingMessage).filter_by(
            scenario_id=scenario.id
        ).limit(5).all()
        
        if not pending_messages:
            return {
                'sent_count': 0,
                'failed_count': 0,
                'remaining_count': 0
            }
        
        sent_count = 0
        failed_count = 0
        
        for pending in pending_messages:
            try:
                logger.info(f"Отправка TikTok сообщения пользователю {pending.tiktok_username}")
                
                # Отправляем сообщение
                success = await service.send_direct_message(
                    pending.tiktok_username, 
                    pending.message_text
                )
                
                if success:
                    # Добавляем в отправленные
                    sent_message = TikTokSentMessage(
                        scenario_id=scenario.id,
                        tiktok_user_id=pending.tiktok_user_id,
                        tiktok_username=pending.tiktok_username,
                        message_text=pending.message_text,
                        delivery_status='sent'
                    )
                    session.add(sent_message)
                    sent_count += 1
                    
                    logger.info(f"TikTok сообщение отправлено: {pending.tiktok_username}")
                else:
                    failed_count += 1
                    logger.warning(f"Не удалось отправить TikTok сообщение: {pending.tiktok_username}")
                
                # Удаляем из очереди в любом случае
                session.delete(pending)
                
                # Задержка между отправками (30-60 секунд)
                if pending != pending_messages[-1]:  # Не ждем после последнего
                    delay = random.randint(TIKTOK_MESSAGE_DELAY, TIKTOK_MESSAGE_DELAY * 2)
                    await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Ошибка отправки TikTok сообщения {pending.tiktok_username}: {e}")
                failed_count += 1
                session.delete(pending)  # Удаляем проблемное сообщение
                continue
        
        session.commit()
        
        # Подсчитываем оставшиеся сообщения
        remaining_count = session.query(TikTokPendingMessage).filter_by(
            scenario_id=scenario.id
        ).count()
        
        return {
            'sent_count': sent_count,
            'failed_count': failed_count,
            'remaining_count': remaining_count
        }
        
    except Exception as e:
        logger.error(f"Ошибка отправки TikTok сообщений {scenario.id}: {e}")
        session.rollback()
        return {
            'sent_count': 0,
            'failed_count': 0,
            'remaining_count': 0
        }
    finally:
        session.close()

# === ФУНКЦИИ ДЛЯ РУЧНОГО УПРАВЛЕНИЯ ===

async def check_tiktok_comments_task(scenario_id: int) -> Dict:
    """Ручная проверка комментариев TikTok"""
    session = Session()
    
    try:
        scenario = session.query(TikTokScenario).filter_by(id=scenario_id).first()
        if not scenario:
            return {'success': False, 'error': 'Сценарий не найден'}
        
        # Проверяем, есть ли активная сессия
        if scenario_id not in tiktok_sessions:
            # Создаем временную сессию
            service = TikTokService(scenario)
            
            if not await service.init_browser():
                return {'success': False, 'error': 'Ошибка инициализации браузера'}
            
            if not await service.authenticate():
                await service.cleanup()
                return {'success': False, 'error': 'Ошибка авторизации'}
            
            try:
                video_id = await service.extract_video_id(scenario.video_link)
                if not video_id:
                    return {'success': False, 'error': 'Не удалось извлечь ID видео'}
                
                result = await check_tiktok_comments_internal(scenario, service)
                return result
                
            finally:
                await service.cleanup()
        else:
            # Используем существующую сессию
            service = tiktok_sessions[scenario_id]
            return await check_tiktok_comments_internal(scenario, service)
            
    except Exception as e:
        logger.error(f"Ошибка ручной проверки TikTok комментариев {scenario_id}: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        session.close()

async def send_tiktok_messages_task(scenario_id: int) -> Dict:
    """Ручная отправка TikTok сообщений"""
    session = Session()
    
    try:
        scenario = session.query(TikTokScenario).filter_by(id=scenario_id).first()
        if not scenario:
            return {'sent_count': 0, 'failed_count': 0, 'remaining_count': 0}
        
        # Проверяем, есть ли активная сессия
        if scenario_id not in tiktok_sessions:
            # Создаем временную сессию
            service = TikTokService(scenario)
            
            if not await service.init_browser():
                return {'sent_count': 0, 'failed_count': 0, 'remaining_count': 0}
            
            if not await service.authenticate():
                await service.cleanup()
                return {'sent_count': 0, 'failed_count': 0, 'remaining_count': 0}
            
            try:
                result = await send_tiktok_messages_internal(scenario, service)
                return result
                
            finally:
                await service.cleanup()
        else:
            # Используем существующую сессию
            service = tiktok_sessions[scenario_id]
            return await send_tiktok_messages_internal(scenario, service)
            
    except Exception as e:
        logger.error(f"Ошибка ручной отправки TikTok сообщений {scenario_id}: {e}")
        return {'sent_count': 0, 'failed_count': 0, 'remaining_count': 0}
    finally:
        session.close()

# === УТИЛИТЫ ===

async def cleanup_tiktok_sessions():
    """Очистка неактивных TikTok сессий"""
    try:
        session = Session()
        
        # Находим неактивные сценарии
        inactive_scenarios = session.query(TikTokScenario).filter(
            TikTokScenario.status.in_(['stopped', 'paused'])
        ).all()
        
        for scenario in inactive_scenarios:
            if scenario.id in tiktok_sessions:
                service = tiktok_sessions[scenario.id]
                await service.cleanup()
                del tiktok_sessions[scenario.id]
                logger.info(f"Очищена TikTok сессия для сценария {scenario.id}")
        
        session.close()
        
    except Exception as e:
        logger.error(f"Ошибка очистки TikTok сессий: {e}")

async def get_tiktok_statistics() -> Dict:
    """Получение статистики TikTok"""
    session = Session()
    
    try:
        # Общая статистика
        total_scenarios = session.query(TikTokScenario).count()
        active_scenarios = session.query(TikTokScenario).filter_by(status='running').count()
        successful_auths = session.query(TikTokScenario).filter_by(auth_status='success').count()
        
        # Статистика сообщений
        total_sent = session.query(TikTokSentMessage).count()
        total_pending = session.query(TikTokPendingMessage).count()
        
        # Статистика за последние 24 часа
        yesterday = datetime.now() - timedelta(days=1)
        recent_sent = session.query(TikTokSentMessage).filter(
            TikTokSentMessage.sent_at >= yesterday
        ).count()
        
        # Самые активные сценарии
        top_scenarios = session.query(TikTokScenario).order_by(
            TikTokScenario.comments_processed.desc()
        ).limit(5).all()
        
        return {
            'total_scenarios': total_scenarios,
            'active_scenarios': active_scenarios,
            'successful_auths': successful_auths,
            'auth_success_rate': (successful_auths / total_scenarios * 100) if total_scenarios > 0 else 0,
            'total_sent_messages': total_sent,
            'pending_messages': total_pending,
            'messages_last_24h': recent_sent,
            'active_sessions': len(tiktok_sessions),
            'top_scenarios': [
                {
                    'id': s.id,
                    'username': s.tiktok_username,
                    'comments_processed': s.comments_processed
                } for s in top_scenarios
            ]
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения TikTok статистики: {e}")
        return {}
    finally:
        session.close()

# === ПЛАНИРОВЩИК ЗАДАЧ ===

async def scheduled_tiktok_cleanup():
    """Планируемая очистка TikTok ресурсов"""
    try:
        await cleanup_tiktok_sessions()
        
        # Удаляем старые логи авторизации (старше 30 дней)
        session = Session()
        try:
            old_date = datetime.now() - timedelta(days=30)
            old_logs = session.query(TikTokAuthenticationLog).filter(
                TikTokAuthenticationLog.created_at < old_date
            )
            deleted_count = old_logs.count()
            old_logs.delete()
            session.commit()
            
            if deleted_count > 0:
                logger.info(f"Удалено {deleted_count} старых TikTok логов авторизации")
                
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Ошибка планируемой очистки TikTok: {e}")

async def restart_failed_tiktok_scenarios():
    """Перезапуск неудачных TikTok сценариев"""
    session = Session()
    
    try:
        # Находим сценарии с неудачной авторизацией, которые можно перезапустить
        failed_scenarios = session.query(TikTokScenario).filter(
            TikTokScenario.auth_status == 'failed',
            TikTokScenario.status == 'running',
            TikTokScenario.auth_attempt < 3  # Максимум 3 попытки
        ).all()
        
        for scenario in failed_scenarios:
            try:
                # Увеличиваем счетчик попыток
                scenario.auth_attempt += 1
                scenario.auth_status = 'waiting'
                scenario.error_message = None
                session.merge(scenario)
                
                # Запускаем сценарий заново
                if scenario.id not in tiktok_tasks:
                    task = asyncio.create_task(
                        process_tiktok_scenario(scenario.id, scenario.user.telegram_id)
                    )
                    tiktok_tasks[scenario.id] = task
                    
                    logger.info(f"Перезапущен TikTok сценарий {scenario.id} (попытка {scenario.auth_attempt})")
                
            except Exception as e:
                logger.error(f"Ошибка перезапуска TikTok сценария {scenario.id}: {e}")
                continue
        
        session.commit()
        
    except Exception as e:
        logger.error(f"Ошибка автоматического перезапуска TikTok сценариев: {e}")
    finally:
        session.close()