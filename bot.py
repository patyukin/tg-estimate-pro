import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import Config
from database import Database
from report_generator import ReportGenerator
from ai_assistant import AIAssistant

# Инициализация конфигурации
config = Config()

# Проверяем конфигурацию
if not config.validate():
    raise SystemExit("Ошибка в конфигурации бота")

logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=config.bot_token)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# Инициализация базы данных
db = Database(config.database_url)
report_gen = ReportGenerator()
ai_assistant = AIAssistant(config)

# ==================== ФУНКЦИИ ФОРМАТИРОВАНИЯ ====================

def format_currency(amount: float) -> str:
    """Красивое форматирование валюты"""
    if amount >= 1000000:
        return f"{amount/1000000:.1f}М ₽"
    elif amount >= 1000:
        return f"{amount/1000:.1f}К ₽"
    else:
        return f"{amount:,.0f} ₽".replace(',', ' ')

def format_duration(hours: float) -> str:
    """Красивое форматирование времени"""
    if hours >= 24:
        days = int(hours // 24)
        remaining_hours = hours % 24
        if remaining_hours == 0:
            return f"{days} дн."
        else:
            return f"{days} дн. {remaining_hours:.1f} ч"
    else:
        return f"{hours:.1f} ч"

def create_progress_bar(current: float, total: float, length: int = 10) -> str:
    """Создание прогресс-бара"""
    if total == 0:
        return "▱" * length
    
    percentage = min(current / total, 1.0)
    filled = int(percentage * length)
    empty = length - filled
    
    return "▰" * filled + "▱" * empty

def format_estimate_card(estimate: Dict, items_count: int = 0, total_cost: float = 0, total_duration: float = 0) -> str:
    """Красивое форматирование карточки сметы"""
    # Определяем статус
    if items_count == 0:
        status = "🔄 Черновик"
        status_color = "🟡"
    elif total_cost > 0:
        status = "✅ Готова"
        status_color = "🟢"
    else:
        status = "⚠️ В работе"
        status_color = "🟠"
    
    # Формируем карточку
    card = f"""
╭─────────────────────────────╮
│ {status_color} <b>{estimate['title'][:20]}{'...' if len(estimate['title']) > 20 else ''}</b>
├─────────────────────────────┤"""
    
    if estimate.get('description'):
        desc = estimate['description'][:40] + '...' if len(estimate['description']) > 40 else estimate['description']
        card += f"\n│ 📝 {desc}"
    
    card += f"""
│ 
│ 📊 Позиций: {items_count}
│ ⏱️ Время: {format_duration(total_duration)}
│ 💰 Сумма: {format_currency(total_cost)}
│ 
│ {status}
╰─────────────────────────────╯"""
    
    return card

def format_template_card(template: Dict) -> str:
    """Красивое форматирование карточки шаблона"""
    category_emoji = {
        'Frontend': '🎨',
        'Backend': '⚙️',
        'DevOps': '🚀',
        'Design': '🎨',
        'Analytics': '📊',
        'Testing': '🧪',
        'Mobile': '📱',
        'Database': '🗄️'
    }.get(template.get('category', ''), '📋')
    
    usage_text = ""
    if template.get('usage_count', 0) > 0:
        usage_text = f"│ 🔥 Использований: {template['usage_count']}\n"
    
    card = f"""
╭─────────────────────────────╮
│ {category_emoji} <b>{template['name'][:20]}{'...' if len(template['name']) > 20 else ''}</b>
├─────────────────────────────┤
│ ⏱️ {format_duration(template['default_duration'])}
│ 💰 {format_currency(template['default_cost'])}
{usage_text}│ 📂 {template.get('category', 'Без категории')}
╰─────────────────────────────╯"""
    
    return card

def format_stats_block(estimates: list, templates: list) -> str:
    """Красивая статистика пользователя"""
    total_estimates = len(estimates)
    total_templates = len(templates)
    
    if total_estimates == 0:
        return """
🏗️ <b>Ваша статистика</b>

📊 Пока нет данных для анализа
Создайте первую смету!"""
    
    # Подсчет статистики
    total_cost = sum(est.get('total_cost', 0) for est in estimates)
    total_duration = sum(est.get('total_duration', 0) for est in estimates)
    avg_estimate_cost = total_cost / total_estimates if total_estimates > 0 else 0
    
    stats = f"""
🏗️ <b>Ваша статистика</b>

📈 <b>Общие показатели:</b>
┣ 📄 Смет создано: {total_estimates}
┣ 🔧 Шаблонов: {total_templates}
┣ 💰 Общая сумма: {format_currency(total_cost)}
┗ ⏱️ Общее время: {format_duration(total_duration)}

📊 <b>Средние значения:</b>
┣ 💵 Средняя смета: {format_currency(avg_estimate_cost)}
┗ 📏 Ставка/час: {format_currency(total_cost/total_duration if total_duration > 0 else 0).replace(' ₽', '₽/ч')}"""
    
    return stats

# FSM состояния
class EstimateStates(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_item_name = State()
    waiting_item_duration = State()
    waiting_item_cost = State()
    editing_estimate = State()
    editing_item = State()
    
    # Состояния для шаблонов работ
    waiting_template_name = State()
    waiting_template_description = State()
    waiting_template_duration = State()
    waiting_template_cost = State()
    waiting_template_category = State()
    editing_template = State()
    
    # Состояния для ИИ-помощника
    waiting_ai_description = State()
    waiting_ai_project_type = State()
    waiting_ai_consultation = State()

# Клавиатуры
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
            InlineKeyboardButton(text="🔧 Шаблоны работ", callback_data="work_templates")
        ]
    ]
    
    # Добавляем ИИ-помощника если доступен
    if ai_assistant.is_enabled():
        keyboard_buttons.append([
            InlineKeyboardButton(text="🤖 ИИ-помощник", callback_data="ai_assistant")
        ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

def get_estimate_keyboard(estimate_id: int):
    """Клавиатура для работы со сметой с улучшенным дизайном"""
    keyboard_buttons = [
        [
            InlineKeyboardButton(text="➕ Добавить", callback_data=f"add_item:{estimate_id}"),
            InlineKeyboardButton(text="📊 Отчет", callback_data=f"generate_report:{estimate_id}")
        ],
        [
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_estimate:{estimate_id}"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data=f"show_estimate:{estimate_id}")
        ]
    ]
    
    # Добавляем ИИ-анализ если доступен
    if ai_assistant.is_enabled():
        keyboard_buttons.append([
            InlineKeyboardButton(text="🤖 ИИ-анализ", callback_data=f"ai_analyze:{estimate_id}")
        ])
    
    keyboard_buttons.extend([
        [InlineKeyboardButton(text="🗑️ Удалить смету", callback_data=f"delete_estimate:{estimate_id}")],
        [InlineKeyboardButton(text="🔙 К сметам", callback_data="my_estimates")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

def get_back_keyboard(callback_data: str = "main_menu"):
    """Клавиатура с кнопкой Назад"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data)]
    ])
    return keyboard

def get_work_templates_keyboard():
    """Клавиатура для управления шаблонами работ"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать шаблон", callback_data="create_template")],
        [InlineKeyboardButton(text="📋 Мои шаблоны", callback_data="my_templates")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])
    return keyboard

def get_add_item_method_keyboard(estimate_id: int):
    """Клавиатура выбора способа добавления позиции"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔧 Из шаблонов", callback_data=f"add_from_template:{estimate_id}")],
        [InlineKeyboardButton(text="✏️ Ввести вручную", callback_data=f"add_manual:{estimate_id}")],
        [InlineKeyboardButton(text="🤖 Сгенерировать ИИ", callback_data=f"ai_generate:{estimate_id}")] if ai_assistant.is_enabled() else [],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"show_estimate:{estimate_id}")]
    ])
    return keyboard

def get_ai_keyboard():
    """Клавиатура ИИ-помощника"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔮 Сгенерировать смету", callback_data="ai_generate_estimate")],
        [InlineKeyboardButton(text="🧠 Консультация", callback_data="ai_consultation")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])
    return keyboard

# Обработчики команд
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start с красивым приветствием"""
    welcome_text = f"""
╔══════════════════════════════════╗
║        🏗️ <b>БОТ-СМЕТЧИК</b> 🏗️        ║  
╠══════════════════════════════════╣
║                                  ║
║   📊 Профессиональное создание   ║
║      смет и управление           ║
║      проектами                   ║
║                                  ║
║   🚀 <b>Возможности:</b>              ║
║   • Создание смет с ИИ           ║
║   • Шаблоны работ               ║
║   • PDF/текст отчеты            ║
║   • Статистика и аналитика      ║
║                                  ║
╚══════════════════════════════════╝

Привет, <b>{message.from_user.first_name}</b>! 👋

🎯 <b>Начнем работу?</b>"""
    
    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help"""
    help_text = """
🏗️ <b>Бот-Сметчик - Помощь</b>

<b>Возможности бота:</b>
• Создание шаблонов типовых работ/услуг
• Создание новых смет на основе шаблонов
• Отслеживание выполняемых работ (активные сметы)
• Добавление позиций работ/услуг с указанием времени и стоимости
• Редактирование существующих смет и шаблонов
• Генерация отчетов в PDF и текстовом формате
• Просмотр и управление вашими сметами

<b>Разделы меню:</b>
📝 <b>Создать новую смету</b> - создание сметы с нуля
📋 <b>Мои сметы</b> - все ваши сметы
⚡ <b>Выполняемые работы</b> - активные сметы с позициями
🔧 <b>Шаблоны работ</b> - управление каталогом работ

<b>Как использовать:</b>
1. Создайте шаблоны работ в разделе "Шаблоны работ":
   - Укажите название, время выполнения и стоимость
   - Добавьте описание и категорию (по желанию)
2. Создайте новую смету с названием и описанием
3. Добавьте позиции работ:
   - Выберите из созданных шаблонов (быстро)
   - Или введите данные вручную
4. Отслеживайте прогресс в "Выполняемые работы"
5. Генерируйте отчеты для клиентов

<b>Команды:</b>
/start - Главное меню
/help - Эта справка
    """
    await message.answer(help_text, parse_mode="HTML", reply_markup=get_back_keyboard())

# Обработчики callback запросов
@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    """Возврат в главное меню с красивым дизайном"""
    welcome_text = f"""
╔══════════════════════════════════╗
║        🏗️ <b>БОТ-СМЕТЧИК</b> 🏗️        ║  
╚══════════════════════════════════╝

Добро пожаловать, <b>{callback.from_user.first_name}</b>! 👋

🎯 <b>Выберите действие:</b>"""
    
    await callback.message.edit_text(
        welcome_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "user_stats")
async def callback_user_stats(callback: CallbackQuery):
    """Показ статистики пользователя"""
    estimates = await db.get_user_estimates(callback.from_user.id)
    templates = await db.get_user_work_templates(callback.from_user.id)
    
    # Получаем детальную статистику
    total_cost = 0
    total_duration = 0
    estimates_with_totals = []
    
    for estimate in estimates:
        totals = await db.get_estimate_total(estimate['id'])
        total_cost += totals['total_cost']
        total_duration += totals['total_duration']
        estimates_with_totals.append({
            **estimate,
            'total_cost': totals['total_cost'],
            'total_duration': totals['total_duration']
        })
    
    stats_text = format_stats_block(estimates_with_totals, templates)
    
    # Добавляем топ шаблоны
    if templates:
        top_templates = sorted(templates, key=lambda x: x.get('usage_count', 0), reverse=True)[:3]
        stats_text += "\n\n🏆 <b>Популярные шаблоны:</b>\n"
        for i, template in enumerate(top_templates, 1):
            stats_text += f"┣ {i}. {template['name'][:20]} ({template.get('usage_count', 0)} исп.)\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="user_stats")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        stats_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "settings")
async def callback_settings(callback: CallbackQuery):
    """Настройки бота"""
    settings_text = """
⚙️ <b>Настройки бота</b>

🔧 <b>Доступные опции:</b>

┣ 🤖 ИИ-помощник: """ + ("✅ Включен" if ai_assistant.is_enabled() else "❌ Отключен") + """
┣ 📊 Валюта: ₽ (Рубли)  
┣ ⏱️ Формат времени: Часы
┗ 📅 Дата создания: """ + datetime.now().strftime("%d.%m.%Y") + """

💡 <b>Советы:</b>
• Создавайте шаблоны для частых работ
• Используйте ИИ для генерации смет
• Регулярно создавайте отчеты
• Следите за статистикой проектов
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        settings_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Показ справки"""
    help_text = """
🏗️ <b>Бот-Сметчик - Помощь</b>

<b>Возможности бота:</b>
• Создание шаблонов типовых работ/услуг
• Создание новых смет на основе шаблонов
• Отслеживание выполняемых работ (активные сметы)
• Добавление позиций работ/услуг с указанием времени и стоимости
• Редактирование существующих смет и шаблонов
• Генерация отчетов в PDF и текстовом формате
• Просмотр и управление вашими сметами

<b>Разделы меню:</b>
📝 <b>Создать новую смету</b> - создание сметы с нуля
📋 <b>Мои сметы</b> - все ваши сметы
⚡ <b>Выполняемые работы</b> - активные сметы с позициями
🔧 <b>Шаблоны работ</b> - управление каталогом работ

<b>Как использовать:</b>
1. Создайте шаблоны работ в разделе "Шаблоны работ":
   - Укажите название, время выполнения и стоимость
   - Добавьте описание и категорию (по желанию)
2. Создайте новую смету с названием и описанием
3. Добавьте позиции работ:
   - Выберите из созданных шаблонов (быстро)
   - Или введите данные вручную
4. Отслеживайте прогресс в "Выполняемые работы"
5. Генерируйте отчеты для клиентов

<b>Команды:</b>
/start - Главное меню
/help - Эта справка
    """
    await callback.message.edit_text(
        help_text, 
        parse_mode="HTML", 
        reply_markup=get_back_keyboard()
    )

# === ОБРАБОТЧИКИ ШАБЛОНОВ РАБОТ ===

@router.callback_query(F.data == "work_templates")
async def callback_work_templates(callback: CallbackQuery):
    """Главное меню шаблонов работ"""
    await callback.message.edit_text(
        "🔧 <b>Шаблоны работ</b>\n\n"
        "Создавайте шаблоны типовых работ с базовым временем и стоимостью "
        "для быстрого добавления в сметы.\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_work_templates_keyboard()
    )

@router.callback_query(F.data == "create_template")
async def callback_create_template(callback: CallbackQuery, state: FSMContext):
    """Начало создания шаблона работы"""
    await callback.message.edit_text(
        "➕ <b>Создание шаблона работы</b>\n\n"
        "Введите название работы/услуги:",
        parse_mode="HTML",
        reply_markup=get_back_keyboard("work_templates")
    )
    await state.set_state(EstimateStates.waiting_template_name)

@router.message(StateFilter(EstimateStates.waiting_template_name))
async def process_template_name(message: Message, state: FSMContext):
    """Обработка названия шаблона"""
    name = message.text.strip()
    if not name:
        await message.answer("❌ Название работы не может быть пустым. Попробуйте еще раз:")
        return
    
    await state.update_data(name=name)
    await message.answer(
        f"✅ Название: {name}\n\n"
        "Введите описание работы (или отправьте 'пропустить'):",
        reply_markup=get_back_keyboard("work_templates")
    )
    await state.set_state(EstimateStates.waiting_template_description)

@router.message(StateFilter(EstimateStates.waiting_template_description))
async def process_template_description(message: Message, state: FSMContext):
    """Обработка описания шаблона"""
    description = message.text.strip()
    if description.lower() == 'пропустить':
        description = ""
    
    await state.update_data(description=description)
    await message.answer(
        f"✅ Описание добавлено\n\n"
        "Введите время выполнения работы в часах (например: 2.5):",
        reply_markup=get_back_keyboard("work_templates")
    )
    await state.set_state(EstimateStates.waiting_template_duration)

@router.message(StateFilter(EstimateStates.waiting_template_duration))
async def process_template_duration(message: Message, state: FSMContext):
    """Обработка времени выполнения шаблона"""
    try:
        duration = float(message.text.replace(",", "."))
        if duration < 0:
            await message.answer("❌ Время не может быть отрицательным. Попробуйте еще раз:")
            return
    except ValueError:
        await message.answer("❌ Неверный формат времени. Введите число (например: 2.5):")
        return
    
    await state.update_data(duration=duration)
    await message.answer(
        f"✅ Время: {duration} ч\n\n"
        "Введите стоимость работы в рублях (например: 5000):",
        reply_markup=get_back_keyboard("work_templates")
    )
    await state.set_state(EstimateStates.waiting_template_cost)

@router.message(StateFilter(EstimateStates.waiting_template_cost))
async def process_template_cost(message: Message, state: FSMContext):
    """Обработка стоимости шаблона"""
    try:
        cost = float(message.text.replace(",", "."))
        if cost < 0:
            await message.answer("❌ Стоимость не может быть отрицательной. Попробуйте еще раз:")
            return
    except ValueError:
        await message.answer("❌ Неверный формат стоимости. Введите число (например: 5000):")
        return
    
    await state.update_data(cost=cost)
    await message.answer(
        f"✅ Стоимость: {cost} ₽\n\n"
        "Введите категорию работы (например: 'Программирование', 'Дизайн') или отправьте 'пропустить':",
        reply_markup=get_back_keyboard("work_templates")
    )
    await state.set_state(EstimateStates.waiting_template_category)

@router.message(StateFilter(EstimateStates.waiting_template_category))
async def process_template_category(message: Message, state: FSMContext):
    """Обработка категории шаблона"""
    category = message.text.strip()
    if category.lower() == 'пропустить':
        category = None
    
    data = await state.get_data()
    
    # Создаем шаблон в базе
    template_id = await db.create_work_template(
        user_id=message.from_user.id,
        name=data['name'],
        description=data['description'],
        default_duration=data['duration'],
        default_cost=data['cost'],
        category=category
    )
    
    await state.clear()
    
    category_text = f"\n📂 Категория: {category}" if category else ""
    await message.answer(
        f"✅ <b>Шаблон работы создан!</b>\n\n"
        f"📝 Название: {data['name']}\n"
        f"📄 Описание: {data['description'] or 'Не указано'}\n"
        f"⏱ Время: {data['duration']} ч\n"
        f"💰 Стоимость: {data['cost']} ₽{category_text}",
        parse_mode="HTML",
        reply_markup=get_work_templates_keyboard()
    )

@router.callback_query(F.data == "my_templates")
async def callback_my_templates(callback: CallbackQuery):
    """Показ списка шаблонов пользователя"""
    templates = await db.get_user_work_templates(callback.from_user.id)
    
    if not templates:
        await callback.message.edit_text(
            "📋 У вас пока нет ни одного шаблона работ.\n\n"
            "Создайте первый шаблон!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Создать шаблон", callback_data="create_template")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="work_templates")]
            ])
        )
        return
    
    keyboard_buttons = []
    text_lines = ["📋 <b>Ваши шаблоны работ:</b>\n"]
    
    for template in templates:
        category_text = f" ({template['category']})" if template['category'] else ""
        text_lines.append(
            f"• {template['name']}{category_text}\n"
            f"  ⏱ {template['default_duration']} ч, 💰 {template['default_cost']} ₽"
        )
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"🔧 {template['name'][:25]}...", 
                callback_data=f"show_template:{template['id']}"
            )
        ])
    
    keyboard_buttons.append([InlineKeyboardButton(text="➕ Создать новый", callback_data="create_template")])
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="work_templates")])
    
    await callback.message.edit_text(
        "\n".join(text_lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    )

@router.callback_query(F.data.startswith("show_template:"))
async def callback_show_template(callback: CallbackQuery):
    """Показ конкретного шаблона"""
    template_id = int(callback.data.split(":")[1])
    
    template = await db.get_work_template(template_id, callback.from_user.id)
    if not template:
        await callback.answer("❌ Шаблон не найден", show_alert=True)
        return
    
    category_text = f"\n📂 Категория: {template['category']}" if template['category'] else ""
    usage_text = f"\n📊 Использований: {template['usage_count']}" if template['usage_count'] > 0 else ""
    
    template_text = (
        f"🔧 <b>Шаблон: {template['name']}</b>\n\n"
        f"📄 Описание: {template['description'] or 'Не указано'}\n"
        f"⏱ Время выполнения: {template['default_duration']} ч\n"
        f"💰 Стоимость: {template['default_cost']} ₽{category_text}{usage_text}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_template:{template_id}")],
        [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_template:{template_id}")],
        [InlineKeyboardButton(text="🔙 К списку", callback_data="my_templates")]
    ])
    
    await callback.message.edit_text(template_text, parse_mode="HTML", reply_markup=keyboard)

@router.callback_query(F.data.startswith("delete_template:"))
async def callback_delete_template(callback: CallbackQuery):
    """Удаление шаблона"""
    template_id = int(callback.data.split(":")[1])
    
    # Подтверждение удаления
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_template:{template_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"show_template:{template_id}")
        ]
    ])
    
    await callback.message.edit_text(
        "⚠️ Вы уверены, что хотите удалить этот шаблон?\n\n"
        "Это действие нельзя отменить!",
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("confirm_delete_template:"))
async def callback_confirm_delete_template(callback: CallbackQuery):
    """Подтверждение удаления шаблона"""
    template_id = int(callback.data.split(":")[1])
    
    await db.delete_work_template(template_id, callback.from_user.id)
    
    await callback.message.edit_text(
        "✅ Шаблон успешно удален!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Мои шаблоны", callback_data="my_templates")],
            [InlineKeyboardButton(text="🔧 Шаблоны работ", callback_data="work_templates")]
        ])
    )

# Обработчики создания смет
@router.callback_query(F.data == "create_estimate")
async def callback_create_estimate(callback: CallbackQuery, state: FSMContext):
    """Начало создания новой сметы"""
    await callback.message.edit_text(
        "📝 Создание новой сметы\n\nВведите название сметы:",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(EstimateStates.waiting_title)

@router.message(StateFilter(EstimateStates.waiting_title))
async def process_estimate_title(message: Message, state: FSMContext):
    """Обработка названия сметы"""
    title = message.text.strip()
    if not title:
        await message.answer("❌ Название сметы не может быть пустым. Попробуйте еще раз:")
        return
    
    await state.update_data(title=title)
    await message.answer(
        f"✅ Название: {title}\n\nТеперь введите описание сметы (или отправьте 'пропустить'):",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(EstimateStates.waiting_description)

@router.message(StateFilter(EstimateStates.waiting_description))
async def process_estimate_description(message: Message, state: FSMContext):
    """Обработка описания сметы"""
    description = message.text.strip()
    if description.lower() == 'пропустить':
        description = ""
    
    data = await state.get_data()
    title = data['title']
    
    # Создаем смету в базе
    estimate_id = await db.create_estimate(message.from_user.id, title, description)
    
    await state.clear()
    await message.answer(
        f"✅ Смета '{title}' успешно создана!\n\n"
        f"Теперь вы можете добавить позиции работ/услуг.",
        reply_markup=get_estimate_keyboard(estimate_id)
    )

@router.callback_query(F.data == "my_estimates")
async def callback_my_estimates(callback: CallbackQuery):
    """Показ списка смет пользователя"""
    estimates = await db.get_user_estimates(callback.from_user.id)
    
    if not estimates:
        await callback.message.edit_text(
            "📋 У вас пока нет ни одной сметы.\n\nСоздайте первую смету!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Создать смету", callback_data="create_estimate")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
            ])
        )
        return
    
    keyboard_buttons = []
    text_lines = ["📋 <b>Ваши сметы:</b>\n"]
    
    for estimate in estimates:
        # PostgreSQL возвращает datetime объект, не строку
        if isinstance(estimate['created_at'], str):
            created_date = datetime.fromisoformat(estimate['created_at'].replace('Z', '+00:00'))
        else:
            created_date = estimate['created_at']
        text_lines.append(f"• {estimate['title']} ({created_date.strftime('%d.%m.%Y')})")
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"📄 {estimate['title']}", 
                callback_data=f"show_estimate:{estimate['id']}"
            )
        ])
    
    keyboard_buttons.append([InlineKeyboardButton(text="📝 Создать новую", callback_data="create_estimate")])
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    
    await callback.message.edit_text(
        "\n".join(text_lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    )

@router.callback_query(F.data == "active_estimates")
async def callback_active_estimates(callback: CallbackQuery):
    """Показ активных смет (выполняемые работы)"""
    estimates = await db.get_user_estimates(callback.from_user.id)
    
    if not estimates:
        await callback.message.edit_text(
            "⚡ У вас пока нет ни одной сметы.\n\nСоздайте первую смету!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Создать смету", callback_data="create_estimate")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
            ])
        )
        return
    
    # Фильтруем активные сметы (со статусом active или draft с позициями)
    active_estimates = []
    for estimate in estimates:
        items = await db.get_estimate_items(estimate['id'])
        if items:  # Если есть позиции, считаем смету активной
            active_estimates.append((estimate, items))
    
    if not active_estimates:
        await callback.message.edit_text(
            "⚡ <b>Выполняемые работы</b>\n\n"
            "У вас пока нет активных смет с позициями работ.\n\n"
            "Создайте смету и добавьте в неё работы!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Создать смету", callback_data="create_estimate")],
                [InlineKeyboardButton(text="📋 Все сметы", callback_data="my_estimates")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
            ])
        )
        return
    
    keyboard_buttons = []
    text_lines = ["⚡ <b>Выполняемые работы:</b>\n"]
    
    for estimate, items in active_estimates:
        # PostgreSQL возвращает datetime объект, не строку
        if isinstance(estimate['created_at'], str):
            created_date = datetime.fromisoformat(estimate['created_at'].replace('Z', '+00:00'))
        else:
            created_date = estimate['created_at']
        
        totals = await db.get_estimate_total(estimate['id'])
        text_lines.append(
            f"• <b>{estimate['title']}</b> ({created_date.strftime('%d.%m.%Y')})\n"
            f"  📋 {len(items)} поз. | ⏱ {totals['total_duration']} ч | 💰 {totals['total_cost']} ₽"
        )
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"⚡ {estimate['title']}", 
                callback_data=f"show_estimate:{estimate['id']}"
            )
        ])
    
    keyboard_buttons.append([InlineKeyboardButton(text="📝 Создать новую", callback_data="create_estimate")])
    keyboard_buttons.append([InlineKeyboardButton(text="📋 Все сметы", callback_data="my_estimates")])
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    
    await callback.message.edit_text(
        "\n".join(text_lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    )

@router.callback_query(F.data.startswith("show_estimate:"))
async def callback_show_estimate(callback: CallbackQuery):
    """Показ конкретной сметы с красивым оформлением"""
    estimate_id = int(callback.data.split(":")[1])
    
    estimate = await db.get_estimate(estimate_id, callback.from_user.id)
    if not estimate:
        await callback.answer("❌ Смета не найдена", show_alert=True)
        return
    
    items = await db.get_estimate_items(estimate_id)
    totals = await db.get_estimate_total(estimate_id)
    
    # Определяем статус сметы
    items_count = len(items)
    if items_count == 0:
        status_indicator = "🔄 Черновик"
        progress_emoji = "⭕"
    elif totals['total_cost'] > 0:
        status_indicator = "✅ Готова к работе"
        progress_emoji = "🟢"
    else:
        status_indicator = "⚠️ В процессе"
        progress_emoji = "🟡"
    
    # Создаем заголовок сметы
    header = f"""
╔══════════════════════════════════╗
║ {progress_emoji} <b>{estimate['title'][:25]}{'...' if len(estimate['title']) > 25 else ''}</b>
╚══════════════════════════════════╝

{status_indicator}"""
    
    if estimate.get('description'):
        header += f"\n\n📝 <i>{estimate['description']}</i>"
    
    # Формируем основной контент
    content_lines = [header, "\n"]
    
    if items:
        content_lines.append("📋 <b>ПОЗИЦИИ РАБОТ:</b>\n")
        
        for i, item in enumerate(items, 1):
            # Форматируем каждую позицию как карточку
            rate = item['cost'] / item['duration'] if item['duration'] > 0 else 0
            
            item_card = f"""
╭─────────────────────────────╮
│ <b>{i}. {item['name'][:20]}{'...' if len(item['name']) > 20 else ''}</b>
├─────────────────────────────┤
│ ⏱️ {format_duration(item['duration'])}
│ 💰 {format_currency(item['cost'])}
│ 📊 {format_currency(rate).replace(' ₽', '₽/ч')}
╰─────────────────────────────╯"""
            
            content_lines.append(item_card)
        
        # Итоговая статистика
        avg_rate = totals['total_cost'] / totals['total_duration'] if totals['total_duration'] > 0 else 0
        
        summary = f"""

╔═══════════════════════════════════╗
║           📊 <b>ИТОГО</b> 📊           ║
╠═══════════════════════════════════╣
║                                   ║
║ ⏱️ Время: <b>{format_duration(totals['total_duration'])}</b>
║ 💰 Сумма: <b>{format_currency(totals['total_cost'])}</b>
║ 📈 Ставка: <b>{format_currency(avg_rate).replace(' ₽', '₽/ч')}</b>
║ 📋 Позиций: <b>{items_count}</b>
║                                   ║
╚═══════════════════════════════════╝"""
        
        content_lines.append(summary)
        
    else:
        content_lines.append("""
╭─────────────────────────────╮
│         📝 <b>ПУСТАЯ СМЕТА</b>        │
├─────────────────────────────┤
│                             │
│  💡 Добавьте первую позицию │
│     для начала работы       │
│                             │
╰─────────────────────────────╯""")
    
    await callback.message.edit_text(
        "\n".join(content_lines),
        parse_mode="HTML",
        reply_markup=get_estimate_keyboard(estimate_id)
    )

# Обработчики добавления позиций
@router.callback_query(F.data.startswith("add_item:"))
async def callback_add_item(callback: CallbackQuery, state: FSMContext):
    """Выбор способа добавления позиции в смету"""
    estimate_id = int(callback.data.split(":")[1])
    
    estimate = await db.get_estimate(estimate_id, callback.from_user.id)
    if not estimate:
        await callback.answer("❌ Смета не найдена", show_alert=True)
        return
    
    await state.update_data(estimate_id=estimate_id)
    await callback.message.edit_text(
        f"➕ <b>Добавление позиции в смету '{estimate['title']}'</b>\n\n"
        "Выберите способ добавления:",
        parse_mode="HTML",
        reply_markup=get_add_item_method_keyboard(estimate_id)
    )

@router.callback_query(F.data.startswith("add_from_template:"))
async def callback_add_from_template(callback: CallbackQuery, state: FSMContext):
    """Добавление позиции из шаблона"""
    estimate_id = int(callback.data.split(":")[1])
    templates = await db.get_user_work_templates(callback.from_user.id)
    
    if not templates:
        await callback.message.edit_text(
            "❌ У вас нет ни одного шаблона работ.\n\n"
            "Сначала создайте шаблоны в разделе 'Шаблоны работ' или добавьте позицию вручную.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔧 Создать шаблон", callback_data="create_template")],
                [InlineKeyboardButton(text="✏️ Ввести вручную", callback_data=f"add_manual:{estimate_id}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data=f"show_estimate:{estimate_id}")]
            ])
        )
        return
    
    keyboard_buttons = []
    text_lines = ["🔧 <b>Выберите шаблон работы:</b>\n"]
    
    # Группируем по категориям
    categories = {}
    for template in templates:
        category = template['category'] or 'Без категории'
        if category not in categories:
            categories[category] = []
        categories[category].append(template)
    
    for category, category_templates in categories.items():
        text_lines.append(f"\n📂 <b>{category}</b>")
        for template in category_templates:
            text_lines.append(
                f"• {template['name']}\n"
                f"  ⏱ {template['default_duration']} ч, 💰 {template['default_cost']} ₽"
            )
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"🔧 {template['name'][:30]}...", 
                    callback_data=f"use_template:{estimate_id}:{template['id']}"
                )
            ])
    
    keyboard_buttons.append([InlineKeyboardButton(text="✏️ Ввести вручную", callback_data=f"add_manual:{estimate_id}")])
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"show_estimate:{estimate_id}")])
    
    await callback.message.edit_text(
        "\n".join(text_lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    )

@router.callback_query(F.data.startswith("use_template:"))
async def callback_use_template(callback: CallbackQuery):
    """Использование шаблона для добавления позиции"""
    parts = callback.data.split(":")
    estimate_id = int(parts[1])
    template_id = int(parts[2])
    
    template = await db.get_work_template(template_id, callback.from_user.id)
    if not template:
        await callback.answer("❌ Шаблон не найден", show_alert=True)
        return
    
    # Добавляем позицию в смету на основе шаблона
    item_id = await db.add_estimate_item(
        estimate_id=estimate_id,
        name=template['name'],
        duration=template['default_duration'],
        cost=template['default_cost']
    )
    
    # Увеличиваем счетчик использования шаблона
    await db.increment_template_usage(template_id)
    
    await callback.answer("✅ Позиция добавлена из шаблона")
    
    # Возвращаемся к просмотру сметы
    await callback_show_estimate(callback)

@router.callback_query(F.data.startswith("add_manual:"))
async def callback_add_manual(callback: CallbackQuery, state: FSMContext):
    """Ручное добавление позиции в смету"""
    estimate_id = int(callback.data.split(":")[1])
    
    estimate = await db.get_estimate(estimate_id, callback.from_user.id)
    if not estimate:
        await callback.answer("❌ Смета не найдена", show_alert=True)
        return
    
    await state.update_data(estimate_id=estimate_id)
    await callback.message.edit_text(
        f"✏️ <b>Ручное добавление позиции в смету '{estimate['title']}'</b>\n\n"
        "Введите наименование работы/услуги:",
        parse_mode="HTML",
        reply_markup=get_back_keyboard(f"show_estimate:{estimate_id}")
    )
    await state.set_state(EstimateStates.waiting_item_name)

@router.message(StateFilter(EstimateStates.waiting_item_name))
async def process_item_name(message: Message, state: FSMContext):
    """Обработка названия позиции"""
    name = message.text.strip()
    if not name:
        await message.answer("❌ Название не может быть пустым. Попробуйте еще раз:")
        return
    
    await state.update_data(item_name=name)
    data = await state.get_data()
    
    await message.answer(
        f"✅ Наименование: {name}\n\n"
        "Введите время выполнения в часах (например: 2.5):",
        reply_markup=get_back_keyboard(f"show_estimate:{data['estimate_id']}")
    )
    await state.set_state(EstimateStates.waiting_item_duration)

@router.message(StateFilter(EstimateStates.waiting_item_duration))
async def process_item_duration(message: Message, state: FSMContext):
    """Обработка времени выполнения"""
    try:
        duration = float(message.text.strip().replace(',', '.'))
        if duration <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректное время в часах (например: 2.5):")
        return
    
    await state.update_data(item_duration=duration)
    data = await state.get_data()
    
    await message.answer(
        f"✅ Время: {duration} ч\n\n"
        "Введите стоимость в рублях (например: 5000):",
        reply_markup=get_back_keyboard(f"show_estimate:{data['estimate_id']}")
    )
    await state.set_state(EstimateStates.waiting_item_cost)

@router.message(StateFilter(EstimateStates.waiting_item_cost))
async def process_item_cost(message: Message, state: FSMContext):
    """Обработка стоимости позиции"""
    try:
        cost = float(message.text.strip().replace(',', '.'))
        if cost < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректную стоимость в рублях (например: 5000):")
        return
    
    data = await state.get_data()
    estimate_id = data['estimate_id']
    item_name = data['item_name']
    item_duration = data['item_duration']
    
    # Добавляем позицию в базу
    await db.add_estimate_item(estimate_id, item_name, item_duration, cost)
    
    await state.clear()
    
    # Показываем обновленную смету
    estimate = await db.get_estimate(estimate_id, message.from_user.id)
    items = await db.get_estimate_items(estimate_id)
    totals = await db.get_estimate_total(estimate_id)
    
    await message.answer(
        f"✅ Позиция '{item_name}' добавлена!\n\n"
        f"📄 <b>{estimate['title']}</b>\n"
        f"Позиций в смете: {len(items)}\n"
        f"Общая стоимость: {totals['total_cost']} ₽",
        parse_mode="HTML",
        reply_markup=get_estimate_keyboard(estimate_id)
    )

# Обработчики редактирования
@router.callback_query(F.data.startswith("edit_estimate:"))
async def callback_edit_estimate(callback: CallbackQuery):
    """Меню редактирования сметы"""
    estimate_id = int(callback.data.split(":")[1])
    
    estimate = await db.get_estimate(estimate_id, callback.from_user.id)
    if not estimate:
        await callback.answer("❌ Смета не найдена", show_alert=True)
        return
    
    items = await db.get_estimate_items(estimate_id)
    
    keyboard_buttons = [
        [InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"edit_title:{estimate_id}")],
        [InlineKeyboardButton(text="📝 Изменить описание", callback_data=f"edit_description:{estimate_id}")]
    ]
    
    if items:
        keyboard_buttons.append([InlineKeyboardButton(text="📋 Редактировать позиции", callback_data=f"edit_items:{estimate_id}")])
    
    keyboard_buttons.extend([
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"show_estimate:{estimate_id}")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        f"✏️ Редактирование сметы '{estimate['title']}'\n\nВыберите что изменить:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    )

@router.callback_query(F.data.startswith("edit_items:"))
async def callback_edit_items(callback: CallbackQuery):
    """Список позиций для редактирования"""
    estimate_id = int(callback.data.split(":")[1])
    
    items = await db.get_estimate_items(estimate_id)
    
    if not items:
        await callback.answer("❌ В смете нет позиций", show_alert=True)
        return
    
    keyboard_buttons = []
    text_lines = ["📋 <b>Выберите позицию для редактирования:</b>\n"]
    
    for i, item in enumerate(items, 1):
        text_lines.append(f"{i}. {item['name']} ({item['duration']} ч, {item['cost']} ₽)")
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"✏️ {item['name'][:20]}...", 
                callback_data=f"edit_item_detail:{item['id']}"
            ),
            InlineKeyboardButton(
                text="🗑️", 
                callback_data=f"delete_item:{item['id']}:{estimate_id}"
            )
        ])
    
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"edit_estimate:{estimate_id}")])
    
    await callback.message.edit_text(
        "\n".join(text_lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    )

@router.callback_query(F.data.startswith("delete_item:"))
async def callback_delete_item(callback: CallbackQuery):
    """Удаление позиции из сметы"""
    parts = callback.data.split(":")
    item_id = int(parts[1])
    estimate_id = int(parts[2])
    
    await db.delete_estimate_item(item_id)
    await callback.answer("✅ Позиция удалена")
    
    # Возвращаемся к списку позиций
    await callback_edit_items(callback)

@router.callback_query(F.data.startswith("delete_estimate:"))
async def callback_delete_estimate(callback: CallbackQuery):
    """Удаление сметы"""
    estimate_id = int(callback.data.split(":")[1])
    
    # Подтверждение удаления
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete:{estimate_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"show_estimate:{estimate_id}")
        ]
    ])
    
    await callback.message.edit_text(
        "⚠️ Вы уверены, что хотите удалить смету?\n\nЭто действие нельзя отменить!",
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("confirm_delete:"))
async def callback_confirm_delete(callback: CallbackQuery):
    """Подтверждение удаления сметы"""
    estimate_id = int(callback.data.split(":")[1])
    
    await db.delete_estimate(estimate_id, callback.from_user.id)
    
    await callback.message.edit_text(
        "✅ Смета успешно удалена!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Мои сметы", callback_data="my_estimates")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
    )

# Обработчики генерации отчетов
@router.callback_query(F.data.startswith("generate_report:"))
async def callback_generate_report(callback: CallbackQuery):
    """Выбор типа отчета"""
    estimate_id = int(callback.data.split(":")[1])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Текстовый отчет", callback_data=f"text_report:{estimate_id}")],
        [InlineKeyboardButton(text="📊 PDF отчет", callback_data=f"pdf_report:{estimate_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"show_estimate:{estimate_id}")]
    ])
    
    await callback.message.edit_text(
        "📊 Выберите тип отчета:",
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("text_report:"))
async def callback_text_report(callback: CallbackQuery):
    """Генерация текстового отчета"""
    estimate_id = int(callback.data.split(":")[1])
    
    estimate = await db.get_estimate(estimate_id, callback.from_user.id)
    if not estimate:
        await callback.answer("❌ Смета не найдена", show_alert=True)
        return
    
    items = await db.get_estimate_items(estimate_id)
    totals = await db.get_estimate_total(estimate_id)
    
    # Генерируем текстовый отчет
    report_text = report_gen.generate_text_report(estimate, items, totals)
    
    # Отправляем отчет как документ
    from io import BytesIO
    report_file = BytesIO(report_text.encode('utf-8'))
    report_file.name = f"smeta_{estimate['title']}.txt"
    
    await callback.message.answer_document(
        document=report_file,
        caption=f"📄 Текстовый отчет по смете '{estimate['title']}'",
        reply_markup=get_estimate_keyboard(estimate_id)
    )

@router.callback_query(F.data.startswith("pdf_report:"))
async def callback_pdf_report(callback: CallbackQuery):
    """Генерация PDF отчета"""
    estimate_id = int(callback.data.split(":")[1])
    
    estimate = await db.get_estimate(estimate_id, callback.from_user.id)
    if not estimate:
        await callback.answer("❌ Смета не найдена", show_alert=True)
        return
    
    items = await db.get_estimate_items(estimate_id)
    totals = await db.get_estimate_total(estimate_id)
    
    try:
        # Генерируем PDF отчет
        pdf_buffer = report_gen.generate_estimate_report(estimate, items, totals)
        pdf_buffer.name = f"smeta_{estimate['title']}.pdf"
        
        await callback.message.answer_document(
            document=pdf_buffer,
            caption=f"📊 PDF отчет по смете '{estimate['title']}'",
            reply_markup=get_estimate_keyboard(estimate_id)
        )
    except Exception as e:
        logger.error(f"Ошибка генерации PDF: {e}")
        await callback.answer("❌ Ошибка при генерации PDF отчета", show_alert=True)

# Обработчики ИИ-помощника
@router.callback_query(F.data == "ai_assistant")
async def callback_ai_assistant(callback: CallbackQuery):
    """Главное меню ИИ-помощника"""
    if not ai_assistant.is_enabled():
        await callback.answer("❌ ИИ-помощник недоступен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🤖 <b>ИИ-помощник</b>\n\n"
        "Выберите, что вас интересует:\n\n"
        "🔮 <b>Генерация сметы</b> - создание позиций на основе описания проекта\n"
        "🧠 <b>Консультация</b> - профессиональные советы по смете и проекту",
        parse_mode="HTML",
        reply_markup=get_ai_keyboard()
    )

@router.callback_query(F.data == "ai_generate_estimate")
async def callback_ai_generate_estimate(callback: CallbackQuery, state: FSMContext):
    """Начало генерации сметы ИИ"""
    if not ai_assistant.is_enabled():
        await callback.answer("❌ ИИ-помощник недоступен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🔮 <b>Генерация сметы с помощью ИИ</b>\n\n"
        "Опишите ваш проект максимально подробно:\n"
        "- Что нужно сделать?\n"
        "- Какие функции должны быть?\n"
        "- Есть ли особые требования?\n\n"
        "Чем подробнее описание, тем точнее будет смета!",
        parse_mode="HTML",
        reply_markup=get_back_keyboard("ai_assistant")
    )
    
    await state.set_state(EstimateStates.waiting_ai_description)

@router.message(StateFilter(EstimateStates.waiting_ai_description))
async def process_ai_description(message: Message, state: FSMContext):
    """Обработка описания проекта для ИИ"""
    project_description = message.text
    
    await state.update_data(ai_description=project_description)
    
    # Клавиатура с типами проектов
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Веб-сайт", callback_data="ai_type:веб-разработка")],
        [InlineKeyboardButton(text="📱 Мобильное приложение", callback_data="ai_type:мобильная разработка")],
        [InlineKeyboardButton(text="🖥️ Десктоп приложение", callback_data="ai_type:десктоп разработка")],
        [InlineKeyboardButton(text="🎨 Дизайн", callback_data="ai_type:дизайн")],
        [InlineKeyboardButton(text="🔧 Интеграция/API", callback_data="ai_type:интеграция")],
        [InlineKeyboardButton(text="📊 Аналитика/BI", callback_data="ai_type:аналитика")],
        [InlineKeyboardButton(text="🏢 Общий проект", callback_data="ai_type:общий")]
    ])
    
    await message.answer(
        "📋 <b>Тип проекта</b>\n\n"
        "Выберите тип проекта для более точной оценки:",
        parse_mode="HTML",
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("ai_type:"))
async def callback_ai_type(callback: CallbackQuery, state: FSMContext):
    """Обработка типа проекта и генерация сметы"""
    project_type = callback.data.split(":")[1]
    
    state_data = await state.get_data()
    project_description = state_data.get("ai_description", "")
    
    logger.info(f"🤖 Пользователь {callback.from_user.id} ({callback.from_user.full_name}) запросил генерацию ИИ-сметы")
    logger.info(f"📝 Тип проекта: {project_type}")
    logger.info(f"📋 Описание проекта: {project_description[:100]}...")
    
    await callback.message.edit_text(
        "🤖 <b>Генерирую смету...</b>\n\n"
        "Пожалуйста, подождите, ИИ анализирует ваш проект и создает детальную смету.",
        parse_mode="HTML"
    )
    
    start_time = time.time()
    
    try:
        # Генерируем позиции сметы с помощью ИИ (в отдельном потоке)
        ai_items = await asyncio.to_thread(
            ai_assistant.generate_estimate_items, 
            project_description, 
            project_type
        )
        
        generation_time = time.time() - start_time
        
        if not ai_items:
            logger.warning(f"❌ Не удалось сгенерировать смету для пользователя {callback.from_user.id} за {generation_time:.2f} сек")
            await callback.message.edit_text(
                "❌ <b>Не удалось сгенерировать смету</b>\n\n"
                "Попробуйте:\n"
                "- Более подробно описать проект\n"
                "- Проверить настройки ИИ\n"
                "- Повторить попытку позже",
                parse_mode="HTML",
                reply_markup=get_back_keyboard("ai_assistant")
            )
            await state.clear()
            return
        
        logger.info(f"✅ Сгенерировано {len(ai_items)} позиций за {generation_time:.2f} сек")
        
        # Создаем смету
        estimate_title = f"ИИ-смета: {project_type}"
        estimate_id = await db.create_estimate(
            callback.from_user.id, 
            estimate_title, 
            project_description
        )
        
        logger.info(f"📊 Создана смета #{estimate_id} для пользователя {callback.from_user.id}")
        
        # Добавляем позиции в смету
        added_items = []
        for item in ai_items:
            try:
                await db.add_estimate_item(estimate_id, item.name, item.duration, item.cost)
                added_items.append(item)
            except Exception as e:
                logger.error(f"❌ Ошибка добавления позиции '{item.name}': {e}")
        
        # Показываем результат
        total_cost = sum(item.cost for item in added_items)
        total_duration = sum(item.duration for item in added_items)
        
        total_time = time.time() - start_time
        logger.info(f"💰 Общая стоимость: {total_cost:.2f}₽, время: {total_duration:.1f}ч")
        logger.info(f"🎉 Смета #{estimate_id} создана за {total_time:.2f} сек")
        
        result_text = f"✅ <b>Смета сгенерирована!</b>\n\n"
        result_text += f"📋 <b>Название:</b> {estimate_title}\n"
        result_text += f"⏱️ <b>Время:</b> {total_duration:.1f} часов\n"
        result_text += f"💰 <b>Стоимость:</b> {total_cost:.2f} ₽\n"
        result_text += f"📊 <b>Позиций:</b> {len(added_items)}\n\n"
        
        if added_items:
            result_text += "<b>Основные позиции:</b>\n"
            for i, item in enumerate(added_items[:5], 1):
                result_text += f"{i}. {item.name} ({item.duration}ч, {item.cost:.0f}₽)\n"
            
            if len(added_items) > 5:
                result_text += f"... и еще {len(added_items) - 5} позиций\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👁️ Посмотреть смету", callback_data=f"show_estimate:{estimate_id}")],
            [InlineKeyboardButton(text="🤖 Новая генерация", callback_data="ai_generate_estimate")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(
            result_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        await state.clear()
        
    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"❌ Ошибка генерации ИИ-сметы для пользователя {callback.from_user.id} за {error_time:.2f} сек: {e}")
        await callback.message.edit_text(
            "❌ <b>Произошла ошибка при генерации сметы</b>\n\n"
            "Попробуйте позже или обратитесь к администратору.",
            parse_mode="HTML",
            reply_markup=get_back_keyboard("ai_assistant")
        )
        await state.clear()

@router.callback_query(F.data.startswith("ai_generate:"))
async def callback_ai_generate_for_estimate(callback: CallbackQuery, state: FSMContext):
    """Генерация позиций для существующей сметы"""
    estimate_id = int(callback.data.split(":")[1])
    
    if not ai_assistant.is_enabled():
        await callback.answer("❌ ИИ-помощник недоступен", show_alert=True)
        return
    
    estimate = await db.get_estimate(estimate_id, callback.from_user.id)
    if not estimate:
        await callback.answer("❌ Смета не найдена", show_alert=True)
        return
    
    await state.update_data(ai_estimate_id=estimate_id)
    
    await callback.message.edit_text(
        f"🔮 <b>Дополнение сметы '{estimate['title']}'</b>\n\n"
        "Опишите какие дополнительные работы нужны:\n"
        "- Что еще нужно сделать?\n"
        "- Какие функции добавить?\n"
        "- Есть ли новые требования?\n\n"
        "ИИ предложит подходящие позиции для вашей сметы!",
        parse_mode="HTML",
        reply_markup=get_back_keyboard(f"show_estimate:{estimate_id}")
    )
    
    await state.set_state(EstimateStates.waiting_ai_description)

@router.callback_query(F.data.startswith("ai_analyze:"))
async def callback_ai_analyze(callback: CallbackQuery):
    """Анализ сметы с помощью ИИ"""
    estimate_id = int(callback.data.split(":")[1])
    
    if not ai_assistant.is_enabled():
        await callback.answer("❌ ИИ-помощник недоступен", show_alert=True)
        return
    
    estimate = await db.get_estimate(estimate_id, callback.from_user.id)
    if not estimate:
        await callback.answer("❌ Смета не найдена", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🤖 <b>Анализирую смету...</b>\n\n"
        "ИИ изучает вашу смету и готовит рекомендации по улучшению.",
        parse_mode="HTML"
    )
    
    try:
        items = await db.get_estimate_items(estimate_id)
        
        if not items:
            await callback.message.edit_text(
                "❌ <b>Невозможно проанализировать</b>\n\n"
                "В смете нет позиций для анализа.",
                parse_mode="HTML",
                reply_markup=get_back_keyboard(f"show_estimate:{estimate_id}")
            )
            return
        
        # Анализируем смету (в отдельном потоке)
        analysis = await asyncio.to_thread(
            ai_assistant.analyze_estimate, 
            estimate, 
            items
        )
        
        if not analysis.suggestions and not analysis.optimization_tips:
            await callback.message.edit_text(
                "❌ <b>Анализ не удался</b>\n\n"
                "Попробуйте позже или обратитесь к администратору.",
                parse_mode="HTML",
                reply_markup=get_back_keyboard(f"show_estimate:{estimate_id}")
            )
            return
        
        # Формируем отчет
        report_text = f"🔍 <b>Анализ сметы '{estimate['title']}'</b>\n\n"
        
        if analysis.suggestions:
            report_text += "💡 <b>Рекомендации:</b>\n"
            for i, suggestion in enumerate(analysis.suggestions, 1):
                report_text += f"{i}. {suggestion}\n"
            report_text += "\n"
        
        if analysis.optimization_tips:
            report_text += "⚡ <b>Оптимизация:</b>\n"
            for i, tip in enumerate(analysis.optimization_tips, 1):
                report_text += f"{i}. {tip}\n"
            report_text += "\n"
        
        if analysis.risk_factors:
            report_text += "⚠️ <b>Риски:</b>\n"
            for i, risk in enumerate(analysis.risk_factors, 1):
                report_text += f"{i}. {risk}\n"
            report_text += "\n"
        
        if analysis.total_estimation:
            est = analysis.total_estimation
            if est.get('min_cost') and est.get('max_cost'):
                report_text += f"💰 <b>Диапазон стоимости:</b> {est['min_cost']:.0f} - {est['max_cost']:.0f} ₽\n"
            if est.get('recommended_buffer'):
                report_text += f"🛡️ <b>Рекомендуемый буфер:</b> {est['recommended_buffer']:.0f}%\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К смете", callback_data=f"show_estimate:{estimate_id}")],
            [InlineKeyboardButton(text="🤖 Новый анализ", callback_data=f"ai_analyze:{estimate_id}")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(
            report_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка анализа сметы: {e}")
        await callback.message.edit_text(
            "❌ <b>Произошла ошибка при анализе</b>\n\n"
            "Попробуйте позже или обратитесь к администратору.",
            parse_mode="HTML",
            reply_markup=get_back_keyboard(f"show_estimate:{estimate_id}")
        )

@router.callback_query(F.data == "ai_consultation")
async def callback_ai_consultation(callback: CallbackQuery, state: FSMContext):
    """Консультация с ИИ"""
    if not ai_assistant.is_enabled():
        await callback.answer("❌ ИИ-помощник недоступен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🧠 <b>ИИ-консультант</b>\n\n"
        "Задайте любой вопрос по смете или проекту:\n\n"
        "Например:\n"
        "• Как правильно оценить время на разработку?\n"
        "• Какие работы часто забывают включить в смету?\n"
        "• Как защитить себя от рисков?\n"
        "• Стоит ли делать скидку клиенту?\n\n"
        "Просто напишите свой вопрос:",
        parse_mode="HTML",
        reply_markup=get_back_keyboard("ai_assistant")
    )
    
    await state.set_state(EstimateStates.waiting_ai_consultation)

@router.message(StateFilter(EstimateStates.waiting_ai_consultation))
async def process_ai_consultation(message: Message, state: FSMContext):
    """Обработка вопроса для консультации"""
    question = message.text
    
    await message.answer(
        "🤖 <b>Думаю над вашим вопросом...</b>\n\n"
        "Анализирую и готовлю профессиональную консультацию.",
        parse_mode="HTML"
    )
    
    try:
        # Получаем ответ от ИИ (в отдельном потоке)
        answer = await asyncio.to_thread(
            ai_assistant.get_consultation, 
            question
        )
        
        if not answer or len(answer) < 10:
            await message.answer(
                "❌ <b>Не удалось получить ответ</b>\n\n"
                "Попробуйте переформулировать вопрос или обратитесь позже.",
                parse_mode="HTML",
                reply_markup=get_back_keyboard("ai_assistant")
            )
            await state.clear()
            return
        
        # Ограничиваем длину ответа для Telegram
        if len(answer) > 3000:
            answer = answer[:3000] + "..."
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❓ Задать еще вопрос", callback_data="ai_consultation")],
            [InlineKeyboardButton(text="🤖 ИИ-помощник", callback_data="ai_assistant")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await message.answer(
            f"🧠 <b>Консультация ИИ-эксперта:</b>\n\n{answer}",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка консультации: {e}")
        await message.answer(
            "❌ <b>Произошла ошибка при получении консультации</b>\n\n"
            "Попробуйте позже или обратитесь к администратору.",
            parse_mode="HTML",
            reply_markup=get_back_keyboard("ai_assistant")
        )
        await state.clear()

async def main():
    """Запуск бота"""
    try:
        # Инициализация базы данных
        await db.init_db()
        logger.info("База данных инициализирована")
        
        # Регистрация роутера
        dp.include_router(router)
        
        # Запуск бота
        logger.info("Запуск бота...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await db.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main()) 