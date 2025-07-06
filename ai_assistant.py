import logging
import json
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import uuid
import time
from gigachat import GigaChat
from config import Config

logger = logging.getLogger(__name__)

@dataclass
class EstimateItem:
    """Позиция сметы"""
    name: str
    duration: float
    cost: float
    description: str = ""

@dataclass
class AIAnalysis:
    """Результат анализа ИИ"""
    suggestions: List[str]
    optimization_tips: List[str]
    risk_factors: List[str]
    total_estimation: Dict[str, float]

class AIAssistant:
    """Помощник с искусственным интеллектом для работы со сметами на базе GigaChat"""
    
    def __init__(self, config: Config):
        self.config = config
        self.enabled = config.ai_enabled
        
        if self.enabled:
            try:
                self.model = config.gigachat_model
                self.giga = GigaChat(
                    credentials=config.gigachat_credentials,
                    scope=config.gigachat_scope,
                    model=self.model,
                    verify_ssl_certs=False
                )
                logger.info(f"ИИ-помощник инициализирован с моделью {self.model}")
            except Exception as e:
                logger.error(f"Ошибка инициализации GigaChat: {e}")
                self.enabled = False
        else:
            logger.warning("ИИ-помощник отключен")
    
    def is_enabled(self) -> bool:
        """Проверка доступности ИИ"""
        return self.enabled
    
    def generate_estimate_items(self, project_description: str, project_type: str = "общий") -> List[EstimateItem]:
        """
        Генерация позиций сметы на основе описания проекта
        
        Args:
            project_description: Описание проекта
            project_type: Тип проекта (веб-разработка, мобильная разработка, дизайн и т.д.)
        
        Returns:
            Список позиций сметы
        """
        if not self.enabled:
            logger.warning("🤖 ИИ-помощник отключен - генерация невозможна")
            return []
        
        logger.info(f"🔮 Начинаю генерацию сметы для проекта типа '{project_type}'")
        logger.debug(f"📝 Описание проекта: {project_description[:100]}...")
        
        start_time = time.time()
        
        try:
            prompt = f"""
            Ты - эксперт по созданию смет для IT-проектов. На основе описания проекта создай детальную смету.
            
            Описание проекта: {project_description}
            Тип проекта: {project_type}
            
            Создай список работ в формате JSON с полями:
            - name: название работы
            - duration: время в часах (float)
            - cost: стоимость в рублях (float)
            - description: краткое описание работы
            
            Учти:
            - Рыночные расценки на 2024 год для России
            - Все этапы разработки (анализ, дизайн, разработка, тестирование, деплой)
            - Возможные риски и дополнительные работы
            - Средняя ставка: junior 1500-2500₽/ч, middle 2500-4000₽/ч, senior 4000-6000₽/ч
            
            Ответь только валидным JSON массивом объектов.
            """
            
            logger.info(f"📤 Отправляю запрос к GigaChat (модель: {self.model})")
            logger.debug(f"🔤 Размер промпта: {len(prompt)} символов")
            
            messages = [{"role": "user", "content": prompt}]
            response = self.giga.chat({"messages": messages})
            
            request_time = time.time() - start_time
            logger.info(f"📥 Получен ответ от GigaChat за {request_time:.2f} сек")
            
            content = response.choices[0].message.content.strip()
            logger.debug(f"📋 Размер ответа: {len(content)} символов")
            logger.debug(f"🔍 Первые 200 символов ответа: {content[:200]}...")
            
            # Парсим JSON
            try:
                logger.info("🔧 Парсим JSON ответ...")
                # Убираем markdown блоки если есть
                if content.startswith('```json') and content.endswith('```'):
                    content = content[7:-3].strip()
                elif content.startswith('```') and content.endswith('```'):
                    content = content[3:-3].strip()
                items_data = json.loads(content)
                items = []
                
                for i, item_data in enumerate(items_data, 1):
                    item = EstimateItem(
                        name=item_data.get('name', ''),
                        duration=float(item_data.get('duration', 0)),
                        cost=float(item_data.get('cost', 0)),
                        description=item_data.get('description', '')
                    )
                    items.append(item)
                    logger.debug(f"✅ Позиция {i}: {item.name} - {item.duration}ч, {item.cost}₽")
                
                total_time = time.time() - start_time
                total_cost = sum(item.cost for item in items)
                total_duration = sum(item.duration for item in items)
                
                logger.info(f"🎉 Сгенерировано {len(items)} позиций сметы за {total_time:.2f} сек")
                logger.info(f"💰 Общая стоимость: {total_cost:.0f}₽, время: {total_duration:.1f}ч")
                return items
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Ошибка парсинга JSON от ИИ: {e}")
                logger.error(f"🔍 Проблемный ответ: {content}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка генерации сметы: {e}")
            logger.error(f"⏱️ Время до ошибки: {time.time() - start_time:.2f} сек")
            return []
    
    def analyze_estimate(self, estimate_data: Dict[str, Any], items: List[Dict[str, Any]]) -> AIAnalysis:
        """
        Анализ существующей сметы и предложения по улучшению
        
        Args:
            estimate_data: Данные сметы
            items: Позиции сметы
        
        Returns:
            Анализ и рекомендации
        """
        if not self.enabled:
            logger.warning("🤖 ИИ-помощник отключен - анализ невозможен")
            return AIAnalysis([], [], [], {})
        
        logger.info(f"🧠 Начинаю анализ сметы '{estimate_data.get('title', 'Без названия')}'")
        
        start_time = time.time()
        
        try:
            # Подготавливаем данные
            total_cost = sum(item.get('cost', 0) for item in items)
            total_duration = sum(item.get('duration', 0) for item in items)
            
            logger.info(f"📊 Анализируем {len(items)} позиций (общая стоимость: {total_cost}₽, время: {total_duration}ч)")
            
            items_text = "\n".join([
                f"- {item.get('name', 'Без названия')}: {item.get('duration', 0)}ч, {item.get('cost', 0)}₽"
                for item in items
            ])
            
            prompt = f"""
            Проанализируй смету IT-проекта и дай рекомендации:
            
            Название: {estimate_data.get('title', 'Без названия')}
            Описание: {estimate_data.get('description', 'Без описания')}
            
            Позиции сметы:
            {items_text}
            
            Общая стоимость: {total_cost}₽
            Общее время: {total_duration}ч
            
            Проанализируй и дай ответ в формате JSON:
            {{
                "suggestions": ["предложение 1", "предложение 2"],
                "optimization_tips": ["совет по оптимизации 1", "совет 2"],
                "risk_factors": ["риск 1", "риск 2"],
                "total_estimation": {{
                    "min_cost": число,
                    "max_cost": число,
                    "recommended_buffer": число_в_процентах
                }}
            }}
            
            Учти:
            - Адекватность расценок и времени
            - Возможные недостающие позиции
            - Риски проекта
            - Рекомендации по буферу времени/бюджета
            """
            
            logger.info("📤 Отправляю запрос на анализ к GigaChat")
            logger.debug(f"🔤 Размер промпта для анализа: {len(prompt)} символов")
            
            messages = [{"role": "user", "content": prompt}]
            response = self.giga.chat({"messages": messages})
            
            request_time = time.time() - start_time
            logger.info(f"📥 Получен анализ от GigaChat за {request_time:.2f} сек")
            
            content = response.choices[0].message.content.strip()
            logger.debug(f"📋 Размер ответа анализа: {len(content)} символов")
            
            try:
                logger.info("🔧 Парсим результат анализа...")
                # Убираем markdown блоки если есть
                if content.startswith('```json') and content.endswith('```'):
                    content = content[7:-3].strip()
                elif content.startswith('```') and content.endswith('```'):
                    content = content[3:-3].strip()
                # Пытаемся найти JSON блок в ответе
                elif '```json' in content and '```' in content:
                    start = content.find('```json') + 7
                    end = content.find('```', start)
                    if end != -1:
                        content = content[start:end].strip()
                analysis_data = json.loads(content)
                
                analysis = AIAnalysis(
                    suggestions=analysis_data.get('suggestions', []),
                    optimization_tips=analysis_data.get('optimization_tips', []),
                    risk_factors=analysis_data.get('risk_factors', []),
                    total_estimation=analysis_data.get('total_estimation', {})
                )
                
                total_time = time.time() - start_time
                logger.info(f"✅ Анализ сметы выполнен за {total_time:.2f} сек")
                logger.info(f"💡 Рекомендаций: {len(analysis.suggestions)}, советов: {len(analysis.optimization_tips)}, рисков: {len(analysis.risk_factors)}")
                
                return analysis
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Ошибка парсинга анализа от ИИ: {e}")
                logger.error(f"🔍 Проблемный ответ анализа: {content}")
                return AIAnalysis([], [], [], {})
                
        except Exception as e:
            logger.error(f"❌ Ошибка анализа сметы: {e}")
            logger.error(f"⏱️ Время до ошибки анализа: {time.time() - start_time:.2f} сек")
            return AIAnalysis([], [], [], {})
    
    def get_consultation(self, question: str, context: str = "") -> str:
        """
        Консультация по вопросам сметы и проекта
        
        Args:
            question: Вопрос пользователя
            context: Контекст (данные о проекте/смете)
        
        Returns:
            Ответ ИИ-консультанта
        """
        if not self.enabled:
            logger.warning("🤖 ИИ-помощник отключен - консультация невозможна")
            return "К сожалению, ИИ-консультант недоступен. Проверьте настройки GIGACHAT_CREDENTIALS."
        
        logger.info(f"💡 Начинаю консультацию по вопросу: {question[:50]}...")
        logger.debug(f"📝 Контекст: {context[:100]}..." if context else "📝 Контекст не предоставлен")
        
        start_time = time.time()
        
        try:
            system_prompt = """
            Ты - эксперт-консультант по IT-проектам и составлению смет. 
            Отвечай конкретно и профессионально, давай практические советы.
            Учитывай российский рынок и современные расценки.
            Если нужна дополнительная информация, попроси уточнить.
            """
            
            user_prompt = f"""
            Контекст: {context}
            
            Вопрос: {question}
            
            Дай профессиональную консультацию.
            """
            
            logger.info("📤 Отправляю запрос на консультацию к GigaChat")
            logger.debug(f"🔤 Размер вопроса: {len(question)} символов, контекста: {len(context)} символов")
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response = self.giga.chat({"messages": messages})
            
            request_time = time.time() - start_time
            logger.info(f"📥 Получен ответ консультации от GigaChat за {request_time:.2f} сек")
            
            answer = response.choices[0].message.content.strip()
            
            total_time = time.time() - start_time
            logger.info(f"✅ Консультация предоставлена за {total_time:.2f} сек")
            logger.info(f"📋 Размер ответа: {len(answer)} символов")
            logger.debug(f"💬 Начало ответа: {answer[:100]}...")
            
            return answer
            
        except Exception as e:
            logger.error(f"❌ Ошибка консультации: {e}")
            logger.error(f"⏱️ Время до ошибки консультации: {time.time() - start_time:.2f} сек")
            return "Произошла ошибка при получении консультации. Попробуйте позже."
    
    def categorize_work(self, work_name: str, work_description: str = "") -> str:
        """
        Автоматическое определение категории работы
        
        Args:
            work_name: Название работы
            work_description: Описание работы
        
        Returns:
            Категория работы
        """
        if not self.enabled:
            logger.debug("🤖 ИИ-помощник отключен - используем категорию по умолчанию")
            return "Общее"
        
        logger.debug(f"🎯 Определяю категорию для работы: {work_name}")
        
        try:
            prompt = f"""
            Определи категорию для следующей работы:
            
            Название: {work_name}
            Описание: {work_description}
            
            Выбери ОДНУ наиболее подходящую категорию из:
            - Анализ и планирование
            - UI/UX дизайн
            - Frontend разработка
            - Backend разработка
            - Мобильная разработка
            - Базы данных
            - Тестирование
            - DevOps и деплой
            - Интеграции
            - Документация
            - Общее
            
            Ответь только названием категории.
            """
            
            messages = [{"role": "user", "content": prompt}]
            response = self.giga.chat({"messages": messages})
            
            category = response.choices[0].message.content.strip()
            logger.info(f"🎯 Категория определена: {category} для '{work_name}'")
            return category
            
        except Exception as e:
            logger.error(f"❌ Ошибка определения категории: {e}")
            return "Общее"
    
    def suggest_similar_works(self, work_name: str, existing_templates: List[Dict[str, Any]]) -> List[str]:
        """
        Предложение похожих работ на основе существующих шаблонов
        
        Args:
            work_name: Название работы
            existing_templates: Существующие шаблоны работ
        
        Returns:
            Список предложений
        """
        if not self.enabled or not existing_templates:
            return []
        
        try:
            templates_text = "\n".join([
                f"- {template.get('name', '')}: {template.get('description', '')}"
                for template in existing_templates[:10]  # Ограничиваем количество
            ])
            
            prompt = f"""
            На основе существующих шаблонов работ предложи 3-5 похожих или дополняющих работ для: {work_name}
            
            Существующие шаблоны:
            {templates_text}
            
            Предложи только названия работ, каждое с новой строки, без номеров и дефисов.
            """
            
            messages = [{"role": "user", "content": prompt}]
            response = self.giga.chat({"messages": messages})
            
            suggestions = [
                line.strip() 
                for line in response.choices[0].message.content.strip().split('\n')
                if line.strip()
            ][:5]  # Ограничиваем до 5 предложений
            
            logger.info(f"Предложено {len(suggestions)} похожих работ")
            return suggestions
            
        except Exception as e:
            logger.error(f"Ошибка предложения работ: {e}")
            return [] 