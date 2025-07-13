"""
FSM состояния для бота
"""
from aiogram.fsm.state import State, StatesGroup


class EstimateStates(StatesGroup):
    """Состояния для работы со сметами"""
    waiting_title = State()
    waiting_description = State()
    waiting_item_name = State()
    waiting_item_duration = State()
    waiting_item_cost = State()
    editing_estimate = State()
    editing_item = State()


class TemplateStates(StatesGroup):
    """Состояния для работы с шаблонами"""
    waiting_template_name = State()
    waiting_template_description = State()
    waiting_template_duration = State()
    waiting_template_cost = State()
    waiting_template_category = State()
    editing_template = State()


class AIStates(StatesGroup):
    """Состояния для ИИ-помощника"""
    waiting_ai_description = State()
    waiting_ai_project_type = State()
    waiting_ai_consultation = State() 