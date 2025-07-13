"""
Обработчики команд бота
"""
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from bot.keyboards.inline import get_main_keyboard
from bot.utils.decorators import error_handler


def setup_commands_router(logger: logging.Logger) -> Router:
    """Настройка роутера для команд"""
    router = Router()


    @router.message(Command("start"))
    @error_handler
    async def cmd_start(message: Message, user_id: int = None, **kwargs):
        """Команда /start"""
        logger.info(f"Пользователь {message.from_user.id} выполнил команду /start")
        welcome_text = f"""
🏗️ <b>Добро пожаловать в EstimatePro!</b>

Привет, {message.from_user.first_name}! 👋

Этот бот поможет вам:
📝 Создавать профессиональные сметы
⚡ Управлять проектами
🔧 Использовать шаблоны работ
🤖 Получать помощь ИИ-ассистента
📊 Анализировать затраты времени

<b>Начните с создания первой сметы!</b>
"""
        
        await message.answer(
            welcome_text,
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )


    @router.message(Command("help"))
    @error_handler
    async def cmd_help(message: Message, **kwargs):
        """Команда /help"""
        logger.info(f"Пользователь {message.from_user.id} выполнил команду /help")
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
        
        await message.answer(
            help_text,
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    
    return router 