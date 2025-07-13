"""
Функции валидации данных
"""
import re
from typing import Tuple, Optional


def validate_duration(duration_str: str) -> Tuple[bool, Optional[float], str]:
    """
    Валидация продолжительности работы
    
    Returns:
        Tuple[bool, Optional[float], str]: (success, duration, error_message)
    """
    try:
        duration = float(duration_str.replace(',', '.'))
        if duration <= 0:
            return False, None, "⚠️ Продолжительность должна быть больше 0"
        if duration > 1000:
            return False, None, "⚠️ Продолжительность не может превышать 1000 часов"
        return True, duration, ""
    except ValueError:
        return False, None, "⚠️ Введите корректное число"


def validate_cost(cost_str: str) -> Tuple[bool, Optional[float], str]:
    """
    Валидация стоимости
    
    Returns:
        Tuple[bool, Optional[float], str]: (success, cost, error_message)
    """
    try:
        cost = float(cost_str.replace(',', '.'))
        if cost < 0:
            return False, None, "⚠️ Стоимость не может быть отрицательной"
        if cost > 10000000:
            return False, None, "⚠️ Стоимость не может превышать 10 млн"
        return True, cost, ""
    except ValueError:
        return False, None, "⚠️ Введите корректное число"


def validate_text_length(text: str, min_length: int = 1, max_length: int = 255) -> Tuple[bool, str]:
    """
    Валидация длины текста
    
    Returns:
        Tuple[bool, str]: (success, error_message)
    """
    text = text.strip()
    if len(text) < min_length:
        return False, f"⚠️ Минимальная длина: {min_length} символов"
    if len(text) > max_length:
        return False, f"⚠️ Максимальная длина: {max_length} символов"
    return True, ""


def sanitize_text(text: str) -> str:
    """Очистка текста от опасных символов"""
    # Удаляем потенциально опасные символы
    text = re.sub(r'[<>]', '', text)
    # Обрезаем лишние пробелы
    text = text.strip()
    return text


def validate_project_type(project_type: str) -> bool:
    """Валидация типа проекта для ИИ"""
    valid_types = [
        'web_app', 'mobile_app', 'desktop_app', 'api', 
        'landing', 'ecommerce', 'crm', 'other'
    ]
    return project_type in valid_types 