"""
Класс для работы с базой данных
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

import asyncpg
from asyncpg import Pool


class Database:
    """Класс для работы с PostgreSQL базой данных"""
    
    def __init__(self, database_url: str, logger: logging.Logger):
        self.database_url = database_url
        self.logger = logger
        self.pool: Optional[Pool] = None
    
    async def init_db(self) -> None:
        """Инициализация подключения к базе данных"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            self.logger.info("Подключение к базе данных установлено")
            
        except Exception as e:
            self.logger.error(f"Ошибка подключения к базе данных: {e}")
            raise

    async def close(self) -> None:
        """Закрытие подключения к базе данных"""
        if self.pool:
            await self.pool.close()
            self.logger.info("Подключение к базе данных закрыто")

    # === МЕТОДЫ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ ===
    
    async def create_user(self, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None) -> int:
        """Создание нового пользователя"""
        async with self.pool.acquire() as conn:
            user_id = await conn.fetchval("""
                INSERT INTO users (telegram_id, username, first_name, last_name)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (telegram_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, telegram_id, username, first_name, last_name)
            
            # Создаем настройки по умолчанию
            await conn.execute("""
                INSERT INTO user_settings (user_id)
                VALUES ($1)
                ON CONFLICT (user_id) DO NOTHING
            """, user_id)
            
            return user_id

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """Получение пользователя по Telegram ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM users WHERE telegram_id = $1
            """, telegram_id)
            return dict(row) if row else None

    # === МЕТОДЫ ДЛЯ РАБОТЫ СО СМЕТАМИ ===
    
    async def create_estimate(self, user_id: int, title: str, description: str = None) -> int:
        """Создание новой сметы"""
        async with self.pool.acquire() as conn:
            estimate_id = await conn.fetchval("""
                INSERT INTO estimates (user_id, title, description)
                VALUES ($1, $2, $3)
                RETURNING id
            """, user_id, title, description)
            return estimate_id

    async def get_user_estimates(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Получение смет пользователя"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT e.*, 
                       COUNT(ei.id) as items_count,
                       COALESCE(SUM(ei.cost), 0) as total_cost,
                       COALESCE(SUM(ei.duration), 0) as total_duration
                FROM estimates e
                LEFT JOIN estimate_items ei ON e.id = ei.estimate_id
                WHERE e.user_id = $1
                GROUP BY e.id
                ORDER BY e.created_at DESC
                LIMIT $2
            """, user_id, limit)
            return [dict(row) for row in rows]

    async def get_estimate_by_id(self, estimate_id: int, user_id: int) -> Optional[Dict]:
        """Получение сметы по ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT e.*, 
                       COUNT(ei.id) as items_count,
                       COALESCE(SUM(ei.cost), 0) as total_cost,
                       COALESCE(SUM(ei.duration), 0) as total_duration
                FROM estimates e
                LEFT JOIN estimate_items ei ON e.id = ei.estimate_id
                WHERE e.id = $1 AND e.user_id = $2
                GROUP BY e.id
            """, estimate_id, user_id)
            return dict(row) if row else None

    async def delete_estimate(self, estimate_id: int, user_id: int) -> bool:
        """Удаление сметы"""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM estimates 
                WHERE id = $1 AND user_id = $2
            """, estimate_id, user_id)
            return result != "DELETE 0"

    # === МЕТОДЫ ДЛЯ РАБОТЫ С ПОЗИЦИЯМИ СМЕТ ===
    
    async def add_estimate_item(self, estimate_id: int, name: str, description: str, duration: float, cost: float) -> int:
        """Добавление позиции в смету"""
        async with self.pool.acquire() as conn:
            item_id = await conn.fetchval("""
                INSERT INTO estimate_items (estimate_id, name, description, duration, cost)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """, estimate_id, name, description, duration, cost)
            
            # Обновляем итоги сметы
            await self._update_estimate_totals(conn, estimate_id)
            return item_id

    async def get_estimate_items(self, estimate_id: int) -> List[Dict]:
        """Получение позиций сметы"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM estimate_items 
                WHERE estimate_id = $1 
                ORDER BY order_index, created_at
            """, estimate_id)
            return [dict(row) for row in rows]

    async def delete_estimate_item(self, item_id: int) -> bool:
        """Удаление позиции сметы"""
        async with self.pool.acquire() as conn:
            # Получаем estimate_id перед удалением
            estimate_id = await conn.fetchval("""
                SELECT estimate_id FROM estimate_items WHERE id = $1
            """, item_id)
            
            if not estimate_id:
                return False
            
            result = await conn.execute("""
                DELETE FROM estimate_items WHERE id = $1
            """, item_id)
            
            # Обновляем итоги сметы
            await self._update_estimate_totals(conn, estimate_id)
            return result != "DELETE 0"

    async def _update_estimate_totals(self, conn, estimate_id: int) -> None:
        """Обновление итогов сметы"""
        await conn.execute("""
            UPDATE estimates 
            SET total_cost = (
                SELECT COALESCE(SUM(cost), 0) 
                FROM estimate_items 
                WHERE estimate_id = $1
            ),
            total_duration = (
                SELECT COALESCE(SUM(duration), 0) 
                FROM estimate_items 
                WHERE estimate_id = $1
            ),
            updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """, estimate_id)

    # === МЕТОДЫ ДЛЯ РАБОТЫ С ШАБЛОНАМИ ===
    
    async def create_work_template(self, user_id: int, name: str, description: str, 
                                 category: str, default_duration: float, default_cost: float) -> int:
        """Создание шаблона работы"""
        async with self.pool.acquire() as conn:
            template_id = await conn.fetchval("""
                INSERT INTO work_templates (user_id, name, description, category, default_duration, default_cost)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """, user_id, name, description, category, default_duration, default_cost)
            return template_id

    async def get_user_templates(self, user_id: int) -> List[Dict]:
        """Получение шаблонов пользователя"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM work_templates 
                WHERE user_id = $1 OR is_public = TRUE
                ORDER BY usage_count DESC, created_at DESC
            """, user_id)
            return [dict(row) for row in rows]

    async def get_template_by_id(self, template_id: int) -> Optional[Dict]:
        """Получение шаблона по ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM work_templates WHERE id = $1
            """, template_id)
            return dict(row) if row else None

    async def increment_template_usage(self, template_id: int) -> None:
        """Увеличение счетчика использования шаблона"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE work_templates 
                SET usage_count = usage_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
            """, template_id)

    async def delete_template(self, template_id: int, user_id: int) -> bool:
        """Удаление шаблона"""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM work_templates 
                WHERE id = $1 AND user_id = $2
            """, template_id, user_id)
            return result != "DELETE 0" 