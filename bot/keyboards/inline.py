"""
Inline клавиатуры
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard():
    """Главная клавиатура с красивым дизайном"""
    keyboard_buttons = [
        [
            InlineKeyboardButton(text="📝 Новая смета", callback_data="create_estimate"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="user_stats")
        ],
        [
            InlineKeyboardButton(text="📋 Мои сметы", callback_data="my_estimates"),
            InlineKeyboardButton(text="⚡ Активные", callback_data="active_estimates")
        ],
        [
            InlineKeyboardButton(text="🔧 Шаблоны работ", callback_data="work_templates"),
            InlineKeyboardButton(text="🤖 ИИ-помощник", callback_data="ai_assistant")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
            InlineKeyboardButton(text="❓ Помощь", callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_estimate_keyboard(estimate_id: int):
    """Клавиатура для работы со сметой"""
    keyboard_buttons = [
        [
            InlineKeyboardButton(
                text="➕ Добавить позицию", 
                callback_data=f"add_item:{estimate_id}"
            ),
            InlineKeyboardButton(
                text="✏️ Редактировать", 
                callback_data=f"edit_estimate:{estimate_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📄 Генерировать отчет", 
                callback_data=f"generate_report:{estimate_id}"
            ),
            InlineKeyboardButton(
                text="🤖 ИИ-анализ", 
                callback_data=f"ai_analyze:{estimate_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑️ Удалить", 
                callback_data=f"delete_estimate:{estimate_id}"
            ),
            InlineKeyboardButton(
                text="◀️ Назад", 
                callback_data="my_estimates"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_back_keyboard(callback_data: str = "main_menu"):
    """Простая клавиатура возврата"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data)]
    ])


def get_work_templates_keyboard():
    """Клавиатура для работы с шаблонами"""
    keyboard_buttons = [
        [
            InlineKeyboardButton(text="➕ Создать шаблон", callback_data="create_template"),
            InlineKeyboardButton(text="📋 Мои шаблоны", callback_data="my_templates")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_add_item_method_keyboard(estimate_id: int):
    """Клавиатура выбора способа добавления позиции"""
    keyboard_buttons = [
        [InlineKeyboardButton(
            text="🔧 Из шаблона", 
            callback_data=f"add_from_template:{estimate_id}"
        )],
        [InlineKeyboardButton(
            text="✏️ Вручную", 
            callback_data=f"add_manual:{estimate_id}"
        )],
        [InlineKeyboardButton(
            text="◀️ Назад", 
            callback_data=f"show_estimate:{estimate_id}"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_ai_keyboard():
    """Клавиатура ИИ-помощника"""
    keyboard_buttons = [
        [InlineKeyboardButton(
            text="🧠 Генерация сметы", 
            callback_data="ai_generate_estimate"
        )],
        [InlineKeyboardButton(
            text="💬 Консультация", 
            callback_data="ai_consultation"
        )],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_confirmation_keyboard(action: str, item_id: int):
    """Клавиатура подтверждения действия"""
    keyboard_buttons = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}:{item_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_report_type_keyboard(estimate_id: int):
    """Клавиатура выбора типа отчета"""
    keyboard_buttons = [
        [InlineKeyboardButton(
            text="📄 Текстовый", 
            callback_data=f"text_report:{estimate_id}"
        )],
        [InlineKeyboardButton(
            text="📋 PDF", 
            callback_data=f"pdf_report:{estimate_id}"
        )],
        [InlineKeyboardButton(
            text="◀️ Назад", 
            callback_data=f"show_estimate:{estimate_id}"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_project_type_keyboard():
    """Клавиатура выбора типа проекта для ИИ"""
    keyboard_buttons = [
        [
            InlineKeyboardButton(text="🌐 Веб-приложение", callback_data="ai_type:web_app"),
            InlineKeyboardButton(text="📱 Мобильное приложение", callback_data="ai_type:mobile_app")
        ],
        [
            InlineKeyboardButton(text="🖥️ Десктоп приложение", callback_data="ai_type:desktop_app"),
            InlineKeyboardButton(text="🔗 API/Сервис", callback_data="ai_type:api")
        ],
        [
            InlineKeyboardButton(text="📄 Лендинг", callback_data="ai_type:landing"),
            InlineKeyboardButton(text="🛒 Интернет-магазин", callback_data="ai_type:ecommerce")
        ],
        [
            InlineKeyboardButton(text="📊 CRM/ERP система", callback_data="ai_type:crm"),
            InlineKeyboardButton(text="🔧 Другое", callback_data="ai_type:other")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="ai_assistant")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons) 