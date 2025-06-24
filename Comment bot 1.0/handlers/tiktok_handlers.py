"""
Полные обработчики для TikTok функционала
handlers/tiktok_handlers.py - НОВЫЙ ФАЙЛ
"""

import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.models import User, TikTokScenario, ProxyServer, TikTokPendingMessage, TikTokSentMessage
from database.connection import Session
from services.encryption import EncryptionService
from utils.validators import is_user, validate_instagram_credentials
from config import MAX_ACTIVE_SCENARIOS, tiktok_tasks
from services.tiktok_service import TikTokService

logger = logging.getLogger(__name__)

async def start_tiktok_scenario_creation(query, context, user_id):
    """Начало создания TikTok сценария"""
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            await query.edit_message_text("❌ Пользователь не найден.")
            return

        # Проверка лимита активных сценариев
        active_count = session.query(TikTokScenario).filter_by(
            user_id=user.id, 
            status='running'
        ).count()
        
        if active_count >= MAX_ACTIVE_SCENARIOS:
            await query.edit_message_text(
                f"❌ <b>Превышен лимит активных TikTok сценариев</b>\n\n"
                f"Максимум: {MAX_ACTIVE_SCENARIOS} активных сценариев\n"
                f"У вас сейчас: {active_count}\n\n"
                f"Остановите один из существующих сценариев перед созданием нового.",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📋 Мои TikTok сценарии", callback_data='my_tiktok_scenarios')
                ]])
            )
            return

        context.user_data.clear()
        context.user_data['platform'] = 'tiktok'
        context.user_data['step'] = 'tiktok_username'
        
        # Показ доступных прокси
        working_proxies = session.query(ProxyServer).filter_by(
            is_active=True, 
            is_working=True
        ).order_by(ProxyServer.usage_count.asc()).all()
        
        proxy_info = f"Доступно рабочих прокси: {len(working_proxies)}" if working_proxies else "❌ Нет доступных прокси"
        
        await query.edit_message_text(
            f"🎵 <b>Создание TikTok сценария</b>\n\n"
            f"📊 {proxy_info}\n\n"
            f"🔧 Шаг 1/6: Введите логин TikTok аккаунта:\n\n"
            f"💡 <i>Пример: username или user@email.com</i>\n\n"
            f"⚠️ <i>TikTok более строгий к ботам, рекомендуется использовать прокси</i>",
            parse_mode='HTML'
        )
    finally:
        session.close()

async def handle_tiktok_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстового ввода для TikTok сценария"""
    if context.user_data.get('platform') != 'tiktok':
        return False
        
    user_id = update.effective_user.id
    if not is_user(user_id):
        await update.message.reply_text("🚫 У вас нет доступа.")
        return True

    text = update.message.text.strip()
    step = context.user_data.get('step')

    try:
        if step == 'tiktok_username':
            if not text or len(text) < 1:
                await update.message.reply_text("❌ Введите корректный логин TikTok.")
                return True
                
            context.user_data['tiktok_username'] = text
            context.user_data['step'] = 'tiktok_password'
            await update.message.reply_text(
                "🔧 Шаг 2/6: Введите пароль TikTok аккаунта:\n\n"
                "⚠️ <i>Пароль будет зашифрован и сохранен безопасно</i>",
                parse_mode='HTML'
            )

        elif step == 'tiktok_password':
            if len(text) < 6:
                await update.message.reply_text("❌ Пароль должен содержать минимум 6 символов.")
                return True
                
            encrypted_password = EncryptionService.encrypt_password(text)
            context.user_data['tiktok_password'] = encrypted_password
            context.user_data['step'] = 'video_link'
            
            await update.message.reply_text(
                "🔧 Шаг 3/6: Введите ссылку на TikTok видео:\n\n"
                "📝 <i>Примеры:</i>\n"
                "• https://www.tiktok.com/@username/video/1234567890\n"
                "• https://vm.tiktok.com/ZMxxx/\n"
                "• https://m.tiktok.com/@username/video/1234567890",
                parse_mode='HTML'
            )

        elif step == 'video_link':
            if not validate_tiktok_video_link(text):
                await update.message.reply_text(
                    "❌ Введите корректную ссылку на TikTok видео.\n\n"
                    "✅ Правильные форматы:\n"
                    "• https://www.tiktok.com/@username/video/1234567890\n"
                    "• https://vm.tiktok.com/ZMxxx/\n"
                    "• https://m.tiktok.com/@username/video/1234567890"
                )
                return True
                
            context.user_data['video_link'] = text
            context.user_data['step'] = 'trigger_word'
            
            await update.message.reply_text(
                "🔧 Шаг 4/6: Введите триггерное слово или фразу:\n\n"
                "💡 <i>Примеры: 'заинтересован', 'хочу узнать', 'подробности', 'цена'</i>\n\n"
                "⚠️ Слово должно быть на том же языке, что и комментарии",
                parse_mode='HTML'
            )

        elif step == 'trigger_word':
            if len(text) < 2:
                await update.message.reply_text("❌ Триггерное слово должно содержать минимум 2 символа.")
                return True
                
            context.user_data['trigger_word'] = text
            context.user_data['step'] = 'dm_message'
            
            await update.message.reply_text(
                "🔧 Шаг 5/6: Введите сообщение для отправки в директ:\n\n"
                "📝 <i>Это сообщение будет отправлено пользователям TikTok, которые написали комментарий с триггерным словом</i>\n\n"
                "💡 <b>Советы:</b>\n"
                "• Будьте вежливы и информативны\n"
                "• Не используйте спам-слова\n"
                "• Максимум 500 символов для TikTok",
                parse_mode='HTML'
            )

        elif step == 'dm_message':
            if len(text) < 10:
                await update.message.reply_text("❌ Сообщение должно содержать минимум 10 символов.")
                return True
                
            if len(text) > 500:
                await update.message.reply_text("❌ Сообщение слишком длинное (максимум 500 символов для TikTok).")
                return True
                
            context.user_data['dm_message'] = text
            
            # Показ меню выбора прокси
            await show_tiktok_proxy_selection(update, context)

        return True

    except Exception as e:
        logger.error(f"Ошибка обработки ввода TikTok: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте снова.")
        return True

async def show_tiktok_proxy_selection(update, context):
    """Показ меню выбора прокси для TikTok"""
    session = Session()
    try:
        # Получаем рабочие прокси
        working_proxies = session.query(ProxyServer).filter_by(
            is_active=True, 
            is_working=True
        ).order_by(ProxyServer.usage_count.asc()).limit(10).all()
        
        keyboard = []
        
        if working_proxies:
            keyboard.append([InlineKeyboardButton("🎯 Лучший автоматически", callback_data='tiktok_choose_best_proxy')])
            keyboard.append([InlineKeyboardButton("🌐 Выбрать прокси", callback_data='tiktok_choose_proxy')])
        
        keyboard.append([InlineKeyboardButton("🛡️ Безопасный режим (без прокси)", callback_data='tiktok_no_proxy')])
        keyboard.append([InlineKeyboardButton("❌ Отменить", callback_data='tiktok_scenarios')])
        
        proxy_info = f"Доступно рабочих прокси: {len(working_proxies)}" if working_proxies else "❌ Нет доступных прокси"
        recommendation = ""
        
        if working_proxies:
            recommendation = (
                "\n\n💡 <b>Рекомендации для TikTok:</b>\n"
                "• TikTok агрессивно блокирует ботов\n"
                "• Прокси критически важны для стабильности\n"
                "• Используйте качественные приватные прокси\n"
                "• Безопасный режим только для тестирования"
            )
        else:
            recommendation = (
                "\n\n⚠️ <b>Внимание:</b>\n"
                "• Без прокси высокий риск блокировки\n"
                "• Добавьте прокси для стабильной работы\n"
                "• Безопасный режим может работать нестабильно"
            )
        
        await update.message.reply_text(
            f"🎵 <b>Выбор прокси для TikTok</b>\n\n"
            f"📊 {proxy_info}\n"
            f"{recommendation}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        session.close()

def validate_tiktok_video_link(link: str) -> bool:
    """Валидация ссылки на TikTok видео"""
    if not link or 'tiktok.com' not in link:
        return False
    
    valid_patterns = [
        '/video/',
        'vm.tiktok.com/',
        'm.tiktok.com/@'
    ]
    
    return any(pattern in link for pattern in valid_patterns)

async def handle_tiktok_proxy_selection(query, context):
    """Обработка выбора прокси для TikTok"""
    data = query.data
    
    if data == 'tiktok_choose_best_proxy':
        await choose_best_tiktok_proxy(query, context)
    elif data == 'tiktok_choose_proxy':
        await show_tiktok_proxy_list(query, context)
    elif data == 'tiktok_no_proxy':
        context.user_data['proxy_id'] = None
        context.user_data['safe_mode'] = True
        await show_tiktok_duration_selection(query, context)
    elif data.startswith('select_tiktok_proxy_'):
        proxy_id = int(data.split('_')[-1])
        context.user_data['proxy_id'] = proxy_id
        await show_tiktok_duration_selection(query, context)

async def choose_best_tiktok_proxy(query, context):
    """Автоматический выбор лучшего прокси для TikTok"""
    session = Session()
    try:
        # Находим лучший прокси по статистике
        best_proxy = session.query(ProxyServer).filter_by(
            is_active=True, 
            is_working=True
        ).order_by(ProxyServer.usage_count.asc()).first()
        
        if best_proxy:
            context.user_data['proxy_id'] = best_proxy.id
            
            await query.edit_message_text(
                f"🎯 <b>Автоматически выбран лучший прокси</b>\n\n"
                f"📡 Прокси: {best_proxy.name}\n"
                f"🌐 Тип: {best_proxy.proxy_type.upper()}\n"
                f"📈 Использований: {best_proxy.usage_count}\n\n"
                f"Продолжить создание TikTok сценария?",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Продолжить", callback_data='tiktok_confirm_proxy')],
                    [InlineKeyboardButton("📋 Выбрать другой", callback_data='tiktok_choose_proxy')],
                    [InlineKeyboardButton("🛡️ Без прокси", callback_data='tiktok_no_proxy')]
                ])
            )
        else:
            await query.edit_message_text(
                "❌ Нет доступных прокси.\n"
                "Создать TikTok сценарий без прокси или добавить новые прокси.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛡️ Безопасный режим", callback_data='tiktok_no_proxy')],
                    [InlineKeyboardButton("🔙 Назад", callback_data='tiktok_scenarios')]
                ])
            )
    finally:
        session.close()

async def show_tiktok_proxy_list(query, context):
    """Показ списка прокси для выбора"""
    session = Session()
    try:
        proxies = session.query(ProxyServer).filter_by(
            is_active=True, 
            is_working=True
        ).order_by(ProxyServer.usage_count.asc()).limit(10).all()
        
        if not proxies:
            await query.edit_message_text(
                "📭 Нет доступных прокси для TikTok",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data='tiktok_scenarios')
                ]])
            )
            return
        
        keyboard = []
        for proxy in proxies:
            status_emoji = "🟢" if proxy.is_working else "🔴"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_emoji} {proxy.name} ({proxy.usage_count} исп.)",
                    callback_data=f'select_tiktok_proxy_{proxy.id}'
                )
            ])
        
        keyboard.extend([
            [InlineKeyboardButton("🛡️ Без прокси", callback_data='tiktok_no_proxy')],
            [InlineKeyboardButton("🔙 Назад", callback_data='tiktok_scenarios')]
        ])
        
        await query.edit_message_text(
            "🌐 <b>Выберите прокси для TikTok:</b>\n\n"
            "💡 Рекомендуется выбрать прокси с наименьшим количеством использований",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        session.close()

async def show_tiktok_duration_selection(query, context):
    """Показ выбора срока активности TikTok сценария"""
    keyboard = [
        [InlineKeyboardButton("1 день", callback_data='tiktok_duration_1d')],
        [InlineKeyboardButton("3 дня", callback_data='tiktok_duration_3d')],
        [InlineKeyboardButton("7 дней", callback_data='tiktok_duration_7d')],
        [InlineKeyboardButton("14 дней", callback_data='tiktok_duration_14d')]
    ]
    
    await query.edit_message_text(
        "⏰ <b>Выберите срок активности TikTok сценария:</b>\n\n"
        "📊 <i>Рекомендация: начните с 1-3 дней для тестирования TikTok автоматизации</i>",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def create_tiktok_scenario(query, context, duration_days: int):
    """Создание TikTok сценария"""
    user_id = query.from_user.id
    session = Session()
    
    try:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            await query.edit_message_text("❌ Пользователь не найден.")
            return

        # Проверка данных
        required_fields = ['tiktok_username', 'tiktok_password', 'video_link', 'trigger_word', 'dm_message']
        missing_fields = [field for field in required_fields if field not in context.user_data]
        
        if missing_fields:
            await query.edit_message_text(
                f"❌ Не хватает данных: {', '.join(missing_fields)}\n"
                "Попробуйте создать сценарий заново."
            )
            context.user_data.clear()
            return

        # Создание сценария
        active_until = datetime.now() + timedelta(days=duration_days)
        
        scenario = TikTokScenario(
            user_id=user.id,
            proxy_id=context.user_data.get('proxy_id'),
            tiktok_username=context.user_data['tiktok_username'],
            tiktok_password_encrypted=context.user_data['tiktok_password'],
            video_link=context.user_data['video_link'],
            trigger_word=context.user_data['trigger_word'],
            dm_message=context.user_data['dm_message'],
            active_until=active_until
        )
        
        session.add(scenario)
        session.commit()
        
        # Информация о прокси
        proxy_info = "🌐 Прямое подключение (без прокси)"
        if scenario.proxy_server:
            proxy_info = f"🌐 Прокси: {scenario.proxy_server.name}"
        elif context.user_data.get('safe_mode'):
            proxy_info = "🛡️ Безопасный режим"
        
        await query.edit_message_text(
            f"✅ <b>TikTok сценарий создан!</b>\n\n"
            f"🆔 ID: #{scenario.id}\n"
            f"📱 Аккаунт: @{scenario.tiktok_username}\n"
            f"🎵 Видео: {scenario.video_link[:50]}...\n"
            f"🎯 Триггер: <code>{scenario.trigger_word}</code>\n"
            f"{proxy_info}\n"
            f"⏰ Активен до: {scenario.active_until.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"🚀 Сценарий будет запущен автоматически через несколько секунд!",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Мои TikTok сценарии", callback_data='my_tiktok_scenarios')],
                [InlineKeyboardButton("⚙️ Управление", callback_data=f'manage_tiktok_{scenario.id}')]
            ])
        )
        
        # Запуск сценария
        await start_tiktok_scenario_task(scenario.id, query.message.chat_id)
        
        context.user_data.clear()
        
    except Exception as e:
        logger.error(f"Ошибка создания TikTok сценария: {e}")
        await query.edit_message_text(
            f"❌ Ошибка при создании сценария: {str(e)[:100]}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Попробовать снова", callback_data='add_tiktok_scenario')
            ]])
        )
        session.rollback()
    finally:
        session.close()

async def start_tiktok_scenario_task(scenario_id: int, chat_id: int):
    """Запуск задачи TikTok сценария"""
    try:
        from services.tiktok_processor import process_tiktok_scenario
        
        # Создаем задачу
        task = asyncio.create_task(
            process_tiktok_scenario(scenario_id, chat_id)
        )
        
        # Сохраняем в глобальном словаре
        tiktok_tasks[scenario_id] = task
        
        logger.info(f"Запущена задача TikTok сценария {scenario_id}")
        
    except Exception as e:
        logger.error(f"Ошибка запуска TikTok задачи {scenario_id}: {e}")

async def show_tiktok_scenarios(query, user_id):
    """Показ TikTok сценариев пользователя"""
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            await query.edit_message_text("❌ Пользователь не найден.")
            return

        tiktok_scenarios = session.query(TikTokScenario).filter_by(user_id=user.id).all()
        
        if not tiktok_scenarios:
            await query.edit_message_text(
                "📭 <b>У вас пока нет TikTok сценариев</b>\n\n"
                "🎵 Создайте первый сценарий для автоматизации TikTok!\n\n"
                "💡 TikTok автоматизация позволяет:\n"
                "• Мониторить комментарии к видео\n"
                "• Автоматически отправлять DM сообщения\n"
                "• Находить потенциальных клиентов",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Создать TikTok сценарий", callback_data='add_tiktok_scenario')],
                    [InlineKeyboardButton("🔙 Назад", callback_data='back')]
                ])
            )
            return

        text = "🎵 <b>Ваши TikTok сценарии:</b>\n\n"
        keyboard = []
        
        for scenario in tiktok_scenarios:
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
            
            # Информация о прокси
            proxy_info = "🌐 Прямое подключение"
            if scenario.proxy_server:
                proxy_status = "🟢" if scenario.proxy_server.is_working else "🔴"
                proxy_info = f"🌐 {proxy_status} {scenario.proxy_server.name}"
            
            # Статистика сообщений
            pending_count = session.query(TikTokPendingMessage).filter_by(scenario_id=scenario.id).count()
            sent_count = session.query(TikTokSentMessage).filter_by(scenario_id=scenario.id).count()
            
            # Время до окончания
            time_left = scenario.active_until - datetime.now()
            if time_left.total_seconds() > 0:
                days_left = time_left.days
                hours_left = time_left.seconds // 3600
                time_info = f"{days_left}д {hours_left}ч" if days_left > 0 else f"{hours_left}ч"
            else:
                time_info = "Истек"
            
            text += (
                f"{status_emoji} <b>TikTok #{scenario.id}</b>\n"
                f"   📱 @{scenario.tiktok_username} {auth_emoji}\n"
                f"   {proxy_info}\n"
                f"   🎯 Триггер: <code>{scenario.trigger_word}</code>\n"
                f"   📊 Обработано: {scenario.comments_processed} комм.\n"
                f"   📩 Отправлено: {sent_count} | В очереди: {pending_count}\n"
                f"   ⏰ Активен: {time_info}\n\n"
            )
            
            keyboard.append([
                InlineKeyboardButton(
                    f"⚙️ TikTok #{scenario.id}", 
                    callback_data=f'manage_tiktok_{scenario.id}'
                )
            ])
        
        keyboard.extend([
            [InlineKeyboardButton("➕ Создать новый", callback_data='add_tiktok_scenario')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back')]
        ])
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        session.close()

async def show_tiktok_scenario_management(query, scenario_id, user_id):
    """Показ меню управления TikTok сценарием"""
    session = Session()
    try:
        scenario = session.query(TikTokScenario).filter_by(id=scenario_id).first()
        if not scenario:
            await query.edit_message_text("❌ TikTok сценарий не найден.")
            return
            
        if scenario.user.telegram_id != user_id:
            await query.edit_message_text("🚫 У вас нет доступа к этому сценарию.")
            return

        # Статистика
        pending_count = session.query(TikTokPendingMessage).filter_by(scenario_id=scenario_id).count()
        sent_count = session.query(TikTokSentMessage).filter_by(scenario_id=scenario_id).count()
        
        proxy_info = "🌐 Прямое подключение"
        if scenario.proxy_server:
            proxy_status = "🟢" if scenario.proxy_server.is_working else "🔴"
            proxy_info = f"🌐 {proxy_status} {scenario.proxy_server.name}"
        
        status_emoji = {
            'running': "🟢 Запущен",
            'paused': "⏸️ Приостановлен", 
            'stopped': "🔴 Остановлен"
        }.get(scenario.status, "❓ Неизвестно")
        
        auth_emoji = {
            'success': "✅ Авторизован",
            'waiting': "⏳ Ожидание",
            'failed': "❌ Ошибка"
        }.get(scenario.auth_status, "❓ Неизвестно")
        
        time_left = scenario.active_until - datetime.now()
        if time_left.total_seconds() > 0:
            days_left = time_left.days
            hours_left = time_left.seconds // 3600
            time_info = f"{days_left}д {hours_left}ч" if days_left > 0 else f"{hours_left}ч"
        else:
            time_info = "Истек"
        
        text = (
            f"⚙️ <b>Управление TikTok сценарием #{scenario_id}</b>\n\n"
            f"📱 Аккаунт: @{scenario.tiktok_username}\n"
            f"🎵 Видео: {scenario.video_link[:40]}...\n"
            f"🎯 Триггер: <code>{scenario.trigger_word}</code>\n"
            f"📊 Статус: {status_emoji}\n"
            f"🔐 Авторизация: {auth_emoji}\n"
            f"{proxy_info}\n\n"
            f"📈 <b>Статистика:</b>\n"
            f"• Обработано комментариев: {scenario.comments_processed}\n"
            f"• Отправлено сообщений: {sent_count}\n"
            f"• В очереди: {pending_count}\n"
            f"• Активен еще: {time_info}\n\n"
            f"📝 Сообщение: <i>{scenario.dm_message[:50]}...</i>"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔍 Проверить комментарии", callback_data=f'check_tiktok_comments_{scenario_id}')],
            [InlineKeyboardButton("📩 Отправить сообщения", callback_data=f'send_tiktok_messages_{scenario_id}')]
        ]
        
        # Кнопки управления в зависимости от статуса
        if scenario.status == 'running':
            keyboard.append([InlineKeyboardButton("⏸ Приостановить", callback_data=f'pause_tiktok_{scenario_id}')])
        elif scenario.status == 'paused':
            keyboard.append([InlineKeyboardButton("▶️ Возобновить", callback_data=f'resume_tiktok_{scenario_id}')])
        
        keyboard.extend([
            [InlineKeyboardButton("🚀 Перезапустить", callback_data=f'restart_tiktok_{scenario_id}')],
            [InlineKeyboardButton("🗑 Удалить", callback_data=f'delete_tiktok_{scenario_id}')],
            [InlineKeyboardButton("🔙 К списку", callback_data='my_tiktok_scenarios')]
        ])
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        session.close()

async def check_tiktok_comments(query, scenario_id, user_id):
    """Проверка комментариев TikTok сценария"""
    session = Session()
    try:
        scenario = session.query(TikTokScenario).filter_by(id=scenario_id).first()
        if not scenario or scenario.user.telegram_id != user_id:
            await query.edit_message_text("❌ Доступ запрещен.")
            return

        await query.edit_message_text(
            f"🔍 <b>Проверка комментариев TikTok #{scenario_id}</b>\n\n"
            f"⏳ Выполняется поиск новых комментариев...\n"
            f"📱 Аккаунт: @{scenario.tiktok_username}\n"
            f"🎯 Триггер: <code>{scenario.trigger_word}</code>",
            parse_mode='HTML'
        )
        
        # Запускаем проверку комментариев
        from services.tiktok_processor import check_tiktok_comments_task
        result = await check_tiktok_comments_task(scenario_id)
        
        if result['success']:
            await query.edit_message_text(
                f"✅ <b>Проверка завершена!</b>\n\n"
                f"📊 Найдено комментариев: {result.get('total_comments', 0)}\n"
                f"🎯 С триггером: {result.get('trigger_comments', 0)}\n"
                f"📩 Добавлено в очередь: {result.get('new_messages', 0)}\n\n"
                f"🕐 Время проверки: {datetime.now().strftime('%H:%M:%S')}",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data=f'manage_tiktok_{scenario_id}')
                ]])
            )
        else:
            await query.edit_message_text(
                f"❌ <b>Ошибка проверки</b>\n\n"
                f"Ошибка: {result.get('error', 'Неизвестная ошибка')}\n\n"
                f"Попробуйте позже или перезапустите сценарий.",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data=f'manage_tiktok_{scenario_id}')
                ]])
            )
    finally:
        session.close()

async def send_tiktok_messages(query, scenario_id, user_id):
    """Отправка сообщений из очереди TikTok"""
    session = Session()
    try:
        scenario = session.query(TikTokScenario).filter_by(id=scenario_id).first()
        if not scenario or scenario.user.telegram_id != user_id:
            await query.edit_message_text("❌ Доступ запрещен.")
            return

        pending_count = session.query(TikTokPendingMessage).filter_by(scenario_id=scenario_id).count()
        
        if pending_count == 0:
            await query.edit_message_text(
                "📭 <b>Очередь сообщений пуста</b>\n\n"
                "Сначала проверьте комментарии для поиска новых триггеров.",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔍 Проверить комментарии", callback_data=f'check_tiktok_comments_{scenario_id}'),
                    InlineKeyboardButton("🔙 Назад", callback_data=f'manage_tiktok_{scenario_id}')
                ]])
            )
            return

        await query.edit_message_text(
            f"📩 <b>Отправка TikTok сообщений</b>\n\n"
            f"⏳ Отправляю {pending_count} сообщений...\n"
            f"📱 Аккаунт: @{scenario.tiktok_username}",
            parse_mode='HTML'
        )
        
        # Запускаем отправку сообщений
        from services.tiktok_processor import send_tiktok_messages_task
        result = await send_tiktok_messages_task(scenario_id)
        
        await query.edit_message_text(
            f"✅ <b>Отправка завершена!</b>\n\n"
            f"📩 Отправлено: {result.get('sent_count', 0)}\n"
            f"❌ Ошибок: {result.get('failed_count', 0)}\n"
            f"⏳ Осталось в очереди: {result.get('remaining_count', 0)}\n\n"
            f"🕐 Время: {datetime.now().strftime('%H:%M:%S')}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data=f'manage_tiktok_{scenario_id}')
            ]])
        )
    finally:
        session.close()

async def pause_tiktok_scenario(query, scenario_id, user_id):
    """Приостановка TikTok сценария"""
    session = Session()
    try:
        scenario = session.query(TikTokScenario).filter_by(id=scenario_id).first()
        if not scenario or scenario.user.telegram_id != user_id:
            await query.edit_message_text("❌ Доступ запрещен.")
            return

        scenario.status = 'paused'
        session.merge(scenario)
        session.commit()
        
        # Останавливаем задачу
        if scenario_id in tiktok_tasks:
            tiktok_tasks[scenario_id].cancel()
            del tiktok_tasks[scenario_id]

        await query.edit_message_text(
            f"⏸️ <b>TikTok сценарий #{scenario_id} приостановлен</b>\n\n"
            f"📱 Аккаунт: @{scenario.tiktok_username}\n"
            f"🕐 Время: {datetime.now().strftime('%H:%M:%S')}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("▶️ Возобновить", callback_data=f'resume_tiktok_{scenario_id}'),
                InlineKeyboardButton("🔙 Назад", callback_data=f'manage_tiktok_{scenario_id}')
            ]])
        )
    finally:
        session.close()

async def resume_tiktok_scenario(query, scenario_id, user_id):
    """Возобновление TikTok сценария"""
    session = Session()
    try:
        scenario = session.query(TikTokScenario).filter_by(id=scenario_id).first()
        if not scenario or scenario.user.telegram_id != user_id:
            await query.edit_message_text("❌ Доступ запрещен.")
            return

        scenario.status = 'running'
        session.merge(scenario)
        session.commit()
        
        # Запускаем задачу
        await start_tiktok_scenario_task(scenario_id, query.message.chat_id)

        await query.edit_message_text(
            f"▶️ <b>TikTok сценарий #{scenario_id} возобновлен</b>\n\n"
            f"📱 Аккаунт: @{scenario.tiktok_username}\n"
            f"🕐 Время: {datetime.now().strftime('%H:%M:%S')}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⏸ Приостановить", callback_data=f'pause_tiktok_{scenario_id}'),
                InlineKeyboardButton("🔙 Назад", callback_data=f'manage_tiktok_{scenario_id}')
            ]])
        )
    finally:
        session.close()

async def restart_tiktok_scenario(query, scenario_id, user_id):
    """Перезапуск TikTok сценария"""
    session = Session()
    try:
        scenario = session.query(TikTokScenario).filter_by(id=scenario_id).first()
        if not scenario or scenario.user.telegram_id != user_id:
            await query.edit_message_text("❌ Доступ запрещен.")
            return

        # Останавливаем старую задачу
        if scenario_id in tiktok_tasks:
            tiktok_tasks[scenario_id].cancel()
            del tiktok_tasks[scenario_id]

        # Сбрасываем статус
        scenario.status = 'running'
        scenario.auth_status = 'waiting'
        scenario.auth_attempt = 1
        scenario.error_message = None
        session.merge(scenario)
        session.commit()

        await query.edit_message_text(
            f"🚀 <b>Перезапуск TikTok сценария #{scenario_id}</b>\n\n"
            f"📱 Аккаунт: @{scenario.tiktok_username}\n"
            f"⏳ Начинается новая авторизация...",
            parse_mode='HTML'
        )

        # Запускаем новую задачу
        await start_tiktok_scenario_task(scenario_id, query.message.chat_id)
        
    finally:
        session.close()

async def delete_tiktok_scenario(query, scenario_id, user_id):
    """Удаление TikTok сценария"""
    session = Session()
    try:
        scenario = session.query(TikTokScenario).filter_by(id=scenario_id).first()
        if not scenario or scenario.user.telegram_id != user_id:
            await query.edit_message_text("❌ Доступ запрещен.")
            return

        # Подтверждение удаления
        await query.edit_message_text(
            f"🗑 <b>Удаление TikTok сценария #{scenario_id}</b>\n\n"
            f"📱 Аккаунт: @{scenario.tiktok_username}\n"
            f"🎯 Триггер: <code>{scenario.trigger_word}</code>\n\n"
            f"⚠️ <b>Это действие необратимо!</b>\n"
            f"Все данные сценария будут удалены.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, удалить", callback_data=f'confirm_delete_tiktok_{scenario_id}')],
                [InlineKeyboardButton("❌ Отменить", callback_data=f'manage_tiktok_{scenario_id}')]
            ])
        )
    finally:
        session.close()

async def confirm_delete_tiktok_scenario(query, scenario_id, user_id):
    """Подтверждение удаления TikTok сценария"""
    session = Session()
    try:
        scenario = session.query(TikTokScenario).filter_by(id=scenario_id).first()
        if not scenario or scenario.user.telegram_id != user_id:
            await query.edit_message_text("❌ Доступ запрещен.")
            return

        # Останавливаем задачу
        if scenario_id in tiktok_tasks:
            tiktok_tasks[scenario_id].cancel()
            del tiktok_tasks[scenario_id]

        username = scenario.tiktok_username
        
        # Удаляем сценарий (связанные записи удаляются автоматически благодаря cascade)
        session.delete(scenario)
        session.commit()

        await query.edit_message_text(
            f"✅ <b>TikTok сценарий удален</b>\n\n"
            f"📱 Аккаунт: @{username}\n"
            f"🕐 Время: {datetime.now().strftime('%H:%M:%S')}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 Мои сценарии", callback_data='my_tiktok_scenarios')
            ]])
        )
        
    except Exception as e:
        logger.error(f"Ошибка удаления TikTok сценария: {e}")
        await query.edit_message_text("❌ Ошибка при удалении сценария.")
    finally:
        session.close()

# === CALLBACK ОБРАБОТЧИКИ ===

async def handle_tiktok_callbacks(update, context):
    """Основной обработчик TikTok callback'ов"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    try:
        # Создание сценария
        if data == 'add_tiktok_scenario':
            await start_tiktok_scenario_creation(query, context, user_id)
        
        # Просмотр сценариев
        elif data == 'my_tiktok_scenarios':
            await show_tiktok_scenarios(query, user_id)
        
        # Выбор прокси
        elif data in ['tiktok_choose_best_proxy', 'tiktok_choose_proxy', 'tiktok_no_proxy']:
            await handle_tiktok_proxy_selection(query, context)
        elif data.startswith('select_tiktok_proxy_'):
            await handle_tiktok_proxy_selection(query, context)
        elif data == 'tiktok_confirm_proxy':
            await show_tiktok_duration_selection(query, context)
        
        # Выбор срока активности
        elif data.startswith('tiktok_duration_'):
            duration = data.split('_')[-1]
            days = {'1d': 1, '3d': 3, '7d': 7, '14d': 14}.get(duration, 1)
            await create_tiktok_scenario(query, context, days)
        
        # Управление сценарием
        elif data.startswith('manage_tiktok_'):
            scenario_id = int(data.split('_')[-1])
            await show_tiktok_scenario_management(query, scenario_id, user_id)
        
        # Действия со сценарием
        elif data.startswith('check_tiktok_comments_'):
            scenario_id = int(data.split('_')[-1])
            await check_tiktok_comments(query, scenario_id, user_id)
        
        elif data.startswith('send_tiktok_messages_'):
            scenario_id = int(data.split('_')[-1])
            await send_tiktok_messages(query, scenario_id, user_id)
        
        elif data.startswith('pause_tiktok_'):
            scenario_id = int(data.split('_')[-1])
            await pause_tiktok_scenario(query, scenario_id, user_id)
        
        elif data.startswith('resume_tiktok_'):
            scenario_id = int(data.split('_')[-1])
            await resume_tiktok_scenario(query, scenario_id, user_id)
        
        elif data.startswith('restart_tiktok_'):
            scenario_id = int(data.split('_')[-1])
            await restart_tiktok_scenario(query, scenario_id, user_id)
        
        elif data.startswith('delete_tiktok_'):
            scenario_id = int(data.split('_')[-1])
            await delete_tiktok_scenario(query, scenario_id, user_id)
        
        elif data.startswith('confirm_delete_tiktok_'):
            scenario_id = int(data.split('_')[-1])
            await confirm_delete_tiktok_scenario(query, scenario_id, user_id)
        
    except Exception as e:
        logger.error(f"Ошибка обработки TikTok callback: {e}")
        await query.edit_message_text(
            f"❌ Произошла ошибка: {str(e)[:100]}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Главное меню", callback_data='back')
            ]])
        )