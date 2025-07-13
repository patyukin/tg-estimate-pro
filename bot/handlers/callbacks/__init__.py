"""
Callback обработчики бота
"""

from aiogram import Router
from . import main, estimates, templates, ai

def setup_callbacks_router() -> Router:
    """Настройка объединенного роутера для всех callback'ов"""
    router = Router()
    
    # Добавляем все роутеры в порядке приоритета
    router.include_router(main.router)
    router.include_router(estimates.router)
    router.include_router(templates.router)
    router.include_router(ai.router)
    
    return router

__all__ = ['setup_callbacks_router'] 