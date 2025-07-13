#!/usr/bin/env python3
"""
Точка входа для запуска бота (для обратной совместимости)
"""

if __name__ == "__main__":
    from bot.main import main
    import asyncio
    asyncio.run(main()) 