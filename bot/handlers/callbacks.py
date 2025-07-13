"""
Объединенные обработчики callback запросов
"""

from .callbacks import setup_callbacks_router

# Экспортируем объединенный роутер
router = setup_callbacks_router() 