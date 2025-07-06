"""
📝 Библиотека промптов для Google Gemini в контексте Авито

Этот модуль содержит готовые промпты и шаблоны для:
- Анализа сообщений покупателей
- Генерации ответов в разных стилях
- Классификации типов сообщений
- Анализа настроения и намерений
- Специализированные промпты для Авито сценариев

Местоположение: src/integrations/gemini/prompts.py
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from ...core.config import MessageType, ResponseStyle


class PromptCategory(str, Enum):
    """Категории промптов"""
    
    ANALYSIS = "analysis"           # Анализ сообщений
    GENERATION = "generation"       # Генерация ответов
    CLASSIFICATION = "classification" # Классификация
    SENTIMENT = "sentiment"         # Анализ настроения
    SYSTEM = "system"              # Системные инструкции


@dataclass
class PromptTemplate:
    """Шаблон промпта"""
    
    name: str
    category: PromptCategory
    template: str
    variables: List[str]
    description: str
    
    def format(self, **kwargs) -> str:
        """Форматирование промпта с переменными"""
        
        # Проверяем что все переменные предоставлены
        missing_vars = [var for var in self.variables if var not in kwargs]
        if missing_vars:
            raise ValueError(f"Отсутствуют переменные: {missing_vars}")
        
        return self.template.format(**kwargs)


class GeminiPromptLibrary:
    """
    📚 Библиотека промптов для Gemini
    
    Содержит готовые промпты для различных сценариев работы с Авито:
    - Анализ входящих сообщений
    - Генерация ответов покупателям
    - Классификация запросов
    - Анализ настроения
    """
    
    def __init__(self):
        """Инициализация библиотеки промптов"""
        
        self.prompts: Dict[str, PromptTemplate] = {}
        self._initialize_prompts()
    
    def _initialize_prompts(self) -> None:
        """Инициализация всех промптов"""
        
        # Системные инструкции
        self._add_system_prompts()
        
        # Промпты анализа
        self._add_analysis_prompts()
        
        # Промпты генерации
        self._add_generation_prompts()
        
        # Промпты классификации
        self._add_classification_prompts()
        
        # Промпты анализа настроения
        self._add_sentiment_prompts()
    
    def _add_system_prompts(self) -> None:
        """Системные инструкции"""
        
        # Основная системная инструкция
        self.prompts["system_avito_seller"] = PromptTemplate(
            name="system_avito_seller",
            category=PromptCategory.SYSTEM,
            template="""
Ты - опытный продавец на площадке Авито. Твоя задача - помогать в общении с покупателями.

ТВОИ ПРИНЦИПЫ:
- Всегда вежлив и дружелюбен
- Отвечаешь быстро и по существу
- Стремишься к продаже, но не навязчиво
- Предоставляешь честную информацию о товаре
- Адаптируешь стиль общения под покупателя

КОНТЕКСТ РАБОТЫ:
- Платформа: Авито
- Цель: Увеличение конверсии продаж
- Аудитория: Покупатели разного уровня
- Ограничения: Краткость ответов (до 200 символов)

ПОМНИ:
- Каждый покупатель важен
- Честность строит доверие  
- Быстрота ответа критична
- Персонализация повышает конверсию
            """,
            variables=[],
            description="Основная системная инструкция для продавца на Авито"
        )
        
        # Инструкция для анализа
        self.prompts["system_analyzer"] = PromptTemplate(
            name="system_analyzer",
            category=PromptCategory.SYSTEM,
            template="""
Ты - эксперт по анализу сообщений на торговых площадках. Твоя задача - точно анализировать намерения покупателей.

ТВОИ НАВЫКИ:
- Определение типа запроса (цена, доступность, встреча, etc.)
- Анализ эмоциональной окраски сообщения
- Оценка серьезности намерений покупателя
- Выявление срочности ответа

ОТВЕЧАЙ ВСЕГДА В JSON ФОРМАТЕ:
{
    "message_type": "price_question|availability|meeting_request|product_info|delivery_question|general_question|greeting|complaint|spam",
    "confidence": 0.0-1.0,
    "sentiment": "positive|negative|neutral", 
    "urgency": "low|medium|high",
    "intent": "краткое описание намерения",
    "keywords": ["найденные", "ключевые", "слова"],
    "serious_buyer": true|false
}

БУДЬ ТОЧЕН И ОБЪЕКТИВЕН В АНАЛИЗЕ.
            """,
            variables=[],
            description="Системная инструкция для анализа сообщений"
        )
    
    def _add_analysis_prompts(self) -> None:
        """Промпты для анализа сообщений"""
        
        # Полный анализ сообщения
        self.prompts["analyze_message"] = PromptTemplate(
            name="analyze_message",
            category=PromptCategory.ANALYSIS,
            template="""
КОНТЕКСТ ТОВАРА:
- Название: {product_title}
- Цена: {product_price} руб.
- Категория: {product_category}
- Описание: {product_description}

ИСТОРИЯ ОБЩЕНИЯ:
{conversation_history}

НОВОЕ СООБЩЕНИЕ ОТ ПОКУПАТЕЛЯ:
"{message_text}"

Проанализируй это сообщение и верни результат в JSON формате согласно системной инструкции.
            """,
            variables=["product_title", "product_price", "product_category", "product_description", "conversation_history", "message_text"],
            description="Полный анализ сообщения с контекстом товара"
        )
        
        # Быстрый анализ без контекста
        self.prompts["quick_analyze"] = PromptTemplate(
            name="quick_analyze",
            category=PromptCategory.ANALYSIS,
            template="""
Быстро проанализируй это сообщение и определи его тип:

"{message_text}"

Верни JSON с типом сообщения и уверенностью.
            """,
            variables=["message_text"],
            description="Быстрый анализ сообщения без контекста"
        )
    
    def _add_generation_prompts(self) -> None:
        """Промпты для генерации ответов"""
        
        # Универсальный генератор ответов
        self.prompts["generate_response"] = PromptTemplate(
            name="generate_response",
            category=PromptCategory.GENERATION,
            template="""
ИНФОРМАЦИЯ О ТОВАРЕ:
- Название: {product_title}
- Цена: {product_price} руб.
- Состояние: {product_condition}
- Описание: {product_description}
- Местоположение: {product_location}
- Доставка: {delivery_info}
- Торг: {negotiation_info}

АНАЛИЗ СООБЩЕНИЯ:
- Тип: {message_type}
- Настроение: {sentiment}
- Срочность: {urgency}
- Намерение: {intent}

СООБЩЕНИЕ ПОКУПАТЕЛЯ:
"{user_message}"

СТИЛЬ ОТВЕТА: {response_style}

ТРЕБОВАНИЯ К ОТВЕТУ:
1. Отвечай в указанном стиле
2. Учитывай тип и настроение сообщения
3. Включай конкретную информацию о товаре
4. Длина: 50-200 символов
5. Будь дружелюбным но профессиональным
6. Если уместно - предлагай встречу/осмотр

Сгенерируй подходящий ответ:
            """,
            variables=[
                "product_title", "product_price", "product_condition", "product_description",
                "product_location", "delivery_info", "negotiation_info", "message_type",
                "sentiment", "urgency", "intent", "user_message", "response_style"
            ],
            description="Универсальный генератор ответов с полным контекстом"
        )
        
        # Ответы на частые вопросы
        self.prompts["faq_response"] = PromptTemplate(
            name="faq_response",
            category=PromptCategory.GENERATION,
            template="""
Покупатель спрашивает: "{question}"

Это частый вопрос типа: {question_type}

Информация для ответа:
{answer_info}

Дай краткий и полезный ответ (до 150 символов):
            """,
            variables=["question", "question_type", "answer_info"],
            description="Ответы на часто задаваемые вопросы"
        )
        
        # Персонализированные ответы
        self.prompts["personalized_response"] = PromptTemplate(
            name="personalized_response",
            category=PromptCategory.GENERATION,
            template="""
ИНФОРМАЦИЯ О ПОКУПАТЕЛЕ:
- Имя: {buyer_name}
- История общения: {conversation_count} сообщений
- Предыдущие интересы: {previous_interests}
- Серьезность намерений: {buyer_seriousness}

ТЕКУЩИЙ ЗАПРОС: "{current_message}"

ТОВАР: {product_title} за {product_price} руб.

Создай персонализированный ответ, обращаясь к покупателю по имени и учитывая историю общения:
            """,
            variables=["buyer_name", "conversation_count", "previous_interests", "buyer_seriousness", "current_message", "product_title", "product_price"],
            description="Персонализированные ответы с учетом истории"
        )
    
    def _add_classification_prompts(self) -> None:
        """Промпты для классификации"""
        
        # Классификация типа сообщения
        self.prompts["classify_message"] = PromptTemplate(
            name="classify_message",
            category=PromptCategory.CLASSIFICATION,
            template="""
Классифицируй тип этого сообщения:

"{message}"

Возможные типы:
- price_question (вопросы о цене, торге)
- availability (доступность товара)
- product_info (информация о товаре)
- meeting_request (запрос встречи, осмотра)
- delivery_question (вопросы доставки)
- general_question (общие вопросы)
- greeting (приветствие)
- complaint (жалобы)
- spam (спам)

Верни JSON: {{"type": "тип", "confidence": 0.0-1.0}}
            """,
            variables=["message"],
            description="Классификация типа сообщения"
        )
        
        # Определение приоритета
        self.prompts["classify_priority"] = PromptTemplate(
            name="classify_priority",
            category=PromptCategory.CLASSIFICATION,
            template="""
Определи приоритет ответа на это сообщение:

"{message}"

Контекст: {context}

Приоритеты:
- urgent (требует немедленного ответа)
- high (важный покупатель/запрос)
- normal (обычный приоритет)
- low (можно ответить позже)

Верни JSON: {{"priority": "уровень", "reasoning": "обоснование"}}
            """,
            variables=["message", "context"],
            description="Определение приоритета ответа"
        )
    
    def _add_sentiment_prompts(self) -> None:
        """Промпты для анализа настроения"""
        
        # Анализ эмоций
        self.prompts["analyze_sentiment"] = PromptTemplate(
            name="analyze_sentiment",
            category=PromptCategory.SENTIMENT,
            template="""
Проанализируй эмоциональную окраску этого сообщения:

"{message}"

Определи:
1. Основное настроение (positive/negative/neutral)
2. Уровень заинтересованности (0.0-1.0)
3. Уровень фрустрации (0.0-1.0)
4. Готовность к покупке (0.0-1.0)

Верни результат в JSON:
{
    "sentiment": "positive|negative|neutral",
    "interest_level": 0.0-1.0,
    "frustration_level": 0.0-1.0,
    "purchase_readiness": 0.0-1.0,
    "emotional_indicators": ["список", "эмоциональных", "маркеров"]
}
            """,
            variables=["message"],
            description="Детальный анализ эмоциональной окраски"
        )
        
        # Оценка серьезности покупателя
        self.prompts["assess_buyer_seriousness"] = PromptTemplate(
            name="assess_buyer_seriousness",
            category=PromptCategory.SENTIMENT,
            template="""
На основе этого сообщения оцени серьезность намерений покупателя:

"{message}"

Дополнительный контекст: {context}

Индикаторы серьезности:
- Конкретные вопросы о товаре
- Готовность к встрече/осмотру
- Обсуждение условий оплаты
- Срочность в сообщениях

Верни оценку в JSON:
{
    "seriousness_score": 0.0-1.0,
    "category": "tire_kicker|interested|serious|ready_to_buy",
    "indicators": ["найденные", "индикаторы"],
    "recommendation": "как отвечать этому покупателю"
}
            """,
            variables=["message", "context"],
            description="Оценка серьезности намерений покупателя"
        )
    
    def get_prompt(self, name: str) -> Optional[PromptTemplate]:
        """
        Получение промпта по имени
        
        Args:
            name: Название промпта
            
        Returns:
            Optional[PromptTemplate]: Промпт или None
        """
        
        return self.prompts.get(name)
    
    def get_prompts_by_category(self, category: PromptCategory) -> List[PromptTemplate]:
        """
        Получение промптов по категории
        
        Args:
            category: Категория промптов
            
        Returns:
            List[PromptTemplate]: Список промптов
        """
        
        return [
            prompt for prompt in self.prompts.values()
            if prompt.category == category
        ]
    
    def list_prompts(self) -> List[str]:
        """Получение списка всех доступных промптов"""
        
        return list(self.prompts.keys())
    
    def search_prompts(self, query: str) -> List[PromptTemplate]:
        """
        Поиск промптов по ключевым словам
        
        Args:
            query: Поисковый запрос
            
        Returns:
            List[PromptTemplate]: Найденные промпты
        """
        
        query_lower = query.lower()
        results = []
        
        for prompt in self.prompts.values():
            if (query_lower in prompt.name.lower() or 
                query_lower in prompt.description.lower() or
                query_lower in prompt.template.lower()):
                results.append(prompt)
        
        return results
    
    def format_prompt(self, name: str, **kwargs) -> str:
        """
        Форматирование промпта с переменными
        
        Args:
            name: Название промпта
            **kwargs: Переменные для подстановки
            
        Returns:
            str: Отформатированный промпт
        """
        
        prompt = self.get_prompt(name)
        if not prompt:
            raise ValueError(f"Промпт '{name}' не найден")
        
        return prompt.format(**kwargs)
    
    def create_custom_prompt(
        self,
        name: str,
        category: PromptCategory,
        template: str,
        variables: List[str],
        description: str
    ) -> None:
        """
        Создание пользовательского промпта
        
        Args:
            name: Название промпта
            category: Категория
            template: Шаблон промпта
            variables: Список переменных
            description: Описание
        """
        
        if name in self.prompts:
            raise ValueError(f"Промпт '{name}' уже существует")
        
        self.prompts[name] = PromptTemplate(
            name=name,
            category=category,
            template=template,
            variables=variables,
            description=description
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики по промптам"""
        
        stats = {
            "total_prompts": len(self.prompts),
            "by_category": {}
        }
        
        # Подсчет по категориям
        for category in PromptCategory:
            count = len(self.get_prompts_by_category(category))
            stats["by_category"][category.value] = count
        
        return stats


# Создание глобального экземпляра библиотеки
prompt_library = GeminiPromptLibrary()

# Готовые наборы для быстрого использования
QUICK_PROMPTS = {
    "analyze": "analyze_message",
    "respond": "generate_response", 
    "classify": "classify_message",
    "sentiment": "analyze_sentiment"
}

# Экспорт
__all__ = [
    "PromptCategory",
    "PromptTemplate", 
    "GeminiPromptLibrary",
    "prompt_library",
    "QUICK_PROMPTS"
]