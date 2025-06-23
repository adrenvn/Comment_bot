"""
Обработчики для управления прокси серверами
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import *
from database.models import ProxyServer
from database.connection import Session
from services.proxy_manager import ProxyManager
from utils.validators import is_admin
from ui.menus import proxy_menu

logger = logging.getLogger(__name__)

async def manage_proxies_menu(query):
    """Показ меню управления прокси"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа к управлению прокси.")
        return
    
    session = Session()
    try:
        stats = ProxyManager.get_proxy_stats()
        
        text = (
            f"🌐 <b>Управление прокси серверами</b>\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"• Всего прокси: {stats.get('total', 0)}\n"
            f"• Активных: {stats.get('active', 0)}\n"
            f"• Работающих: {stats.get('working', 0)}\n"
            f"• HTTP: {stats.get('types', {}).get('http', 0)}\n"
            f"• HTTPS: {stats.get('types', {}).get('https', 0)}\n"
            f"• SOCKS5: {stats.get('types', {}).get('socks5', 0)}\n"
        )
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=proxy_menu()
        )
    finally:
        session.close()

async def start_add_proxy(query, context):
    """Начало добавления нового прокси"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    context.user_data.clear()
    context.user_data['proxy_step'] = 'name'
    
    await query.edit_message_text(
        "🌐 <b>Добавление нового прокси</b>\n\n"
        "Шаг 1/6: Введите название прокси\n\n"
        "💡 <i>Примеры:</i>\n"
        "• 922Proxy Main\n"
        "• ProxyRotator #1\n"
        "• Premium Proxy US",
        parse_mode='HTML'
    )

async def list_proxies(query):
    """Показ списка прокси"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    proxies = ProxyManager.get_proxy_list()
    
    if not proxies:
        await query.edit_message_text(
            "📭 Прокси серверы не настроены.",
            reply_markup=proxy_menu()
        )
        return
    
    text = "📋 <b>Список прокси серверов:</b>\n\n"
    keyboard = []
    
    for proxy in proxies[:10]:  # Показываем только первые 10
        status_emoji = "🟢" if proxy.is_active and proxy.is_working else "🔴"
        last_check = proxy.last_check.strftime('%d.%m %H:%M') if proxy.last_check else "Никогда"
        
        text += (
            f"{status_emoji} <b>{proxy.name}</b>\n"
            f"   📡 {proxy.proxy_type.upper()}://{proxy.host}:{proxy.port}\n"
            f"   📊 Использований: {proxy.usage_count}\n"
            f"   🕐 Проверка: {last_check}\n\n"
        )
        
        # Кнопки управления прокси
        row = []
        row.append(InlineKeyboardButton(f"⚙️ {proxy.name[:10]}", callback_data=f'manage_proxy_{proxy.id}'))
        row.append(InlineKeyboardButton("🔍", callback_data=f'check_proxy_{proxy.id}'))
        row.append(InlineKeyboardButton("🗑️", callback_data=f'delete_proxy_{proxy.id}'))
        keyboard.append(row)
    
    if len(proxies) > 10:
        text += f"... и еще {len(proxies) - 10} прокси"
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='manage_proxies')])
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def check_all_proxies(query):
    """Проверка всех прокси"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    await query.edit_message_text("🔍 Проверяю все прокси серверы...")
    
    results = ProxyManager.check_all_proxies()
    
    if results['working'] == 0 and results['failed'] == 0:
        await query.edit_message_text(
            "📭 Нет активных прокси для проверки.",
            reply_markup=proxy_menu()
        )
        return
    
    text = (
        f"🔍 <b>Результаты проверки прокси:</b>\n\n"
        f"✅ Работают: {results['working']}\n"
        f"❌ Не работают: {results['failed']}\n\n"
        f"<b>Детали:</b>\n" + "\n".join(results['results'][:15])
    )
    
    if len(results['results']) > 15:
        text += f"\n... и еще {len(results['results']) - 15} прокси"
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=proxy_menu()
    )

async def show_proxy_stats(query):
    """Показ подробной статистики прокси"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    session = Session()
    try:
        stats = ProxyManager.get_proxy_stats()
        
        # Статистика использования в сценариях
        from database.models import Scenario
        scenarios_with_proxy = session.query(Scenario).filter(Scenario.proxy_id.isnot(None)).count()
        scenarios_without_proxy = session.query(Scenario).filter(Scenario.proxy_id.is_(None)).count()
        
        # Топ используемых прокси
        top_proxies = session.query(ProxyServer).filter_by(is_active=True).order_by(
            ProxyServer.usage_count.desc()
        ).limit(5).all()
        
        text = (
            f"📊 <b>Детальная статистика прокси</b>\n\n"
            f"<b>🌐 Общая информация:</b>\n"
            f"• Всего прокси: {stats.get('total', 0)}\n"
            f"• Активных: {stats.get('active', 0)}\n"
            f"• Работающих: {stats.get('working', 0)}\n"
            f"• Общее использование: {stats.get('usage', 0)}\n\n"
            f"<b>📡 По типам:</b>\n"
            f"• HTTP: {stats.get('types', {}).get('http', 0)}\n"
            f"• HTTPS: {stats.get('types', {}).get('https', 0)}\n"
            f"• SOCKS5: {stats.get('types', {}).get('socks5', 0)}\n\n"
            f"<b>🎯 Использование в сценариях:</b>\n"
            f"• С прокси: {scenarios_with_proxy}\n"
            f"• Без прокси: {scenarios_without_proxy}\n"
        )
        
        if top_proxies:
            text += f"\n<b>🔥 Топ используемых:</b>\n"
            for i, proxy in enumerate(top_proxies, 1):
                text += f"{i}. {proxy.name} - {proxy.usage_count} исп.\n"
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=proxy_menu()
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики прокси: {e}")
        await query.edit_message_text("❌ Ошибка получения статистики.")
    finally:
        session.close()

async def handle_proxy_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода данных прокси"""
    if 'proxy_step' not in context.user_data:
        return
        
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 У вас нет доступа.")
        return

    text = update.message.text.strip()
    step = context.user_data['proxy_step']

    try:
        if step == 'name':
            if not text or len(text) < 3:
                await update.message.reply_text("❌ Название должно содержать минимум 3 символа.")
                return
            
            context.user_data['proxy_name'] = text
            context.user_data['proxy_step'] = 'type'
            
            keyboard = [
                [InlineKeyboardButton("HTTP", callback_data='proxy_type_http')],
                [InlineKeyboardButton("HTTPS", callback_data='proxy_type_https')],
                [InlineKeyboardButton("SOCKS5", callback_data='proxy_type_socks5')]
            ]
            
            await update.message.reply_text(
                "🌐 Шаг 2/6: Выберите тип прокси:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif step == 'host':
            if not text or '.' not in text:
                await update.message.reply_text(
                    "❌ Введите корректный хост\n\n"
                    "💡 <i>Примеры:</i>\n"
                    "• proxy.922s5.com\n"
                    "• 192.168.1.100\n"
                    "• my-proxy-server.com",
                    parse_mode='HTML'
                )
                return
            
            context.user_data['proxy_host'] = text
            context.user_data['proxy_step'] = 'port'
            
            await update.message.reply_text(
                "🌐 Шаг 4/6: Введите порт прокси\n\n"
                "💡 <i>Примеры: 8080, 3128, 1080</i>",
                parse_mode='HTML'
            )

        elif step == 'port':
            try:
                port = int(text)
                if port < 1 or port > 65535:
                    raise ValueError("Порт вне диапазона")
            except ValueError:
                await update.message.reply_text("❌ Введите корректный номер порта (1-65535).")
                return
            
            context.user_data['proxy_port'] = port
            context.user_data['proxy_step'] = 'username'
            
            await update.message.reply_text(
                "🌐 Шаг 5/6: Введите имя пользователя прокси\n\n"
                "Если авторизация не требуется, отправьте: <code>нет</code>",
                parse_mode='HTML'
            )

        elif step == 'username':
            if text.lower() in ['нет', 'no', 'none', '-', 'skip']:
                context.user_data['proxy_username'] = None
                context.user_data['proxy_password'] = None
                await confirm_proxy_creation(update, context)
            else:
                context.user_data['proxy_username'] = text
                context.user_data['proxy_step'] = 'password'
                
                await update.message.reply_text(
                    "🌐 Шаг 6/6: Введите пароль прокси:"
                )

        elif step == 'password':
            context.user_data['proxy_password'] = text
            await confirm_proxy_creation(update, context)

    except Exception as e:
        logger.error(f"Ошибка обработки ввода прокси: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте снова.")

async def handle_proxy_type_selection(query, context, proxy_type):
    """Обработчик выбора типа прокси"""
    context.user_data['proxy_type'] = proxy_type
    context.user_data['proxy_step'] = 'host'
    
    await query.edit_message_text(
        f"🌐 Шаг 3/6: Выбран тип <b>{proxy_type.upper()}</b>\n\n"
        f"Введите хост прокси сервера:",
        parse_mode='HTML'
    )

async def confirm_proxy_creation(update, context):
    """Подтверждение создания прокси"""
    required_fields = ['proxy_name', 'proxy_type', 'proxy_host', 'proxy_port']
    if not all(field in context.user_data for field in required_fields):
        await update.message.reply_text("❌ Ошибка: не все данные заполнены.")
        return
    
    auth_info = ""
    if context.user_data.get('proxy_username'):
        auth_info = f"\n👤 Логин: {context.user_data['proxy_username']}\n🔐 Пароль: {'*' * len(context.user_data.get('proxy_password', ''))}"
    
    confirmation_text = (
        f"✅ <b>Подтверждение создания прокси</b>\n\n"
        f"📝 Название: {context.user_data['proxy_name']}\n"
        f"🌐 Тип: {context.user_data['proxy_type'].upper()}\n"
        f"🏠 Хост: {context.user_data['proxy_host']}\n"
        f"🚪 Порт: {context.user_data['proxy_port']}{auth_info}\n\n"
        f"⚠️ После создания будет выполнена проверка работоспособности."
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Создать прокси", callback_data='confirm_proxy')],
        [InlineKeyboardButton("❌ Отменить", callback_data='manage_proxies')]
    ]
    
    await update.message.reply_text(
        confirmation_text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def create_proxy_server(query, context):
    """Создание прокси сервера"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    try:
        # Проверка данных
        required_fields = ['proxy_name', 'proxy_type', 'proxy_host', 'proxy_port']
        if not all(field in context.user_data for field in required_fields):
            await query.edit_message_text("❌ Ошибка создания прокси.")
            return
        
        # Валидация данных
        if not ProxyManager.validate_proxy_data(
            context.user_data['proxy_type'],
            context.user_data['proxy_host'],
            context.user_data['proxy_port']
        ):
            await query.edit_message_text("❌ Некорректные данные прокси.")
            return
        
        # Создание прокси
        proxy = ProxyManager.create_proxy(
            name=context.user_data['proxy_name'],
            proxy_type=context.user_data['proxy_type'],
            host=context.user_data['proxy_host'],
            port=context.user_data['proxy_port'],
            username=context.user_data.get('proxy_username'),
            password=context.user_data.get('proxy_password')
        )
        
        if not proxy:
            await query.edit_message_text("❌ Ошибка при создании прокси.")
            return
        
        # Проверка работоспособности
        await query.edit_message_text("🔍 Проверяю работоспособность прокси...")
        
        is_working = ProxyManager.check_proxy_health(proxy)
        
        session = Session()
        try:
            proxy.is_working = is_working
            proxy.last_check = datetime.now()
            session.merge(proxy)
            session.commit()
        finally:
            session.close()
        
        status_text = "✅ работает" if is_working else "❌ не работает"
        
        await query.edit_message_text(
            f"🌐 <b>Прокси создан!</b>\n\n"
            f"📝 Название: {proxy.name}\n"
            f"🌐 Адрес: {proxy.proxy_type}://{proxy.host}:{proxy.port}\n"
            f"📊 Статус: {status_text}\n"
            f"🆔 ID прокси: #{proxy.id}\n\n"
            f"{'✅ Прокси готов к использованию!' if is_working else '⚠️ Проверьте настройки прокси'}",
            parse_mode='HTML',
            reply_markup=proxy_menu()
        )
        
        logger.info(f"Создан прокси {proxy.id} пользователем {query.from_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка создания прокси: {e}")
        await query.edit_message_text("❌ Ошибка при создании прокси.")
    finally:
        context.user_data.clear()

async def delete_proxy_server(query, proxy_id):
    """Удаление прокси сервера"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    session = Session()
    try:
        proxy = session.query(ProxyServer).filter_by(id=proxy_id).first()
        if not proxy:
            await query.edit_message_text("❌ Прокси не найден.")
            return
        
        # Проверяем, используется ли прокси в сценариях
        from database.models import Scenario
        scenarios_count = session.query(Scenario).filter_by(proxy_id=proxy_id).count()
        
        if scenarios_count > 0:
            await query.edit_message_text(
                f"❌ <b>Нельзя удалить прокси '{proxy.name}'</b>\n\n"
                f"Он используется в {scenarios_count} активных сценариях.\n"
                f"Сначала остановите или удалите эти сценарии.",
                parse_mode='HTML',
                reply_markup=proxy_menu()
            )
            return
        
        proxy_name = proxy.name
        session.delete(proxy)
        session.commit()
        
        await query.edit_message_text(
            f"🗑️ Прокси <b>'{proxy_name}'</b> успешно удален.",
            parse_mode='HTML',
            reply_markup=proxy_menu()
        )
        
        logger.info(f"Удален прокси {proxy_id} пользователем {query.from_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка удаления прокси: {e}")
        await query.edit_message_text("❌ Ошибка при удалении прокси.")
    finally:
        session.close()

async def check_single_proxy(query, proxy_id):
    """Проверка одного прокси"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    session = Session()
    try:
        proxy = session.query(ProxyServer).filter_by(id=proxy_id).first()
        if not proxy:
            await query.edit_message_text("❌ Прокси не найден.")
            return
        
        await query.edit_message_text(f"🔍 Проверяю прокси <b>{proxy.name}</b>...", parse_mode='HTML')
        
        is_working = ProxyManager.check_proxy_health(proxy)
        proxy.is_working = is_working
        proxy.last_check = datetime.now()
        session.commit()
        
        status_text = "✅ работает" if is_working else "❌ не работает"
        
        await query.edit_message_text(
            f"🔍 <b>Результат проверки</b>\n\n"
            f"📝 Прокси: {proxy.name}\n"
            f"🌐 Адрес: {proxy.proxy_type}://{proxy.host}:{proxy.port}\n"
            f"📊 Статус: {status_text}\n"
            f"🕐 Проверено: {datetime.now().strftime('%d.%m %H:%M')}\n"
            f"📈 Использований: {proxy.usage_count}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К списку прокси", callback_data='list_proxies')
            ]])
        )
        
    except Exception as e:
        logger.error(f"Ошибка проверки прокси {proxy_id}: {e}")
        await query.edit_message_text("❌ Ошибка при проверке прокси.")
    finally:
        session.close()

async def manage_single_proxy(query, proxy_id):
    """Управление отдельным прокси"""
    if not is_admin(query.from_user.id):
        await query.edit_message_text("🚫 У вас нет доступа.")
        return
    
    session = Session()
    try:
        proxy = session.query(ProxyServer).filter_by(id=proxy_id).first()
        if not proxy:
            await query.edit_message_text("❌ Прокси не найден.")
            return
        
        # Статистика использования прокси
        from database.models import Scenario
        scenarios_using = session.query(Scenario).filter_by(proxy_id=proxy_id).count()
        
        status_emoji = "🟢" if proxy.is_active and proxy.is_working else "🔴"
        last_check = proxy.last_check.strftime('%d.%m %H:%M') if proxy.last_check else "Никогда"
        
        text = (
            f"⚙️ <b>Управление прокси #{proxy.id}</b>\n\n"
            f"📝 Название: {proxy.name}\n"
            f"🌐 Тип: {proxy.proxy_type.upper()}\n"
            f"🏠 Адрес: {proxy.host}:{proxy.port}\n"
            f"📊 Статус: {status_emoji}\n"
            f"🕐 Последняя проверка: {last_check}\n"
            f"📈 Использований: {proxy.usage_count}\n"
            f"🎯 В сценариях: {scenarios_using}\n"
            f"📅 Создан: {proxy.created_at.strftime('%d.%m.%Y %H:%M')}"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🔍 Проверить", callback_data=f'check_proxy_{proxy_id}'),
                InlineKeyboardButton("🔄 Сбросить счетчик", callback_data=f'reset_proxy_counter_{proxy_id}')
            ]
        ]
        
        # Кнопка активации/деактивации
        if proxy.is_active:
            keyboard.append([InlineKeyboardButton("⏸️ Деактивировать", callback_data=f'deactivate_proxy_{proxy_id}')])
        else:
            keyboard.append([InlineKeyboardButton("▶️ Активировать", callback_data=f'activate_proxy_{proxy_id}')])
        
        keyboard.extend([
            [InlineKeyboardButton("🗑️ Удалить", callback_data=f'delete_proxy_{proxy_id}')],
            [InlineKeyboardButton("🔙 К списку", callback_data='list_proxies')]
        ])
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Ошибка управления прокси {proxy_id}: {e}")
        await query.edit_message_text("❌ Ошибка при получении информации о прокси.")
    finally:
        session.close()