"""
Планировщик задач для фоновых операций
"""

import logging
from datetime import datetime, timedelta
from telegram.ext import ContextTypes

from database.models import Scenario, RequestLog, ProxyServer
from database.connection import Session
from services.instagram import cleanup_inactive_scenarios
from services.proxy_922 import Proxy922Manager

logger = logging.getLogger(__name__)

async def check_scheduled_tasks(context: ContextTypes.DEFAULT_TYPE):
    """Проверка запланированных задач"""
    session = Session()
    try:
        now = datetime.now()
        scheduled_scenarios = session.query(Scenario).filter(
            Scenario.next_check_time <= now,
            Scenario.status == 'running',
            Scenario.auth_status == 'success'
        ).all()
        
        for scenario in scheduled_scenarios:
            try:
                bot = context.bot
                user = scenario.user
                
                from services.instagram import auto_check_comments
                await auto_check_comments(scenario.id, bot, user.telegram_id)
                
                # Сброс времени следующей проверки
                scenario.next_check_time = None
                session.merge(scenario)
                session.commit()
                
            except Exception as e:
                logger.error(f"Ошибка выполнения запланированной задачи для сценария {scenario.id}: {e}")
                
    except Exception as e:
        logger.error(f"Ошибка в фоновой задаче check_scheduled_tasks: {e}")
    finally:
        session.close()

async def cleanup_old_data(context: ContextTypes.DEFAULT_TYPE):
    """Очистка старых данных"""
    session = Session()
    try:
        # Удаление логов старше 7 дней
        week_ago = datetime.now() - timedelta(days=7)
        old_logs = session.query(RequestLog).filter(RequestLog.request_time < week_ago)
        deleted_logs = old_logs.count()
        old_logs.delete()
        
        # Очистка неактивных сценариев
        cleaned_scenarios = cleanup_inactive_scenarios()
        
        session.commit()
        
        if deleted_logs > 0 or cleaned_scenarios > 0:
            logger.info(f"Очищено: {deleted_logs} логов, {cleaned_scenarios} просроченных сценариев")
            
    except Exception as e:
        logger.error(f"Ошибка очистки данных: {e}")
        session.rollback()
    finally:
        session.close()

async def check_proxy_health_scheduled(context: ContextTypes.DEFAULT_TYPE):
    """Планируемая проверка работоспособности прокси"""
    try:
        # Пакетная проверка случайных прокси
        results = Proxy922Manager.bulk_check_proxies(batch_size=5)
        
        if results['checked'] > 0:
            logger.info(f"Автоматическая проверка прокси: {results['working']} работают, {results['failed']} не работают")
        
        # Автоматическая ротация прокси
        deactivated = Proxy922Manager.auto_rotate_proxies()
        if deactivated > 0:
            logger.info(f"Автоматически деактивировано {deactivated} неработающих прокси")
            
    except Exception as e:
        logger.error(f"Ошибка планируемой проверки прокси: {e}")

async def send_daily_reports(context: ContextTypes.DEFAULT_TYPE):
    """Отправка ежедневных отчетов администраторам"""
    try:
        from database.models import Admin, User
        from config import ADMIN_TELEGRAM_ID
        
        session = Session()
        
        # Статистика за последние 24 часа
        yesterday = datetime.now() - timedelta(days=1)
        
        # Активные сценарии
        active_scenarios = session.query(Scenario).filter_by(status='running').count()
        
        # Новые пользователи за день
        new_users = session.query(User).filter(User.created_at >= yesterday).count()
        
        # Запросы за день
        daily_requests = session.query(RequestLog).filter(RequestLog.request_time >= yesterday).count()
        successful_requests = session.query(RequestLog).filter(
            RequestLog.request_time >= yesterday,
            RequestLog.success == True
        ).count()
        
        # Статистика прокси
        working_proxies = session.query(ProxyServer).filter_by(is_active=True, is_working=True).count()
        total_proxies = session.query(ProxyServer).filter_by(is_active=True).count()
        
        report_text = (
            f"📊 <b>Ежедневный отчет</b>\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
            f"<b>🤖 Сценарии:</b>\n"
            f"• Активных: {active_scenarios}\n\n"
            f"<b>👥 Пользователи:</b>\n"
            f"• Новых за день: {new_users}\n\n"
            f"<b>📈 Активность:</b>\n"
            f"• Запросов за день: {daily_requests}\n"
            f"• Успешных: {successful_requests}\n"
            f"• Успешность: {(successful_requests/daily_requests*100):.1f}%\n\n" if daily_requests > 0 else "• Запросов не было\n\n"
            f"<b>🌐 Прокси:</b>\n"
            f"• Работающих: {working_proxies}/{total_proxies}\n"
        )
        
        # Отправка отчета всем админам
        admins = session.query(Admin).all()
        bot = context.bot
        
        for admin in admins:
            try:
                await bot.send_message(
                    chat_id=admin.telegram_id,
                    text=report_text,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Ошибка отправки отчета админу {admin.telegram_id}: {e}")
        
        session.close()
        
    except Exception as e:
        logger.error(f"Ошибка отправки ежедневных отчетов: {e}")

async def monitor_scenarios_health(context: ContextTypes.DEFAULT_TYPE):
    """Мониторинг здоровья сценариев"""
    try:
        session = Session()
        
        # Проверяем сценарии с ошибками авторизации
        failed_scenarios = session.query(Scenario).filter(
            Scenario.status == 'running',
            Scenario.auth_status == 'failed'
        ).all()
        
        if failed_scenarios:
            from database.models import Admin
            admins = session.query(Admin).all()
            bot = context.bot
            
            alert_text = (
                f"⚠️ <b>Проблемы со сценариями</b>\n\n"
                f"Найдено {len(failed_scenarios)} сценариев с ошибками авторизации:\n\n"
            )
            
            for scenario in failed_scenarios[:5]:  # Показываем первые 5
                alert_text += f"• #{scenario.id} @{scenario.ig_username}\n"
            
            if len(failed_scenarios) > 5:
                alert_text += f"... и еще {len(failed_scenarios) - 5} сценариев\n"
            
            alert_text += "\n🔧 Требуется внимание администратора"
            
            for admin in admins:
                try:
                    await bot.send_message(
                        chat_id=admin.telegram_id,
                        text=alert_text,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления админу {admin.telegram_id}: {e}")
        
        session.close()
        
    except Exception as e:
        logger.error(f"Ошибка мониторинга здоровья сценариев: {e}")

async def optimize_proxy_usage(context: ContextTypes.DEFAULT_TYPE):
    """Оптимизация использования прокси"""
    try:
        session = Session()
        
        # Балансировка нагрузки на прокси
        scenarios_with_proxy = session.query(Scenario).filter(
            Scenario.proxy_id.isnot(None),
            Scenario.status == 'running'
        ).all()
        
        # Группируем по прокси и считаем нагрузку
        proxy_usage = {}
        for scenario in scenarios_with_proxy:
            proxy_id = scenario.proxy_id
            if proxy_id not in proxy_usage:
                proxy_usage[proxy_id] = []
            proxy_usage[proxy_id].append(scenario)
        
        # Находим перегруженные прокси (более 3 сценариев на один прокси)
        overloaded_proxies = {pid: scenarios for pid, scenarios in proxy_usage.items() if len(scenarios) > 3}
        
        if overloaded_proxies:
            logger.info(f"Найдено {len(overloaded_proxies)} перегруженных прокси")
            
            # Здесь можно добавить логику перебалансировки
            # Например, переназначение части сценариев на менее загруженные прокси
        
        session.close()
        
    except Exception as e:
        logger.error(f"Ошибка оптимизации использования прокси: {e}")

async def backup_database(context: ContextTypes.DEFAULT_TYPE):
    """Создание резервной копии базы данных"""
    try:
        import shutil
        import os
        from config import DATABASE_PATH
        
        # Извлекаем путь к файлу БД из DATABASE_PATH
        if 'sqlite:///' in DATABASE_PATH:
            db_file_path = DATABASE_PATH.replace('sqlite:///', '')
        else:
            logger.warning("Резервное копирование поддерживается только для SQLite")
            return
        
        if not os.path.exists(db_file_path):
            logger.warning(f"Файл базы данных не найден: {db_file_path}")
            return
        
        # Создаем папку для бэкапов
        backup_dir = os.path.join(os.path.dirname(db_file_path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Создаем имя файла бэкапа с датой
        backup_filename = f"bot_database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Копируем файл
        shutil.copy2(db_file_path, backup_path)
        
        # Удаляем старые бэкапы (оставляем только последние 7)
        backup_files = [f for f in os.listdir(backup_dir) if f.startswith('bot_database_backup_')]
        backup_files.sort(reverse=True)
        
        for old_backup in backup_files[7:]:  # Удаляем все кроме последних 7
            try:
                os.remove(os.path.join(backup_dir, old_backup))
            except:
                pass
        
        logger.info(f"Создана резервная копия базы данных: {backup_filename}")
        
    except Exception as e:
        logger.error(f"Ошибка создания резервной копии: {e}")

# === ПЛАНИРОВЩИК УВЕДОМЛЕНИЙ ===

async def send_low_proxy_alert(context: ContextTypes.DEFAULT_TYPE):
    """Уведомление о нехватке рабочих прокси"""
    try:
        session = Session()
        
        working_proxies_count = session.query(ProxyServer).filter_by(
            is_active=True, 
            is_working=True
        ).count()
        
        # Если рабочих прокси меньше 3, отправляем уведомление
        if working_proxies_count < 3:
            from database.models import Admin
            admins = session.query(Admin).all()
            bot = context.bot
            
            alert_text = (
                f"⚠️ <b>Критически мало рабочих прокси!</b>\n\n"
                f"🌐 Рабочих прокси: {working_proxies_count}\n"
                f"🎯 Рекомендуется минимум: 5\n\n"
                f"📥 Добавьте новые прокси или проверьте существующие"
            )
            
            for admin in admins:
                try:
                    await bot.send_message(
                        chat_id=admin.telegram_id,
                        text=alert_text,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления о прокси админу {admin.telegram_id}: {e}")
        
        session.close()
        
    except Exception as e:
        logger.error(f"Ошибка проверки количества прокси: {e}")

# === СИСТЕМА АВТОМАТИЧЕСКИХ ЗАДАЧ ===

class TaskScheduler:
    """Планировщик автоматических задач"""
    
    @staticmethod
    def setup_scheduled_jobs(job_queue):
        """Настройка всех запланированных задач"""
        
        # Проверка запланированных задач сценариев - каждую минуту
        job_queue.run_repeating(
            check_scheduled_tasks, 
            interval=60, 
            first=0,
            name="check_scheduled_tasks"
        )
        
        # Очистка старых данных - каждый час
        job_queue.run_repeating(
            cleanup_old_data, 
            interval=3600, 
            first=3600,
            name="cleanup_old_data"
        )
        
        # Проверка прокси - каждые 30 минут
        job_queue.run_repeating(
            check_proxy_health_scheduled, 
            interval=1800, 
            first=300,  # Первая проверка через 5 минут после запуска
            name="check_proxy_health"
        )
        
        # Мониторинг здоровья сценариев - каждые 10 минут
        job_queue.run_repeating(
            monitor_scenarios_health, 
            interval=600, 
            first=600,
            name="monitor_scenarios_health"
        )
        
        # Оптимизация использования прокси - каждые 2 часа
        job_queue.run_repeating(
            optimize_proxy_usage, 
            interval=7200, 
            first=7200,
            name="optimize_proxy_usage"
        )
        
        # Проверка количества прокси - каждые 4 часа
        job_queue.run_repeating(
            send_low_proxy_alert, 
            interval=14400, 
            first=1800,
            name="low_proxy_alert"
        )
        
        # Резервное копирование - каждые 6 часов
        job_queue.run_repeating(
            backup_database, 
            interval=21600, 
            first=21600,
            name="backup_database"
        )
        
        # Ежедневные отчеты - в 9:00 каждый день
        job_queue.run_daily(
            send_daily_reports,
            time=datetime.now().replace(hour=9, minute=0, second=0).time(),
            name="daily_reports"
        )
        
        logger.info("✅ Все запланированные задачи настроены")

def get_scheduler_status() -> dict:
    """Получение статуса планировщика"""
    try:
        session = Session()
        
        # Статистика задач
        pending_checks = session.query(Scenario).filter(
            Scenario.next_check_time.isnot(None),
            Scenario.status == 'running'
        ).count()
        
        active_scenarios = session.query(Scenario).filter_by(status='running').count()
        
        # Статистика за последний час
        hour_ago = datetime.now() - timedelta(hours=1)
        recent_requests = session.query(RequestLog).filter(
            RequestLog.request_time >= hour_ago
        ).count()
        
        session.close()
        
        return {
            'pending_checks': pending_checks,
            'active_scenarios': active_scenarios,
            'recent_requests': recent_requests,
            'last_update': datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения статуса планировщика: {e}")
        return {}