"""
Обработчики команд Telegram бота
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from database.models import Admin, User
from database.connection import Session
from utils.validators import is_admin, is_user
from ui.menus import main_menu
from config import ADMIN_TELEGRAM_ID, tasks, instabots

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    session = Session()
    
    try:
        # Добавляем первого админа если его нет
        if not session.query(Admin).first() and ADMIN_TELEGRAM_ID:
            session.add(Admin(telegram_id=int(ADMIN_TELEGRAM_ID)))
            session.commit()
            logger.info(f"Добавлен первый админ: {ADMIN_TELEGRAM_ID}")

        # Проверка доступа
        if not is_admin(user_id) and not is_user(user_id):
            await update.message.reply_text(
                "🚫 У вас нет доступа к боту.\n"
                "Обратитесь к администратору для получения доступа."
            )
            return

        # Автодобавление админа как пользователя
        if is_admin(user_id) and not is_user(user_id):
            session.add(User(telegram_id=user_id))
            session.commit()
            logger.info(f"Админ {user_id} добавлен как пользователь")

        is_admin_user = is_admin(user_id)
        is_user_user = is_user(user_id)
        
        welcome_text = (
            "🤖 <b>Instagram Automation Bot v2.0</b>\n\n"
            "👋 Добро пожаловать! Ваш помощник для автоматизации работы с комментариями Instagram.\n\n"
            "🎯 <b>Новые возможности:</b>\n"
            "• 🌐 Поддержка прокси серверов\n"
            "• 📥 Массовый импорт прокси (922Proxy)\n"
            "• 🔄 Автоматическая ротация прокси\n"
            "• 📊 Улучшенная статистика\n"
            "• ⚙️ Модульная архитектура\n\n"
            "Выберите действие в меню ниже:"
        )
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='HTML',
            reply_markup=main_menu(is_admin_user, is_user_user)
        )
        
    except Exception as e:
        logger.error(f"Ошибка в команде /start: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
    finally:
        session.close()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    if not is_admin(update.effective_user.id) and not is_user(update.effective_user.id):
        await update.message.reply_text("🚫 У вас нет доступа.")
        return

    help_text = """
🤖 <b>Instagram Automation Bot v2.0 - Справка</b>

<b>🆕 Что нового в версии 2.0:</b>
• 🌐 Полная поддержка прокси серверов
• 📥 Интеграция с 922Proxy и другими провайдерами
• 🔄 Автоматическая проверка и ротация прокси
• ⚙️ Модульная архитектура для лучшей производительности
• 📊 Расширенная аналитика и мониторинг

<b>📋 Основные функции:</b>
1. <b>Сценарии автоматизации</b> - поиск комментариев и отправка DM
2. <b>Управление прокси</b> - добавление, проверка, импорт
3. <b>Планирование задач</b> - автоматические проверки
4. <b>Детальная статистика</b> - отслеживание эффективности

<b>🌐 Работа с прокси:</b>
• Поддержка HTTP, HTTPS, SOCKS5
• Автоматическая проверка работоспособности
• Балансировка нагрузки между прокси
• Импорт из 922Proxy, Bright Data, Oxylabs

<b>🔧 Для пользователей:</b>
• /start - запуск бота и главное меню
• Создание сценариев через интерфейс
• Мониторинг через уведомления

<b>👑 Для администраторов:</b>
• /adduser [ID] - добавить пользователя
• /deleteuser [ID] - удалить пользователя  
• /addadmin [ID] - добавить администратора
• Полное управление прокси серверами
• Глобальная статистика и мониторинг

<b>🛡 Безопасность:</b>
• Все пароли зашифрованы AES-256
• Антидетект система через прокси
• Ограничения по запросам
• Автоматическая ротация IP

<b>⚡ Производительность:</b>
• Асинхронная обработка
• Оптимизированные запросы к Instagram
• Кэширование и балансировка нагрузки

<b>📞 Поддержка:</b>
При возникновении проблем обращайтесь к администратору или изучите документацию в разделе "Помощь".
"""
    
    await update.message.reply_text(help_text, parse_mode='HTML')

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление пользователя"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("🚫 У вас нет прав для этой команды.")
        return

    if not context.args:
        await update.message.reply_text(
            "📝 <b>Использование:</b> /adduser [Telegram ID]\n\n"
            "<i>Пример:</i> /adduser 123456789",
            parse_mode='HTML'
        )
        return

    try:
        new_user_id = int(context.args[0])
        session = Session()
        
        if session.query(User).filter_by(telegram_id=new_user_id).first():
            await update.message.reply_text("❌ Этот пользователь уже существует.")
        else:
            session.add(User(telegram_id=new_user_id))
            session.commit()
            await update.message.reply_text(f"✅ Пользователь {new_user_id} успешно добавлен.")
            logger.info(f"Админ {user_id} добавил пользователя {new_user_id}")
            
    except ValueError:
        await update.message.reply_text("❌ Укажите корректный Telegram ID (число).")
    except Exception as e:
        logger.error(f"Ошибка добавления пользователя: {e}")
        await update.message.reply_text("❌ Произошла ошибка при добавлении пользователя.")
    finally:
        session.close()

async def delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление пользователя"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("🚫 У вас нет прав для этой команды.")
        return

    if not context.args:
        await update.message.reply_text(
            "📝 <b>Использование:</b> /deleteuser [Telegram ID]\n\n"
            "<i>Пример:</i> /deleteuser 123456789",
            parse_mode='HTML'
        )
        return

    try:
        target_user_id = int(context.args[0])
        session = Session()
        
        user = session.query(User).filter_by(telegram_id=target_user_id).first()
        if not user:
            await update.message.reply_text(f"❌ Пользователь {target_user_id} не найден.")
        else:
            # Останавливаем все сценарии пользователя
            for scenario in user.scenarios:
                if scenario.id in tasks:
                    tasks[scenario.id].cancel()
                    del tasks[scenario.id]
                if scenario.id in instabots:
                    try:
                        instabots[scenario.id].logout()
                    except:
                        pass
                    del instabots[scenario.id]
                    
            session.delete(user)
            session.commit()
            await update.message.reply_text(f"✅ Пользователь {target_user_id} удален вместе со всеми сценариями.")
            logger.info(f"Админ {user_id} удалил пользователя {target_user_id}")
            
    except ValueError:
        await update.message.reply_text("❌ Укажите корректный Telegram ID (число).")
    except Exception as e:
        logger.error(f"Ошибка удаления пользователя: {e}")
        await update.message.reply_text("❌ Произошла ошибка при удалении пользователя.")
    finally:
        session.close()

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление администратора"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("🚫 У вас нет прав для этой команды.")
        return

    if not context.args:
        await update.message.reply_text(
            "📝 <b>Использование:</b> /addadmin [Telegram ID]\n\n"
            "<i>Пример:</i> /addadmin 123456789",
            parse_mode='HTML'
        )
        return

    try:
        new_admin_id = int(context.args[0])
        session = Session()
        
        if session.query(Admin).filter_by(telegram_id=new_admin_id).first():
            await update.message.reply_text("❌ Этот администратор уже существует.")
        else:
            session.add(Admin(telegram_id=new_admin_id))
            # Также добавляем как пользователя если его нет
            if not session.query(User).filter_by(telegram_id=new_admin_id).first():
                session.add(User(telegram_id=new_admin_id))
            session.commit()
            await update.message.reply_text(f"✅ Администратор {new_admin_id} добавлен.")
            logger.info(f"Админ {user_id} добавил админа {new_admin_id}")
            
    except ValueError:
        await update.message.reply_text("❌ Укажите корректный Telegram ID (число).")
    except Exception as e:
        logger.error(f"Ошибка добавления админа: {e}")
        await update.message.reply_text("❌ Произошла ошибка при добавлении администратора.")
    finally:
        session.close()