"""
Reply клавиатуры
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_cancel_keyboard():
    """Клавиатура отмены действия"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🚫 Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def get_skip_keyboard():
    """Клавиатура пропуска этапа"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭️ Пропустить")],
            [KeyboardButton(text="🚫 Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def get_category_keyboard():
    """Клавиатура выбора категории шаблона"""
    categories = [
        "Frontend", "Backend", "DevOps", "Design", 
        "Analytics", "Testing", "Mobile", "Database"
    ]
    
    keyboard_buttons = []
    # Группируем по 2 кнопки в ряд
    for i in range(0, len(categories), 2):
        row = [KeyboardButton(text=categories[i])]
        if i + 1 < len(categories):
            row.append(KeyboardButton(text=categories[i + 1]))
        keyboard_buttons.append(row)
    
    # Добавляем кнопку отмены
    keyboard_buttons.append([KeyboardButton(text="🚫 Отмена")])
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def remove_keyboard():
    """Удаление клавиатуры"""
    from aiogram.types import ReplyKeyboardRemove
    return ReplyKeyboardRemove() 