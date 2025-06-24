"""
Обновленные меню и клавиатуры для Instagram Automation Bot v2.0 с поддержкой TikTok
ui/menus.py - ОБНОВЛЕННЫЙ ФАЙЛ
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import ENABLE_TIKTOK

def main_menu(is_admin_user: bool, is_user_user: bool) -> InlineKeyboardMarkup:
    """Главное меню с выбором платформы"""
    keyboard = []
    
    if is_user_user:
        # Если обе платформы доступны, показываем выбор
        if ENABLE_TIKTOK:
            keyboard.append([
                InlineKeyboardButton("📸 Instagram", callback_data='instagram_scenarios'),
                InlineKeyboardButton("🎵 TikTok", callback_data='tiktok_scenarios')
            ])
        else:
            # Только Instagram
            keyboard.append([InlineKeyboardButton("📂 Сценарии", callback_data='instagram_scenarios')])
    
    if is_admin_user:
        keyboard.append([InlineKeyboardButton("👑 Админ-панель", callback_data='admin_panel')])
    
    keyboard.append([InlineKeyboardButton("❓ Помощь", callback_data='help')])
    
    return InlineKeyboardMarkup(keyboard)

def platforms_menu() -> InlineKeyboardMarkup:
    """Меню выбора платформы"""
    keyboard = [
        [InlineKeyboardButton("📸 Instagram сценарии", callback_data='instagram_scenarios')]
    ]
    
    if ENABLE_TIKTOK:
        keyboard.append([InlineKeyboardButton("🎵 TikTok сценарии", callback_data='tiktok_scenarios')])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='back')])
    
    return InlineKeyboardMarkup(keyboard)

def admin_menu() -> InlineKeyboardMarkup:
    """Меню администратора с поддержкой TikTok"""
    keyboard = [
        [InlineKeyboardButton("👥 Пользователи", callback_data='manage_users')],
        [InlineKeyboardButton("👑 Администраторы", callback_data='manage_admins')],
        [InlineKeyboardButton("🌐 Прокси", callback_data='manage_proxies')],
        [InlineKeyboardButton("⚙️ Настройки авторизации", callback_data='auth_settings')],
        [InlineKeyboardButton("📊 Статистика", callback_data='status_scenarios')]
    ]
    
    # Платформенная статистика
    platform_row = []
    platform_row.append(InlineKeyboardButton("📸 Instagram", callback_data='instagram_stats'))
    
    if ENABLE_TIKTOK:
        platform_row.append(InlineKeyboardButton("🎵 TikTok", callback_data='tiktok_stats'))
    
    if platform_row:
        keyboard.append(platform_row)
    
    keyboard.extend([
        [InlineKeyboardButton("📋 Все сценарии", callback_data='all_scenarios')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back')]
    ])
    
    return InlineKeyboardMarkup(keyboard)

def proxy_menu() -> InlineKeyboardMarkup:
    """Меню управления прокси"""
    keyboard = [
        [
            InlineKeyboardButton("➕ Добавить прокси", callback_data='add_proxy'),
            InlineKeyboardButton("📥 Импорт", callback_data='import_menu')
        ],
        [
            InlineKeyboardButton("📋 Список прокси", callback_data='list_proxies'),
            InlineKeyboardButton("📤 Экспорт", callback_data='export_proxies')
        ],
        [
            InlineKeyboardButton("🔍 Проверить все", callback_data='check_all_proxies'),
            InlineKeyboardButton("⚙️ Операции", callback_data='bulk_operations')
        ],
        [InlineKeyboardButton("📊 Статистика", callback_data='proxy_stats')]
    ]
    
    # Добавляем тестирование платформ
    if ENABLE_TIKTOK:
        keyboard.append([
            InlineKeyboardButton("📸 Тест Instagram", callback_data='test_instagram_proxies'),
            InlineKeyboardButton("🎵 Тест TikTok", callback_data='test_tiktok_proxies')
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='admin_panel')])
    
    return InlineKeyboardMarkup(keyboard)

def scenarios_menu() -> InlineKeyboardMarkup:
    """Меню Instagram сценариев"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить сценарий", callback_data='add_scenario')],
        [InlineKeyboardButton("📋 Мои сценарии", callback_data='my_scenarios')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back')]
    ]
    return InlineKeyboardMarkup(keyboard)

def tiktok_scenarios_menu() -> InlineKeyboardMarkup:
    """Меню TikTok сценариев"""
    keyboard = [
        [InlineKeyboardButton("➕ Создать TikTok сценарий", callback_data='add_tiktok_scenario')],
        [InlineKeyboardButton("📋 Мои TikTok сценарии", callback_data='my_tiktok_scenarios')]
    ]
    
    # Добавляем переключение на Instagram если доступен
    keyboard.append([InlineKeyboardButton("📸 Переключиться на Instagram", callback_data='instagram_scenarios')])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='back')])
    
    return InlineKeyboardMarkup(keyboard)

def proxy_selection_menu(proxies: list, platform: str = 'instagram') -> InlineKeyboardMarkup:
    """Меню выбора прокси для конкретной платформы"""
    keyboard = []
    
    platform_emoji = "📸" if platform == 'instagram' else "🎵"
    
    for proxy in proxies:
        usage_info = f"({proxy.usage_count} исп.)"
        status_emoji = "🟢" if proxy.is_working else "🔴"
        
        # Добавляем информацию о производительности для конкретной платформы
        performance_info = ""
        if hasattr(proxy, 'performance') and proxy.performance:
            if platform == 'instagram':
                success_rate = proxy.performance.ig_success_rate
            else:
                success_rate = proxy.performance.tiktok_success_rate
                
            if success_rate > 0:
                performance_info = f" - {success_rate:.0f}%"
        
        callback_prefix = 'select_tiktok_proxy_' if platform == 'tiktok' else 'select_proxy_'
        
        keyboard.append([
            InlineKeyboardButton(
                f"{status_emoji} {proxy.name} {usage_info}{performance_info}",
                callback_data=f'{callback_prefix}{proxy.id}'
            )
        ])
    
    # Платформо-специфичные опции
    if platform == 'tiktok':
        keyboard.extend([
            [InlineKeyboardButton("🎯 Лучший автоматически", callback_data='tiktok_choose_best_proxy')],
            [InlineKeyboardButton("🛡️ Безопасный режим (без прокси)", callback_data='tiktok_no_proxy')],
            [InlineKeyboardButton("❌ Отменить", callback_data='tiktok_scenarios')]
        ])
    else:
        keyboard.extend([
            [InlineKeyboardButton("🎯 Лучший автоматически", callback_data='choose_best_proxy')],
            [InlineKeyboardButton("🛡️ Безопасный режим (без прокси)", callback_data='safe_mode_creation')],
            [InlineKeyboardButton("❌ Отменить", callback_data='scenarios_menu')]
        ])
    
    return InlineKeyboardMarkup(keyboard)

def scenario_management_menu(scenario_id: int, scenario_data: dict, platform: str = 'instagram') -> InlineKeyboardMarkup:
    """Меню управления сценарием (универсальное для обеих платформ)"""
    platform_emoji = "📸" if platform == 'instagram' else "🎵"
    
    if platform == 'tiktok':
        keyboard = [
            [InlineKeyboardButton("🔍 Проверить комментарии", callback_data=f'check_tiktok_comments_{scenario_id}')],
            [InlineKeyboardButton(f"📩 Отправить сообщения ({scenario_data.get('pending_count', 0)})", callback_data=f'send_tiktok_messages_{scenario_id}')]
        ]
        
        # Кнопки управления
        if scenario_data.get('status') == 'running':
            keyboard.append([InlineKeyboardButton("⏸ Приостановить", callback_data=f'pause_tiktok_{scenario_id}')])
        else:
            keyboard.append([InlineKeyboardButton("▶️ Возобновить", callback_data=f'resume_tiktok_{scenario_id}')])
        
        keyboard.extend([
            [InlineKeyboardButton("🚀 Перезапустить", callback_data=f'restart_tiktok_{scenario_id}')],
            [InlineKeyboardButton("🗑 Удалить", callback_data=f'delete_tiktok_{scenario_id}')],
            [InlineKeyboardButton("🔙 Назад", callback_data='my_tiktok_scenarios')]
        ])
    else:
        keyboard = [
            [InlineKeyboardButton("🔍 Проверить комментарии", callback_data=f'check_comments_{scenario_id}')],
            [InlineKeyboardButton(f"📩 Отправить сообщения ({scenario_data.get('pending_count', 0)})", callback_data=f'send_messages_{scenario_id}')],
            [InlineKeyboardButton("⏰ Запланировать проверку", callback_data=f'schedule_check_{scenario_id}')]
        ]
        
        # Информация о следующей проверке
        next_check = scenario_data.get('next_check', 'Не запланировано')
        keyboard.append([InlineKeyboardButton(f"⏳ Следующая: {next_check}", callback_data='noop')])
        
        # Кнопки управления
        if scenario_data.get('status') == 'running':
            keyboard.append([InlineKeyboardButton("⏸ Приостановить", callback_data=f'pause_{scenario_id}')])
        else:
            keyboard.append([InlineKeyboardButton("▶️ Возобновить", callback_data=f'resume_{scenario_id}')])
        
        keyboard.extend([
            [InlineKeyboardButton("🚀 Перезапустить (v2.0)", callback_data=f'restart_{scenario_id}')],
            [InlineKeyboardButton("🗑 Удалить", callback_data=f'delete_{scenario_id}')],
            [InlineKeyboardButton("🔙 Назад", callback_data='my_scenarios')]
        ])
    
    # Информация о прокси (универсальная)
    proxy_info = scenario_data.get('proxy_info', '🌐 Без прокси')
    keyboard.insert(-3, [InlineKeyboardButton(proxy_info, callback_data='noop')])
    
    return InlineKeyboardMarkup(keyboard)

def duration_selection_menu(platform: str = 'instagram') -> InlineKeyboardMarkup:
    """Меню выбора срока активности сценария"""
    platform_emoji = "📸" if platform == 'instagram' else "🎵"
    callback_prefix = 'tiktok_duration_' if platform == 'tiktok' else ''
    
    keyboard = [
        [InlineKeyboardButton("1 день", callback_data=f'{callback_prefix}1d')],
        [InlineKeyboardButton("3 дня", callback_data=f'{callback_prefix}3d')],
        [InlineKeyboardButton("7 дней", callback_data=f'{callback_prefix}7d')],
        [InlineKeyboardButton("14 дней", callback_data=f'{callback_prefix}14d')]
    ]
    
    if platform == 'instagram':
        keyboard.append([InlineKeyboardButton("30 дней", callback_data='30d')])
    
    return InlineKeyboardMarkup(keyboard)

# === НОВЫЕ МЕНЮ ДЛЯ TIKTOK ===

def tiktok_proxy_selection_menu(proxies: list) -> InlineKeyboardMarkup:
    """Специальное меню выбора прокси для TikTok"""
    keyboard = []
    
    # Рекомендуемые прокси для TikTok (с лучшей статистикой)
    if proxies:
        keyboard.append([InlineKeyboardButton("🏆 Рекомендуемые для TikTok:", callback_data='noop')])
        
        for proxy in proxies[:5]:  # Топ 5 прокси
            status_emoji = "🟢" if proxy.is_working else "🔴"
            performance_info = ""
            
            if hasattr(proxy, 'performance') and proxy.performance:
                tiktok_rate = proxy.performance.tiktok_success_rate
                if tiktok_rate > 0:
                    performance_info = f" ({tiktok_rate:.0f}% TikTok)"
                elif proxy.performance.overall_success_rate > 0:
                    performance_info = f" ({proxy.performance.overall_success_rate:.0f}% общий)"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_emoji} {proxy.name}{performance_info}",
                    callback_data=f'select_tiktok_proxy_{proxy.id}'
                )
            ])
    
    keyboard.extend([
        [InlineKeyboardButton("🎯 Автовыбор лучшего", callback_data='tiktok_choose_best_proxy')],
        [InlineKeyboardButton("📋 Все прокси", callback_data='tiktok_choose_proxy')],
        [InlineKeyboardButton("🛡️ Без прокси (рискованно)", callback_data='tiktok_no_proxy')],
        [InlineKeyboardButton("❌ Отменить", callback_data='tiktok_scenarios')]
    ])
    
    return InlineKeyboardMarkup(keyboard)

# === СТАТИСТИЧЕСКИЕ МЕНЮ ===

def platform_stats_menu() -> InlineKeyboardMarkup:
    """Меню статистики по платформам"""
    keyboard = [
        [InlineKeyboardButton("📸 Instagram статистика", callback_data='detailed_instagram_stats')],
    ]
    
    if ENABLE_TIKTOK:
        keyboard.append([InlineKeyboardButton("🎵 TikTok статистика", callback_data='detailed_tiktok_stats')])
    
    keyboard.extend([
        [InlineKeyboardButton("📊 Сравнение платформ", callback_data='compare_platforms')],
        [InlineKeyboardButton("🌐 Производительность прокси", callback_data='proxy_platform_stats')],
        [InlineKeyboardButton("🔙 Назад", callback_data='admin_panel')]
    ])
    
    return InlineKeyboardMarkup(keyboard)

def proxy_platform_stats_menu() -> InlineKeyboardMarkup:
    """Меню статистики прокси по платформам"""
    keyboard = [
        [InlineKeyboardButton("📸 Instagram прокси", callback_data='proxy_instagram_stats')],
    ]
    
    if ENABLE_TIKTOK:
        keyboard.append([InlineKeyboardButton("🎵 TikTok прокси", callback_data='proxy_tiktok_stats')])
    
    keyboard.extend([
        [InlineKeyboardButton("🏆 Лучшие прокси", callback_data='top_performing_proxies')],
        [InlineKeyboardButton("⚠️ Проблемные прокси", callback_data='problematic_proxies')],
        [InlineKeyboardButton("🔙 Назад", callback_data='proxy_stats')]
    ])
    
    return InlineKeyboardMarkup(keyboard)

# === НАСТРОЙКИ АВТОРИЗАЦИИ ===

def auth_settings_menu() -> InlineKeyboardMarkup:
    """Меню настроек авторизации с поддержкой платформ"""
    keyboard = [
        [InlineKeyboardButton("⚡ Быстрая настройка", callback_data='auth_quick_setup')],
        [InlineKeyboardButton("🔧 Детальные настройки", callback_data='auth_detailed_setup')]
    ]
    
    # Платформенные настройки
    platform_row = []
    platform_row.append(InlineKeyboardButton("📸 Instagram", callback_data='auth_instagram_settings'))
    
    if ENABLE_TIKTOK:
        platform_row.append(InlineKeyboardButton("🎵 TikTok", callback_data='auth_tiktok_settings'))
    
    keyboard.append(platform_row)
    
    keyboard.extend([
        [InlineKeyboardButton("📊 Статистика авторизации", callback_data='auth_statistics')],
        [InlineKeyboardButton("🔄 Сбросить по умолчанию", callback_data='auth_reset_defaults')],
        [InlineKeyboardButton("🔙 Назад", callback_data='admin_panel')]
    ])
    
    return InlineKeyboardMarkup(keyboard)

def auth_presets_menu() -> InlineKeyboardMarkup:
    """Меню предустановок авторизации"""
    keyboard = [
        [InlineKeyboardButton("🔥 Агрессивная", callback_data='auth_preset_aggressive')],
        [InlineKeyboardButton("⚖️ Сбалансированная", callback_data='auth_preset_balanced')],
        [InlineKeyboardButton("🐢 Консервативная", callback_data='auth_preset_conservative')],
        [InlineKeyboardButton("👻 Скрытная", callback_data='auth_preset_stealth')]
    ]
    
    # Платформо-специфичные предустановки
    if ENABLE_TIKTOK:
        keyboard.extend([
            [InlineKeyboardButton("🎵 TikTok оптимизированная", callback_data='auth_preset_tiktok_optimized')],
            [InlineKeyboardButton("📸 Instagram фокус", callback_data='auth_preset_instagram_focus')]
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='auth_settings')])
    
    return InlineKeyboardMarkup(keyboard)

# === ПОМОЩЬ И ДОКУМЕНТАЦИЯ ===

def help_menu() -> InlineKeyboardMarkup:
    """Меню помощи с поддержкой платформ"""
    keyboard = [
        [InlineKeyboardButton("📖 Руководство пользователя", callback_data='help_user_guide')],
        [InlineKeyboardButton("🌐 Настройка прокси", callback_data='help_proxy_setup')]
    ]
    
    # Платформенная помощь
    platform_help = []
    platform_help.append(InlineKeyboardButton("📸 Instagram", callback_data='help_instagram'))
    
    if ENABLE_TIKTOK:
        platform_help.append(InlineKeyboardButton("🎵 TikTok", callback_data='help_tiktok'))
    
    keyboard.append(platform_help)
    
    keyboard.extend([
        [InlineKeyboardButton("🚀 Улучшенная авторизация", callback_data='help_enhanced_auth')],
        [InlineKeyboardButton("🔧 Устранение неполадок", callback_data='help_troubleshooting')],
        [InlineKeyboardButton("📞 Поддержка", callback_data='help_support')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back')]
    ])
    
    return InlineKeyboardMarkup(keyboard)

def help_platform_menu(platform: str) -> InlineKeyboardMarkup:
    """Меню помощи для конкретной платформы"""
    platform_emoji = "📸" if platform == 'instagram' else "🎵"
    platform_name = "Instagram" if platform == 'instagram' else "TikTok"
    
    keyboard = [
        [InlineKeyboardButton(f"🚀 Начало работы с {platform_name}", callback_data=f'help_{platform}_getting_started')],
        [InlineKeyboardButton(f"⚙️ Создание сценариев", callback_data=f'help_{platform}_scenarios')],
        [InlineKeyboardButton(f"🔐 Авторизация", callback_data=f'help_{platform}_auth')],
        [InlineKeyboardButton(f"🌐 Прокси для {platform_name}", callback_data=f'help_{platform}_proxies')],
        [InlineKeyboardButton(f"❓ Частые вопросы", callback_data=f'help_{platform}_faq')],
        [InlineKeyboardButton("🔙 Назад", callback_data='help')]
    ]
    
    return InlineKeyboardMarkup(keyboard)

# === РАСШИРЕННЫЕ УПРАВЛЯЮЩИЕ МЕНЮ ===

def bulk_scenario_operations_menu(platform: str = 'all') -> InlineKeyboardMarkup:
    """Меню массовых операций со сценариями"""
    keyboard = []
    
    if platform == 'all' or platform == 'instagram':
        keyboard.append([InlineKeyboardButton("📸 Все Instagram сценарии", callback_data='bulk_instagram_operations')])
    
    if platform == 'all' or platform == 'tiktok':
        if ENABLE_TIKTOK:
            keyboard.append([InlineKeyboardButton("🎵 Все TikTok сценарии", callback_data='bulk_tiktok_operations')])
    
    keyboard.extend([
        [InlineKeyboardButton("⏸ Приостановить все", callback_data='pause_all_scenarios')],
        [InlineKeyboardButton("▶️ Запустить все", callback_data='resume_all_scenarios')],
        [InlineKeyboardButton("🔄 Перезапустить неудачные", callback_data='restart_failed_scenarios')],
        [InlineKeyboardButton("🗑 Очистить завершенные", callback_data='cleanup_completed_scenarios')],
        [InlineKeyboardButton("🔙 Назад", callback_data='admin_panel')]
    ])
    
    return InlineKeyboardMarkup(keyboard)

def platform_comparison_menu() -> InlineKeyboardMarkup:
    """Меню сравнения платформ"""
    keyboard = [
        [InlineKeyboardButton("📊 Общая статистика", callback_data='general_platform_comparison')],
        [InlineKeyboardButton("🔐 Сравнение авторизации", callback_data='auth_platform_comparison')],
        [InlineKeyboardButton("📩 Эффективность сообщений", callback_data='messaging_platform_comparison')],
        [InlineKeyboardButton("🌐 Использование прокси", callback_data='proxy_platform_comparison')],
        [InlineKeyboardButton("⏱ Временной анализ", callback_data='time_platform_comparison')],
        [InlineKeyboardButton("🔙 Назад", callback_data='platform_stats_menu')]
    ]
    
    return InlineKeyboardMarkup(keyboard)

# === БЫСТРЫЕ ДЕЙСТВИЯ ===

def quick_platform_actions_menu() -> InlineKeyboardMarkup:
    """Меню быстрых действий по платформам"""
    keyboard = [
        [InlineKeyboardButton("📸 Быстрый Instagram", callback_data='quick_instagram_scenario')],
    ]
    
    if ENABLE_TIKTOK:
        keyboard.append([InlineKeyboardButton("🎵 Быстрый TikTok", callback_data='quick_tiktok_scenario')])
    
    keyboard.extend([
        [InlineKeyboardButton("🔍 Проверить все комментарии", callback_data='check_all_comments')],
        [InlineKeyboardButton("📩 Отправить все сообщения", callback_data='send_all_messages')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back')]
    ])
    
    return InlineKeyboardMarkup(keyboard)

def emergency_actions_menu() -> InlineKeyboardMarkup:
    """Меню экстренных действий"""
    keyboard = [
        [InlineKeyboardButton("🚨 СТОП все сценарии", callback_data='emergency_stop_all')],
        [InlineKeyboardButton("🔄 Перезапуск системы", callback_data='emergency_restart_system')],
        [InlineKeyboardButton("🌐 Отключить все прокси", callback_data='emergency_disable_proxies')],
        [InlineKeyboardButton("📊 Экстренная диагностика", callback_data='emergency_diagnostics')],
        [InlineKeyboardButton("🔙 Назад", callback_data='admin_panel')]
    ]
    
    return InlineKeyboardMarkup(keyboard)

# === УТИЛИТЫ ===

def confirmation_menu(confirm_action: str, cancel_action: str = 'back', 
                     platform: str = None) -> InlineKeyboardMarkup:
    """Универсальное меню подтверждения с поддержкой платформ"""
    platform_emoji = ""
    if platform == 'instagram':
        platform_emoji = "📸 "
    elif platform == 'tiktok':
        platform_emoji = "🎵 "
    
    keyboard = [
        [InlineKeyboardButton(f"✅ {platform_emoji}Подтвердить", callback_data=confirm_action)],
        [InlineKeyboardButton("❌ Отменить", callback_data=cancel_action)]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_menu(action: str = 'back', platform: str = None) -> InlineKeyboardMarkup:
    """Простое меню с кнопкой "Назад" с учетом платформы"""
    text = "🔙 Назад"
    if platform == 'instagram':
        text = "📸 К Instagram"
    elif platform == 'tiktok':
        text = "🎵 К TikTok"
    
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=action)]])

def pagination_menu(current_page: int, total_pages: int, 
                   base_callback: str, platform: str = None) -> InlineKeyboardMarkup:
    """Меню пагинации с поддержкой платформ"""
    keyboard = []
    
    # Кнопки навигации
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f'{base_callback}_page_{current_page-1}'))
    
    platform_emoji = ""
    if platform == 'instagram':
        platform_emoji = "📸 "
    elif platform == 'tiktok':
        platform_emoji = "🎵 "
    
    nav_buttons.append(InlineKeyboardButton(f"{platform_emoji}{current_page}/{total_pages}", callback_data='noop'))
    
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f'{base_callback}_page_{current_page+1}'))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    return InlineKeyboardMarkup(keyboard)

# === ГОТОВЫЕ ШАБЛОНЫ ===

COMMON_MENUS = {
    'main': main_menu,
    'admin': admin_menu,
    'proxy': proxy_menu,
    'platforms': platforms_menu,
    'help': help_menu,
    'back': back_menu
}

PLATFORM_MENUS = {
    'instagram_scenarios': scenarios_menu,
    'tiktok_scenarios': tiktok_scenarios_menu,
    'duration_instagram': lambda: duration_selection_menu('instagram'),
    'duration_tiktok': lambda: duration_selection_menu('tiktok')
}

PROXY_MENUS = {
    'import': lambda: None,  # Placeholder for existing proxy import menu
    'export': lambda: None,  # Placeholder for existing proxy export menu
    'platform_stats': proxy_platform_stats_menu
}

AUTH_MENUS = {
    'settings': auth_settings_menu,
    'presets': auth_presets_menu
}

ADMIN_MENUS = {
    'platform_stats': platform_stats_menu,
    'bulk_operations': bulk_scenario_operations_menu,
    'emergency': emergency_actions_menu,
    'comparison': platform_comparison_menu
}

def get_menu(menu_type: str, platform: str = None, **kwargs) -> InlineKeyboardMarkup:
    """Универсальная функция получения меню по типу с поддержкой платформ"""
    if menu_type in COMMON_MENUS:
        return COMMON_MENUS[menu_type](**kwargs)
    elif menu_type in PLATFORM_MENUS:
        return PLATFORM_MENUS[menu_type]()
    elif menu_type in AUTH_MENUS:
        return AUTH_MENUS[menu_type]()
    elif menu_type in ADMIN_MENUS:
        return ADMIN_MENUS[menu_type](**kwargs)
    elif menu_type == 'scenario_management':
        return scenario_management_menu(platform=platform, **kwargs)
    elif menu_type == 'proxy_selection':
        return proxy_selection_menu(platform=platform, **kwargs)
    elif menu_type == 'help_platform':
        return help_platform_menu(platform)
    else:
        return back_menu()

# === КНОПКИ НАВИГАЦИИ ===

def get_platform_back_button(platform: str) -> InlineKeyboardButton:
    """Получение кнопки возврата для конкретной платформы"""
    if platform == 'instagram':
        return InlineKeyboardButton("📸 К Instagram", callback_data='instagram_scenarios')
    elif platform == 'tiktok':
        return InlineKeyboardButton("🎵 К TikTok", callback_data='tiktok_scenarios')
    else:
        return InlineKeyboardButton("🔙 Назад", callback_data='back')

def get_platform_emoji(platform: str) -> str:
    """Получение эмодзи для платформы"""
    return "📸" if platform == 'instagram' else "🎵" if platform == 'tiktok' else "🔹"

def get_platform_name(platform: str) -> str:
    """Получение названия платформы"""
    return "Instagram" if platform == 'instagram' else "TikTok" if platform == 'tiktok' else "Unknown"