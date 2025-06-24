"""
Основные обработчики callback запросов (нажатий кнопок)
ОБНОВЛЕННЫЙ ФАЙЛ handlers/callbacks.py
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
        
        # === УЛУЧШЕННАЯ АВТОРИЗАЦИЯ ===
        elif data.startswith('challenge_confirmed_'):
            from services.enhanced_auth import handle_enhanced_auth_callbacks
            await handle_enhanced_auth_callbacks(update, context)
            
        elif data.startswith('sms_requested_'):
            from services.enhanced_auth import handle_enhanced_auth_callbacks
            await handle_enhanced_auth_callbacks(update, context)
            
        elif data.startswith('retry_now_'):
            from services.enhanced_auth import handle_enhanced_auth_callbacks
            await handle_enhanced_auth_callbacks(update, context)
            
        elif data.startswith('switch_proxy_'):
            from services.enhanced_auth import handle_enhanced_auth_callbacks
            await handle_enhanced_auth_callbacks(update, context)
            
        elif data.startswith('safe_mode_'):
            from services.enhanced_auth import handle_enhanced_auth_callbacks
            await handle_enhanced_auth_callbacks(update, context)
            
        elif data.startswith('slow_mode_'):
            from services.enhanced_auth import handle_enhanced_auth_callbacks
            await handle_enhanced_auth_callbacks(update, context)
            
        elif data.startswith('cancel_sms_'):
            from services.enhanced_auth import handle_enhanced_auth_callbacks
            await handle_enhanced_auth_callbacks(update, context)
        
        # === НАСТРОЙКИ АВТОРИЗАЦИИ (АДМИН) ===
        elif data == 'auth_settings':
            if is_admin_user:
                from services.enhanced_auth import admin_auth_settings_menu
                await admin_auth_settings_menu(query)
            else:
                await query.edit_message_text("🚫 У вас нет доступа к настройкам авторизации.")
                
        elif data == 'auth_quick_setup':
            if is_admin_user:
                await show_auth_presets_menu(query)
            else:
                await query.edit_message_text("🚫 У вас нет доступа к настройкам.")
                
        elif data == 'auth_statistics':
            if is_admin_user:
                await show_auth_statistics(query)
            else:
                await query.edit_message_text("🚫 У вас нет доступа к статистике.")
                
        elif data.startswith('auth_preset_'):
            if is_admin_user:
                preset = data.split('_')[-1]
                await apply_auth_preset_callback(query, preset)
            else:
                await query.edit_message_text("🚫 У вас нет доступа к настройкам.")
        
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
        
        # === ВЫБОР ПРОКСИ ДЛЯ СЦЕНАРИЯ (УЛУЧШЕННЫЙ) ===
        elif data == 'choose_proxy':
            await show_proxy_selection(query, context)
        elif data == 'choose_best_proxy':
            await choose_best_proxy_automatically(query, context)
        elif data == 'safe_mode_creation':
            await handle_safe_mode_creation(query, context)
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
            await restart_scenario_enhanced(query, scenario_id, user_id)  # ОБНОВЛЕНО
        elif data.startswith('delete_'):
            scenario_id = int(data.split("_")[1])
            await delete_scenario(query, scenario_id, user_id)
        
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

# === НОВЫЕ ФУНКЦИИ ДЛЯ УЛУЧШЕННОЙ АВТОРИЗАЦИИ ===

async def show_auth_presets_menu(query):
    """Меню предустановок авторизации"""
    text = (
        "⚡ <b>Быстрая настройка авторизации</b>\n\n"
        "Выберите предустановку:\n\n"
        "🔥 <b>Агрессивная</b> - быстро, много попыток\n"
        "⚖️ <b>Сбалансированная</b> - оптимально (рекомендуется)\n"
        "🐢 <b>Консервативная</b> - медленно, безопасно\n"
        "👻 <b>Скрытная</b> - максимальная осторожность"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔥 Агрессивная", callback_data='auth_preset_aggressive')],
        [InlineKeyboardButton("⚖️ Сбалансированная", callback_data='auth_preset_balanced')],
        [InlineKeyboardButton("🐢 Консервативная", callback_data='auth_preset_conservative')],
        [InlineKeyboardButton("👻 Скрытная", callback_data='auth_preset_stealth')],
        [InlineKeyboardButton("🔙 Назад", callback_data='auth_settings')]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def apply_auth_preset_callback(query, preset_name):
    """Применение предустановки авторизации"""
    from services.enhanced_auth import apply_auth_preset, get_auth_config
    
    success = apply_auth_preset(preset_name)
    
    if success:
        config = get_auth_config()
        preset_names = {
            'aggressive': '🔥 Агрессивная',
            'balanced': '⚖️ Сбалансированная', 
            'conservative': '🐢 Консервативная',
            'stealth': '👻 Скрытная'
        }
        
        await query.edit_message_text(
            f"✅ <b>Применена предустановка: {preset_names.get(preset_name, preset_name)}</b>\n\n"
            f"⚡ Быстрых попыток: {config['max_fast_attempts']}\n"
            f"⏰ Задержка: {config['fast_retry_delay']//60} мин\n"
            f"🔄 Автосмена прокси: {'✅' if config['auto_switch_proxy'] else '❌'}\n"
            f"🛡️ Безопасный режим: {'✅' if config['safe_mode_no_proxy'] else '❌'}\n\n"
            f"Настройки применены ко всем новым авторизациям.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К настройкам", callback_data='auth_settings')
            ]])
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка применения предустановки.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data='auth_quick_setup')
            ]])
        )

async def show_auth_statistics(query):
    """Показ статистики авторизации"""
    try:
        from database.models import Scenario, AuthenticationLog, ProxyPerformance
        from database.connection import Session
        
        session = Session()
        
        # Общая статистика
        total_scenarios = session.query(Scenario).count()
        auth_success = session.query(Scenario).filter_by(auth_status='success').count()
        auth_failed = session.query(Scenario).filter_by(auth_status='failed').count()
        auth_waiting = session.query(Scenario).filter_by(auth_status='waiting').count()
        
        success_rate = (auth_success / total_scenarios * 100) if total_scenarios > 0 else 0
        
        # Частые ошибки
        common_errors = session.query(Scenario.error_message).filter(
            Scenario.error_message.isnot(None)
        ).all()
        
        error_counts = {}
        for error in common_errors:
            error_type = error[0][:50] if error[0] else "Неизвестная ошибка"
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        top_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        text = (
            f"📊 <b>Статистика авторизации</b>\n\n"
            f"<b>📈 Общие показатели:</b>\n"
            f"• Всего сценариев: {total_scenarios}\n"
            f"• Успешных: {auth_success} ({success_rate:.1f}%)\n"
            f"• Неудачных: {auth_failed}\n"
            f"• В процессе: {auth_waiting}\n\n"
        )
        
        if top_errors:
            text += f"<b>🔍 Частые ошибки:</b>\n"
            for error, count in top_errors:
                text += f"• {error}: {count}\n"
        
        # Добавляем рекомендации
        if success_rate < 50:
            text += f"\n⚠️ <b>Рекомендации:</b>\n• Проверьте настройки прокси\n• Используйте безопасный режим\n• Увеличьте задержки между попытками"
        elif success_rate < 80:
            text += f"\n💡 <b>Можно улучшить:</b>\n• Добавьте больше рабочих прокси\n• Настройте автосмену прокси"
        else:
            text += f"\n✅ <b>Отличные показатели!</b>\nСистема работает эффективно."
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data='auth_statistics')],
            [InlineKeyboardButton("📋 Детальный отчет", callback_data='auth_detailed_stats')],
            [InlineKeyboardButton("🔙 Назад", callback_data='auth_settings')]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        session.close()
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики авторизации: {e}")
        await query.edit_message_text(
            f"❌ Ошибка получения статистики: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data='auth_settings')
            ]])
        )

async def choose_best_proxy_automatically(query, context):
    """Автоматический выбор лучшего прокси"""
    from database.models import ProxyServer, ProxyPerformance
    from database.connection import Session
    
    session = Session()
    try:
        # Находим лучший прокси по статистике
        best_proxy = session.query(ProxyServer).join(ProxyPerformance, isouter=True).filter_by(
            is_active=True, 
            is_working=True
        ).order_by(ProxyPerformance.success_rate.desc(), ProxyServer.usage_count.asc()).first()
        
        if best_proxy:
            context.user_data['proxy_id'] = best_proxy.id
            
            # Получаем статистику для отображения
            perf = session.query(ProxyPerformance).filter_by(proxy_id=best_proxy.id).first()
            success_rate = perf.success_rate if perf else "новый прокси"
            
            await query.edit_message_text(
                f"🎯 <b>Автоматически выбран лучший прокси</b>\n\n"
                f"📡 Прокси: {best_proxy.name}\n"
                f"🌐 Тип: {best_proxy.proxy_type.upper()}\n"
                f"📊 Успешность: {success_rate}%\n"
                f"📈 Использований: {best_proxy.usage_count}\n\n"
                f"Продолжите создание сценария с этим прокси:",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Продолжить", callback_data='confirm_proxy_choice')],
                    [InlineKeyboardButton("📋 Выбрать другой", callback_data='choose_proxy')],
                    [InlineKeyboardButton("🛡️ Без прокси", callback_data='no_proxy')]
                ])
            )
        else:
            await query.edit_message_text(
                "❌ Нет доступных прокси.\n"
                "Создайте сценарий без прокси или добавьте новые прокси.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛡️ Безопасный режим", callback_data='safe_mode_creation')],
                    [InlineKeyboardButton("🔙 Назад", callback_data='scenarios_menu')]
                ])
            )
    finally:
        session.close()

async def handle_safe_mode_creation(query, context):
    """Обработка создания сценария в безопасном режиме"""
    context.user_data['proxy_id'] = None
    context.user_data['safe_mode'] = True
    
    await query.edit_message_text(
        f"🛡️ <b>Безопасный режим</b>\n\n"
        f"Сценарий будет создан без использования прокси.\n"
        f"Это снижает анонимность, но может помочь с проблемными аккаунтами.\n\n"
        f"Продолжить создание сценария?",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Продолжить", callback_data='confirm_proxy_choice')],
            [InlineKeyboardButton("🌐 Выбрать прокси", callback_data='choose_proxy')],
            [InlineKeyboardButton("🔙 Назад", callback_data='scenarios_menu')]
        ])
    )

# === ОБНОВЛЕННАЯ ФУНКЦИЯ ПЕРЕЗАПУСКА ===

async def restart_scenario_enhanced(query, scenario_id, user_id):
    """Перезапуск сценария с улучшенной авторизацией"""
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

        # Остановка старой задачи
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

        # Запуск новой задачи с улучшенной авторизацией
        from services.enhanced_auth import run_enhanced_instagram_scenario
        tasks[scenario_id] = asyncio.create_task(
            run_enhanced_instagram_scenario(scenario_id, query.message.chat_id)
        )
        
        await query.edit_message_text(
            "🚀 <b>Сценарий перезапущен с улучшенной авторизацией v2.0</b>\n\n"
            f"📱 Сценарий: #{scenario_id}\n"
            f"👤 Аккаунт: @{scenario.ig_username}\n\n"
            f"⚡ Начинается быстрая авторизация...\n"
            f"📊 Отслеживайте прогресс в реальном времени",
            parse_mode='HTML',
            reply_markup=show_scenario_management_menu(scenario_id)
        )
        logger.info(f"Сценарий {scenario_id} перезапущен с улучшенной авторизацией пользователем {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка перезапуска сценария с улучшенной авторизацией: {e}")
        await query.edit_message_text("❌ Ошибка при перезапуске сценария.")
    finally:
        session.close()

# === ОСТАЛЬНЫЕ ФУНКЦИИ ОСТАЮТСЯ БЕЗ ИЗМЕНЕНИЙ ===
# (Все остальные функции из оригинального файла остаются такими же)

# Импортируем остальные функции из оригинального файла
from handlers.callbacks import (
    check_scenario_comments, send_pending_messages, show_schedule_menu,
    set_check_timer, pause_scenario, resume_scenario, delete_scenario,
    show_manage_users_info, show_manage_admins_info, show_scenarios_status,
    show_all_scenarios, show_help_info, show_scenario_management_menu
)