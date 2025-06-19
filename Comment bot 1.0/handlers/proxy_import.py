"""
Обработчики для массового импорта прокси
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from services.proxy_922 import UniversalProxyImporter, PROXY_PROVIDERS_CONFIG, Proxy922Manager
from utils.validators import is_admin
from ui.menus import proxy_menu

logger = logging.getLogger(__name__)

async def show_import_menu(query):
    """Показ меню импорта прокси"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    text = (
        "📥 <b>Массовый импорт прокси</b>\n\n"
        "Выберите способ импорта прокси серверов:"
    )
    
    keyboard = [
        [InlineKeyboardButton("🌐 922Proxy", callback_data='import_922proxy')],
        [InlineKeyboardButton("📝 Из текста", callback_data='import_from_text')],
        [InlineKeyboardButton("📁 Популярные провайдеры", callback_data='import_providers')],
        [InlineKeyboardButton("🔙 Назад", callback_data='manage_proxies')]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_providers_menu(query):
    """Показ меню популярных провайдеров"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    text = "📁 <b>Популярные прокси провайдеры</b>\n\nВыберите провайдера:"
    
    keyboard = []
    for provider_key, config in PROXY_PROVIDERS_CONFIG.items():
        keyboard.append([
            InlineKeyboardButton(
                f"🌐 {config['name']}", 
                callback_data=f'import_provider_{provider_key}'
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='import_menu')])
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start_922proxy_import(query, context):
    """Начало импорта 922Proxy"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    context.user_data.clear()
    context.user_data['import_step'] = '922_credentials'
    context.user_data['provider'] = '922proxy'
    
    text = (
        "🌐 <b>Импорт из 922Proxy</b>\n\n"
        "Для автоматического импорта через API введите ваши данные:\n\n"
        "Шаг 1/3: Введите API ключ (или 'пропустить' для ручного импорта):"
    )
    
    await query.edit_message_text(text, parse_mode='HTML')

async def start_text_import(query, context):
    """Начало импорта из текста"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    context.user_data.clear()
    context.user_data['import_step'] = 'text_input'
    context.user_data['provider'] = 'custom'
    
    text = (
        "📝 <b>Импорт из текста</b>\n\n"
        "Введите список прокси в поддерживаемом формате:\n\n"
        "<b>Поддерживаемые форматы:</b>\n"
        "• <code>IP:PORT:USER:PASS</code>\n"
        "• <code>USER:PASS@IP:PORT</code>\n"
        "• <code>IP:PORT@USER:PASS</code>\n"
        "• <code>IP:PORT</code> (без авторизации)\n\n"
        "<i>Каждый прокси с новой строки</i>"
    )
    
    await query.edit_message_text(text, parse_mode='HTML')

async def start_provider_import(query, context, provider):
    """Начало импорта для конкретного провайдера"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    if provider not in PROXY_PROVIDERS_CONFIG:
        await query.edit_message_text("❌ Неизвестный провайдер.")
        return
    
    config = PROXY_PROVIDERS_CONFIG[provider]
    context.user_data.clear()
    context.user_data['import_step'] = 'provider_text'
    context.user_data['provider'] = provider
    
    instructions = UniversalProxyImporter.get_import_instructions(provider)
    
    text = (
        f"🌐 <b>Импорт {config['name']}</b>\n\n"
        f"{instructions}\n\n"
        f"Введите список прокси:"
    )
    
    await query.edit_message_text(text, parse_mode='HTML')

async def handle_import_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода данных для импорта"""
    if 'import_step' not in context.user_data:
        return
        
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 У вас нет доступа.")
        return

    text = update.message.text.strip()
    step = context.user_data['import_step']
    provider = context.user_data.get('provider', 'custom')

    try:
        if step == '922_credentials':
            if text.lower() in ['пропустить', 'skip', '-']:
                # Переходим к ручному импорту
                context.user_data['import_step'] = 'text_input'
                await update.message.reply_text(
                    "📝 <b>Ручной импорт 922Proxy</b>\n\n"
                    "Введите список прокси в формате:\n"
                    "• <code>IP:PORT:USER:PASS</code>\n"
                    "• <code>USER:PASS@IP:PORT</code>\n\n"
                    "<i>Каждый прокси с новой строки</i>",
                    parse_mode='HTML'
                )
            else:
                # Сохраняем API ключ и переходим к получению списка
                context.user_data['api_key'] = text
                await update.message.reply_text(
                    "🔄 Попытка получить список прокси через API...\n"
                    "<i>Это может занять некоторое время</i>",
                    parse_mode='HTML'
                )
                await process_922_api_import(update, context)

        elif step in ['text_input', 'provider_text']:
            await process_text_import(update, context, text, provider)

    except Exception as e:
        logger.error(f"Ошибка обработки импорта: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке.")

async def process_922_api_import(update, context):
    """Обработка импорта через API 922Proxy"""
    try:
        api_key = context.user_data.get('api_key')
        
        # Попытка получить прокси через API
        manager = Proxy922Manager(api_key=api_key)
        proxies = manager.get_proxy_list_from_api()
        
        if not proxies:
            await update.message.reply_text(
                "❌ Не удалось получить прокси через API.\n"
                "Проверьте API ключ или используйте ручной импорт.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 К импорту", callback_data='import_menu')
                ]])
            )
            return
        
        # Импорт полученных прокси
        imported_count = Proxy922Manager.import_proxies_to_database(
            proxies, 'socks5', '922Proxy API'
        )
        
        await update.message.reply_text(
            f"✅ <b>Импорт завершен!</b>\n\n"
            f"📊 Получено через API: {len(proxies)}\n"
            f"📥 Импортировано: {imported_count}\n"
            f"🌐 Провайдер: 922Proxy\n"
            f"📡 Тип: SOCKS5",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔍 Проверить прокси", callback_data='check_all_proxies'),
                InlineKeyboardButton("📋 К списку", callback_data='list_proxies')
            ]])
        )
        
    except Exception as e:
        logger.error(f"Ошибка API импорта 922Proxy: {e}")
        await update.message.reply_text(
            "❌ Ошибка при импорте через API.\n"
            "Попробуйте ручной импорт."
        )
    finally:
        context.user_data.clear()

async def process_text_import(update, context, proxy_text, provider):
    """Обработка импорта из текста"""
    try:
        if not proxy_text or len(proxy_text) < 10:
            await update.message.reply_text("❌ Слишком короткий текст. Введите список прокси.")
            return
        
        # Определяем тип прокси
        proxy_type = 'socks5' if provider == '922proxy' else 'http'
        if provider in PROXY_PROVIDERS_CONFIG:
            proxy_type = PROXY_PROVIDERS_CONFIG[provider]['default_type']
        
        await update.message.reply_text(
            "🔄 Обрабатываю список прокси...\n"
            "<i>Это может занять некоторое время</i>",
            parse_mode='HTML'
        )
        
        # Импорт прокси
        result = UniversalProxyImporter.import_from_text(
            proxy_text, provider, proxy_type
        )
        
        if result['success']:
            # Предлагаем проверить импортированные прокси
            keyboard = [
                [InlineKeyboardButton("🔍 Проверить все", callback_data='check_all_proxies')],
                [InlineKeyboardButton("📋 К списку прокси", callback_data='list_proxies')],
                [InlineKeyboardButton("🔙 К импорту", callback_data='import_menu')]
            ]
            
            await update.message.reply_text(
                f"✅ <b>Импорт завершен!</b>\n\n"
                f"📊 {result['message']}\n"
                f"🌐 Провайдер: {PROXY_PROVIDERS_CONFIG.get(provider, {}).get('name', provider.title())}\n"
                f"📡 Тип: {proxy_type.upper()}\n\n"
                f"🔍 Рекомендуется проверить работоспособность прокси.",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                f"❌ <b>Ошибка импорта</b>\n\n"
                f"{result['message']}",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Попробовать снова", callback_data='import_menu')
                ]])
            )
        
    except Exception as e:
        logger.error(f"Ошибка текстового импорта: {e}")
        await update.message.reply_text("❌ Ошибка при импорте прокси.")
    finally:
        context.user_data.clear()

async def bulk_proxy_operations(query):
    """Массовые операции с прокси"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    text = (
        "⚙️ <b>Массовые операции</b>\n\n"
        "Выберите операцию:"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔍 Проверить все прокси", callback_data='check_all_proxies')],
        [InlineKeyboardButton("🔄 Автоматическая ротация", callback_data='auto_rotate_proxies')],
        [InlineKeyboardButton("📊 Пакетная проверка", callback_data='bulk_check_proxies')],
        [InlineKeyboardButton("🗑️ Очистить неработающие", callback_data='cleanup_failed_proxies')],
        [InlineKeyboardButton("🔙 Назад", callback_data='manage_proxies')]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def auto_rotate_proxies(query):
    """Автоматическая ротация прокси"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    await query.edit_message_text("🔄 Выполняю автоматическую ротацию прокси...")
    
    try:
        deactivated_count = Proxy922Manager.auto_rotate_proxies()
        
        await query.edit_message_text(
            f"✅ <b>Ротация завершена</b>\n\n"
            f"📊 Деактивировано неработающих прокси: {deactivated_count}\n\n"
            f"ℹ️ Прокси деактивируются если не работают более 24 часов.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data='bulk_operations')
            ]])
        )
        
    except Exception as e:
        logger.error(f"Ошибка автоматической ротации: {e}")
        await query.edit_message_text("❌ Ошибка при ротации прокси.")

async def bulk_check_proxies(query):
    """Пакетная проверка прокси"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    await query.edit_message_text("🔍 Выполняю пакетную проверку прокси...")
    
    try:
        results = Proxy922Manager.bulk_check_proxies(batch_size=20)
        
        text = (
            f"🔍 <b>Пакетная проверка завершена</b>\n\n"
            f"📊 Проверено: {results['checked']}\n"
            f"✅ Работают: {results['working']}\n"
            f"❌ Не работают: {results['failed']}\n"
        )
        
        if results['errors']:
            text += f"\n⚠️ Ошибок: {len(results['errors'])}"
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Проверить еще", callback_data='bulk_check_proxies'),
                InlineKeyboardButton("🔙 Назад", callback_data='bulk_operations')
            ]])
        )
        
    except Exception as e:
        logger.error(f"Ошибка пакетной проверки: {e}")
        await query.edit_message_text("❌ Ошибка при проверке прокси.")

async def cleanup_failed_proxies(query):
    """Очистка неработающих прокси"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    from database.models import ProxyServer, Scenario
    from database.connection import Session
    
    session = Session()
    try:
        # Подсчитываем неработающие прокси, которые не используются
        failed_proxies = session.query(ProxyServer).filter(
            ProxyServer.is_working == False,
            ProxyServer.is_active == False
        ).all()
        
        # Проверяем, какие из них не используются в сценариях
        unused_failed = []
        for proxy in failed_proxies:
            scenarios_count = session.query(Scenario).filter_by(proxy_id=proxy.id).count()
            if scenarios_count == 0:
                unused_failed.append(proxy)
        
        if not unused_failed:
            await query.edit_message_text(
                "ℹ️ <b>Очистка не требуется</b>\n\n"
                "Нет неработающих прокси, которые можно безопасно удалить.",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data='bulk_operations')
                ]])
            )
            return
        
        # Показываем подтверждение
        text = (
            f"🗑️ <b>Подтверждение очистки</b>\n\n"
            f"Найдено {len(unused_failed)} неработающих прокси, которые можно удалить:\n\n"
        )
        
        for proxy in unused_failed[:5]:  # Показываем первые 5
            text += f"• {proxy.name} ({proxy.host}:{proxy.port})\n"
        
        if len(unused_failed) > 5:
            text += f"... и еще {len(unused_failed) - 5} прокси\n"
        
        text += "\n⚠️ Это действие необратимо!"
        
        keyboard = [
            [InlineKeyboardButton("✅ Удалить все", callback_data='confirm_cleanup_proxies')],
            [InlineKeyboardButton("❌ Отменить", callback_data='bulk_operations')]
        ]
        
        # Сохраняем список для удаления в контексте
        query.message.bot_data['proxies_to_cleanup'] = [p.id for p in unused_failed]
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Ошибка подготовки очистки прокси: {e}")
        await query.edit_message_text("❌ Ошибка при подготовке очистки.")
    finally:
        session.close()

async def confirm_cleanup_proxies(query):
    """Подтверждение очистки прокси"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    proxy_ids = query.message.bot_data.get('proxies_to_cleanup', [])
    if not proxy_ids:
        await query.edit_message_text("❌ Список прокси для удаления не найден.")
        return
    
    session = Session()
    try:
        deleted_count = 0
        
        for proxy_id in proxy_ids:
            proxy = session.query(ProxyServer).filter_by(id=proxy_id).first()
            if proxy:
                session.delete(proxy)
                deleted_count += 1
        
        session.commit()
        
        # Очищаем временные данные
        query.message.bot_data.pop('proxies_to_cleanup', None)
        
        await query.edit_message_text(
            f"✅ <b>Очистка завершена</b>\n\n"
            f"🗑️ Удалено неработающих прокси: {deleted_count}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data='bulk_operations')
            ]])
        )
        
    except Exception as e:
        logger.error(f"Ошибка удаления прокси: {e}")
        session.rollback()
        await query.edit_message_text("❌ Ошибка при удалении прокси.")
    finally:
        session.close()

# === ПЛАНИРОВЩИК АВТОМАТИЧЕСКИХ ОПЕРАЦИЙ ===

async def schedule_proxy_maintenance():
    """Планировщик автоматического обслуживания прокси"""
    try:
        # Автоматическая ротация каждые 6 часов
        Proxy922Manager.auto_rotate_proxies()
        
        # Пакетная проверка случайных прокси каждый час
        results = Proxy922Manager.bulk_check_proxies(batch_size=5)
        
        logger.info(f"Автоматическое обслуживание прокси: проверено {results['checked']}, "
                   f"работают {results['working']}, не работают {results['failed']}")
        
    except Exception as e:
        logger.error(f"Ошибка автоматического обслуживания прокси: {e}")

# === ЭКСПОРТ ПРОКСИ ===

async def export_proxies(query):
    """Экспорт списка прокси"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    text = (
        "📤 <b>Экспорт прокси</b>\n\n"
        "Выберите формат экспорта:"
    )
    
    keyboard = [
        [InlineKeyboardButton("📝 IP:PORT:USER:PASS", callback_data='export_format_1')],
        [InlineKeyboardButton("🔗 USER:PASS@IP:PORT", callback_data='export_format_2')],
        [InlineKeyboardButton("🌐 Только рабочие", callback_data='export_working_only')],
        [InlineKeyboardButton("📊 Статистика TXT", callback_data='export_stats')],
        [InlineKeyboardButton("🔙 Назад", callback_data='manage_proxies')]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def process_proxy_export(query, export_type):
    """Обработка экспорта прокси"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    from database.models import ProxyServer
    from database.connection import Session
    
    session = Session()
    try:
        # Получаем прокси в зависимости от типа экспорта
        if export_type == 'export_working_only':
            proxies = session.query(ProxyServer).filter_by(
                is_active=True, 
                is_working=True
            ).all()
            title = "Рабочие прокси"
        else:
            proxies = session.query(ProxyServer).filter_by(is_active=True).all()
            title = "Все активные прокси"
        
        if not proxies:
            await query.edit_message_text(
                "📭 Нет прокси для экспорта.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data='export_proxies')
                ]])
            )
            return
        
        # Формирование текста экспорта
        export_text = f"# {title}\n# Экспортировано: {len(proxies)} прокси\n# Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        
        for proxy in proxies:
            if export_type == 'export_format_1':
                # IP:PORT:USER:PASS
                if proxy.username and proxy.password_encrypted:
                    try:
                        password = ProxyManager.decrypt_password(proxy.password_encrypted)
                        line = f"{proxy.host}:{proxy.port}:{proxy.username}:{password}"
                    except:
                        line = f"{proxy.host}:{proxy.port}"
                else:
                    line = f"{proxy.host}:{proxy.port}"
            elif export_type == 'export_format_2':
                # USER:PASS@IP:PORT
                if proxy.username and proxy.password_encrypted:
                    try:
                        password = ProxyManager.decrypt_password(proxy.password_encrypted)
                        line = f"{proxy.username}:{password}@{proxy.host}:{proxy.port}"
                    except:
                        line = f"{proxy.host}:{proxy.port}"
                else:
                    line = f"{proxy.host}:{proxy.port}"
            elif export_type == 'export_stats':
                # Детальная статистика
                status = "🟢" if proxy.is_working else "🔴"
                last_check = proxy.last_check.strftime('%d.%m %H:%M') if proxy.last_check else "Никогда"
                line = f"{status} {proxy.name} | {proxy.proxy_type}://{proxy.host}:{proxy.port} | Использований: {proxy.usage_count} | Проверка: {last_check}"
            else:
                line = f"{proxy.host}:{proxy.port}"
            
            export_text += line + "\n"
        
        # Отправляем файл, если текст слишком длинный
        if len(export_text) > 4000:
            # Создаем временный файл
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(export_text)
                temp_filename = f.name
            
            try:
                with open(temp_filename, 'rb') as f:
                    await query.message.reply_document(
                        document=f,
                        filename=f"proxies_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        caption=f"📤 Экспорт прокси: {len(proxies)} шт."
                    )
                
                await query.edit_message_text(
                    f"✅ <b>Экспорт завершен</b>\n\n"
                    f"📊 Экспортировано: {len(proxies)} прокси\n"
                    f"📁 Файл отправлен выше",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Назад", callback_data='export_proxies')
                    ]])
                )
                
            finally:
                # Удаляем временный файл
                try:
                    os.unlink(temp_filename)
                except:
                    pass
        else:
            # Отправляем как текст
            await query.edit_message_text(
                f"📤 <b>Экспорт прокси</b>\n\n<pre>{export_text}</pre>",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data='export_proxies')
                ]])
            )
        
    except Exception as e:
        logger.error(f"Ошибка экспорта прокси: {e}")
        await query.edit_message_text("❌ Ошибка при экспорте прокси.")
    finally:
        session.close()

# === ТЕСТИРОВАНИЕ ПРОКСИ ===

async def test_proxy_with_instagram(query, proxy_id):
    """Тестирование прокси с Instagram"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    from database.models import ProxyServer
    from database.connection import Session
    from services.proxy_manager import ProxyManager
    
    session = Session()
    try:
        proxy = session.query(ProxyServer).filter_by(id=proxy_id).first()
        if not proxy:
            await query.edit_message_text("❌ Прокси не найден.")
            return
        
        await query.edit_message_text(
            f"🧪 Тестирую прокси <b>{proxy.name}</b> с Instagram...\n\n"
            f"<i>Это может занять до 30 секунд</i>",
            parse_mode='HTML'
        )
        
        # Тестируем прокси с Instagram
        success = await test_proxy_instagram_connection(proxy)
        
        if success:
            result_text = (
                f"✅ <b>Тест прошел успешно</b>\n\n"
                f"📝 Прокси: {proxy.name}\n"
                f"🌐 Адрес: {proxy.proxy_type}://{proxy.host}:{proxy.port}\n"
                f"📱 Instagram: Доступен\n"
                f"🕐 Тест: {datetime.now().strftime('%d.%m %H:%M')}"
            )
        else:
            result_text = (
                f"❌ <b>Тест не пройден</b>\n\n"
                f"📝 Прокси: {proxy.name}\n"
                f"🌐 Адрес: {proxy.proxy_type}://{proxy.host}:{proxy.port}\n"
                f"📱 Instagram: Недоступен\n"
                f"🕐 Тест: {datetime.now().strftime('%d.%m %H:%M')}\n\n"
                f"⚠️ Прокси может быть заблокирован Instagram"
            )
        
        await query.edit_message_text(
            result_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К прокси", callback_data=f'manage_proxy_{proxy_id}')
            ]])
        )
        
    except Exception as e:
        logger.error(f"Ошибка тестирования прокси с Instagram: {e}")
        await query.edit_message_text("❌ Ошибка при тестировании прокси.")
    finally:
        session.close()

async def test_proxy_instagram_connection(proxy: ProxyServer) -> bool:
    """Тестирование подключения к Instagram через прокси"""
    try:
        from services.proxy_manager import ProxyManager
        import requests
        
        proxy_dict = ProxyManager.get_proxy_dict(proxy)
        if not proxy_dict:
            return False
        
        # Тестируем доступность Instagram
        instagram_urls = [
            'https://www.instagram.com/',
            'https://i.instagram.com/api/v1/users/web_info/',
        ]
        
        for url in instagram_urls:
            try:
                response = requests.get(
                    url,
                    proxies=proxy_dict,
                    timeout=15,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                )
                
                # Проверяем, что получили ответ от Instagram
                if response.status_code in [200, 404] and 'instagram' in response.text.lower():
                    return True
                    
            except requests.exceptions.Timeout:
                continue
            except Exception:
                continue
        
        return False
        
    except Exception as e:
        logger.error(f"Ошибка тестирования Instagram подключения: {e}")
        return False