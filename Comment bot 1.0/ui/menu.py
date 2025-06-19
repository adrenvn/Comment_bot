"""
Меню и клавиатуры для Instagram Automation Bot v2.0
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu(is_admin_user: bool, is_user_user: bool) -> InlineKeyboardMarkup:
    """Главное меню"""
    keyboard = []
    if is_user_user:
        keyboard.append([InlineKeyboardButton("📂 Сценарии", callback_data='scenarios_menu')])
    if is_admin_user:
        keyboard.append([InlineKeyboardButton("👑 Админ-панель", callback_data='admin_panel')])
    keyboard.append([InlineKeyboardButton("❓ Помощь", callback_data='help')])
    return InlineKeyboardMarkup(keyboard)

def admin_menu() -> InlineKeyboardMarkup:
    """Меню администратора"""
    keyboard = [
        [InlineKeyboardButton("👥 Пользователи", callback_data='manage_users')],
        [InlineKeyboardButton("👑 Администраторы", callback_data='manage_admins')],
        [InlineKeyboardButton("🌐 Прокси", callback_data='manage_proxies')],
        [InlineKeyboardButton("📊 Статистика", callback_data='status_scenarios')],
        [InlineKeyboardButton("📋 Все сценарии", callback_data='all_scenarios')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back')]
    ]
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
        [InlineKeyboardButton("📊 Статистика", callback_data='proxy_stats')],
        [InlineKeyboardButton("🔙 Назад", callback_data='admin_panel')]
    ]
    return InlineKeyboardMarkup(keyboard)

def scenarios_menu() -> InlineKeyboardMarkup:
    """Меню сценариев"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить сценарий", callback_data='add_scenario')],
        [InlineKeyboardButton("📋 Мои сценарии", callback_data='my_scenarios')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back')]
    ]
    return InlineKeyboardMarkup(keyboard)

def proxy_selection_menu(proxies: list) -> InlineKeyboardMarkup:
    """Меню выбора прокси для сценария"""
    keyboard = []
    
    for proxy in proxies:
        usage_info = f"({proxy.usage_count} исп.)"
        status_emoji = "🟢" if proxy.is_working else "🔴"
        keyboard.append([
            InlineKeyboardButton(
                f"{status_emoji} {proxy.name} {usage_info}",
                callback_data=f'select_proxy_{proxy.id}'
            )
        ])
    
    keyboard.extend([
        [InlineKeyboardButton("🚫 Без прокси", callback_data='no_proxy')],
        [InlineKeyboardButton("❌ Отменить", callback_data='scenarios_menu')]
    ])
    
    return InlineKeyboardMarkup(keyboard)

def scenario_management_menu(scenario_id: int, scenario_data: dict) -> InlineKeyboardMarkup:
    """Меню управления конкретным сценарием"""
    keyboard = [
        [InlineKeyboardButton("🔍 Проверить комментарии", callback_data=f'check_comments_{scenario_id}')],
        [InlineKeyboardButton(f"📩 Отправить сообщения ({scenario_data.get('pending_count', 0)})", callback_data=f'send_messages_{scenario_id}')],
        [InlineKeyboardButton("⏰ Запланировать проверку", callback_data=f'schedule_check_{scenario_id}')],
    ]
    
    # Информация о следующей проверке
    next_check = scenario_data.get('next_check', 'Не запланировано')
    keyboard.append([InlineKeyboardButton(f"⏳ Следующая: {next_check}", callback_data='noop')])
    
    # Информация о прокси
    proxy_info = scenario_data.get('proxy_info', '🌐 Без прокси')
    keyboard.append([InlineKeyboardButton(proxy_info, callback_data='noop')])
    
    # Кнопки управления
    if scenario_data.get('status') == 'running':
        keyboard.append([InlineKeyboardButton("⏸ Приостановить", callback_data=f'pause_{scenario_id}')])
    else:
        keyboard.append([InlineKeyboardButton("▶️ Возобновить", callback_data=f'resume_{scenario_id}')])
    
    keyboard.extend([
        [InlineKeyboardButton("🔄 Перезапустить", callback_data=f'restart_{scenario_id}')],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f'delete_{scenario_id}')],
        [InlineKeyboardButton("🔙 Назад", callback_data='my_scenarios')]
    ])
    
    return InlineKeyboardMarkup(keyboard)

def proxy_import_menu() -> InlineKeyboardMarkup:
    """Меню импорта прокси"""
    keyboard = [
        [InlineKeyboardButton("🌐 922Proxy", callback_data='import_922proxy')],
        [InlineKeyboardButton("📝 Из текста", callback_data='import_from_text')],
        [InlineKeyboardButton("📁 Популярные провайдеры", callback_data='import_providers')],
        [InlineKeyboardButton("🔙 Назад", callback_data='manage_proxies')]
    ]
    return InlineKeyboardMarkup(keyboard)

def proxy_providers_menu() -> InlineKeyboardMarkup:
    """Меню выбора провайдера прокси"""
    from services.proxy_922 import PROXY_PROVIDERS_CONFIG
    
    keyboard = []
    for provider_key, config in PROXY_PROVIDERS_CONFIG.items():
        keyboard.append([
            InlineKeyboardButton(
                f"🌐 {config['name']}", 
                callback_data=f'import_provider_{provider_key}'
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='import_menu')])
    return InlineKeyboardMarkup(keyboard)

def proxy_bulk_operations_menu() -> InlineKeyboardMarkup:
    """Меню массовых операций с прокси"""
    keyboard = [
        [InlineKeyboardButton("🔍 Проверить все прокси", callback_data='check_all_proxies')],
        [InlineKeyboardButton("🔄 Автоматическая ротация", callback_data='auto_rotate_proxies')],
        [InlineKeyboardButton("📊 Пакетная проверка", callback_data='bulk_check_proxies')],
        [InlineKeyboardButton("🗑️ Очистить неработающие", callback_data='cleanup_failed_proxies')],
        [InlineKeyboardButton("🔙 Назад", callback_data='manage_proxies')]
    ]
    return InlineKeyboardMarkup(keyboard)

def proxy_export_menu() -> InlineKeyboardMarkup:
    """Меню экспорта прокси"""
    keyboard = [
        [InlineKeyboardButton("📝 IP:PORT:USER:PASS", callback_data='export_format_1')],
        [InlineKeyboardButton("🔗 USER:PASS@IP:PORT", callback_data='export_format_2')],
        [InlineKeyboardButton("🌐 Только рабочие", callback_data='export_working_only')],
        [InlineKeyboardButton("📊 Статистика TXT", callback_data='export_stats')],
        [InlineKeyboardButton("🔙 Назад", callback_data='manage_proxies')]
    ]
    return InlineKeyboardMarkup(keyboard)

def proxy_management_menu(proxy_id: int, proxy_data: dict) -> InlineKeyboardMarkup:
    """Меню управления отдельным прокси"""
    keyboard = [
        [
            InlineKeyboardButton("🔍 Проверить", callback_data=f'check_proxy_{proxy_id}'),
            InlineKeyboardButton("🧪 Тест с Instagram", callback_data=f'test_proxy_instagram_{proxy_id}')
        ],
        [InlineKeyboardButton("🔄 Сбросить счетчик", callback_data=f'reset_proxy_counter_{proxy_id}')]
    ]
    
    # Кнопка активации/деактивации
    if proxy_data.get('is_active'):
        keyboard.append([InlineKeyboardButton("⏸️ Деактивировать", callback_data=f'deactivate_proxy_{proxy_id}')])
    else:
        keyboard.append([InlineKeyboardButton("▶️ Активировать", callback_data=f'activate_proxy_{proxy_id}')])
    
    keyboard.extend([
        [InlineKeyboardButton("🗑️ Удалить", callback_data=f'delete_proxy_{proxy_id}')],
        [InlineKeyboardButton("🔙 К списку", callback_data='list_proxies')]
    ])
    
    return InlineKeyboardMarkup(keyboard)

def schedule_check_menu(scenario_id: int) -> InlineKeyboardMarkup:
    """Меню планирования проверки"""
    keyboard = [
        [InlineKeyboardButton("⏰ Через 15 минут", callback_data=f'set_timer_15_{scenario_id}')],
        [InlineKeyboardButton("⏰ Через 30 минут", callback_data=f'set_timer_30_{scenario_id}')],
        [InlineKeyboardButton("⏰ Через 1 час", callback_data=f'set_timer_60_{scenario_id}')],
        [InlineKeyboardButton("⏰ Через 2 часа", callback_data=f'set_timer_120_{scenario_id}')],
        [InlineKeyboardButton("⏰ Через 6 часов", callback_data=f'set_timer_360_{scenario_id}')],
        [InlineKeyboardButton("🔙 Назад", callback_data=f'manage_{scenario_id}')]
    ]
    return InlineKeyboardMarkup(keyboard)

def duration_selection_menu() -> InlineKeyboardMarkup:
    """Меню выбора срока активности сценария"""
    keyboard = [
        [InlineKeyboardButton("1 день", callback_data='1d')],
        [InlineKeyboardButton("3 дня", callback_data='3d')],
        [InlineKeyboardButton("7 дней", callback_data='7d')],
        [InlineKeyboardButton("14 дней", callback_data='14d')],
        [InlineKeyboardButton("30 дней", callback_data='30d')]
    ]
    return InlineKeyboardMarkup(keyboard)

def proxy_type_selection_menu() -> InlineKeyboardMarkup:
    """Меню выбора типа прокси"""
    keyboard = [
        [InlineKeyboardButton("HTTP", callback_data='proxy_type_http')],
        [InlineKeyboardButton("HTTPS", callback_data='proxy_type_https')],
        [InlineKeyboardButton("SOCKS5", callback_data='proxy_type_socks5')]
    ]
    return InlineKeyboardMarkup(keyboard)

def confirmation_menu(confirm_action: str, cancel_action: str = 'back') -> InlineKeyboardMarkup:
    """Универсальное меню подтверждения"""
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data=confirm_action)],
        [InlineKeyboardButton("❌ Отменить", callback_data=cancel_action)]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_menu(action: str = 'back') -> InlineKeyboardMarkup:
    """Простое меню с кнопкой "Назад" """
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data=action)]])

def pagination_menu(current_page: int, total_pages: int, base_callback: str) -> InlineKeyboardMarkup:
    """Меню пагинации"""
    keyboard = []
    
    # Кнопки навигации
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f'{base_callback}_page_{current_page-1}'))
    
    nav_buttons.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data='noop'))
    
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f'{base_callback}_page_{current_page+1}'))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    return InlineKeyboardMarkup(keyboard)

# === БЫСТРЫЕ ДЕЙСТВИЯ ===

def quick_proxy_actions_menu(proxy_id: int) -> InlineKeyboardMarkup:
    """Меню быстрых действий для прокси"""
    keyboard = [
        [
            InlineKeyboardButton("🔍", callback_data=f'check_proxy_{proxy_id}'),
            InlineKeyboardButton("🧪", callback_data=f'test_proxy_instagram_{proxy_id}'),
            InlineKeyboardButton("⚙️", callback_data=f'manage_proxy_{proxy_id}'),
            InlineKeyboardButton("🗑️", callback_data=f'delete_proxy_{proxy_id}')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def quick_scenario_actions_menu(scenario_id: int) -> InlineKeyboardMarkup:
    """Меню быстрых действий для сценария"""
    keyboard = [
        [
            InlineKeyboardButton("🔍", callback_data=f'check_comments_{scenario_id}'),
            InlineKeyboardButton("📩", callback_data=f'send_messages_{scenario_id}'),
            InlineKeyboardButton("⏰", callback_data=f'schedule_check_{scenario_id}'),
            InlineKeyboardButton("⚙️", callback_data=f'manage_{scenario_id}')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# === СПЕЦИАЛИЗИРОВАННЫЕ МЕНЮ ===

def proxy_health_status_menu(working_count: int, total_count: int) -> InlineKeyboardMarkup:
    """Меню статуса здоровья прокси"""
    keyboard = [
        [InlineKeyboardButton(f"✅ Работают: {working_count}", callback_data='filter_working_proxies')],
        [InlineKeyboardButton(f"❌ Не работают: {total_count - working_count}", callback_data='filter_failed_proxies')],
        [InlineKeyboardButton("🔄 Обновить статус", callback_data='check_all_proxies')],
        [InlineKeyboardButton("🔙 Назад", callback_data='manage_proxies')]
    ]
    return InlineKeyboardMarkup(keyboard)

def scenario_filter_menu() -> InlineKeyboardMarkup:
    """Меню фильтрации сценариев"""
    keyboard = [
        [InlineKeyboardButton("🟢 Активные", callback_data='filter_scenarios_running')],
        [InlineKeyboardButton("⏸️ Приостановленные", callback_data='filter_scenarios_paused')],
        [InlineKeyboardButton("🔴 Остановленные", callback_data='filter_scenarios_stopped')],
        [InlineKeyboardButton("🌐 С прокси", callback_data='filter_scenarios_with_proxy')],
        [InlineKeyboardButton("📱 Без прокси", callback_data='filter_scenarios_no_proxy')],
        [InlineKeyboardButton("🔙 Назад", callback_data='my_scenarios')]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_tools_menu() -> InlineKeyboardMarkup:
    """Меню инструментов администратора"""
    keyboard = [
        [InlineKeyboardButton("📊 Общая статистика", callback_data='admin_global_stats')],
        [InlineKeyboardButton("🔄 Перезапуск всех сценариев", callback_data='admin_restart_all')],
        [InlineKeyboardButton("⏸️ Остановка всех сценариев", callback_data='admin_stop_all')],
        [InlineKeyboardButton("🗑️ Очистка базы данных", callback_data='admin_cleanup_db')],
        [InlineKeyboardButton("📤 Экспорт всех данных", callback_data='admin_export_all')],
        [InlineKeyboardButton("🔙 Назад", callback_data='admin_panel')]
    ]
    return InlineKeyboardMarkup(keyboard)

def notification_settings_menu() -> InlineKeyboardMarkup:
    """Меню настройки уведомлений"""
    keyboard = [
        [InlineKeyboardButton("🔔 Уведомления о сценариях", callback_data='notif_scenarios')],
        [InlineKeyboardButton("🌐 Уведомления о прокси", callback_data='notif_proxies')],
        [InlineKeyboardButton("📊 Еженедельные отчеты", callback_data='notif_weekly')],
        [InlineKeyboardButton("🚨 Критические ошибки", callback_data='notif_errors')],
        [InlineKeyboardButton("🔙 Назад", callback_data='admin_panel')]
    ]
    return InlineKeyboardMarkup(keyboard)

# === КОНТЕКСТНЫЕ МЕНЮ ===

def context_menu_for_failed_proxy(proxy_id: int) -> InlineKeyboardMarkup:
    """Контекстное меню для неработающего прокси"""
    keyboard = [
        [InlineKeyboardButton("🔄 Повторить проверку", callback_data=f'recheck_proxy_{proxy_id}')],
        [InlineKeyboardButton("⚙️ Настройки прокси", callback_data=f'manage_proxy_{proxy_id}')],
        [InlineKeyboardButton("🗑️ Удалить прокси", callback_data=f'delete_proxy_{proxy_id}')],
        [InlineKeyboardButton("⏸️ Деактивировать", callback_data=f'deactivate_proxy_{proxy_id}')],
        [InlineKeyboardButton("🔙 Назад", callback_data='list_proxies')]
    ]
    return InlineKeyboardMarkup(keyboard)

def context_menu_for_failed_scenario(scenario_id: int) -> InlineKeyboardMarkup:
    """Контекстное меню для проблемного сценария"""
    keyboard = [
        [InlineKeyboardButton("🔄 Перезапустить", callback_data=f'restart_{scenario_id}')],
        [InlineKeyboardButton("🌐 Сменить прокси", callback_data=f'change_proxy_{scenario_id}')],
        [InlineKeyboardButton("⚙️ Диагностика", callback_data=f'diagnose_{scenario_id}')],
        [InlineKeyboardButton("📋 Логи ошибок", callback_data=f'error_logs_{scenario_id}')],
        [InlineKeyboardButton("🔙 Назад", callback_data='my_scenarios')]
    ]
    return InlineKeyboardMarkup(keyboard)

# === ПОМОЩЬ И ИНФОРМАЦИЯ ===

def help_menu() -> InlineKeyboardMarkup:
    """Меню помощи"""
    keyboard = [
        [InlineKeyboardButton("📖 Руководство пользователя", callback_data='help_user_guide')],
        [InlineKeyboardButton("🌐 Настройка прокси", callback_data='help_proxy_setup')],
        [InlineKeyboardButton("🎯 Создание сценариев", callback_data='help_scenarios')],
        [InlineKeyboardButton("🔧 Устранение неполадок", callback_data='help_troubleshooting')],
        [InlineKeyboardButton("📞 Поддержка", callback_data='help_support')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back')]
    ]
    return InlineKeyboardMarkup(keyboard)

def proxy_provider_help_menu(provider: str) -> InlineKeyboardMarkup:
    """Меню помощи для конкретного провайдера прокси"""
    keyboard = [
        [InlineKeyboardButton("📋 Форматы данных", callback_data=f'help_formats_{provider}')],
        [InlineKeyboardButton("🔧 Настройка", callback_data=f'help_setup_{provider}')],
        [InlineKeyboardButton("❓ FAQ", callback_data=f'help_faq_{provider}')],
        [InlineKeyboardButton("🔙 Назад", callback_data='import_providers')]
    ]
    return InlineKeyboardMarkup(keyboard)

# === ДИНАМИЧЕСКИЕ МЕНЮ ===

def create_dynamic_proxy_list_menu(proxies: list, page: int = 1, per_page: int = 5) -> InlineKeyboardMarkup:
    """Создание динамического меню списка прокси с пагинацией"""
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_proxies = proxies[start_idx:end_idx]
    
    keyboard = []
    
    for proxy in page_proxies:
        status_emoji = "🟢" if proxy.is_working else "🔴"
        row = [
            InlineKeyboardButton(
                f"{status_emoji} {proxy.name}",
                callback_data=f'proxy_details_{proxy.id}'
            ),
            quick_proxy_actions_menu(proxy.id).inline_keyboard[0][0],  # Кнопка проверки
            quick_proxy_actions_menu(proxy.id).inline_keyboard[0][3]   # Кнопка удаления
        ]
        keyboard.append(row)
    
    # Добавляем пагинацию если нужно
    total_pages = (len(proxies) + per_page - 1) // per_page
    if total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data=f'proxy_list_page_{page-1}'))
        nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data='noop'))
        if page < total_pages:
            nav_row.append(InlineKeyboardButton("➡️", callback_data=f'proxy_list_page_{page+1}'))
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='manage_proxies')])
    
    return InlineKeyboardMarkup(keyboard)

def create_dynamic_scenario_list_menu(scenarios: list, page: int = 1, per_page: int = 3) -> InlineKeyboardMarkup:
    """Создание динамического меню списка сценариев с пагинацией"""
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_scenarios = scenarios[start_idx:end_idx]
    
    keyboard = []
    
    for scenario in page_scenarios:
        status_emoji = {
            'running': "🟢",
            'paused': "⏸️",
            'stopped': "🔴"
        }.get(scenario.status, "❓")
        
        keyboard.append([
            InlineKeyboardButton(
                f"{status_emoji} Сценарий #{scenario.id}",
                callback_data=f'manage_{scenario.id}'
            )
        ])
    
    # Добавляем пагинацию если нужно
    total_pages = (len(scenarios) + per_page - 1) // per_page
    if total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data=f'scenarios_page_{page-1}'))
        nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data='noop'))
        if page < total_pages:
            nav_row.append(InlineKeyboardButton("➡️", callback_data=f'scenarios_page_{page+1}'))
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='scenarios_menu')])
    
    return InlineKeyboardMarkup(keyboard)

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def add_back_button(keyboard: list, callback_data: str = 'back') -> InlineKeyboardMarkup:
    """Добавление кнопки 'Назад' к существующей клавиатуре"""
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=callback_data)])
    return InlineKeyboardMarkup(keyboard)

def add_pagination(keyboard: list, current_page: int, total_pages: int, base_callback: str) -> InlineKeyboardMarkup:
    """Добавление пагинации к существующей клавиатуре"""
    if total_pages > 1:
        nav_buttons = []
        if current_page > 1:
            nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f'{base_callback}_page_{current_page-1}'))
        
        nav_buttons.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data='noop'))
        
        if current_page < total_pages:
            nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f'{base_callback}_page_{current_page+1}'))
        
        keyboard.append(nav_buttons)
    
    return InlineKeyboardMarkup(keyboard)

def create_inline_list(items: list, callback_prefix: str, items_per_row: int = 1) -> InlineKeyboardMarkup:
    """Создание inline клавиатуры из списка элементов"""
    keyboard = []
    
    for i in range(0, len(items), items_per_row):
        row = []
        for j in range(items_per_row):
            if i + j < len(items):
                item = items[i + j]
                row.append(InlineKeyboardButton(
                    str(item['name']),
                    callback_data=f'{callback_prefix}_{item["id"]}'
                ))
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

# === ГОТОВЫЕ ШАБЛОНЫ ===

COMMON_MENUS = {
    'main': main_menu,
    'admin': admin_menu,
    'proxy': proxy_menu,
    'scenarios': scenarios_menu,
    'help': help_menu,
    'back': back_menu
}

PROXY_MENUS = {
    'import': proxy_import_menu,
    'export': proxy_export_menu,
    'bulk_ops': proxy_bulk_operations_menu,
    'providers': proxy_providers_menu,
    'type_selection': proxy_type_selection_menu
}

SCENARIO_MENUS = {
    'duration': duration_selection_menu,
    'schedule': schedule_check_menu,
    'filter': scenario_filter_menu
}

def get_menu(menu_type: str, **kwargs) -> InlineKeyboardMarkup:
    """Универсальная функция получения меню по типу"""
    if menu_type in COMMON_MENUS:
        return COMMON_MENUS[menu_type](**kwargs)
    elif menu_type in PROXY_MENUS:
        return PROXY_MENUS[menu_type](**kwargs)
    elif menu_type in SCENARIO_MENUS:
        return SCENARIO_MENUS[menu_type](**kwargs)
    else:
        return back_menu()