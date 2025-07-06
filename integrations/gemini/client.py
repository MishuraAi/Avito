"""
🤖 Расширенный клиент для Google Gemini API

Этот модуль содержит продвинутый клиент для работы с Gemini:
- Асинхронная работа с API
- Автоматические повторы при ошибках
- Управление контекстом диалога
- Мониторинг токенов и стоимости
- Кеширование ответов
- Обработка фильтров безопасности

Местоположение: src/integrations/gemini/client.py
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import hashlib

import google.generativeai as genai
import aiohttp
from aiohttp import ClientSession, ClientTimeout

from ..base import BaseIntegration
from . import (
    GeminiIntegrationConfig,
    GeminiMessage,
    GeminiResponse,
    GeminiModel,
    GeminiRole,
    GeminiAPIException,
    GeminiRateLimitException,
    GeminiSafetyException
)


# Настройка логгера
logger = logging.getLogger(__name__)


class GeminiAPIClient(BaseIntegration):
    """
    🤖 Расширенный клиент для Google Gemini API
    
    Предоставляет высокоуровневые методы для работы с Gemini:
    - Генерация текста с контекстом
    - Управление диалогами
    - Кеширование и оптимизация
    - Мониторинг использования
    """
    
    def __init__(self, config: GeminiIntegrationConfig):
        """
        Инициализация Gemini клиента
        
        Args:
            config: Конфигурация интеграции с Gemini
        """
        
        super().__init__("gemini_api", config.__dict__)
        
        self.config = config
        self.model = None
        
        # Диалоговые сессии
        self.active_sessions: Dict[str, List[GeminiMessage]] = {}
        
        # Кеш ответов
        self.response_cache: Dict[str, Tuple[GeminiResponse, datetime]] = {}
        self.cache_ttl = timedelta(hours=1)
        
        # Токен трекинг
        self.token_usage = {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_requests": 0,
            "estimated_cost": 0.0
        }
        
        # Настройки повторов
        self.retry_delays = [1, 2, 4, 8, 16]  # Экспоненциальная задержка
        
        logger.info("Gemini API клиент инициализирован с моделью %s", config.model.value)
    
    async def connect(self) -> bool:
        """Подключение к Gemini API"""
        
        try:
            # Настройка API ключа
            genai.configure(api_key=self.config.api_key)
            
            # Создание модели
            self.model = genai.GenerativeModel(self.config.model.value)
            
            # Тестовый запрос для проверки подключения
            test_response = await self._make_generation_request(
                "Ответь одним словом: OK",
                max_retries=1
            )
            
            if test_response and "ok" in test_response.text.lower():
                self.is_connected = True
                self.connection_time = datetime.now()
                logger.info("✅ Подключение к Gemini API успешно")
                return True
            else:
                logger.error("❌ Тест подключения к Gemini API не прошел")
                return False
                
        except Exception as e:
            self.last_error = str(e)
            logger.error("❌ Ошибка подключения к Gemini API: %s", e)
            return False
    
    async def disconnect(self) -> None:
        """Отключение от Gemini API"""
        
        self.model = None
        self.is_connected = False
        
        # Очищаем кеши
        self.active_sessions.clear()
        self.response_cache.clear()
        
        logger.info("Отключение от Gemini API")
    
    async def health_check(self) -> bool:
        """Проверка состояния API"""
        
        try:
            if not self.model:
                return False
            
            # Простой запрос для проверки
            response = await self._make_generation_request(
                "Проверка работы API. Ответь: работает",
                max_retries=1
            )
            
            return response is not None and "работает" in response.text.lower()
            
        except Exception as e:
            logger.error("Ошибка health check Gemini API: %s", e)
            return False
    
    async def generate_text(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        system_instruction: Optional[str] = None,
        use_cache: bool = True
    ) -> Optional[GeminiResponse]:
        """
        Генерация текста с поддержкой контекста
        
        Args:
            prompt: Текст промпта
            session_id: ID сессии для поддержания контекста (опционально)
            system_instruction: Системная инструкция (опционально)
            use_cache: Использовать кеширование
            
        Returns:
            Optional[GeminiResponse]: Ответ от Gemini или None при ошибке
        """
        
        start_time = datetime.now()
        
        try:
            # Проверяем кеш
            if use_cache:
                cache_key = self._generate_cache_key(prompt, session_id, system_instruction)
                cached_response = self._get_cached_response(cache_key)
                
                if cached_response:
                    logger.debug("Ответ взят из кеша")
                    return cached_response
            
            # Подготавливаем контекст диалога
            messages = self._prepare_conversation_context(prompt, session_id, system_instruction)
            
            # Генерируем ответ
            response = await self._make_generation_request(messages)
            
            if response:
                # Сохраняем в кеш
                if use_cache:
                    self._cache_response(cache_key, response)
                
                # Обновляем сессию
                if session_id:
                    self._update_session(session_id, prompt, response.text)
                
                # Обновляем метрики
                processing_time = (datetime.now() - start_time).total_seconds()
                self.update_metrics(True, processing_time)
                self._update_token_usage(response)
                
                logger.info("Текст сгенерирован: %d символов за %.2f сек", 
                           len(response.text), processing_time)
            
            return response
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(False, processing_time)
            logger.error("Ошибка генерации текста: %s", e)
            return None
    
    async def generate_with_conversation(
        self,
        prompt: str,
        conversation_history: List[GeminiMessage],
        system_instruction: Optional[str] = None
    ) -> Optional[GeminiResponse]:
        """
        Генерация с явной историей диалога
        
        Args:
            prompt: Новый промпт
            conversation_history: История диалога
            system_instruction: Системная инструкция
            
        Returns:
            Optional[GeminiResponse]: Ответ от Gemini
        """
        
        try:
            # Подготавливаем полный контекст
            full_messages = conversation_history.copy()
            
            # Добавляем системную инструкцию если есть
            if system_instruction:
                system_msg = GeminiMessage(
                    role=GeminiRole.SYSTEM,
                    content=system_instruction
                )
                full_messages.insert(0, system_msg)
            
            # Добавляем новый промпт
            user_msg = GeminiMessage(
                role=GeminiRole.USER,
                content=prompt
            )
            full_messages.append(user_msg)
            
            # Генерируем ответ
            response = await self._make_generation_request(full_messages)
            
            return response
            
        except Exception as e:
            logger.error("Ошибка генерации с историей: %s", e)
            return None
    
    async def analyze_content(
        self,
        content: str,
        analysis_type: str = "sentiment"
    ) -> Optional[Dict[str, Any]]:
        """
        Анализ контента с помощью Gemini
        
        Args:
            content: Контент для анализа
            analysis_type: Тип анализа (sentiment, classification, etc.)
            
        Returns:
            Optional[Dict]: Результат анализа
        """
        
        try:
            # Формируем промпт для анализа
            analysis_prompts = {
                "sentiment": f"""
                Проанализируй эмоциональную окраску этого текста и верни результат в JSON:
                {{"sentiment": "positive/negative/neutral", "confidence": 0.0-1.0, "explanation": "объяснение"}}
                
                Текст: {content}
                """,
                
                "classification": f"""
                Классифицируй этот текст по типу сообщения в Авито и верни JSON:
                {{"type": "price_question/availability/meeting_request/general", "confidence": 0.0-1.0}}
                
                Текст: {content}
                """,
                
                "urgency": f"""
                Определи срочность этого сообщения и верни JSON:
                {{"urgency": "low/medium/high", "confidence": 0.0-1.0, "reasoning": "обоснование"}}
                
                Текст: {content}
                """
            }
            
            prompt = analysis_prompts.get(analysis_type, analysis_prompts["sentiment"])
            
            response = await self.generate_text(prompt, use_cache=True)
            
            if response:
                # Пытаемся распарсить JSON ответ
                try:
                    return json.loads(response.text.strip())
                except json.JSONDecodeError:
                    # Если не JSON, возвращаем как текст
                    return {"result": response.text, "type": "text"}
            
            return None
            
        except Exception as e:
            logger.error("Ошибка анализа контента: %s", e)
            return None
    
    def create_session(self, session_id: str, system_instruction: Optional[str] = None) -> None:
        """
        Создание новой диалоговой сессии
        
        Args:
            session_id: Уникальный ID сессии
            system_instruction: Системная инструкция для сессии
        """
        
        self.active_sessions[session_id] = []
        
        if system_instruction:
            system_msg = GeminiMessage(
                role=GeminiRole.SYSTEM,
                content=system_instruction
            )
            self.active_sessions[session_id].append(system_msg)
        
        logger.debug("Создана сессия %s", session_id)
    
    def clear_session(self, session_id: str) -> None:
        """
        Очистка диалоговой сессии
        
        Args:
            session_id: ID сессии для очистки
        """
        
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.debug("Сессия %s очищена", session_id)
    
    def get_session_history(self, session_id: str) -> List[GeminiMessage]:
        """
        Получение истории сессии
        
        Args:
            session_id: ID сессии
            
        Returns:
            List[GeminiMessage]: История сообщений
        """
        
        return self.active_sessions.get(session_id, []).copy()
    
    async def _make_generation_request(
        self,
        content,
        max_retries: Optional[int] = None
    ) -> Optional[GeminiResponse]:
        """
        Выполнение запроса к Gemini API с повторами
        
        Args:
            content: Контент для генерации (строка или список сообщений)
            max_retries: Максимум повторов (по умолчанию из конфига)
            
        Returns:
            Optional[GeminiResponse]: Ответ от API
        """
        
        if max_retries is None:
            max_retries = self.config.max_retries
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                # Подготавливаем конфигурацию генерации
                generation_config = self.config.get_generation_config()
                
                # Выполняем запрос
                if isinstance(content, str):
                    # Простой текстовый запрос
                    response = await self.model.generate_content_async(
                        content,
                        generation_config=generation_config
                    )
                else:
                    # Диалог из нескольких сообщений
                    formatted_messages = [msg.to_dict() for msg in content]
                    response = await self.model.generate_content_async(
                        formatted_messages,
                        generation_config=generation_config
                    )
                
                # Проверяем на фильтры безопасности
                if hasattr(response, 'prompt_feedback'):
                    if response.prompt_feedback and response.prompt_feedback.block_reason:
                        raise GeminiSafetyException(
                            f"Контент заблокирован фильтрами: {response.prompt_feedback.block_reason}",
                            []
                        )
                
                # Парсим ответ
                return self._parse_response(response)
                
            except Exception as e:
                last_exception = e
                
                # Проверяем нужно ли повторить
                if attempt < max_retries:
                    if self._should_retry(e):
                        delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                        logger.warning("Попытка %d/%d неудачна, повтор через %d сек: %s", 
                                     attempt + 1, max_retries + 1, delay, e)
                        await asyncio.sleep(delay)
                        continue
                
                # Больше не повторяем
                break
        
        # Все попытки исчерпаны
        logger.error("Все попытки исчерпаны, последняя ошибка: %s", last_exception)
        return None
    
    def _should_retry(self, exception: Exception) -> bool:
        """Определяет стоит ли повторять запрос"""
        
        # Повторяем при временных ошибках
        retry_conditions = [
            "timeout" in str(exception).lower(),
            "connection" in str(exception).lower(),
            "500" in str(exception),
            "502" in str(exception),
            "503" in str(exception),
            "429" in str(exception)  # Rate limit
        ]
        
        return any(retry_conditions)
    
    def _parse_response(self, response) -> GeminiResponse:
        """Парсинг ответа от Gemini API"""
        
        # Извлекаем текст
        text = response.text if hasattr(response, 'text') else str(response)
        
        # Извлекаем метаданные если доступны
        prompt_tokens = None
        completion_tokens = None
        total_tokens = None
        
        if hasattr(response, 'usage_metadata'):
            usage = response.usage_metadata
            prompt_tokens = getattr(usage, 'prompt_token_count', None)
            completion_tokens = getattr(usage, 'candidates_token_count', None)
            total_tokens = getattr(usage, 'total_token_count', None)
        
        # Проверяем причину завершения
        finish_reason = None
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            finish_reason = getattr(candidate, 'finish_reason', None)
        
        # Извлекаем рейтинги безопасности
        safety_ratings = None
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'safety_ratings'):
                safety_ratings = [
                    {
                        "category": rating.category.name,
                        "probability": rating.probability.name
                    }
                    for rating in candidate.safety_ratings
                ]
        
        return GeminiResponse(
            text=text,
            model_used=self.config.model.value,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            finish_reason=finish_reason.name if finish_reason else None,
            safety_ratings=safety_ratings,
            raw_response=response._pb if hasattr(response, '_pb') else None
        )
    
    def _prepare_conversation_context(
        self,
        prompt: str,
        session_id: Optional[str],
        system_instruction: Optional[str]
    ) -> List[GeminiMessage]:
        """Подготовка контекста диалога"""
        
        messages = []
        
        # Добавляем системную инструкцию
        if system_instruction:
            messages.append(GeminiMessage(
                role=GeminiRole.SYSTEM,
                content=system_instruction
            ))
        
        # Добавляем историю сессии
        if session_id and session_id in self.active_sessions:
            messages.extend(self.active_sessions[session_id])
        
        # Добавляем новый промпт
        messages.append(GeminiMessage(
            role=GeminiRole.USER,
            content=prompt
        ))
        
        return messages
    
    def _update_session(self, session_id: str, user_prompt: str, ai_response: str) -> None:
        """Обновление истории сессии"""
        
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = []
        
        # Добавляем сообщения в историю
        user_msg = GeminiMessage(role=GeminiRole.USER, content=user_prompt)
        ai_msg = GeminiMessage(role=GeminiRole.MODEL, content=ai_response)
        
        self.active_sessions[session_id].extend([user_msg, ai_msg])
        
        # Ограничиваем длину истории (последние 20 сообщений)
        if len(self.active_sessions[session_id]) > 20:
            self.active_sessions[session_id] = self.active_sessions[session_id][-20:]
    
    def _generate_cache_key(
        self,
        prompt: str,
        session_id: Optional[str],
        system_instruction: Optional[str]
    ) -> str:
        """Генерация ключа кеша"""
        
        key_parts = [
            prompt,
            session_id or "",
            system_instruction or "",
            self.config.model.value,
            str(self.config.temperature)
        ]
        
        combined = "|".join(key_parts)
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[GeminiResponse]:
        """Получение ответа из кеша"""
        
        if cache_key in self.response_cache:
            response, timestamp = self.response_cache[cache_key]
            
            # Проверяем TTL
            if datetime.now() - timestamp < self.cache_ttl:
                return response
            else:
                # Удаляем устаревший кеш
                del self.response_cache[cache_key]
        
        return None
    
    def _cache_response(self, cache_key: str, response: GeminiResponse) -> None:
        """Сохранение ответа в кеш"""
        
        self.response_cache[cache_key] = (response, datetime.now())
        
        # Ограничиваем размер кеша
        if len(self.response_cache) > 500:
            # Удаляем 20% старых записей
            old_keys = sorted(
                self.response_cache.keys(),
                key=lambda k: self.response_cache[k][1]
            )[:100]
            
            for key in old_keys:
                del self.response_cache[key]
    
    def _update_token_usage(self, response: GeminiResponse) -> None:
        """Обновление статистики использования токенов"""
        
        if response.prompt_tokens:
            self.token_usage["total_prompt_tokens"] += response.prompt_tokens
        
        if response.completion_tokens:
            self.token_usage["total_completion_tokens"] += response.completion_tokens
        
        self.token_usage["total_requests"] += 1
        
        # Примерная оценка стоимости (условные единицы)
        if response.total_tokens:
            self.token_usage["estimated_cost"] += response.total_tokens * 0.0001
    
    def get_extended_metrics(self) -> Dict[str, Any]:
        """Получение расширенных метрик"""
        
        base_metrics = self.get_metrics()
        
        return {
            **base_metrics,
            "token_usage": self.token_usage,
            "active_sessions": len(self.active_sessions),
            "cache_size": len(self.response_cache),
            "model_used": self.config.model.value
        }
    
    def clear_cache(self) -> None:
        """Очистка всех кешей"""
        
        self.response_cache.clear()
        logger.info("Кеш Gemini клиента очищен")


# Фабричная функция
async def create_gemini_client(config: GeminiIntegrationConfig) -> GeminiAPIClient:
    """
    🏭 Создание и подключение Gemini клиента
    
    Args:
        config: Конфигурация интеграции
        
    Returns:
        GeminiAPIClient: Готовый к работе клиент
    """
    
    if not config.validate():
        raise ValueError("Некорректная конфигурация Gemini API")
    
    client = GeminiAPIClient(config)
    
    # Подключаемся к API
    success = await client.connect()
    if not success:
        raise GeminiAPIException("Не удалось подключиться к Gemini API", 0)
    
    logger.info("Gemini API клиент создан и подключен")
    return client