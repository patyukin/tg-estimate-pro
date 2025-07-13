"""
Middleware для логирования действий пользователей
"""
import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования входящих сообщений и callback'ов"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Обработка события"""
        user_id = None
        username = None
        
        # Извлекаем информацию о пользователе
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user
            user_id = user.id
            username = user.username or f"{user.first_name} {user.last_name or ''}".strip()
        
        # Логируем в зависимости от типа события
        if isinstance(event, Message):
            content = event.text or event.caption or f"[{event.content_type}]"
            self.logger.info(
                f"Message from {username} ({user_id}): {content[:100]}..."
                if len(content) > 100 else f"Message from {username} ({user_id}): {content}"
            )
        elif isinstance(event, CallbackQuery):
            self.logger.info(
                f"Callback from {username} ({user_id}): {event.data}"
            )
        
        try:
            # Выполняем обработчик
            result = await handler(event, data)
            return result
        except Exception as e:
            self.logger.error(
                f"Error handling event from {username} ({user_id}): {e}",
                exc_info=True
            )
            raise 