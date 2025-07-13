"""
Модели данных для базы данных
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class User:
    """Модель пользователя"""
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'is_active': self.is_active
        }


@dataclass
class Estimate:
    """Модель сметы"""
    id: int
    user_id: int
    title: str
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None
    total_cost: float = 0.0
    total_duration: float = 0.0
    status: str = "draft"  # draft, active, completed, archived

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'total_cost': self.total_cost,
            'total_duration': self.total_duration,
            'status': self.status
        }


@dataclass
class EstimateItem:
    """Модель позиции сметы"""
    id: int
    estimate_id: int
    name: str
    description: Optional[str]
    duration: float
    cost: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    order_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            'id': self.id,
            'estimate_id': self.estimate_id,
            'name': self.name,
            'description': self.description,
            'duration': self.duration,
            'cost': self.cost,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'order_index': self.order_index
        }


@dataclass
class WorkTemplate:
    """Модель шаблона работы"""
    id: int
    user_id: int
    name: str
    description: Optional[str]
    category: str
    default_duration: float
    default_cost: float
    usage_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_public: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'default_duration': self.default_duration,
            'default_cost': self.default_cost,
            'usage_count': self.usage_count,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'is_public': self.is_public
        }


@dataclass
class UserSettings:
    """Модель настроек пользователя"""
    id: int
    user_id: int
    default_hourly_rate: Optional[float] = None
    timezone: str = "UTC"
    language: str = "ru"
    notifications_enabled: bool = True
    ai_assistance_enabled: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'default_hourly_rate': self.default_hourly_rate,
            'timezone': self.timezone,
            'language': self.language,
            'notifications_enabled': self.notifications_enabled,
            'ai_assistance_enabled': self.ai_assistance_enabled,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

 