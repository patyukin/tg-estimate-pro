"""
Вспомогательные функции для форматирования и обработки данных
"""
from typing import Dict


def format_currency(amount: float) -> str:
    """Красивое форматирование валюты"""
    if amount >= 1000000:
        return f"{amount/1000000:.1f}М ₽"
    elif amount >= 1000:
        return f"{amount/1000:.1f}К ₽"
    else:
        return f"{amount:,.0f} ₽".replace(',', ' ')


def format_duration(hours: float) -> str:
    """Красивое форматирование времени"""
    if hours >= 24:
        days = int(hours // 24)
        remaining_hours = hours % 24
        if remaining_hours == 0:
            return f"{days} дн."
        else:
            return f"{days} дн. {remaining_hours:.1f} ч"
    else:
        return f"{hours:.1f} ч"


def create_progress_bar(current: float, total: float, length: int = 10) -> str:
    """Создание прогресс-бара"""
    if total == 0:
        return "▱" * length
    
    percentage = min(current / total, 1.0)
    filled = int(percentage * length)
    empty = length - filled
    
    return "▰" * filled + "▱" * empty


def format_estimate_card(estimate: Dict, items_count: int = 0, total_cost: float = 0, total_duration: float = 0) -> str:
    """Красивое форматирование карточки сметы"""
    # Определяем статус
    if items_count == 0:
        status = "🔄 Черновик"
        status_color = "🟡"
    elif total_cost > 0:
        status = "✅ Готова"
        status_color = "🟢"
    else:
        status = "⚠️ В работе"
        status_color = "🟠"
    
    # Формируем карточку
    card = f"""
╭─────────────────────────────╮
│ {status_color} <b>{estimate['title'][:20]}{'...' if len(estimate['title']) > 20 else ''}</b>
├─────────────────────────────┤"""
    
    if estimate.get('description'):
        desc = estimate['description'][:40] + '...' if len(estimate['description']) > 40 else estimate['description']
        card += f"\n│ 📝 {desc}"
    
    card += f"""
│ 
│ 📊 Позиций: {items_count}
│ ⏱️ Время: {format_duration(total_duration)}
│ 💰 Сумма: {format_currency(total_cost)}
│ 
│ {status}
╰─────────────────────────────╯"""
    
    return card


def format_template_card(template: Dict) -> str:
    """Красивое форматирование карточки шаблона"""
    category_emoji = {
        'Frontend': '🎨',
        'Backend': '⚙️',
        'DevOps': '🚀',
        'Design': '🎨',
        'Analytics': '📊',
        'Testing': '🧪',
        'Mobile': '📱',
        'Database': '🗄️'
    }.get(template.get('category', ''), '📋')
    
    usage_text = ""
    if template.get('usage_count', 0) > 0:
        usage_text = f"│ 🔥 Использований: {template['usage_count']}\n"
    
    card = f"""
╭─────────────────────────────╮
│ {category_emoji} <b>{template['name'][:20]}{'...' if len(template['name']) > 20 else ''}</b>
├─────────────────────────────┤
│ ⏱️ {format_duration(template['default_duration'])}
│ 💰 {format_currency(template['default_cost'])}
{usage_text}│ 📂 {template.get('category', 'Без категории')}
╰─────────────────────────────╯"""
    
    return card


def format_stats_block(estimates: list, templates: list) -> str:
    """Красивая статистика пользователя"""
    total_estimates = len(estimates)
    total_templates = len(templates)
    
    if total_estimates == 0:
        return """
🏗️ <b>Ваша статистика</b>

📊 Пока нет данных для анализа
Создайте первую смету!"""
    
    # Подсчет статистики
    total_cost = sum(est.get('total_cost', 0) for est in estimates)
    total_duration = sum(est.get('total_duration', 0) for est in estimates)
    avg_estimate_cost = total_cost / total_estimates if total_estimates > 0 else 0
    
    stats = f"""
🏗️ <b>Ваша статистика</b>

📈 <b>Общие показатели:</b>
┣ 📄 Смет создано: {total_estimates}
┣ 🔧 Шаблонов: {total_templates}
┣ 💰 Общая сумма: {format_currency(total_cost)}
┗ ⏱️ Общее время: {format_duration(total_duration)}

📊 <b>Средние значения:</b>
┣ 💵 Средняя смета: {format_currency(avg_estimate_cost)}
┗ 📏 Ставка/час: {format_currency(total_cost/total_duration if total_duration > 0 else 0).replace(' ₽', '₽/ч')}"""
    
    return stats 