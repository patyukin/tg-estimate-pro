import os
import logging
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO") -> None:
    """Настройка логирования"""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def get_env(key: str, default: Optional[str] = None, required: bool = False) -> str:
    """Получение переменной окружения"""
    value = os.getenv(key, default)
    if required and not value:
        raise ValueError(f"Переменная окружения {key} обязательна")
    return value or ""


@dataclass
class Config:
    """Конфигурация бота"""
    bot_token: str
    database_url: str
    log_level: str
    gigachat_credentials: str
    gigachat_model: str
    gigachat_scope: str
    ai_enabled: bool

    @classmethod
    def from_env(cls, env_file: str = ".env") -> "Config":
        """Создание конфигурации из переменных окружения"""
        try:
            load_dotenv(env_file)
            logger.info(f"Конфигурация загружена из {env_file}")
        except Exception as e:
            logger.warning(f"Не удалось загрузить {env_file}: {e}")

        config = cls(
            bot_token=get_env("BOT_TOKEN", required=True),
            database_url=get_env("DATABASE_URL", "postgresql://bot_user:bot_password@localhost:5432/estimates_db"),
            log_level=get_env("LOG_LEVEL", "INFO"),
            gigachat_credentials=get_env("GIGACHAT_CREDENTIALS", ""),
            gigachat_model=get_env("GIGACHAT_MODEL", "GigaChat"),
            gigachat_scope=get_env("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
            ai_enabled=get_env("AI_ENABLED", "true").lower() == "true"
        )
        
        setup_logging(config.log_level)
        config.validate()
        return config

    @property
    def is_ai_available(self) -> bool:
        """Доступен ли ИИ"""
        return self.ai_enabled and bool(self.gigachat_credentials)

    def validate(self) -> None:
        """Валидация конфигурации"""
        if not self.bot_token:
            raise ValueError("BOT_TOKEN не может быть пустым")
        
        if not self.database_url:
            raise ValueError("DATABASE_URL не может быть пустым")
        
        if self.ai_enabled and not self.gigachat_credentials:
            logger.warning("AI_ENABLED=true, но GIGACHAT_CREDENTIALS не установлен. ИИ-функции будут отключены.")
        
        logger.info("Конфигурация валидна")

    def __str__(self) -> str:
        """Строковое представление без секретных данных"""
        return (
            f"Config(database_url='{self.database_url}', "
            f"log_level='{self.log_level}', "
            f"ai_enabled={self.ai_enabled}, "
            f"bot_token={'*' * len(self.bot_token)}')"
        ) 