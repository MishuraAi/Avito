"""
🧠 ИИ-консультант на базе Google Gemini для Avito AI Responder

Этот модуль содержит основную логику ИИ-консультанта, который:
- Анализирует входящие сообщения от покупателей
- Генерирует умные ответы на основе контекста
- Адаптирует стиль общения под ситуацию
- Использует знания о товаре для персонализации

Местоположение: src/core/ai_consultant.py
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

import google.generativeai as genai
from pydantic import BaseModel

from .config import AIConfig, ResponseStyle, MessageType, CoreConfig


# Настройка логгера
logger = logging.getLogger(__name__)


class ProductContext(BaseModel):
    """Контекст товара для персонализации ответов"""
    
    title: str
    price: Optional[int] = None
    description: Optional[str] = None
    category: Optional[str] = None
    condition: Optional[str] = None  # новый, б/у, отличное состояние
    location: Optional[str] = None
    seller_name: Optional[str] = None
    
    # Дополнительная информация
    delivery_available: bool = False
    negotiable: bool = True
    urgent_sale: bool = False


class UserContext(BaseModel):
    """Контекст пользователя для персонализации"""
    
    user_id: str
    name: Optional[str] = None
    message_history: List[str] = []
    last_interaction: Optional[datetime] = None
    
    # Поведенческая информация
    is_serious_buyer: bool = True
    preferred_style: Optional[ResponseStyle] = None
    blocked: bool = False


class ConversationAnalysis(BaseModel):
    """Результат анализа сообщения"""
    
    message_type: MessageType
    confidence: float
    intent: str
    sentiment: str  # positive, negative, neutral
    urgency: str   # low, medium, high
    keywords_found: List[str]
    requires_human: bool = False


class AIConsultant:
    """
    🧠 Главный класс ИИ-консультанта
    
    Отвечает за:
    - Подключение к Gemini API
    - Анализ входящих сообщений  
    - Генерацию персонализированных ответов
    - Адаптацию стиля общения
    """
    
    def __init__(self, config: AIConfig, api_key: str):
        """
        Инициализация ИИ-консультанта
        
        Args:
            config: Конфигурация ИИ
            api_key: API ключ Google Gemini
        """
        self.config = config
        self.api_key = api_key
        self._setup_gemini()
        
        # Кеш для ответов
        self._response_cache: Dict[str, Tuple[str, datetime]] = {}
        
        # Счетчики для метрик
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "gemini_calls": 0,
            "errors": 0,
            "avg_response_time": 0.0
        }
        
        logger.info("ИИ-консультант инициализирован с моделью %s", config.model_name)
    
    def _setup_gemini(self) -> None:
        """Настройка подключения к Gemini API"""
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.config.model_name)
            logger.info("Gemini API настроен успешно")
        except Exception as e:
            logger.error("Ошибка настройки Gemini API: %s", e)
            raise
    
    async def analyze_message(
        self,
        message: str,
        user_context: UserContext,
        product_context: ProductContext
    ) -> ConversationAnalysis:
        """
        🔍 Анализ входящего сообщения
        
        Определяет:
        - Тип сообщения (вопрос о цене, доступности, etc.)
        - Намерение пользователя
        - Эмоциональную окраску
        - Срочность ответа
        
        Args:
            message: Текст сообщения
            user_context: Контекст пользователя
            product_context: Контекст товара
            
        Returns:
            ConversationAnalysis: Результат анализа
        """
        self.metrics["total_requests"] += 1
        start_time = datetime.now()
        
        try:
            # Создаем промпт для анализа
            analysis_prompt = self._create_analysis_prompt(message, user_context, product_context)
            
            # Отправляем запрос к Gemini
            response = await self._call_gemini(analysis_prompt)
            analysis_data = self._parse_analysis_response(response)
            
            # Обновляем метрики
            self.metrics["gemini_calls"] += 1
            self._update_response_time(start_time)
            
            logger.info("Сообщение проанализировано: тип=%s, уверенность=%.2f", 
                       analysis_data.message_type, analysis_data.confidence)
            
            return analysis_data
            
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error("Ошибка анализа сообщения: %s", e)
            
            # Возвращаем базовый анализ при ошибке
            return ConversationAnalysis(
                message_type=MessageType.GENERAL_QUESTION,
                confidence=0.5,
                intent="unknown",
                sentiment="neutral", 
                urgency="medium",
                keywords_found=[],
                requires_human=True
            )
    
    async def generate_response(
        self,
        message: str,
        analysis: ConversationAnalysis,
        user_context: UserContext,
        product_context: ProductContext
    ) -> str:
        """
        💬 Генерация персонализированного ответа
        
        Создает ответ учитывая:
        - Результат анализа сообщения
        - Контекст товара и пользователя
        - Заданный стиль общения
        - Историю переписки
        
        Args:
            message: Исходное сообщение
            analysis: Результат анализа
            user_context: Контекст пользователя
            product_context: Контекст товара
            
        Returns:
            str: Сгенерированный ответ
        """
        start_time = datetime.now()
        
        try:
            # Проверяем кеш
            cache_key = self._generate_cache_key(message, analysis, product_context)
            
            if self.config.cache_responses:
                cached_response = self._get_cached_response(cache_key)
                if cached_response:
                    self.metrics["cache_hits"] += 1
                    logger.debug("Ответ взят из кеша")
                    return cached_response
            
            # Создаем промпт для генерации ответа
            response_prompt = self._create_response_prompt(
                message, analysis, user_context, product_context
            )
            
            # Генерируем ответ через Gemini
            raw_response = await self._call_gemini(response_prompt)
            formatted_response = self._format_response(raw_response, analysis, product_context)
            
            # Сохраняем в кеш
            if self.config.cache_responses:
                self._cache_response(cache_key, formatted_response)
            
            # Обновляем метрики
            self.metrics["gemini_calls"] += 1
            self._update_response_time(start_time)
            
            logger.info("Ответ сгенерирован, длина: %d символов", len(formatted_response))
            return formatted_response
            
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error("Ошибка генерации ответа: %s", e)
            
            # Возвращаем базовый ответ при ошибке
            return self._get_fallback_response(analysis.message_type, product_context)
    
    def _create_analysis_prompt(
        self,
        message: str,
        user_context: UserContext,
        product_context: ProductContext
    ) -> str:
        """Создание промпта для анализа сообщения"""
        
        prompt = f"""
Ты - эксперт по анализу сообщений на торговой площадке Авито.
Проанализируй входящее сообщение от покупателя и верни результат в JSON формате.

КОНТЕКСТ ТОВАРА:
- Название: {product_context.title}
- Цена: {product_context.price or 'не указана'} руб.
- Описание: {product_context.description or 'отсутствует'}
- Категория: {product_context.category or 'общая'}

СООБЩЕНИЕ ПОКУПАТЕЛЯ:
"{message}"

ИСТОРИЯ ОБЩЕНИЯ:
{user_context.message_history[-3:] if user_context.message_history else "Первое сообщение"}

Определи и верни в JSON:
1. message_type - тип сообщения (price_question, availability, product_info, meeting_request, delivery_question, general_question, greeting, complaint, spam)
2. confidence - уверенность в классификации (0.0-1.0)
3. intent - основное намерение пользователя (1-2 слова)
4. sentiment - эмоциональная окраска (positive, negative, neutral)
5. urgency - срочность (low, medium, high)
6. keywords_found - найденные ключевые слова (массив)
7. requires_human - нужно ли вмешательство человека (true/false)

Отвечай только валидным JSON без дополнительного текста.
"""
        
        return prompt.strip()
    
    def _create_response_prompt(
        self,
        message: str,
        analysis: ConversationAnalysis,
        user_context: UserContext,
        product_context: ProductContext
    ) -> str:
        """Создание промпта для генерации ответа"""
        
        # Определяем стиль общения
        style_instructions = self._get_style_instructions(self.config.response_style)
        
        prompt = f"""
Ты - опытный продавец на Авито, отвечаешь покупателю.

СТИЛЬ ОБЩЕНИЯ: {style_instructions}

ИНФОРМАЦИЯ О ТОВАРЕ:
- Название: {product_context.title}
- Цена: {product_context.price or 'договорная'} руб.
- Состояние: {product_context.condition or 'хорошее'}
- Описание: {product_context.description or 'см. объявление'}
- Доставка: {'доступна' if product_context.delivery_available else 'самовывоз'}
- Торг: {'возможен' if product_context.negotiable else 'неуместен'}

АНАЛИЗ СООБЩЕНИЯ:
- Тип: {analysis.message_type}
- Намерение: {analysis.intent}
- Настроение: {analysis.sentiment}
- Срочность: {analysis.urgency}

СООБЩЕНИЕ ПОКУПАТЕЛЯ:
"{message}"

ТРЕБОВАНИЯ К ОТВЕТУ:
1. Отвечай персонально и по существу
2. Используй указанный стиль общения
3. Включай конкретную информацию о товаре
4. Длина ответа: 50-200 символов
5. Если можешь - предлагай встречу/осмотр
6. Будь дружелюбным но не навязчивым

Сгенерируй ответ:
"""
        
        return prompt.strip()
    
    def _get_style_instructions(self, style: ResponseStyle) -> str:
        """Получение инструкций для стиля общения"""
        
        style_map = {
            ResponseStyle.PROFESSIONAL: "Официальный, вежливый, используй 'Вы'",
            ResponseStyle.FRIENDLY: "Дружелюбный, теплый, можно использовать 'ты'", 
            ResponseStyle.CASUAL: "Простой, неформальный, как с другом",
            ResponseStyle.SALES: "Активно продающий, подчеркивай выгоды"
        }
        
        return style_map.get(style, "Нейтральный, вежливый")
    
    async def _call_gemini(self, prompt: str) -> str:
        """Вызов Gemini API с обработкой ошибок"""
        
        try:
            # Настройки генерации
            generation_config = {
                "temperature": self.config.temperature,
                "max_output_tokens": self.config.max_tokens,
            }
            
            # Асинхронный вызов
            response = await asyncio.wait_for(
                self.model.generate_content_async(
                    prompt,
                    generation_config=generation_config
                ),
                timeout=self.config.response_timeout
            )
            
            return response.text
            
        except asyncio.TimeoutError:
            logger.warning("Таймаут запроса к Gemini API")
            raise
        except Exception as e:
            logger.error("Ошибка вызова Gemini API: %s", e)
            raise
    
    def _parse_analysis_response(self, response: str) -> ConversationAnalysis:
        """Парсинг ответа анализа от Gemini"""
        
        try:
            data = json.loads(response.strip())
            return ConversationAnalysis(**data)
        except json.JSONDecodeError as e:
            logger.warning("Ошибка парсинга JSON ответа: %s", e)
            # Возвращаем базовый анализ
            return ConversationAnalysis(
                message_type=MessageType.GENERAL_QUESTION,
                confidence=0.5,
                intent="unclear",
                sentiment="neutral",
                urgency="medium", 
                keywords_found=[]
            )
    
    def _format_response(
        self,
        raw_response: str,
        analysis: ConversationAnalysis,
        product_context: ProductContext
    ) -> str:
        """Форматирование финального ответа"""
        
        response = raw_response.strip()
        
        # Базовые замены
        if product_context.price:
            response = response.replace("{price}", str(product_context.price))
        
        if product_context.seller_name:
            response = response.replace("{seller_name}", product_context.seller_name)
        
        # Обрезаем если слишком длинный
        if len(response) > 500:
            response = response[:497] + "..."
        
        return response
    
    def _generate_cache_key(
        self,
        message: str,
        analysis: ConversationAnalysis,
        product_context: ProductContext
    ) -> str:
        """Генерация ключа кеша"""
        
        key_parts = [
            analysis.message_type.value,
            str(product_context.price or 0),
            product_context.category or "general",
            str(hash(message.lower().strip()))[:8]
        ]
        
        return ":".join(key_parts)
    
    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Получение ответа из кеша"""
        
        if cache_key in self._response_cache:
            response, timestamp = self._response_cache[cache_key]
            
            # Проверяем не истек ли TTL
            if datetime.now() - timestamp < timedelta(seconds=self.config.cache_ttl):
                return response
            else:
                # Удаляем устаревший кеш
                del self._response_cache[cache_key]
        
        return None
    
    def _cache_response(self, cache_key: str, response: str) -> None:
        """Сохранение ответа в кеш"""
        
        self._response_cache[cache_key] = (response, datetime.now())
        
        # Ограничиваем размер кеша
        if len(self._response_cache) > 1000:
            # Удаляем 20% самых старых записей
            old_keys = sorted(
                self._response_cache.keys(),
                key=lambda k: self._response_cache[k][1]
            )[:200]
            
            for key in old_keys:
                del self._response_cache[key]
    
    def _get_fallback_response(
        self,
        message_type: MessageType,
        product_context: ProductContext
    ) -> str:
        """Получение запасного ответа при ошибке"""
        
        fallback_responses = {
            MessageType.PRICE_QUESTION: f"Цена {product_context.price or 'указана в объявлении'} руб. Торг возможен!",
            MessageType.AVAILABILITY: "Товар в наличии. Можете посмотреть!",
            MessageType.GREETING: "Здравствуйте! Чем могу помочь?",
            MessageType.GENERAL_QUESTION: "Спасибо за интерес! Отвечу на все вопросы."
        }
        
        return fallback_responses.get(
            message_type,
            "Спасибо за сообщение! Скоро отвечу подробнее."
        )
    
    def _update_response_time(self, start_time: datetime) -> None:
        """Обновление метрик времени ответа"""
        
        response_time = (datetime.now() - start_time).total_seconds()
        
        # Обновляем среднее время ответа
        current_avg = self.metrics["avg_response_time"]
        total_requests = self.metrics["total_requests"]
        
        self.metrics["avg_response_time"] = (
            (current_avg * (total_requests - 1) + response_time) / total_requests
        )
    
    def get_metrics(self) -> Dict:
        """Получение метрик работы консультанта"""
        
        cache_hit_rate = 0.0
        if self.metrics["total_requests"] > 0:
            cache_hit_rate = self.metrics["cache_hits"] / self.metrics["total_requests"]
        
        return {
            **self.metrics,
            "cache_hit_rate": cache_hit_rate,
            "cache_size": len(self._response_cache)
        }
    
    def clear_cache(self) -> None:
        """Очистка кеша ответов"""
        
        self._response_cache.clear()
        logger.info("Кеш ответов очищен")


async def create_ai_consultant(api_key: str, config: Optional[AIConfig] = None) -> AIConsultant:
    """
    🏭 Фабричная функция для создания ИИ-консультанта
    
    Args:
        api_key: API ключ Google Gemini
        config: Конфигурация (опционально)
        
    Returns:
        AIConsultant: Готовый к работе консультант
    """
    
    if not config:
        config = AIConfig()
    
    consultant = AIConsultant(config, api_key)
    
    # Тестируем подключение
    try:
        test_response = await consultant._call_gemini("Тест подключения. Ответь 'OK'")
        logger.info("ИИ-консультант создан и протестирован: %s", test_response[:50])
    except Exception as e:
        logger.error("Ошибка тестирования консультанта: %s", e)
        raise
    
    return consultant