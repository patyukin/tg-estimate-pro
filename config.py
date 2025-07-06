import os
import logging
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class Config:
    """Класс для управления конфигурацией бота"""
    
    def __init__(self, env_file: str = ".env"):
        """
        Инициализация конфигурации
        
        Args:
            env_file: путь к файлу с переменными окружения
        """
        self.env_file = env_file
        self.load_config()
    
    def load_config(self):
        """Загрузка конфигурации из переменных окружения"""
        try:
            load_dotenv(self.env_file)
            logger.info(f"Конфигурация загружена из {self.env_file}")
        except Exception as e:
            logger.warning(f"Не удалось загрузить {self.env_file}: {e}")
        
        # Загружаем параметры
        self._bot_token = self._get_required_env("BOT_TOKEN")
        self._database_url = self._get_env("DATABASE_URL", "postgresql://bot_user:bot_password@localhost:5432/estimates_db")
        self._log_level = self._get_env("LOG_LEVEL", "INFO")
        
        # AI параметры (GigaChat)
        self._gigachat_credentials = self._get_env("GIGACHAT_CREDENTIALS", "")
        self._gigachat_model = self._get_env("GIGACHAT_MODEL", "GigaChat")
        self._gigachat_scope = self._get_env("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
        self._ai_enabled = self._get_env("AI_ENABLED", "true").lower() == "true"
        
        # Настройка логирования
        self._setup_logging()
    
    def _get_required_env(self, key: str) -> str:
        """Получение обязательной переменной окружения"""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Переменная окружения {key} не найдена")
        return value
    
    def _get_env(self, key: str, default: str) -> str:
        """Получение переменной окружения с значением по умолчанию"""
        return os.getenv(key, default)
    
    def _setup_logging(self):
        """Настройка логирования"""
        log_level = getattr(logging, self._log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    @property
    def bot_token(self) -> str:
        """Токен телеграм-бота"""
        return self._bot_token
    
    @property
    def database_url(self) -> str:
        """URL подключения к базе данных"""
        return self._database_url
    
    @property
    def log_level(self) -> str:
        """Уровень логирования"""
        return self._log_level
    
    @property
    def gigachat_credentials(self) -> str:
        """GigaChat авторизационные данные"""
        return self._gigachat_credentials
    
    @property
    def gigachat_model(self) -> str:
        """Модель GigaChat"""
        return self._gigachat_model
    
    @property
    def gigachat_scope(self) -> str:
        """Scope для GigaChat API"""
        return self._gigachat_scope
    
    @property
    def ai_enabled(self) -> bool:
        """Включен ли ИИ"""
        return self._ai_enabled and bool(self._gigachat_credentials)
    
    def validate(self) -> bool:
        """Проверка корректности конфигурации"""
        try:
            if not self.bot_token:
                raise ValueError("BOT_TOKEN не может быть пустым")
            
            if not self.database_url:
                raise ValueError("DATABASE_URL не может быть пустым")
            
            if self._ai_enabled and not self._gigachat_credentials:
                logger.warning("AI_ENABLED=true, но GIGACHAT_CREDENTIALS не установлен. ИИ-функции будут отключены.")
                
            logger.info("Конфигурация прошла валидацию")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка валидации конфигурации: {e}")
            return False
    
    def __str__(self) -> str:
        """Строковое представление конфигурации (без секретных данных)"""
        return (
            f"Config(database_url='{self.database_url}', "
            f"log_level='{self.log_level}', "
            f"ai_enabled={self.ai_enabled}, "
            f"bot_token={'*' * len(self.bot_token) if self.bot_token else 'None'})"
        ) 