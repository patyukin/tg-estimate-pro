import asyncpg
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, database_url: str):
        """
        Инициализация PostgreSQL базы данных
        
        Args:
            database_url: URL подключения к PostgreSQL
        """
        self.database_url = database_url
        self.connection_pool = None
        
        if not database_url.startswith("postgresql://"):
            raise ValueError("Поддерживается только PostgreSQL база данных")

    async def init_db(self):
        """Инициализация PostgreSQL и создание пула подключений"""
        self.connection_pool = await asyncpg.create_pool(
            self.database_url,
            min_size=1,
            max_size=10
        )
        logger.info("PostgreSQL подключение инициализировано")
    
    async def get_connection(self):
        """Получение подключения к PostgreSQL"""
        return await self.connection_pool.acquire()
    
    async def release_connection(self, conn):
        """Освобождение подключения к PostgreSQL"""
        await self.connection_pool.release(conn)

    async def create_estimate(self, user_id: int, title: str, description: str = "") -> int:
        """Создание новой сметы"""
        conn = await self.get_connection()
        try:
            result = await conn.fetchval(
                "INSERT INTO estimates_app.estimates (user_id, title, description) VALUES ($1, $2, $3) RETURNING id",
                user_id, title, description
            )
            return result
        finally:
            await self.release_connection(conn)

    async def get_user_estimates(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение всех смет пользователя"""
        conn = await self.get_connection()
        try:
            rows = await conn.fetch(
                "SELECT * FROM estimates_app.estimates WHERE user_id = $1 ORDER BY created_at DESC",
                user_id
            )
            return [dict(row) for row in rows]
        finally:
            await self.release_connection(conn)

    async def get_estimate(self, estimate_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение сметы по ID"""
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow(
                "SELECT * FROM estimates_app.estimates WHERE id = $1 AND user_id = $2",
                estimate_id, user_id
            )
            return dict(row) if row else None
        finally:
            await self.release_connection(conn)

    async def update_estimate(self, estimate_id: int, user_id: int, title: str = None, description: str = None):
        """Обновление сметы"""
        updates = []
        params = []
        param_count = 1
        
        if title is not None:
            updates.append(f"title = ${param_count}")
            params.append(title)
            param_count += 1
        if description is not None:
            updates.append(f"description = ${param_count}")
            params.append(description)
            param_count += 1
        
        if not updates:
            return
            
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([estimate_id, user_id])
        
        conn = await self.get_connection()
        try:
            await conn.execute(
                f"UPDATE estimates_app.estimates SET {', '.join(updates)} WHERE id = ${param_count} AND user_id = ${param_count + 1}",
                *params
            )
        finally:
            await self.release_connection(conn)

    async def delete_estimate(self, estimate_id: int, user_id: int):
        """Удаление сметы"""
        conn = await self.get_connection()
        try:
            await conn.execute(
                "DELETE FROM estimates_app.estimates WHERE id = $1 AND user_id = $2",
                estimate_id, user_id
            )
        finally:
            await self.release_connection(conn)

    async def add_estimate_item(self, estimate_id: int, name: str, duration: float, cost: float) -> int:
        """Добавление позиции в смету"""
        conn = await self.get_connection()
        try:
            result = await conn.fetchval(
                "INSERT INTO estimates_app.estimate_items (estimate_id, name, duration, cost) VALUES ($1, $2, $3, $4) RETURNING id",
                estimate_id, name, duration, cost
            )
            return result
        finally:
            await self.release_connection(conn)

    async def get_estimate_items(self, estimate_id: int) -> List[Dict[str, Any]]:
        """Получение всех позиций сметы"""
        conn = await self.get_connection()
        try:
            rows = await conn.fetch(
                "SELECT * FROM estimates_app.estimate_items WHERE estimate_id = $1 ORDER BY id",
                estimate_id
            )
            return [dict(row) for row in rows]
        finally:
            await self.release_connection(conn)

    async def update_estimate_item(self, item_id: int, name: str = None, duration: float = None, cost: float = None):
        """Обновление позиции сметы"""
        updates = []
        params = []
        param_count = 1
        
        if name is not None:
            updates.append(f"name = ${param_count}")
            params.append(name)
            param_count += 1
        if duration is not None:
            updates.append(f"duration = ${param_count}")
            params.append(duration)
            param_count += 1
        if cost is not None:
            updates.append(f"cost = ${param_count}")
            params.append(cost)
            param_count += 1
        
        if not updates:
            return
            
        params.append(item_id)
        
        conn = await self.get_connection()
        try:
            await conn.execute(
                f"UPDATE estimates_app.estimate_items SET {', '.join(updates)} WHERE id = ${param_count}",
                *params
            )
        finally:
            await self.release_connection(conn)

    async def delete_estimate_item(self, item_id: int):
        """Удаление позиции из сметы"""
        conn = await self.get_connection()
        try:
            await conn.execute("DELETE FROM estimates_app.estimate_items WHERE id = $1", item_id)
        finally:
            await self.release_connection(conn)

    async def get_estimate_total(self, estimate_id: int) -> Dict[str, float]:
        """Получение итогов по смете"""
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow(
                "SELECT SUM(duration) as total_duration, SUM(cost) as total_cost FROM estimates_app.estimate_items WHERE estimate_id = $1",
                estimate_id
            )
            return {
                "total_duration": float(row["total_duration"] or 0),
                "total_cost": float(row["total_cost"] or 0)
            }
        finally:
            await self.release_connection(conn)
    
    # === МЕТОДЫ ДЛЯ ШАБЛОНОВ РАБОТ ===
    
    async def create_work_template(self, user_id: int, name: str, description: str = "", 
                                 default_duration: float = 0, default_cost: float = 0, 
                                 category: str = None) -> int:
        """Создание шаблона работы"""
        conn = await self.get_connection()
        try:
            result = await conn.fetchval(
                """INSERT INTO estimates_app.work_templates 
                   (user_id, name, description, default_duration, default_cost, category) 
                   VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
                user_id, name, description, default_duration, default_cost, category
            )
            return result
        finally:
            await self.release_connection(conn)
    
    async def get_user_work_templates(self, user_id: int, category: str = None) -> List[Dict[str, Any]]:
        """Получение шаблонов работ пользователя"""
        conn = await self.get_connection()
        try:
            if category:
                rows = await conn.fetch(
                    """SELECT * FROM estimates_app.work_templates 
                       WHERE user_id = $1 AND category = $2 AND is_active = true 
                       ORDER BY usage_count DESC, name""",
                    user_id, category
                )
            else:
                rows = await conn.fetch(
                    """SELECT * FROM estimates_app.work_templates 
                       WHERE user_id = $1 AND is_active = true 
                       ORDER BY usage_count DESC, name""",
                    user_id
                )
            return [dict(row) for row in rows]
        finally:
            await self.release_connection(conn)
    
    async def get_work_template(self, template_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение шаблона работы по ID"""
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow(
                "SELECT * FROM estimates_app.work_templates WHERE id = $1 AND user_id = $2",
                template_id, user_id
            )
            return dict(row) if row else None
        finally:
            await self.release_connection(conn)
    
    async def update_work_template(self, template_id: int, user_id: int, name: str = None, 
                                 description: str = None, default_duration: float = None, 
                                 default_cost: float = None, category: str = None):
        """Обновление шаблона работы"""
        updates = []
        params = []
        param_count = 1
        
        if name is not None:
            updates.append(f"name = ${param_count}")
            params.append(name)
            param_count += 1
        if description is not None:
            updates.append(f"description = ${param_count}")
            params.append(description)
            param_count += 1
        if default_duration is not None:
            updates.append(f"default_duration = ${param_count}")
            params.append(default_duration)
            param_count += 1
        if default_cost is not None:
            updates.append(f"default_cost = ${param_count}")
            params.append(default_cost)
            param_count += 1
        if category is not None:
            updates.append(f"category = ${param_count}")
            params.append(category)
            param_count += 1
        
        if not updates:
            return
            
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([template_id, user_id])
        
        conn = await self.get_connection()
        try:
            await conn.execute(
                f"""UPDATE estimates_app.work_templates SET {', '.join(updates)} 
                    WHERE id = ${param_count} AND user_id = ${param_count + 1}""",
                *params
            )
        finally:
            await self.release_connection(conn)
    
    async def delete_work_template(self, template_id: int, user_id: int):
        """Удаление шаблона работы (мягкое удаление)"""
        conn = await self.get_connection()
        try:
            await conn.execute(
                "UPDATE estimates_app.work_templates SET is_active = false WHERE id = $1 AND user_id = $2",
                template_id, user_id
            )
        finally:
            await self.release_connection(conn)
    
    async def increment_template_usage(self, template_id: int):
        """Увеличение счетчика использования шаблона"""
        conn = await self.get_connection()
        try:
            await conn.execute(
                "UPDATE estimates_app.work_templates SET usage_count = usage_count + 1 WHERE id = $1",
                template_id
            )
        finally:
            await self.release_connection(conn)
    
    async def get_template_categories(self, user_id: int) -> List[str]:
        """Получение списка категорий шаблонов пользователя"""
        conn = await self.get_connection()
        try:
            rows = await conn.fetch(
                """SELECT DISTINCT category FROM estimates_app.work_templates 
                   WHERE user_id = $1 AND category IS NOT NULL AND is_active = true 
                   ORDER BY category""",
                user_id
            )
            return [row['category'] for row in rows]
        finally:
            await self.release_connection(conn)

    async def close(self):
        """Закрытие пула подключений"""
        if self.connection_pool:
            await self.connection_pool.close()
            logger.info("PostgreSQL подключения закрыты") 