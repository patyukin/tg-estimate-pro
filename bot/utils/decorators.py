"""
Декораторы для обработчиков
"""
import functools
import logging
from typing import Callable, Any

from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)


def error_handler(func: Callable) -> Callable:
    """Декоратор для обработки ошибок в хендлерах"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка в {func.__name__}: {e}", exc_info=True)
            
            # Попытка найти объект для ответа
            for arg in args:
                if isinstance(arg, (Message, CallbackQuery)):
                    try:
                        if isinstance(arg, Message):
                            await arg.answer("⚠️ Произошла ошибка. Попробуйте позже.")
                        else:
                            await arg.message.answer("⚠️ Произошла ошибка. Попробуйте позже.")
                    except:
                        pass
                    break
            
            raise e
    
    return wrapper


def admin_only(func: Callable) -> Callable:
    """Декоратор для ограничения доступа только админам"""
    @functools.wraps(func)
    async def wrapper(message_or_callback, *args, **kwargs) -> Any:
        user_id = message_or_callback.from_user.id
        
        # Здесь можно добавить проверку админских прав
        # Например, сверка с базой данных или списком админов
        
        return await func(message_or_callback, *args, **kwargs)
    
    return wrapper


def rate_limit(calls_per_minute: int = 10):
    """Декоратор для ограничения частоты вызовов"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Здесь можно реализовать логику rate limiting
            # Например, с использованием Redis или in-memory storage
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator 