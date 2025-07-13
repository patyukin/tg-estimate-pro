"""
Обработчики inline режима
"""
import logging

from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent

logger = logging.getLogger(__name__)
router = Router()


@router.inline_query()
async def inline_query_handler(query: InlineQuery, **kwargs):
    """Обработчик inline запросов"""
    # Пока что простая заглушка для inline режима
    results = [
        InlineQueryResultArticle(
            id="1",
            title="EstimatePro",
            description="Бот для создания профессиональных смет",
            input_message_content=InputTextMessageContent(
                message_text="🏗️ EstimatePro - профессиональный бот для создания смет!\n\nПопробуйте: @your_bot_username"
            )
        )
    ]
    
    await query.answer(results, cache_time=300) 