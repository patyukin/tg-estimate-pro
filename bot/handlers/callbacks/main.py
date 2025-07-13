"""
Обработчики главного меню и навигации
"""
import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.keyboards.inline import get_main_keyboard, get_back_keyboard
from bot.utils.decorators import error_handler
from bot.utils.helpers import format_stats_block

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "main_menu")
@error_handler
async def callback_main_menu(callback: CallbackQuery, **kwargs):
    """Возврат в главное меню"""
    welcome_text = f"""
🏗️ <b>EstimatePro</b>

Добро пожаловать, <b>{callback.from_user.first_name}</b>! 👋

🎯 <b>Выберите действие:</b>"""
    
    await callback.message.edit_text(
        welcome_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )


@router.callback_query(F.data == "user_stats")
@error_handler
async def callback_user_stats(callback: CallbackQuery, user_id: int, db, **kwargs):
    """Показ статистики пользователя"""
    estimates = await db.get_user_estimates(user_id)
    templates = await db.get_user_templates(user_id)
    
    stats_text = format_stats_block(estimates, templates)
    
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
@error_handler
async def callback_settings(callback: CallbackQuery, config, **kwargs):
    """Настройки бота"""
    settings_text = f"""
⚙️ <b>Настройки бота</b>

🔧 <b>Доступные опции:</b>

┣ 🤖 ИИ-помощник: {"✅ Включен" if config.is_ai_available else "❌ Отключен"}
┣ 📊 Валюта: ₽ (Рубли)  
┣ ⏱️ Формат времени: Часы
┗ 📅 Дата создания: {datetime.now().strftime("%d.%m.%Y")}

💡 <b>Советы:</b>
• Создавайте шаблоны для частых работ
• Используйте ИИ для генерации смет
• Регулярно создавайте отчеты
• Следите за статистикой проектов
"""
    
    await callback.message.edit_text(
        settings_text,
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )


@router.callback_query(F.data == "help")
@error_handler
async def callback_help(callback: CallbackQuery, **kwargs):
    """Показ справки"""
    help_text = """
🆘 <b>Помощь по использованию EstimatePro</b>

<b>📝 Основные функции:</b>
• <b>Сметы</b> - создание и управление сметами проектов
• <b>Шаблоны</b> - сохранение часто используемых работ
• <b>ИИ-помощник</b> - автоматическая генерация смет
• <b>Отчеты</b> - экспорт в различных форматах

<b>🚀 Быстрый старт:</b>
1. Нажмите "📝 Новая смета"
2. Введите название проекта
3. Добавьте описание (опционально)
4. Добавляйте позиции работ
5. Генерируйте отчет

<b>💡 Полезные советы:</b>
• Используйте шаблоны для ускорения работы
• ИИ-помощник поможет оценить сложные проекты
• Все данные сохраняются автоматически
• Можно экспортировать сметы в PDF

<b>🔧 Шаблоны работ:</b>
Создавайте шаблоны для повторяющихся задач:
Frontend, Backend, DevOps, Design и др.

<b>🤖 ИИ-ассистент:</b>
Опишите проект, выберите тип, и получите
готовую смету с разбивкой по задачам.

<b>❓ Нужна помощь?</b>
Используйте кнопки меню для навигации
"""
    
    await callback.message.edit_text(
        help_text,
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    ) 