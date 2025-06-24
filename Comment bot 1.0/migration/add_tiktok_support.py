#!/usr/bin/env python3
"""
Скрипт миграции базы данных для добавления поддержки TikTok
migrations/add_tiktok_support.py - НОВЫЙ ФАЙЛ
"""

import sys
import os
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Добавляем корневую директорию в путь для импорта модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATABASE_PATH
from database.models import Base
from database.connection import engine

logger = logging.getLogger(__name__)

class TikTokMigration:
    """Класс для выполнения миграции TikTok"""
    
    def __init__(self):
        self.engine = engine
        self.migration_name = "add_tiktok_support"
        self.migration_version = "2.0.0"
        
    def check_migration_status(self) -> bool:
        """Проверка, была ли уже выполнена миграция"""
        try:
            with self.engine.connect() as conn:
                # Проверяем существование таблицы tiktok_scenarios
                result = conn.execute(text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='tiktok_scenarios'
                """))
                
                if result.fetchone():
                    print("✅ Миграция TikTok уже выполнена")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Ошибка проверки статуса миграции: {e}")
            return False
    
    def backup_database(self) -> bool:
        """Создание резервной копии базы данных"""
        try:
            if 'sqlite:///' in DATABASE_PATH:
                db_file = DATABASE_PATH.replace('sqlite:///', '')
                backup_file = f"{db_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Создаем резервную копию
                import shutil
                shutil.copy2(db_file, backup_file)
                
                print(f"✅ Резервная копия создана: {backup_file}")
                return True
            else:
                print("⚠️ Резервное копирование поддерживается только для SQLite")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка создания резервной копии: {e}")
            return False
    
    def create_migration_log_table(self):
        """Создание таблицы для отслеживания миграций"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS migration_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        migration_name VARCHAR(100) NOT NULL,
                        version VARCHAR(20) NOT NULL,
                        executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN DEFAULT TRUE,
                        error_message TEXT
                    )
                """))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Ошибка создания таблицы миграций: {e}")
            raise
    
    def log_migration(self, success: bool, error_message: str = None):
        """Запись результата миграции в лог"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO migration_log (migration_name, version, success, error_message)
                    VALUES (:name, :version, :success, :error)
                """), {
                    'name': self.migration_name,
                    'version': self.migration_version,
                    'success': success,
                    'error': error_message
                })
                conn.commit()
                
        except Exception as e:
            logger.error(f"Ошибка записи лога миграции: {e}")
    
    def execute_migration(self) -> bool:
        """Выполнение основной миграции"""
        try:
            print("🚀 Начало миграции для добавления поддержки TikTok...")
            
            # Создаем все новые таблицы
            Base.metadata.create_all(self.engine)
            
            # Проверяем, что таблицы созданы
            with self.engine.connect() as conn:
                # Проверяем основные TikTok таблицы
                required_tables = [
                    'tiktok_scenarios',
                    'tiktok_sent_messages', 
                    'tiktok_pending_messages',
                    'tiktok_authentication_logs'
                ]
                
                for table in required_tables:
                    result = conn.execute(text(f"""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name='{table}'
                    """))
                    
                    if not result.fetchone():
                        raise Exception(f"Таблица {table} не была создана")
                    else:
                        print(f"✅ Таблица {table} создана успешно")
            
            # Обновляем существующие таблицы при необходимости
            self._update_existing_tables()
            
            print("✅ Миграция TikTok выполнена успешно!")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка выполнения миграции: {e}")
            print(f"❌ Ошибка миграции: {e}")
            return False
    
    def _update_existing_tables(self):
        """Обновление существующих таблиц для поддержки TikTok"""
        try:
            with self.engine.connect() as conn:
                # Добавляем новые колонки в proxy_performance если их нет
                try:
                    conn.execute(text("""
                        ALTER TABLE proxy_performance 
                        ADD COLUMN tiktok_auth_attempts INTEGER DEFAULT 0
                    """))
                    print("✅ Добавлена колонка tiktok_auth_attempts")
                except:
                    pass  # Колонка уже существует
                
                try:
                    conn.execute(text("""
                        ALTER TABLE proxy_performance 
                        ADD COLUMN tiktok_auth_successes INTEGER DEFAULT 0
                    """))
                    print("✅ Добавлена колонка tiktok_auth_successes")
                except:
                    pass
                
                try:
                    conn.execute(text("""
                        ALTER TABLE proxy_performance 
                        ADD COLUMN tiktok_challenge_rate REAL DEFAULT 0.0
                    """))
                    print("✅ Добавлена колонка tiktok_challenge_rate")
                except:
                    pass
                
                try:
                    conn.execute(text("""
                        ALTER TABLE proxy_performance 
                        ADD COLUMN total_usage_count INTEGER DEFAULT 0
                    """))
                    print("✅ Добавлена колонка total_usage_count")
                except:
                    pass
                
                # Создаем таблицу настроек пользователей если её нет
                try:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS user_settings (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            preferred_platform VARCHAR(20) DEFAULT 'instagram',
                            timezone VARCHAR(50) DEFAULT 'UTC',
                            language VARCHAR(10) DEFAULT 'ru',
                            notify_auth_success BOOLEAN DEFAULT TRUE,
                            notify_auth_failed BOOLEAN DEFAULT TRUE,
                            notify_messages_sent BOOLEAN DEFAULT TRUE,
                            notify_daily_summary BOOLEAN DEFAULT FALSE,
                            max_scenarios_instagram INTEGER DEFAULT 2,
                            max_scenarios_tiktok INTEGER DEFAULT 2,
                            auto_pause_on_errors BOOLEAN DEFAULT TRUE,
                            require_proxy_for_tiktok BOOLEAN DEFAULT FALSE,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users (id)
                        )
                    """))
                    print("✅ Создана таблица user_settings")
                except:
                    pass
                
                # Создаем таблицу статистики платформ
                try:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS platform_stats (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            platform VARCHAR(20) NOT NULL,
                            date DATETIME DEFAULT CURRENT_TIMESTAMP,
                            active_scenarios INTEGER DEFAULT 0,
                            successful_auths INTEGER DEFAULT 0,
                            failed_auths INTEGER DEFAULT 0,
                            messages_sent INTEGER DEFAULT 0,
                            messages_failed INTEGER DEFAULT 0,
                            comments_processed INTEGER DEFAULT 0,
                            triggers_found INTEGER DEFAULT 0,
                            avg_auth_time REAL DEFAULT 0.0,
                            avg_message_time REAL DEFAULT 0.0
                        )
                    """))
                    print("✅ Создана таблица platform_stats")
                except:
                    pass
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Ошибка обновления существующих таблиц: {e}")
            raise
    
    def verify_migration(self) -> bool:
        """Проверка успешности миграции"""
        try:
            with self.engine.connect() as conn:
                # Проверяем структуру новых таблиц
                test_queries = [
                    "SELECT COUNT(*) FROM tiktok_scenarios",
                    "SELECT COUNT(*) FROM tiktok_sent_messages",
                    "SELECT COUNT(*) FROM tiktok_pending_messages",
                    "SELECT COUNT(*) FROM tiktok_authentication_logs",
                    "SELECT COUNT(*) FROM user_settings",
                    "SELECT COUNT(*) FROM platform_stats"
                ]
                
                for query in test_queries:
                    try:
                        result = conn.execute(text(query))
                        count = result.scalar()
                        table_name = query.split("FROM ")[1]
                        print(f"✅ Таблица {table_name}: {count} записей")
                    except Exception as e:
                        print(f"❌ Ошибка проверки таблицы {query}: {e}")
                        return False
                
                # Проверяем связи между таблицами
                conn.execute(text("""
                    SELECT ts.id, u.telegram_id, ps.name 
                    FROM tiktok_scenarios ts
                    LEFT JOIN users u ON ts.user_id = u.id
                    LEFT JOIN proxy_servers ps ON ts.proxy_id = ps.id
                    LIMIT 1
                """))
                
                print("✅ Связи между таблицами работают корректно")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка проверки миграции: {e}")
            print(f"❌ Ошибка проверки миграции: {e}")
            return False
    
    def rollback_migration(self) -> bool:
        """Откат миграции (удаление TikTok таблиц)"""
        try:
            print("🔄 Начало отката миграции TikTok...")
            
            with self.engine.connect() as conn:
                # Удаляем TikTok таблицы в правильном порядке (с учетом внешних ключей)
                tables_to_drop = [
                    'tiktok_authentication_logs',
                    'tiktok_pending_messages',
                    'tiktok_sent_messages',
                    'tiktok_scenarios',
                    'platform_stats'
                ]
                
                for table in tables_to_drop:
                    try:
                        conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                        print(f"✅ Удалена таблица {table}")
                    except Exception as e:
                        print(f"⚠️ Не удалось удалить таблицу {table}: {e}")
                
                # Удаляем добавленные колонки из proxy_performance
                # SQLite не поддерживает DROP COLUMN, поэтому пересоздаем таблицу
                try:
                    conn.execute(text("""
                        CREATE TABLE proxy_performance_backup AS 
                        SELECT id, proxy_id, auth_attempts, auth_successes, 
                               challenge_rate, avg_response_time, last_success, 
                               last_failure, blacklisted_until
                        FROM proxy_performance
                    """))
                    
                    conn.execute(text("DROP TABLE proxy_performance"))
                    conn.execute(text("ALTER TABLE proxy_performance_backup RENAME TO proxy_performance"))
                    
                    print("✅ Восстановлена исходная структура proxy_performance")
                except Exception as e:
                    print(f"⚠️ Ошибка восстановления proxy_performance: {e}")
                
                conn.commit()
                
            print("✅ Откат миграции выполнен успешно")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отката миграции: {e}")
            print(f"❌ Ошибка отката: {e}")
            return False

def main():
    """Основная функция миграции"""
    print("=" * 60)
    print("🎵 Instagram Automation Bot v2.0 - TikTok Migration")
    print("=" * 60)
    
    migration = TikTokMigration()
    
    # Проверяем, не была ли уже выполнена миграция
    if migration.check_migration_status():
        choice = input("Миграция уже выполнена. Хотите выполнить откат? (y/N): ")
        if choice.lower() == 'y':
            success = migration.rollback_migration()
            migration.log_migration(success, None if success else "Rollback failed")
        return
    
    try:
        # Создаем таблицу логов миграций
        migration.create_migration_log_table()
        
        # Создаем резервную копию
        if not migration.backup_database():
            choice = input("Не удалось создать резервную копию. Продолжить? (y/N): ")
            if choice.lower() != 'y':
                return
        
        # Выполняем миграцию
        success = migration.execute_migration()
        
        if success:
            # Проверяем результат
            if migration.verify_migration():
                migration.log_migration(True)
                print("\n🎉 Миграция TikTok завершена успешно!")
                print("Теперь можно запускать бота с поддержкой TikTok")
            else:
                migration.log_migration(False, "Verification failed")
                print("\n❌ Миграция выполнена, но проверка не прошла")
        else:
            migration.log_migration(False, "Migration execution failed")
            print("\n❌ Миграция не удалась")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Миграция прервана пользователем")
        migration.log_migration(False, "Interrupted by user")
    except Exception as e:
        print(f"\n❌ Критическая ошибка миграции: {e}")
        migration.log_migration(False, str(e))
        logger.error(f"Критическая ошибка миграции: {e}")

if __name__ == "__main__":
    # Настраиваем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('migration.log'),
            logging.StreamHandler()
        ]
    )
    
    main()