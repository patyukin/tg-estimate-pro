"""
Middleware для аутентификации пользователей
"""
import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from bot.database.database import Database

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Middleware для автоматической регистрации/аутентификации пользователей"""
    
    def __init__(self, database: Database):
        self.db = database
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Обработка события"""
        user = None
        
        # Извлекаем пользователя из события
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user
        
        if user:
            try:
                # Пытаемся найти пользователя в базе
                db_user = await self.db.get_user_by_telegram_id(user.id)
                
                if not db_user:
                    # Если пользователя нет, создаем его
                    user_id = await self.db.create_user(
                        telegram_id=user.id,
                        username=user.username,
                        first_name=user.first_name,
                        last_name=user.last_name
                    )
                    logger.info(f"Created new user: {user.first_name} ({user.id})")
                    
                    # Получаем созданного пользователя
                    db_user = await self.db.get_user_by_telegram_id(user.id)
                else:
                    # Обновляем информацию о пользователе если она изменилась
                    if (db_user['username'] != user.username or 
                        db_user['first_name'] != user.first_name or 
                        db_user['last_name'] != user.last_name):
                        
                        await self.db.create_user(
                            telegram_id=user.id,
                            username=user.username,
                            first_name=user.first_name,
                            last_name=user.last_name
                        )
                        db_user = await self.db.get_user_by_telegram_id(user.id)
                
                # Добавляем пользователя в данные для хендлера
                data['user'] = db_user
                data['user_id'] = db_user['id']
                
            except Exception as e:
                logger.error(f"Error in auth middleware for user {user.id}: {e}")
                # Не блокируем выполнение, но не добавляем данные пользователя
        
        return await handler(event, data) 