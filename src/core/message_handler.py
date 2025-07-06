"""
📨 Обработчик сообщений для Avito AI Responder

Этот модуль отвечает за:
- Прием и валидацию входящих сообщений
- Классификацию типов сообщений
- Фильтрацию спама и нежелательных сообщений
- Управление очередью обработки
- Координацию с ИИ-консультантом

Местоположение: src/core/message_handler.py
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque

from pydantic import BaseModel

from .config import (
    MessageHandlerConfig, MessageType, MESSAGE_KEYWORDS,
    get_keywords_for_type
)
from .ai_consultant import (
    AIConsultant, UserContext, ProductContext, ConversationAnalysis
)


# Настройка логгера
logger = logging.getLogger(__name__)


class IncomingMessage(BaseModel):
    """Модель входящего сообщения"""
    
    message_id: str
    user_id: str
    product_id: str
    text: str
    timestamp: datetime
    
    # Метаданные
    user_name: Optional[str] = None
    platform: str = "avito"  # avito, direct, etc
    is_read: bool = False
    
    # Техническая информация
    raw_data: Optional[Dict] = None


class ProcessedMessage(BaseModel):
    """Обработанное сообщение с результатами анализа"""
    
    original: IncomingMessage
    analysis: ConversationAnalysis
    response: Optional[str] = None
    processing_time: float = 0.0
    
    # Статус обработки
    status: str = "pending"  # pending, processed, error, blocked
    error_message: Optional[str] = None
    
    # Метки для фильтрации
    is_spam: bool = False
    is_duplicate: bool = False
    requires_human: bool = False


class RateLimiter:
    """Ограничитель частоты сообщений от пользователей"""
    
    def __init__(self, max_messages: int, window_seconds: int):
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.user_messages: Dict[str, deque] = defaultdict(deque)
    
    def is_allowed(self, user_id: str) -> bool:
        """Проверяет разрешено ли сообщение от пользователя"""
        
        now = datetime.now()
        user_queue = self.user_messages[user_id]
        
        # Очищаем старые сообщения
        while user_queue and (now - user_queue[0]).total_seconds() > self.window_seconds:
            user_queue.popleft()
        
        # Проверяем лимит
        if len(user_queue) >= self.max_messages:
            return False
        
        # Добавляем текущее сообщение
        user_queue.append(now)
        return True
    
    def get_remaining_time(self, user_id: str) -> int:
        """Возвращает оставшееся время блокировки в секундах"""
        
        user_queue = self.user_messages[user_id]
        if not user_queue or len(user_queue) < self.max_messages:
            return 0
        
        oldest_message = user_queue[0]
        elapsed = (datetime.now() - oldest_message).total_seconds()
        
        return max(0, int(self.window_seconds - elapsed))


class SpamDetector:
    """Детектор спама и нежелательных сообщений"""
    
    def __init__(self):
        # Паттерны спама
        self.spam_patterns = [
            r'\b(?:зараб|доход|инвест|криптовалют|биткоин)\w*',
            r'\b(?:займ|кредит|деньги)\s+(?:быстро|срочно)',
            r'\bMLM\b|сетевой\s+маркетинг',
            r'(?:https?://|www\.)\w+',  # Ссылки
            r'\b(?:пирамид|схем)\w*',
            r'(?:телеграм|telegram)\s*:?\s*@?\w+',
        ]
        
        # Подозрительные ключевые слова
        self.spam_keywords = {
            'заработок', 'инвестиции', 'криптовалюта', 'биткоин',
            'займ', 'кредит', 'быстрые деньги', 'млм', 'пирамида',
            'схема', 'телеграм', 'whatsapp', 'viber'
        }
        
        # Кеш проверенных сообщений
        self._spam_cache: Dict[str, bool] = {}
    
    def is_spam(self, message: str, user_context: Optional[UserContext] = None) -> Tuple[bool, float]:
        """
        Проверяет является ли сообщение спамом
        
        Returns:
            Tuple[bool, float]: (is_spam, confidence_score)
        """
        
        message_lower = message.lower().strip()
        
        # Проверяем кеш
        if message_lower in self._spam_cache:
            return self._spam_cache[message_lower], 1.0
        
        spam_score = 0.0
        
        # Проверяем паттерны
        for pattern in self.spam_patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                spam_score += 0.3
        
        # Проверяем ключевые слова
        for keyword in self.spam_keywords:
            if keyword in message_lower:
                spam_score += 0.2
        
        # Проверяем длину (очень короткие или очень длинные)
        if len(message) < 3 or len(message) > 1000:
            spam_score += 0.1
        
        # Проверяем повторяющиеся символы
        if len(set(message)) < len(message) * 0.3:
            spam_score += 0.2
        
        # Проверяем контекст пользователя
        if user_context and user_context.blocked:
            spam_score += 0.5
        
        is_spam = spam_score > 0.7
        
        # Кешируем результат
        self._spam_cache[message_lower] = is_spam
        
        return is_spam, min(spam_score, 1.0)


class MessageClassifier:
    """Классификатор типов сообщений"""
    
    def __init__(self):
        self.keywords_cache = {
            msg_type: [kw.lower() for kw in keywords]
            for msg_type, keywords in MESSAGE_KEYWORDS.items()
        }
    
    def classify_message(self, message: str) -> Tuple[MessageType, float]:
        """
        Классифицирует тип сообщения
        
        Returns:
            Tuple[MessageType, float]: (message_type, confidence)
        """
        
        message_lower = message.lower().strip()
        scores = defaultdict(float)
        
        # Подсчитываем совпадения ключевых слов
        for msg_type, keywords in self.keywords_cache.items():
            for keyword in keywords:
                if keyword in message_lower:
                    # Больше очков за точное совпадение слова
                    if f' {keyword} ' in f' {message_lower} ':
                        scores[msg_type] += 1.0
                    else:
                        scores[msg_type] += 0.5
        
        if not scores:
            return MessageType.GENERAL_QUESTION, 0.5
        
        # Находим тип с максимальным счетом
        best_type = max(scores.keys(), key=lambda x: scores[x])
        max_score = scores[best_type]
        
        # Нормализуем уверенность
        total_keywords = len(self.keywords_cache[best_type])
        confidence = min(max_score / total_keywords, 1.0)
        
        return best_type, confidence


class MessageHandler:
    """
    📨 Главный класс обработчика сообщений
    
    Координирует весь процесс обработки:
    1. Валидация входящих сообщений
    2. Фильтрация спама и лимитирование
    3. Классификация типов сообщений  
    4. Передача ИИ-консультанту
    5. Отправка ответов
    """
    
    def __init__(
        self,
        config: MessageHandlerConfig,
        ai_consultant: AIConsultant
    ):
        """
        Инициализация обработчика сообщений
        
        Args:
            config: Конфигурация обработчика
            ai_consultant: ИИ-консультант для генерации ответов
        """
        self.config = config
        self.ai_consultant = ai_consultant
        
        # Компоненты фильтрации
        self.rate_limiter = RateLimiter(
            config.rate_limit_messages,
            config.rate_limit_window
        )
        self.spam_detector = SpamDetector()
        self.classifier = MessageClassifier()
        
        # Очередь сообщений для обработки
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.processing_active = False
        
        # Кеш пользователей и товаров
        self.user_contexts: Dict[str, UserContext] = {}
        self.product_contexts: Dict[str, ProductContext] = {}
        
        # Метрики
        self.metrics = {
            "messages_received": 0,
            "messages_processed": 0,
            "messages_blocked": 0,
            "spam_detected": 0,
            "errors": 0,
            "avg_processing_time": 0.0
        }
        
        logger.info("Обработчик сообщений инициализирован")
    
    async def handle_message(
        self,
        message: IncomingMessage,
        user_context: Optional[UserContext] = None,
        product_context: Optional[ProductContext] = None
    ) -> ProcessedMessage:
        """
        🎯 Основной метод обработки сообщения
        
        Args:
            message: Входящее сообщение
            user_context: Контекст пользователя (опционально)
            product_context: Контекст товара (опционально)
            
        Returns:
            ProcessedMessage: Результат обработки
        """
        self.metrics["messages_received"] += 1
        start_time = datetime.now()
        
        logger.info("Обработка сообщения %s от пользователя %s", 
                   message.message_id, message.user_id)
        
        try:
            # 1. Валидация сообщения
            validation_result = self._validate_message(message)
            if not validation_result.is_valid:
                return ProcessedMessage(
                    original=message,
                    analysis=ConversationAnalysis(
                        message_type=MessageType.GENERAL_QUESTION,
                        confidence=0.0,
                        intent="invalid",
                        sentiment="neutral",
                        urgency="low",
                        keywords_found=[]
                    ),
                    status="blocked",
                    error_message=validation_result.error_message
                )
            
            # 2. Получаем контексты
            user_ctx = user_context or self._get_user_context(message.user_id)
            product_ctx = product_context or self._get_product_context(message.product_id)
            
            # 3. Проверяем rate limiting
            if not self.rate_limiter.is_allowed(message.user_id):
                self.metrics["messages_blocked"] += 1
                remaining_time = self.rate_limiter.get_remaining_time(message.user_id)
                
                return ProcessedMessage(
                    original=message,
                    analysis=ConversationAnalysis(
                        message_type=MessageType.GENERAL_QUESTION,
                        confidence=0.0,
                        intent="rate_limited",
                        sentiment="neutral",
                        urgency="low",
                        keywords_found=[]
                    ),
                    status="blocked",
                    error_message=f"Слишком много сообщений. Подождите {remaining_time} секунд."
                )
            
            # 4. Проверяем на спам
            if self.config.spam_detection:
                is_spam, spam_confidence = self.spam_detector.is_spam(message.text, user_ctx)
                
                if is_spam:
                    self.metrics["spam_detected"] += 1
                    logger.warning("Обнаружен спам от пользователя %s", message.user_id)
                    
                    return ProcessedMessage(
                        original=message,
                        analysis=ConversationAnalysis(
                            message_type=MessageType.SPAM,
                            confidence=spam_confidence,
                            intent="spam",
                            sentiment="negative",
                            urgency="low",
                            keywords_found=[]
                        ),
                        status="blocked",
                        is_spam=True,
                        error_message="Сообщение заблокировано как спам"
                    )
            
            # 5. Классифицируем сообщение
            message_type, type_confidence = self.classifier.classify_message(message.text)
            
            # 6. Анализируем через ИИ
            analysis = await self.ai_consultant.analyze_message(
                message.text, user_ctx, product_ctx
            )
            
            # Комбинируем результаты классификации
            if type_confidence > analysis.confidence:
                analysis.message_type = message_type
                analysis.confidence = type_confidence
            
            # 7. Генерируем ответ
            response = await self.ai_consultant.generate_response(
                message.text, analysis, user_ctx, product_ctx
            )
            
            # 8. Обновляем контекст пользователя
            self._update_user_context(user_ctx, message.text, analysis)
            
            # 9. Создаем результат
            processing_time = (datetime.now() - start_time).total_seconds()
            
            processed = ProcessedMessage(
                original=message,
                analysis=analysis,
                response=response,
                processing_time=processing_time,
                status="processed",
                requires_human=analysis.requires_human
            )
            
            # Обновляем метрики
            self.metrics["messages_processed"] += 1
            self._update_avg_processing_time(processing_time)
            
            logger.info("Сообщение обработано за %.2f сек, тип: %s", 
                       processing_time, analysis.message_type)
            
            return processed
            
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error("Ошибка обработки сообщения %s: %s", message.message_id, e)
            
            return ProcessedMessage(
                original=message,
                analysis=ConversationAnalysis(
                    message_type=MessageType.GENERAL_QUESTION,
                    confidence=0.0,
                    intent="error",
                    sentiment="neutral",
                    urgency="high",
                    keywords_found=[]
                ),
                status="error",
                error_message=str(e),
                requires_human=True
            )
    
    def _validate_message(self, message: IncomingMessage) -> 'ValidationResult':
        """Валидация входящего сообщения"""
        
        # Проверяем длину
        if len(message.text) < self.config.min_message_length:
            return ValidationResult(
                False, f"Сообщение слишком короткое (минимум {self.config.min_message_length} символов)"
            )
        
        if len(message.text) > self.config.max_message_length:
            return ValidationResult(
                False, f"Сообщение слишком длинное (максимум {self.config.max_message_length} символов)"
            )
        
        # Проверяем что есть текст
        if not message.text.strip():
            return ValidationResult(False, "Пустое сообщение")
        
        # Проверяем обязательные поля
        if not message.user_id or not message.product_id:
            return ValidationResult(False, "Отсутствуют обязательные поля")
        
        return ValidationResult(True, "OK")
    
    def _get_user_context(self, user_id: str) -> UserContext:
        """Получение или создание контекста пользователя"""
        
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = UserContext(
                user_id=user_id,
                message_history=[],
                last_interaction=datetime.now(),
                is_serious_buyer=True
            )
        
        return self.user_contexts[user_id]
    
    def _get_product_context(self, product_id: str) -> ProductContext:
        """Получение или создание контекста товара"""
        
        if product_id not in self.product_contexts:
            # В реальном приложении здесь будет запрос к БД
            self.product_contexts[product_id] = ProductContext(
                title="Товар из объявления",
                description="Подробности в объявлении"
            )
        
        return self.product_contexts[product_id]
    
    def _update_user_context(
        self, 
        user_context: UserContext, 
        message: str, 
        analysis: ConversationAnalysis
    ) -> None:
        """Обновление контекста пользователя"""
        
        # Добавляем сообщение в историю
        user_context.message_history.append(message)
        
        # Ограничиваем историю
        if len(user_context.message_history) > 10:
            user_context.message_history = user_context.message_history[-10:]
        
        # Обновляем время последнего взаимодействия
        user_context.last_interaction = datetime.now()
        
        # Оцениваем серьезность покупателя
        if analysis.message_type == MessageType.SPAM:
            user_context.is_serious_buyer = False
        elif analysis.message_type in [MessageType.MEETING_REQUEST, MessageType.PRICE_QUESTION]:
            user_context.is_serious_buyer = True
    
    def _update_avg_processing_time(self, processing_time: float) -> None:
        """Обновление среднего времени обработки"""
        
        current_avg = self.metrics["avg_processing_time"]
        total_processed = self.metrics["messages_processed"]
        
        self.metrics["avg_processing_time"] = (
            (current_avg * (total_processed - 1) + processing_time) / total_processed
        )
    
    async def start_background_processing(self) -> None:
        """Запуск фоновой обработки очереди сообщений"""
        
        if self.processing_active:
            logger.warning("Фоновая обработка уже запущена")
            return
        
        self.processing_active = True
        logger.info("Запущена фоновая обработка сообщений")
        
        while self.processing_active:
            try:
                # Ждем сообщение из очереди
                message_data = await asyncio.wait_for(
                    self.message_queue.get(), timeout=1.0
                )
                
                # Обрабатываем сообщение
                await self.handle_message(message_data["message"])
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("Ошибка фоновой обработки: %s", e)
    
    def stop_background_processing(self) -> None:
        """Остановка фоновой обработки"""
        
        self.processing_active = False
        logger.info("Фоновая обработка остановлена")
    
    def get_metrics(self) -> Dict:
        """Получение метрик обработчика"""
        
        success_rate = 0.0
        if self.metrics["messages_received"] > 0:
            success_rate = self.metrics["messages_processed"] / self.metrics["messages_received"]
        
        return {
            **self.metrics,
            "success_rate": success_rate,
            "queue_size": self.message_queue.qsize(),
            "user_contexts_count": len(self.user_contexts),
            "product_contexts_count": len(self.product_contexts)
        }
    
    def clear_cache(self) -> None:
        """Очистка кешей контекстов"""
        
        self.user_contexts.clear()
        self.product_contexts.clear()
        self.spam_detector._spam_cache.clear()
        
        logger.info("Кеши обработчика очищены")


class ValidationResult(BaseModel):
    """Результат валидации сообщения"""
    
    is_valid: bool
    error_message: Optional[str] = None


# Фабричная функция
async def create_message_handler(
    config: MessageHandlerConfig,
    ai_consultant: AIConsultant
) -> MessageHandler:
    """
    🏭 Создание настроенного обработчика сообщений
    
    Args:
        config: Конфигурация обработчика
        ai_consultant: ИИ-консультант
        
    Returns:
        MessageHandler: Готовый обработчик
    """
    
    handler = MessageHandler(config, ai_consultant)
    
    logger.info("Обработчик сообщений создан и готов к работе")
    
    return handler