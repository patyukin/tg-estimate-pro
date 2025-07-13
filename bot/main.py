"""
Главная точка входа Telegram бота
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import Config
from bot.database.database import Database
from bot.handlers import messages, callbacks, inline
from bot.handlers.commands import setup_commands_router
from bot.middlewares.logging import LoggingMiddleware
from bot.middlewares.auth import AuthMiddleware

logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    try:
        # Инициализация конфигурации
        config = Config.from_env()
        logger.info("Конфигурация загружена успешно")
        
        # Инициализация бота и диспетчера
        bot = Bot(token=config.bot_token)
        dp = Dispatcher(storage=MemoryStorage())
        
        # Инициализация базы данных
        db = Database(config.database_url, logger)
        await db.init_db()
        logger.info("База данных инициализирована")
        
        # Подключение middleware
        dp.message.middleware(LoggingMiddleware(logger))
        dp.callback_query.middleware(LoggingMiddleware(logger))
        dp.message.middleware(AuthMiddleware(db))
        dp.callback_query.middleware(AuthMiddleware(db))
        
        # Регистрация роутеров
        dp.include_router(setup_commands_router(logger))
        dp.include_router(callbacks.router)
        dp.include_router(messages.router)
        dp.include_router(inline.router)
        
        # Передаем зависимости в контекст
        dp["config"] = config
        dp["db"] = db
        
        logger.info("Бот запущен!")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        raise
    finally:
        if 'db' in locals():
            await db.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main()) 