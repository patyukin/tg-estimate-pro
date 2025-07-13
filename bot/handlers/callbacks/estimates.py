"""
Обработчики для управления сметами
"""
import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.keyboards.inline import (
    get_estimate_keyboard, get_add_item_method_keyboard
)
from bot.keyboards.reply import get_cancel_keyboard
from bot.utils.states import EstimateStates
from bot.utils.decorators import error_handler
from bot.utils.helpers import format_estimate_card

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "create_estimate")
@error_handler
async def callback_create_estimate(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Создание новой сметы"""
    await callback.message.edit_text(
        "📝 <b>Создание новой сметы</b>\n\n"
        "Введите название сметы:\n"
        "<i>Например: 'Разработка интернет-магазина'</i>",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "Введите название сметы:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(EstimateStates.waiting_title)


@router.callback_query(F.data == "my_estimates")
@error_handler
async def callback_my_estimates(callback: CallbackQuery, user_id: int, db, **kwargs):
    """Показ всех смет пользователя"""
    estimates = await db.get_user_estimates(user_id)
    
    if not estimates:
        text = """
📋 <b>Мои сметы</b>

📝 У вас пока нет смет.

Создайте первую смету для начала работы!
"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Создать смету", callback_data="create_estimate")],
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
        ])
    else:
        text = f"📋 <b>Мои сметы</b> ({len(estimates)})\n\n"
        
        # Показываем последние 5 смет
        for estimate in estimates[:5]:
            items_count = estimate.get('items_count', 0)
            total_cost = estimate.get('total_cost', 0)
            total_duration = estimate.get('total_duration', 0)
            
            text += format_estimate_card(estimate, items_count, total_cost, total_duration) + "\n\n"
        
        # Создаем клавиатуру
        keyboard_buttons = []
        for i, estimate in enumerate(estimates[:8]):  # Ограничиваем 8 сметами
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"📄 {estimate['title'][:25]}", 
                    callback_data=f"show_estimate:{estimate['id']}"
                )
            ])
        
        keyboard_buttons.extend([
            [InlineKeyboardButton(text="📝 Новая смета", callback_data="create_estimate")],
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("show_estimate:"))
@error_handler
async def callback_show_estimate(callback: CallbackQuery, user_id: int, db, **kwargs):
    """Показ детальной информации о смете"""
    estimate_id = int(callback.data.split(":")[1])
    estimate = await db.get_estimate_by_id(estimate_id, user_id)
    
    if not estimate:
        await callback.answer("⚠️ Смета не найдена!")
        return
    
    # Получаем позиции сметы
    items = await db.get_estimate_items(estimate_id)
    
    text = f"""
📄 <b>{estimate['title']}</b>

"""
    
    if estimate.get('description'):
        text += f"📝 <b>Описание:</b>\n{estimate['description']}\n\n"
    
    # Показываем позиции
    if items:
        text += f"📊 <b>Позиции работ ({len(items)}):</b>\n\n"
        total_cost = 0
        total_duration = 0
        
        for i, item in enumerate(items[:10], 1):  # Показываем первые 10
            total_cost += item['cost']
            total_duration += item['duration']
            text += f"┣ {i}. <b>{item['name']}</b>\n"
            text += f"   ⏱️ {item['duration']} ч  💰 {item['cost']:,.0f} ₽\n"
        
        if len(items) > 10:
            text += f"\n... и еще {len(items) - 10} позиций\n"
        
        text += f"\n📈 <b>Итого:</b>\n"
        text += f"⏱️ Время: {total_duration} ч\n"
        text += f"💰 Стоимость: {total_cost:,.0f} ₽"
    else:
        text += "📝 Пока нет позиций в смете.\n\nДобавьте первую позицию!"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_estimate_keyboard(estimate_id)
    )


@router.callback_query(F.data.startswith("add_item:"))
@error_handler
async def callback_add_item(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Выбор способа добавления позиции"""
    estimate_id = int(callback.data.split(":")[1])
    
    text = """
➕ <b>Добавление позиции</b>

Выберите способ добавления:
• <b>Из шаблона</b> - быстро и стандартно
• <b>Вручную</b> - полный контроль
"""
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_add_item_method_keyboard(estimate_id)
    )


@router.callback_query(F.data.startswith("add_manual:"))
@error_handler
async def callback_add_manual(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Добавление позиции вручную"""
    estimate_id = int(callback.data.split(":")[1])
    
    await state.update_data(estimate_id=estimate_id)
    
    await callback.message.edit_text(
        "✏️ <b>Добавление позиции вручную</b>\n\n"
        "Введите название позиции:\n"
        "<i>Например: 'Разработка API пользователей'</i>",
        parse_mode="HTML"
    )
    
    await callback.message.answer(
        "Введите название позиции:",
        reply_markup=get_cancel_keyboard()
    )
    
    await state.set_state(EstimateStates.waiting_item_name)


@router.callback_query(F.data.startswith("add_from_template:"))
@error_handler
async def callback_add_from_template(callback: CallbackQuery, user_id: int, db, **kwargs):
    """Показ шаблонов для добавления"""
    estimate_id = int(callback.data.split(":")[1])
    templates = await db.get_user_templates(user_id)
    
    if not templates:
        text = """
🔧 <b>Шаблоны недоступны</b>

У вас пока нет шаблонов.
Создайте шаблон или добавьте позицию вручную.
"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✏️ Добавить вручную",
                callback_data=f"add_manual:{estimate_id}"
            )],
            [InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"show_estimate:{estimate_id}"
            )]
        ])
    else:
        text = f"🔧 <b>Выберите шаблон</b> ({len(templates)})\n\n"
        
        # Группируем по категориям
        categories = {}
        for template in templates:
            category = template.get('category', 'Без категории')
            if category not in categories:
                categories[category] = []
            categories[category].append(template)
        
        # Создаем клавиатуру
        keyboard_buttons = []
        for category, cat_templates in categories.items():
            text += f"📂 <b>{category}</b>\n"
            for template in cat_templates[:3]:
                text += f"┣ {template['name']} ({template['default_duration']} ч, {template['default_cost']} ₽)\n"
                keyboard_buttons.append([InlineKeyboardButton(
                    text=f"🔧 {template['name'][:35]}",
                    callback_data=f"use_template:{estimate_id}:{template['id']}"
                )])
            text += "\n"
        
        keyboard_buttons.extend([
            [InlineKeyboardButton(
                text="✏️ Добавить вручную",
                callback_data=f"add_manual:{estimate_id}"
            )],
            [InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"show_estimate:{estimate_id}"
            )]
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("use_template:"))
@error_handler
async def callback_use_template(callback: CallbackQuery, user_id: int, db, **kwargs):
    """Использование шаблона для добавления позиции"""
    parts = callback.data.split(":")
    estimate_id = int(parts[1])
    template_id = int(parts[2])
    
    # Получаем шаблон
    template = await db.get_template_by_id(template_id)
    if not template:
        await callback.answer("⚠️ Шаблон не найден!")
        return
    
    try:
        # Добавляем позицию из шаблона
        item_id = await db.add_estimate_item(
            estimate_id=estimate_id,
            name=template['name'],
            description=template.get('description', ''),
            duration=template['default_duration'],
            cost=template['default_cost']
        )
        
        # Увеличиваем счетчик использования шаблона
        await db.increment_template_usage(template_id)
        
        await callback.answer("✅ Позиция добавлена!")
        
        # Показываем обновленную смету
        await callback_show_estimate(callback, user_id=user_id, db=db)
        
    except Exception as e:
        logger.error(f"Ошибка добавления позиции из шаблона: {e}")
        await callback.answer("⚠️ Ошибка при добавлении позиции!")


@router.callback_query(F.data.startswith("delete_estimate:"))
@error_handler
async def callback_delete_estimate(callback: CallbackQuery, **kwargs):
    """Подтверждение удаления сметы"""
    estimate_id = int(callback.data.split(":")[1])
    
    text = "🗑️ <b>Удаление сметы</b>\n\nВы уверены, что хотите удалить эту смету?"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_delete:estimate:{estimate_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"show_estimate:{estimate_id}")
        ]
    ])
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("confirm_delete:"))
@error_handler
async def callback_confirm_delete(callback: CallbackQuery, user_id: int, db, **kwargs):
    """Окончательное удаление"""
    parts = callback.data.split(":")
    item_type = parts[1]  # estimate или item
    item_id = int(parts[2])
    
    if item_type == "estimate":
        success = await db.delete_estimate(item_id, user_id)
        if success:
            await callback.answer("✅ Смета удалена!")
            await callback_my_estimates(callback, user_id=user_id, db=db)
        else:
            await callback.answer("⚠️ Ошибка при удалении!")


@router.callback_query(F.data == "active_estimates")
@error_handler
async def callback_active_estimates(callback: CallbackQuery, user_id: int, db, **kwargs):
    """Показ активных смет (с позициями)"""
    estimates = await db.get_user_estimates(user_id)
    
    # Фильтруем только сметы с позициями
    active_estimates = []
    for estimate in estimates:
        items_count = estimate.get('items_count', 0)
        if items_count > 0:
            active_estimates.append(estimate)
    
    if not active_estimates:
        text = """
⚡ <b>Активные сметы</b>

📝 Нет смет с позициями работ.

Создайте смету и добавьте позиции,
чтобы они появились здесь!
"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Создать смету", callback_data="create_estimate")],
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
        ])
    else:
        text = f"⚡ <b>Активные сметы</b> ({len(active_estimates)})\n\n"
        
        for estimate in active_estimates[:5]:
            items_count = estimate.get('items_count', 0)
            total_cost = estimate.get('total_cost', 0)
            total_duration = estimate.get('total_duration', 0)
            
            # Прогресс-бар (условно считаем что 100% = все позиции готовы)
            progress = "▰▰▰▱▱▱▱" if items_count > 0 else "▱▱▱▱▱▱▱"
            
            text += f"""
╭─────────────────────────╮
│ 📄 <b>{estimate['title'][:20]}</b>
├─────────────────────────┤
│ 📊 Позиций: {items_count}
│ ⏱️ Время: {total_duration} ч
│ 💰 Сумма: {total_cost:,.0f} ₽
│ 📈 {progress}
╰─────────────────────────╯

"""
        
        # Клавиатура
        keyboard_buttons = []
        for estimate in active_estimates[:6]:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"⚡ {estimate['title'][:25]}", 
                    callback_data=f"show_estimate:{estimate['id']}"
                )
            ])
        
        keyboard_buttons.extend([
            [InlineKeyboardButton(text="📋 Все сметы", callback_data="my_estimates")],
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    ) 