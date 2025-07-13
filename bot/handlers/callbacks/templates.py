"""
Обработчики для управления шаблонами работ
"""
import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.keyboards.inline import get_work_templates_keyboard
from bot.keyboards.reply import get_cancel_keyboard
from bot.utils.states import TemplateStates
from bot.utils.decorators import error_handler
from bot.utils.helpers import format_template_card

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "work_templates")
@error_handler
async def callback_work_templates(callback: CallbackQuery, **kwargs):
    """Меню работы с шаблонами"""
    text = """
🔧 <b>Шаблоны работ</b>

Создавайте и используйте шаблоны для:
• Ускорения создания смет
• Стандартизации работ
• Точной оценки времени и стоимости

<b>Выберите действие:</b>
"""
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_work_templates_keyboard()
    )


@router.callback_query(F.data == "create_template")
@error_handler
async def callback_create_template(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Создание нового шаблона"""
    await callback.message.edit_text(
        "📝 <b>Создание шаблона работы</b>\n\n"
        "Введите название шаблона:\n"
        "<i>Например: 'Верстка главной страницы'</i>",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "Введите название шаблона:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(TemplateStates.waiting_template_name)


@router.callback_query(F.data == "my_templates")
@error_handler
async def callback_my_templates(callback: CallbackQuery, user_id: int, db, **kwargs):
    """Показ пользовательских шаблонов"""
    templates = await db.get_user_templates(user_id)
    
    if not templates:
        text = """
🔧 <b>Мои шаблоны</b>

📝 У вас пока нет шаблонов.

Создайте первый шаблон для ускорения работы!
"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать шаблон", callback_data="create_template")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="work_templates")]
        ])
    else:
        text = f"🔧 <b>Мои шаблоны</b> ({len(templates)})\n\n"
        
        # Группируем по категориям
        categories = {}
        for template in templates:
            category = template.get('category', 'Без категории')
            if category not in categories:
                categories[category] = []
            categories[category].append(template)
        
        for category, cat_templates in categories.items():
            text += f"📂 <b>{category}</b>\n"
            for template in cat_templates[:3]:  # Показываем только первые 3
                text += format_template_card(template) + "\n"
            if len(cat_templates) > 3:
                text += f"... и еще {len(cat_templates) - 3} шаблонов\n"
            text += "\n"
        
        # Создаем клавиатуру с шаблонами
        keyboard_buttons = []
        for i, template in enumerate(templates[:10]):  # Ограничиваем 10 шаблонами
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"🔧 {template['name'][:30]}", 
                    callback_data=f"show_template:{template['id']}"
                )
            ])
        
        keyboard_buttons.extend([
            [InlineKeyboardButton(text="➕ Создать шаблон", callback_data="create_template")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="work_templates")]
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("show_template:"))
@error_handler
async def callback_show_template(callback: CallbackQuery, db, **kwargs):
    """Показ детальной информации о шаблоне"""
    template_id = int(callback.data.split(":")[1])
    template = await db.get_template_by_id(template_id)
    
    if not template:
        await callback.answer("⚠️ Шаблон не найден!")
        return
    
    text = f"""
🔧 <b>Шаблон работы</b>

<b>📝 Название:</b> {template['name']}
<b>📂 Категория:</b> {template.get('category', 'Без категории')}
<b>⏱️ Время:</b> {template['default_duration']} ч
<b>💰 Стоимость:</b> {template['default_cost']} ₽
<b>🔥 Использований:</b> {template.get('usage_count', 0)}
"""
    
    if template.get('description'):
        text += f"\n<b>📄 Описание:</b>\n{template['description']}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🗑️ Удалить", 
            callback_data=f"delete_template:{template_id}"
        )],
        [InlineKeyboardButton(text="◀️ К списку", callback_data="my_templates")]
    ])
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("delete_template:"))
@error_handler
async def callback_delete_template(callback: CallbackQuery, **kwargs):
    """Подтверждение удаления шаблона"""
    template_id = int(callback.data.split(":")[1])
    
    text = "🗑️ <b>Удаление шаблона</b>\n\nВы уверены, что хотите удалить этот шаблон?"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_delete_template:{template_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"show_template:{template_id}")
        ]
    ])
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("confirm_delete_template:"))
@error_handler
async def callback_confirm_delete_template(callback: CallbackQuery, user_id: int, db, **kwargs):
    """Окончательное удаление шаблона"""
    template_id = int(callback.data.split(":")[1])
    
    success = await db.delete_template(template_id, user_id)
    
    if success:
        await callback.answer("✅ Шаблон удален!")
        await callback_my_templates(callback, user_id=user_id, db=db)
    else:
        await callback.answer("⚠️ Ошибка при удалении!") 