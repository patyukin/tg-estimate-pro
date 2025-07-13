"""
Обработчики ИИ-помощника
"""
import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.keyboards.inline import get_ai_keyboard, get_back_keyboard
from bot.keyboards.reply import get_cancel_keyboard
from bot.utils.states import AIStates
from bot.utils.decorators import error_handler

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "ai_assistant")
@error_handler
async def callback_ai_assistant(callback: CallbackQuery, config, **kwargs):
    """Меню ИИ-помощника"""
    if config.is_ai_available:
        text = """
🤖 <b>ИИ-помощник</b>

Искусственный интеллект поможет вам:
• 🧠 Генерировать сметы по описанию
• 💬 Консультировать по проектам
• 📊 Анализировать сложность задач

<b>Выберите действие:</b>
"""
    else:
        text = """
🤖 <b>ИИ-помощник недоступен</b>

Для работы с ИИ необходимо настроить
подключение к сервису GigaChat.

💡 <b>Альтернативы:</b>
• Используйте готовые шаблоны
• Создавайте сметы вручную
"""
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_ai_keyboard() if config.is_ai_available else get_back_keyboard()
    )


@router.callback_query(F.data == "ai_generate_estimate")
@error_handler
async def callback_ai_generate_estimate(callback: CallbackQuery, state: FSMContext, config, **kwargs):
    """Генерация сметы с помощью ИИ"""
    if not config.is_ai_available:
        await callback.answer("⚠️ ИИ-помощник недоступен!")
        return
    
    await callback.message.edit_text(
        "🤖 <b>Генерация сметы с ИИ</b>\n\n"
        "Опишите ваш проект:\n"
        "<i>Чем подробнее опишете, тем точнее будет смета</i>",
        parse_mode="HTML"
    )
    
    await callback.message.answer(
        "Опишите проект (минимум 10 символов):",
        reply_markup=get_cancel_keyboard()
    )
    
    await state.set_state(AIStates.waiting_ai_description)


@router.callback_query(F.data == "ai_consultation")
@error_handler
async def callback_ai_consultation(callback: CallbackQuery, state: FSMContext, config, **kwargs):
    """ИИ консультация"""
    if not config.is_ai_available:
        await callback.answer("⚠️ ИИ-помощник недоступен!")
        return
    
    await callback.message.edit_text(
        "💬 <b>Консультация с ИИ</b>\n\n"
        "Задайте вопрос о разработке, оценке времени,\n"
        "выборе технологий или планировании проекта:",
        parse_mode="HTML"
    )
    
    await callback.message.answer(
        "Задайте ваш вопрос:",
        reply_markup=get_cancel_keyboard()
    )
    
    await state.set_state(AIStates.waiting_ai_consultation) 