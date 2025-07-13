"""
Обработчики сообщений в FSM состояниях
"""
import logging

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.keyboards.inline import get_main_keyboard, get_estimate_keyboard
from bot.keyboards.reply import get_cancel_keyboard, get_category_keyboard, get_skip_keyboard, remove_keyboard
from bot.utils.states import EstimateStates, TemplateStates, AIStates
from bot.utils.decorators import error_handler
from bot.utils.validators import validate_duration, validate_cost, validate_text_length, sanitize_text
from bot.utils.helpers import format_estimate_card

logger = logging.getLogger(__name__)
router = Router()


# === ОБРАБОТКА ОТМЕНЫ ===

@router.message(F.text == "🚫 Отмена")
@error_handler
async def process_cancel(message: Message, state: FSMContext, **kwargs):
    """Отмена любого FSM состояния"""
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer(
            "❌ Действие отменено!",
            reply_markup=remove_keyboard()
        )
        await message.answer(
            "🏗️ <b>Главное меню</b>",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )


# === СОЗДАНИЕ ШАБЛОНОВ ===

@router.message(StateFilter(TemplateStates.waiting_template_name))
@error_handler
async def process_template_name(message: Message, state: FSMContext, **kwargs):
    """Обработка названия шаблона"""
    name = sanitize_text(message.text)
    
    # Валидация
    is_valid, error_msg = validate_text_length(name, min_length=3, max_length=100)
    if not is_valid:
        await message.answer(error_msg)
        return
    
    await state.update_data(name=name)
    await message.answer(
        f"✅ <b>Название:</b> {name}\n\n"
        f"📝 Теперь введите описание шаблона:\n"
        f"<i>Или нажмите 'Пропустить' если не нужно</i>",
        reply_markup=get_skip_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(TemplateStates.waiting_template_description)


@router.message(StateFilter(TemplateStates.waiting_template_description))
@error_handler
async def process_template_description(message: Message, state: FSMContext, **kwargs):
    """Обработка описания шаблона"""
    if message.text == "⏭️ Пропустить":
        description = ""
    else:
        description = sanitize_text(message.text)
        is_valid, error_msg = validate_text_length(description, min_length=0, max_length=500)
        if not is_valid:
            await message.answer(error_msg)
            return
    
    await state.update_data(description=description)
    await message.answer(
        "⏱️ Введите время выполнения в часах:\n"
        "<i>Например: 8 или 2.5</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(TemplateStates.waiting_template_duration)


@router.message(StateFilter(TemplateStates.waiting_template_duration))
@error_handler
async def process_template_duration(message: Message, state: FSMContext, **kwargs):
    """Обработка времени выполнения шаблона"""
    is_valid, duration, error_msg = validate_duration(message.text)
    if not is_valid:
        await message.answer(error_msg)
        return
    
    await state.update_data(duration=duration)
    await message.answer(
        f"✅ <b>Время:</b> {duration} ч\n\n"
        f"💰 Введите стоимость в рублях:\n"
        f"<i>Например: 5000 или 7500.50</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(TemplateStates.waiting_template_cost)


@router.message(StateFilter(TemplateStates.waiting_template_cost))
@error_handler
async def process_template_cost(message: Message, state: FSMContext, **kwargs):
    """Обработка стоимости шаблона"""
    is_valid, cost, error_msg = validate_cost(message.text)
    if not is_valid:
        await message.answer(error_msg)
        return
    
    await state.update_data(cost=cost)
    await message.answer(
        f"✅ <b>Стоимость:</b> {cost} ₽\n\n"
        f"📂 Выберите категорию:",
        reply_markup=get_category_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(TemplateStates.waiting_template_category)


@router.message(StateFilter(TemplateStates.waiting_template_category))
@error_handler
async def process_template_category(message: Message, state: FSMContext, user_id: int, db, **kwargs):
    """Обработка категории и создание шаблона"""
    category = message.text
    
    # Проверяем валидность категории
    valid_categories = [
        "Frontend", "Backend", "DevOps", "Design", 
        "Analytics", "Testing", "Mobile", "Database"
    ]
    
    if category not in valid_categories:
        await message.answer(
            "⚠️ Выберите категорию из предложенных кнопок!"
        )
        return
    
    # Получаем все данные
    data = await state.get_data()
    
    try:
        # Создаем шаблон в базе данных
        template_id = await db.create_work_template(
            user_id=user_id,
            name=data['name'],
            description=data['description'],
            category=category,
            default_duration=data['duration'],
            default_cost=data['cost']
        )
        
        await message.answer(
            f"✅ <b>Шаблон создан!</b>\n\n"
            f"📝 <b>Название:</b> {data['name']}\n"
            f"📂 <b>Категория:</b> {category}\n"
            f"⏱️ <b>Время:</b> {data['duration']} ч\n"
            f"💰 <b>Стоимость:</b> {data['cost']} ₽",
            reply_markup=remove_keyboard(),
            parse_mode="HTML"
        )
        
        await message.answer(
            "🏗️ <b>Главное меню</b>",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка создания шаблона: {e}")
        await message.answer(
            "⚠️ Ошибка при создании шаблона. Попробуйте позже.",
            reply_markup=remove_keyboard()
        )
    
    await state.clear()


# === СОЗДАНИЕ СМЕТ ===

@router.message(StateFilter(EstimateStates.waiting_title))
@error_handler
async def process_estimate_title(message: Message, state: FSMContext, **kwargs):
    """Обработка названия сметы"""
    title = sanitize_text(message.text)
    
    # Валидация
    is_valid, error_msg = validate_text_length(title, min_length=3, max_length=200)
    if not is_valid:
        await message.answer(error_msg)
        return
    
    await state.update_data(title=title)
    await message.answer(
        f"✅ <b>Название:</b> {title}\n\n"
        f"📝 Добавьте описание проекта:\n"
        f"<i>Или нажмите 'Пропустить' если не нужно</i>",
        reply_markup=get_skip_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(EstimateStates.waiting_description)


@router.message(StateFilter(EstimateStates.waiting_description))
@error_handler
async def process_estimate_description(message: Message, state: FSMContext, user_id: int, db, **kwargs):
    """Обработка описания и создание сметы"""
    if message.text == "⏭️ Пропустить":
        description = ""
    else:
        description = sanitize_text(message.text)
        is_valid, error_msg = validate_text_length(description, min_length=0, max_length=1000)
        if not is_valid:
            await message.answer(error_msg)
            return
    
    # Получаем данные
    data = await state.get_data()
    
    try:
        # Создаем смету в базе данных
        estimate_id = await db.create_estimate(
            user_id=user_id,
            title=data['title'],
            description=description
        )
        
        # Получаем созданную смету
        estimate = await db.get_estimate_by_id(estimate_id, user_id)
        
        success_text = f"""
✅ <b>Смета создана!</b>

{format_estimate_card(estimate, 0, 0, 0)}

Теперь добавьте позиции работ:
"""
        
        await message.answer(
            success_text,
            reply_markup=remove_keyboard(),
            parse_mode="HTML"
        )
        
        await message.answer(
            "Что будем делать дальше?",
            reply_markup=get_estimate_keyboard(estimate_id),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка создания сметы: {e}")
        await message.answer(
            "⚠️ Ошибка при создании сметы. Попробуйте позже.",
            reply_markup=remove_keyboard()
        )
    
    await state.clear()


# === ДОБАВЛЕНИЕ ПОЗИЦИЙ В СМЕТУ ===

@router.message(StateFilter(EstimateStates.waiting_item_name))
@error_handler
async def process_item_name(message: Message, state: FSMContext, **kwargs):
    """Обработка названия позиции"""
    name = sanitize_text(message.text)
    
    # Валидация
    is_valid, error_msg = validate_text_length(name, min_length=3, max_length=200)
    if not is_valid:
        await message.answer(error_msg)
        return
    
    await state.update_data(item_name=name)
    await message.answer(
        f"✅ <b>Позиция:</b> {name}\n\n"
        f"⏱️ Введите время выполнения в часах:\n"
        f"<i>Например: 8 или 2.5</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(EstimateStates.waiting_item_duration)


@router.message(StateFilter(EstimateStates.waiting_item_duration))
@error_handler
async def process_item_duration(message: Message, state: FSMContext, **kwargs):
    """Обработка времени выполнения позиции"""
    is_valid, duration, error_msg = validate_duration(message.text)
    if not is_valid:
        await message.answer(error_msg)
        return
    
    await state.update_data(item_duration=duration)
    await message.answer(
        f"✅ <b>Время:</b> {duration} ч\n\n"
        f"💰 Введите стоимость в рублях:\n"
        f"<i>Например: 5000 или 7500.50</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(EstimateStates.waiting_item_cost)


@router.message(StateFilter(EstimateStates.waiting_item_cost))
@error_handler
async def process_item_cost(message: Message, state: FSMContext, user_id: int, db, **kwargs):
    """Обработка стоимости позиции и добавление в смету"""
    is_valid, cost, error_msg = validate_cost(message.text)
    if not is_valid:
        await message.answer(error_msg)
        return
    
    # Получаем все данные
    data = await state.get_data()
    estimate_id = data['estimate_id']
    
    try:
        # Добавляем позицию в смету
        item_id = await db.add_estimate_item(
            estimate_id=estimate_id,
            name=data['item_name'],
            description="",
            duration=data['item_duration'],
            cost=cost
        )
        
        # Получаем обновленную смету
        estimate = await db.get_estimate_by_id(estimate_id, user_id)
        
        success_text = f"""
✅ <b>Позиция добавлена!</b>

📝 <b>Название:</b> {data['item_name']}
⏱️ <b>Время:</b> {data['item_duration']} ч
💰 <b>Стоимость:</b> {cost} ₽

{format_estimate_card(estimate, estimate.get('items_count', 0), estimate.get('total_cost', 0), estimate.get('total_duration', 0))}
"""
        
        await message.answer(
            success_text,
            reply_markup=remove_keyboard(),
            parse_mode="HTML"
        )
        
        await message.answer(
            "Что будем делать дальше?",
            reply_markup=get_estimate_keyboard(estimate_id),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка добавления позиции: {e}")
        await message.answer(
            "⚠️ Ошибка при добавлении позиции. Попробуйте позже.",
            reply_markup=remove_keyboard()
        )
    
    await state.clear()


# === ИИ-ПОМОЩНИК ===

@router.message(StateFilter(AIStates.waiting_ai_description))
@error_handler
async def process_ai_description(message: Message, state: FSMContext, **kwargs):
    """Обработка описания проекта для ИИ"""
    description = sanitize_text(message.text)
    
    # Валидация
    is_valid, error_msg = validate_text_length(description, min_length=10, max_length=1000)
    if not is_valid:
        await message.answer(error_msg)
        return
    
    await state.update_data(ai_description=description)
    await message.answer(
        f"✅ <b>Описание принято!</b>\n\n"
        f"📋 Выберите тип проекта:",
        reply_markup=remove_keyboard(),
        parse_mode="HTML"
    )
    
    # Отправляем клавиатуру выбора типа проекта
    from bot.keyboards.inline import get_project_type_keyboard
    await message.answer(
        "🎯 <b>Тип проекта:</b>",
        reply_markup=get_project_type_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AIStates.waiting_ai_project_type)


@router.message(StateFilter(AIStates.waiting_ai_consultation))
@error_handler
async def process_ai_consultation(message: Message, state: FSMContext, config, **kwargs):
    """Обработка консультации с ИИ"""
    question = sanitize_text(message.text)
    
    # Валидация
    is_valid, error_msg = validate_text_length(question, min_length=5, max_length=500)
    if not is_valid:
        await message.answer(error_msg)
        return
    
    await message.answer(
        "🤖 Обрабатываю ваш запрос...",
        reply_markup=remove_keyboard()
    )
    
    # Здесь должна быть интеграция с ИИ
    if config.is_ai_available:
        # TODO: Интеграция с GigaChat или другим ИИ
        response = f"""
🤖 <b>ИИ-консультант отвечает:</b>

По вашему вопросу: "{question[:100]}"

К сожалению, ИИ-помощник временно недоступен. 
Попробуйте позже или обратитесь к документации.

💡 <b>Общие рекомендации:</b>
• Разбивайте сложные задачи на простые
• Используйте шаблоны для типовых работ
• Учитывайте время на тестирование и отладку
• Добавляйте 20-30% к оценкам времени
"""
    else:
        response = """
🤖 <b>ИИ-помощник недоступен</b>

Для работы с ИИ необходимо настроить подключение к сервису.

💡 <b>Альтернативы:</b>
• Используйте готовые шаблоны
• Обратитесь к документации
• Воспользуйтесь статистикой проектов
"""
    
    await message.answer(
        response,
        parse_mode="HTML"
    )
    
    await message.answer(
        "🏗️ <b>Главное меню</b>",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )
    
    await state.clear() 