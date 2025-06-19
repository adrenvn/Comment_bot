"""
Основные обработчики callback запросов (нажатий кнопок)
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from utils.validators import is_admin, is_user
from ui.menus import main_menu, admin_menu, scenarios_menu
from handlers.scenarios import (
    start_scenario_creation, show_user_scenarios, handle_proxy_choice,
    show_proxy_selection, select_proxy_for_scenario, handle_duration_selection,
    confirm_scenario_creation, show_scenario_management
)
from handlers.proxy import (
    manage_proxies_menu, start_add_proxy, list_proxies, check_all_proxies,
    show_proxy_stats, handle_proxy_type_selection, create_proxy_server,
    delete_proxy_server, check_single_proxy, manage_single_proxy
)
from handlers.proxy_import import (
    show_import_menu, show_providers_menu, start_922proxy_import,
    start_text_import, start_provider_import, bulk_proxy_operations,
    auto_rotate_proxies, bulk_check_proxies, cleanup_failed_proxies,
    confirm_cleanup_proxies, export_proxies, process_proxy_export,
    test_proxy_with_instagram
)

logger = logging.getLogger(__name__)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Основной обработчик нажатий кнопок"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data

    # Проверка доступа
    if not is_admin(user_id) and not is_user(user_id):
        await query.edit_message_text("🚫 У вас нет доступа к боту.")
        return

    is_admin_user = is_admin(user_id)
    is_user_user = is_user(user_id)

    try:
        # === ОСНОВНАЯ НАВИГАЦИЯ ===
        if data == 'back':
            await query.edit_message_text(
                "🏠 Главное меню:",
                reply_markup=main_menu(is_admin_user, is_user_user)
            )
        elif data == 'scenarios_menu':
            await query.edit_message_text(
                "📂 Управление сценариями:",
                reply_markup=scenarios_menu()
            )
        elif data == 'admin_panel':
            if is_admin_user:
                await query.edit_message_text(
                    "👑 Панель администратора:",
                    reply_markup=admin_menu()
                )
            else:
                await query.edit_message_text("🚫 У вас нет доступа к админ-панели.")
        
        # === УПРАВЛЕНИЕ ПРОКСИ ===
        elif data == 'manage_proxies':
            await manage_proxies_menu(query)
        elif data == 'add_proxy':
            await start_add_proxy(query, context)
        elif data == 'list_proxies':
            await list_proxies(query)
        elif data == 'check_all_proxies':
            await check_all_proxies(query)
        elif data == 'proxy_stats':
            await show_proxy_stats(query)
        elif data.startswith('proxy_type_'):
            proxy_type = data.split('_')[2]
            await handle_proxy_type_selection(query, context, proxy_type)
        elif data == 'confirm_proxy':
            await create_proxy_server(query, context)
        elif data.startswith('delete_proxy_'):
            proxy_id = int(data.split('_')[2])
            await delete_proxy_server(query, proxy_id)
        elif data.startswith('check_proxy_'):
            proxy_id = int(data.split('_')[2])
            await check_single_proxy(query, proxy_id)
        elif data.startswith('manage_proxy_'):
            proxy_id = int(data.split('_')[2])
            await manage_single_proxy(query, proxy_id)
        elif data.startswith('test_proxy_instagram_'):
            proxy_id = int(data.split('_')[3])
            await test_proxy_with_instagram(query, proxy_id)
        
        # === ИМПОРТ ПРОКСИ ===
        elif data == 'import_menu':
            await show_import_menu(query)
        elif data == 'import_providers':
            await show_providers_menu(query)
        elif data == 'import_922proxy':
            await start_922proxy_import(query, context)
        elif data == 'import_from_text':
            await start_text_import(query, context)
        elif data.startswith('import_provider_'):
            provider = data.split('_')[2]
            await start_provider_import(query, context, provider)
        
        # === МАССОВЫЕ ОПЕРАЦИИ С ПРОКСИ ===
        elif data == 'bulk_operations':
            await bulk_proxy_operations(query)
        elif data == 'auto_rotate_proxies':
            await auto_rotate_proxies(query)
        elif data == 'bulk_check_proxies':
            await bulk_check_proxies(query)
        elif data == 'cleanup_failed_proxies':
            await cleanup_failed_proxies(query)
        elif data == 'confirm_cleanup_proxies':
            await confirm_cleanup_proxies(query)
        
        # === ЭКСПОРТ ПРОКСИ ===
        elif data == 'export_proxies':
            await export_proxies(query)
        elif data.startswith('export_'):
            await process_proxy_export(query, data)
        
        # === СЦЕНАРИИ ===
        elif data == 'add_scenario':
            await start_scenario_creation(query, context, user_id)
        elif data == 'my_scenarios':
            await show_user_scenarios(query, user_id)
        elif data.startswith('manage_'):
            scenario_id = int(data.split("_")[1])
            await show_scenario_management(query, scenario_id, user_id)
        
        # === ВЫБОР ПРОКСИ ДЛЯ СЦЕНАРИЯ ===
        elif data == 'choose_proxy':
            await show_proxy_selection(query, context)
        elif data == 'no_proxy':
            await handle_proxy_choice(query, context)
        elif data.startswith('select_proxy_'):
            proxy_id = int(data.split("_")[2])
            await select_proxy_for_scenario(query, context, proxy_id)
        
        # === СОЗДАНИЕ СЦЕНАРИЯ ===
        elif data == 'confirm_scenario':
            await confirm_scenario_creation(query, context)
        elif data in ['1d', '3d', '7d', '14d', '30d']:
            await handle_duration_selection(query, context, data)
        
        # === УПРАВЛЕНИЕ СЦЕНАРИЯМИ ===
        elif data.startswith('check_comments_'):
            scenario_id = int(data.split("_")[2])
            await check_scenario_comments(query, scenario_id, user_id)
        elif data.startswith('send_messages_'):
            scenario_id = int(data.split("_")[2])
            await send_pending_messages(query, scenario_id, user_id)
        elif data.startswith('schedule_check_'):
            scenario_id = int(data.split("_")[2])
            await show_schedule_menu(query, scenario_id)
        elif data.startswith('set_timer_'):
            parts = data.split("_")
            minutes = int(parts[2])
            scenario_id = int(parts[3])
            await set_check_timer(query, minutes, scenario_id)
        elif data.startswith('pause_'):
            scenario_id = int(data.split("_")[1])
            await pause_scenario(query, scenario_id, user_id)
        elif data.startswith('resume_'):
            scenario_id = int(data.split("_")[1])
            await resume_scenario(query, scenario_id, user_id)
        elif data.startswith('restart_'):
            scenario_id = int(data.split("_")[1])
            await restart_scenario(query, scenario_id, user_id)
        elif data.startswith('delete_'):
            scenario_id = int(data.split("_")[1])
            await delete_scenario(query, scenario_id, user_id)
        elif data.startswith('captcha_confirmed_'):
            scenario_id = int(data.split('_')[-1])
            from config import captcha_confirmed
            captcha_confirmed[scenario_id] = True
            await query.edit_message_text("✅ Подтверждение получено. Повторная попытка входа...")
        
        # === АДМИНСКИЕ ФУНКЦИИ ===
        elif data == 'manage_users':
            await show_manage_users_info(query)
        elif data == 'manage_admins':
            await show_manage_admins_info(query)
        elif data == 'status_scenarios':
            if is_admin_user:
                await show_scenarios_status(query)
        elif data == 'all_scenarios':
            if is_admin_user:
                await show_all_scenarios(query)
        
        # === ПОМОЩЬ ===
        elif data == 'help':
            await show_help_info(query)
        
        # === ИНФОРМАЦИОННЫЕ КНОПКИ ===
        elif data == 'noop':
            pass  # Ничего не делаем для информационных кнопок

    except Exception as e:
        logger.error(f"Ошибка в обработчике кнопок: {e}")
        await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")

# === ФУНКЦИИ УПРАВЛЕНИЯ СЦЕНАРИЯМИ ===

async def check_scenario_comments(query, scenario_id, user_id):
    """Проверка комментариев для сценария"""
    from services.instagram import InstagramService
    from database.models import Scenario, RequestLog
    from database.connection import Session
    from config import MAX_REQUESTS_PER_HOUR
    from datetime import timedelta
    
    session = Session()
    try:
        scenario = session.query(Scenario).filter_by(id=scenario_id).first()
        if not scenario:
            await query.edit_message_text("❌ Сценарий не найден.")
            return
            
        # Проверка прав доступа
        if scenario.user.telegram_id != user_id and not is_admin(user_id):
            await query.edit_message_text("🚫 У вас нет доступа к этому сценарию.")
            return

        # Проверки перед выполнением
        if scenario.auth_status != 'success':
            await query.edit_message_text(
                "❌ <b>Сценарий не авторизован</b>\n\n"
                "Перезапустите сценарий для повторной авторизации.",
                parse_mode='HTML',
                reply_markup=show_scenario_management_menu(scenario_id)
            )
            return

        if scenario.status != 'running':
            await query.edit_message_text(
                "❌ <b>Сценарий неактивен</b>\n\n"
                "Возобновите работу сценария.",
                parse_mode='HTML',
                reply_markup=show_scenario_management_menu(scenario_id)
            )
            return

        # Проверка лимита запросов
        hour_ago = datetime.now() - timedelta(hours=1)
        requests_count = session.query(RequestLog).filter(
            RequestLog.scenario_id == scenario_id,
            RequestLog.request_time >= hour_ago
        ).count()
        
        if requests_count >= MAX_REQUESTS_PER_HOUR:
            await query.edit_message_text(
                f"⚠️ <b>Превышен лимит запросов</b>\n\n"
                f"Лимит: {MAX_REQUESTS_PER_HOUR} запросов в час\n"
                f"Использовано: {requests_count}\n\n"
                f"Попробуйте позже.",
                parse_mode='HTML',
                reply_markup=show_scenario_management_menu(scenario_id)
            )
            return

        await query.edit_message_text("🔍 Проверяю комментарии...")

        # Выполнение проверки
        result = await InstagramService.check_comments_for_scenario(scenario_id)
        
        if result['success']:
            result_text = (
                f"✅ <b>Проверка завершена</b>\n\n"
                f"📊 Проверено комментариев: {result['processed']}\n"
                f"🎯 Найдено с триггером: {result['new_found']}\n"
                f"📈 Всего обработано: {result['total_processed']}\n"
                f"🕐 Запросов за час: {requests_count + 1}/{MAX_REQUESTS_PER_HOUR}"
            )
        else:
            result_text = f"❌ <b>Ошибка проверки</b>\n\n{result['message']}"
        
        await query.edit_message_text(
            result_text,
            parse_mode='HTML',
            reply_markup=show_scenario_management_menu(scenario_id)
        )
        
    finally:
        session.close()

async def send_pending_messages(query, scenario_id, user_id):
    """Отправка ожидающих сообщений"""
    from services.instagram import InstagramService
    from database.models import Scenario
    from database.connection import Session
    
    session = Session()
    try:
        scenario = session.query(Scenario).filter_by(id=scenario_id).first()
        if not scenario:
            await query.edit_message_text("❌ Сценарий не найден.")
            return
            
        # Проверка прав доступа
        if scenario.user.telegram_id != user_id and not is_admin(user_id):
            await query.edit_message_text("🚫 У вас нет доступа к этому сценарию.")
            return

        if scenario.auth_status != 'success':
            await query.edit_message_text(
                "❌ Сценарий не авторизован.",
                reply_markup=show_scenario_management_menu(scenario_id)
            )
            return

        if scenario.status != 'running':
            await query.edit_message_text(
                "❌ Сценарий неактивен.",
                reply_markup=show_scenario_management_menu(scenario_id)
            )
            return

        await query.edit_message_text("📩 Начинаю отправку сообщений...")

        # Выполнение отправки
        result = await InstagramService.send_pending_messages_for_scenario(scenario_id)
        
        if result['success']:
            result_text = (
                f"✅ <b>Отправка завершена</b>\n\n"
                f"📤 Отправлено: {result['sent']} сообщений\n"
            )
            if result['errors'] > 0:
                result_text += f"❌ Ошибок: {result['errors']}\n"
            if result['remaining'] > 0:
                result_text += f"⏳ Осталось в очереди: {result['remaining']}"
        else:
            result_text = f"❌ <b>Ошибка отправки</b>\n\n{result['message']}"

        await query.edit_message_text(
            result_text,
            parse_mode='HTML',
            reply_markup=show_scenario_management_menu(scenario_id)
        )
        
    finally:
        session.close()

async def show_schedule_menu(query, scenario_id):
    """Показ меню планирования проверки"""
    from ui.menus import schedule_check_menu
    
    await query.edit_message_text(
        "⏰ <b>Планирование автоматической проверки</b>\n\n"
        "Выберите время для следующей проверки комментариев:",
        parse_mode='HTML',
        reply_markup=schedule_check_menu(scenario_id)
    )

async def set_check_timer(query, minutes, scenario_id):
    """Установка таймера проверки"""
    from database.models import Scenario
    from database.connection import Session
    from datetime import timedelta
    
    session = Session()
    try:
        scenario = session.query(Scenario).filter_by(id=scenario_id).first()
        if not scenario:
            await query.edit_message_text("❌ Сценарий не найден.")
            return
            
        next_check = datetime.now() + timedelta(minutes=minutes)
        scenario.next_check_time = next_check
        session.merge(scenario)
        session.commit()
        
        await query.edit_message_text(
            f"✅ <b>Проверка запланирована</b>\n\n"
            f"🕐 Время: {next_check.strftime('%d.%m.%Y %H:%M')}\n"
            f"⏳ Через: {minutes} минут",
            parse_mode='HTML',
            reply_markup=show_scenario_management_menu(scenario_id)
        )
        
        logger.info(f"Запланирована проверка сценария {scenario_id} на {next_check}")
        
    except Exception as e:
        logger.error(f"Ошибка планирования проверки: {e}")
        await query.edit_message_text("❌ Ошибка при планировании проверки.")
    finally:
        session.close()

async def pause_scenario(query, scenario_id, user_id):
    """Приостановка сценария"""
    from database.models import Scenario
    from database.connection import Session
    
    session = Session()
    try:
        scenario = session.query(Scenario).filter_by(id=scenario_id).first()
        if not scenario:
            await query.edit_message_text("❌ Сценарий не найден.")
            return
            
        if scenario.user.telegram_id != user_id and not is_admin(user_id):
            await query.edit_message_text("🚫 У вас нет доступа к этому сценарию.")
            return
            
        if scenario.status == 'running':
            scenario.status = 'paused'
            session.merge(scenario)
            session.commit()
            
            await query.edit_message_text(
                "⏸️ <b>Сценарий приостановлен</b>\n\n"
                "Все автоматические операции остановлены.",
                parse_mode='HTML',
                reply_markup=show_scenario_management_menu(scenario_id)
            )
            logger.info(f"Сценарий {scenario_id} приостановлен пользователем {user_id}")
        else:
            await query.edit_message_text(
                "❌ Сценарий уже неактивен.",
                reply_markup=show_scenario_management_menu(scenario_id)
            )
    finally:
        session.close()

async def resume_scenario(query, scenario_id, user_id):
    """Возобновление сценария"""
    from database.models import Scenario
    from database.connection import Session
    
    session = Session()
    try:
        scenario = session.query(Scenario).filter_by(id=scenario_id).first()
        if not scenario:
            await query.edit_message_text("❌ Сценарий не найден.")
            return
            
        if scenario.user.telegram_id != user_id and not is_admin(user_id):
            await query.edit_message_text("🚫 У вас нет доступа к этому сценарию.")
            return
            
        if scenario.status == 'paused':
            scenario.status = 'running'
            session.merge(scenario)
            session.commit()
            
            await query.edit_message_text(
                "▶️ <b>Сценарий возобновлен</b>\n\n"
                "Автоматические операции восстановлены.",
                parse_mode='HTML',
                reply_markup=show_scenario_management_menu(scenario_id)
            )
            logger.info(f"Сценарий {scenario_id} возобновлен пользователем {user_id}")
        else:
            await query.edit_message_text(
                "❌ Сценарий не приостановлен.",
                reply_markup=show_scenario_management_menu(scenario_id)
            )
    finally:
        session.close()

async def restart_scenario(query, scenario_id, user_id):
    """Перезапуск сценария"""
    from database.models import Scenario
    from database.connection import Session
    from config import tasks, instabots
    import asyncio
    
    session = Session()
    try:
        scenario = session.query(Scenario).filter_by(id=scenario_id).first()
        if not scenario:
            await query.edit_message_text("❌ Сценарий не найден.")
            return
            
        if scenario.user.telegram_id != user_id and not is_admin(user_id):
            await query.edit_message_text("🚫 У вас нет доступа к этому сценарию.")
            return

        # Остановка старой задачи если есть
        if scenario_id in tasks:
            tasks[scenario_id].cancel()
            del tasks[scenario_id]
            
        if scenario_id in instabots:
            try:
                instabots[scenario_id].logout()
            except:
                pass
            del instabots[scenario_id]

        # Сброс состояния
        scenario.status = 'running'
        scenario.auth_status = 'waiting'
        scenario.auth_attempt = 1
        scenario.error_message = None
        session.merge(scenario)
        session.commit()

        # Запуск новой задачи
        from services.instagram import run_instagram_scenario
        tasks[scenario_id] = asyncio.create_task(
            run_instagram_scenario(scenario_id, query.message.chat_id)
        )
        
        await query.edit_message_text(
            "🔄 <b>Сценарий перезапущен</b>\n\n"
            "Начинается повторная авторизация в Instagram...",
            parse_mode='HTML',
            reply_markup=show_scenario_management_menu(scenario_id)
        )
        logger.info(f"Сценарий {scenario_id} перезапущен пользователем {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка перезапуска сценария: {e}")
        await query.edit_message_text("❌ Ошибка при перезапуске сценария.")
    finally:
        session.close()

async def delete_scenario(query, scenario_id, user_id):
    """Удаление сценария"""
    from database.models import Scenario
    from database.connection import Session
    from config import tasks, instabots
    
    session = Session()
    try:
        scenario = session.query(Scenario).filter_by(id=scenario_id).first()
        if not scenario:
            await query.edit_message_text("❌ Сценарий не найден.")
            return
            
        if scenario.user.telegram_id != user_id and not is_admin(user_id):
            await query.edit_message_text("🚫 У вас нет доступа к этому сценарию.")
            return

        # Остановка задачи
        if scenario_id in tasks:
            tasks[scenario_id].cancel()
            del tasks[scenario_id]
            
        if scenario_id in instabots:
            try:
                instabots[scenario_id].logout()
            except:
                pass
            del instabots[scenario_id]

        # Удаление из базы
        session.delete(scenario)
        session.commit()
        
        await query.edit_message_text(
            f"🗑️ <b>Сценарий #{scenario_id} удален</b>\n\n"
            f"Все связанные данные очищены.",
            parse_mode='HTML',
            reply_markup=scenarios_menu()
        )
        logger.info(f"Сценарий {scenario_id} удален пользователем {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка удаления сценария: {e}")
        await query.edit_message_text("❌ Ошибка при удалении сценария.")
    finally:
        session.close()

# === АДМИНСКИЕ ФУНКЦИИ ===

async def show_manage_users_info(query):
    """Показ информации об управлении пользователями"""
    await query.edit_message_text(
        "👥 <b>Управление пользователями</b>\n\n"
        "Доступные команды:\n\n"
        "• <code>/adduser [Telegram ID]</code>\n"
        "  Добавить нового пользователя\n\n"
        "• <code>/deleteuser [Telegram ID]</code>\n"
        "  Удалить пользователя и все его сценарии\n\n"
        "<b>Примеры:</b>\n"
        "• <code>/adduser 123456789</code>\n"
        "• <code>/deleteuser 987654321</code>\n\n"
        "⚠️ <i>Будьте осторожны при удалении пользователей - все их данные будут потеряны</i>",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Назад", callback_data='admin_panel')
        ]])
    )

async def show_manage_admins_info(query):
    """Показ информации об управлении администраторами"""
    await query.edit_message_text(
        "👑 <b>Управление администраторами</b>\n\n"
        "Доступная команда:\n\n"
        "• <code>/addadmin [Telegram ID]</code>\n"
        "  Добавить нового администратора\n\n"
        "<b>Пример:</b>\n"
        "• <code>/addadmin 123456789</code>\n\n"
        "ℹ️ <i>Новый администратор автоматически получает права пользователя</i>\n"
        "⚠️ <i>Удаление администраторов пока недоступно через команды</i>",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Назад", callback_data='admin_panel')
        ]])
    )

async def show_scenarios_status(query):
    """Показ статистики сценариев для админов"""
    from database.models import Scenario, User
    from database.connection import Session
    
    session = Session()
    try:
        scenarios = session.query(Scenario).all()
        if not scenarios:
            await query.edit_message_text(
                "📭 Активных сценариев нет.",
                reply_markup=admin_menu()
            )
            return
            
        text = "📊 <b>Глобальная статистика сценариев:</b>\n\n"
        
        # Статистика по статусам
        running = session.query(Scenario).filter_by(status='running').count()
        paused = session.query(Scenario).filter_by(status='paused').count()
        stopped = session.query(Scenario).filter_by(status='stopped').count()
        
        # Статистика авторизации
        auth_success = session.query(Scenario).filter_by(auth_status='success').count()
        auth_failed = session.query(Scenario).filter_by(auth_status='failed').count()
        auth_waiting = session.query(Scenario).filter_by(auth_status='waiting').count()
        
        # Пользователи
        total_users = session.query(User).count()
        active_users = session.query(User).join(Scenario).filter(
            Scenario.status == 'running'
        ).distinct().count()
        
        text += (
            f"<b>📊 По статусам:</b>\n"
            f"🟢 Активных: {running}\n"
            f"⏸️ Приостановлено: {paused}\n"
            f"🔴 Остановлено: {stopped}\n\n"
            f"<b>🔐 Авторизация:</b>\n"
            f"✅ Успешно: {auth_success}\n"
            f"❌ Ошибки: {auth_failed}\n"
            f"⏳ Ожидание: {auth_waiting}\n\n"
            f"<b>👥 Пользователи:</b>\n"
            f"• Всего: {total_users}\n"
            f"• С активными сценариями: {active_users}\n\n"
        )
        
        # Топ активных сценариев
        top_scenarios = session.query(Scenario).filter_by(
            status='running'
        ).order_by(Scenario.comments_processed.desc()).limit(5).all()
        
        if top_scenarios:
            text += f"<b>🔥 Топ активных сценариев:</b>\n"
            for i, scenario in enumerate(top_scenarios, 1):
                text += f"{i}. #{scenario.id} @{scenario.ig_username} - {scenario.comments_processed} комм.\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data='status_scenarios')],
            [InlineKeyboardButton("📋 Все сценарии", callback_data='all_scenarios')],
            [InlineKeyboardButton("🔙 Назад", callback_data='admin_panel')]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        await query.edit_message_text("❌ Ошибка получения статистики.")
    finally:
        session.close()

async def show_all_scenarios(query):
    """Показ всех сценариев для админов"""
    from database.models import Scenario
    from database.connection import Session
    
    session = Session()
    try:
        scenarios = session.query(Scenario).order_by(Scenario.created_at.desc()).limit(20).all()
        
        if not scenarios:
            await query.edit_message_text(
                "📭 Сценарии не найдены.",
                reply_markup=admin_menu()
            )
            return
            
        text = "📋 <b>Все сценарии (последние 20):</b>\n\n"
        keyboard = []
        
        for scenario in scenarios:
            status_emoji = {
                'running': "🟢",
                'paused': "⏸️", 
                'stopped': "🔴"
            }.get(scenario.status, "❓")
            
            auth_emoji = {
                'success': "✅",
                'waiting': "⏳",
                'failed': "❌"
            }.get(scenario.auth_status, "❓")
            
            proxy_info = f"🌐 {scenario.proxy_server.name}" if scenario.proxy_server else "📱 Прямое"
            
            text += (
                f"{status_emoji} <b>#{scenario.id}</b> | User: {scenario.user.telegram_id}\n"
                f"   👤 @{scenario.ig_username} {auth_emoji}\n"
                f"   {proxy_info} | {scenario.trigger_word}\n"
                f"   📊 {scenario.comments_processed} комм. | "
                f"📅 {scenario.created_at.strftime('%d.%m %H:%M')}\n\n"
            )
            
            # Кнопки управления для проблемных сценариев
            if scenario.status == 'running' and scenario.auth_status == 'failed':
                keyboard.append([
                    InlineKeyboardButton(
                        f"🔧 Исправить #{scenario.id}", 
                        callback_data=f'admin_fix_{scenario.id}'
                    )
                ])
        
        if len(scenarios) == 20:
            text += "<i>Показаны последние 20 сценариев</i>"
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='admin_panel')])
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения списка сценариев: {e}")
        await query.edit_message_text("❌ Ошибка получения списка сценариев.")
    finally:
        session.close()

async def show_help_info(query):
    """Показ справочной информации"""
    help_text = """
🤖 <b>Instagram Automation Bot v2.0 - Помощь</b>

<b>🆕 Главные улучшения версии 2.0:</b>
• 🌐 Полная поддержка прокси серверов
• 📥 Интеграция с 922Proxy и другими провайдерами  
• 🔄 Автоматическая проверка и ротация прокси
• ⚡ Модульная архитектура для лучшей производительности
• 📊 Расширенная аналитика и мониторинг

<b>🎯 Основные возможности:</b>
• Автоматический поиск комментариев с триггер-словами
• Отправка персонализированных DM сообщений
• Планирование автоматических проверок
• Детальная статистика и аналитика
• Поддержка множественных прокси серверов

<b>🌐 Работа с прокси:</b>
• Поддержка HTTP, HTTPS, SOCKS5 протоколов
• Автоматическая проверка работоспособности
• Балансировка нагрузки между серверами
• Массовый импорт из популярных провайдеров

<b>🔒 Безопасность:</b>
• Шифрование всех паролей AES-256
• Антидетект система через ротацию прокси
• Ограничения запросов для избежания блокировок
• Сохранение анонимности при работе

<b>📞 Нужна помощь?</b>
Обращайтесь к администратору для решения проблем или дополнительных настроек.
"""
    
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    
    await query.edit_message_text(
        help_text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Назад", callback_data='back')
        ]])
    )

def show_scenario_management_menu(scenario_id):
    """Вспомогательная функция для получения меню управления сценарием"""
    from ui.menus import scenario_management_menu
    from database.models import Scenario, PendingMessage
    from database.connection import Session
    
    session = Session()
    try:
        scenario = session.query(Scenario).filter_by(id=scenario_id).first()
        if not scenario:
            return None
        
        pending_count = session.query(PendingMessage).filter_by(scenario_id=scenario_id).count()
        next_check = scenario.next_check_time.strftime('%d.%m %H:%M') if scenario.next_check_time else "Не запланировано"
        
        proxy_info = "🌐 Без прокси"
        if scenario.proxy_server:
            proxy_status = "🟢" if scenario.proxy_server.is_working else "🔴"
            proxy_info = f"🌐 {proxy_status} {scenario.proxy_server.name}"
        
        scenario_data = {
            'pending_count': pending_count,
            'next_check': next_check,
            'proxy_info': proxy_info,
            'status': scenario.status
        }
        
        return scenario_management_menu(scenario_id, scenario_data)
        
    finally:
        session.close()