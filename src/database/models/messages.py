"""
💬 Модели сообщений для Avito AI Responder

Этот модуль содержит модели для работы с сообщениями и диалогами:
- Message - модель сообщения
- Conversation - модель диалога/чата
- MessageTemplate - шаблоны сообщений
- MessageAnalytics - аналитика сообщений

Местоположение: src/database/models/messages.py
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, 
    Numeric, ForeignKey, UniqueConstraint, Index, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from .base import BaseModel, AnalyticsMixin, StatusEnum, PriorityEnum


class MessageType(str, Enum):
    """Типы сообщений"""
    
    PRICE_QUESTION = "price_question"
    AVAILABILITY = "availability" 
    PRODUCT_INFO = "product_info"
    MEETING_REQUEST = "meeting_request"
    DELIVERY_QUESTION = "delivery_question"
    GENERAL_QUESTION = "general_question"
    GREETING = "greeting"
    COMPLAINT = "complaint"
    SPAM = "spam"


class MessageStatus(str, Enum):
    """Статусы сообщений"""
    
    RECEIVED = "received"         # Получено
    PROCESSING = "processing"     # Обрабатывается
    RESPONDED = "responded"       # Отвечено
    FAILED = "failed"            # Ошибка обработки
    IGNORED = "ignored"          # Проигнорировано


class MessageDirection(str, Enum):
    """Направление сообщения"""
    
    INCOMING = "incoming"         # Входящее (от покупателя)
    OUTGOING = "outgoing"        # Исходящее (от бота/продавца)


class ConversationStatus(str, Enum):
    """Статусы диалогов"""
    
    ACTIVE = "active"            # Активный диалог
    WAITING = "waiting"          # Ожидает ответа
    COMPLETED = "completed"      # Завершен
    ARCHIVED = "archived"        # Архивирован
    BLOCKED = "blocked"          # Заблокирован


class Message(BaseModel, AnalyticsMixin):
    """
    💬 Модель сообщения
    
    Хранит все сообщения в системе (входящие и исходящие)
    """
    
    __tablename__ = "messages"
    
    # Связи
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID диалога"
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        comment="ID пользователя (для входящих сообщений)"
    )
    
    seller_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sellers.id", ondelete="CASCADE"),
        nullable=True,
        comment="ID продавца (для исходящих сообщений)"
    )
    
    # Основные данные сообщения
    avito_message_id = Column(
        String(100),
        nullable=True,
        comment="ID сообщения в Авито"
    )
    
    direction = Column(
        ENUM(MessageDirection, name="message_direction_enum"),
        nullable=False,
        comment="Направление сообщения"
    )
    
    message_type = Column(
        ENUM(MessageType, name="message_type_enum"),
        nullable=True,
        comment="Тип сообщения (классификация)"
    )
    
    content = Column(
        Text,
        nullable=False,
        comment="Текст сообщения"
    )
    
    original_content = Column(
        Text,
        nullable=True,
        comment="Оригинальный текст (до обработки)"
    )
    
    # Статус и обработка
    status = Column(
        ENUM(MessageStatus, name="message_status_enum"),
        nullable=False,
        default=MessageStatus.RECEIVED,
        comment="Статус обработки сообщения"
    )
    
    priority = Column(
        String(20),
        nullable=False,
        default=PriorityEnum.MEDIUM,
        comment="Приоритет сообщения"
    )
    
    is_automated = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Создано ли автоматически"
    )
    
    is_template_based = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Основано ли на шаблоне"
    )
    
    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("message_templates.id"),
        nullable=True,
        comment="ID использованного шаблона"
    )
    
    # Временные метки
    sent_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время отправки"
    )
    
    delivered_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время доставки"
    )
    
    read_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время прочтения"
    )
    
    # Обработка ИИ
    ai_analysis = Column(
        JSONB,
        nullable=True,
        comment="Результат анализа ИИ"
    )
    
    ai_confidence = Column(
        Numeric(5, 4),
        nullable=True,
        comment="Уверенность ИИ в анализе (0-1)"
    )
    
    processing_time_ms = Column(
        Integer,
        nullable=True,
        comment="Время обработки в миллисекундах"
    )
    
    # Эмоциональный анализ
    sentiment = Column(
        String(20),
        nullable=True,
        comment="Эмоциональная окраска (positive/negative/neutral)"
    )
    
    sentiment_score = Column(
        Numeric(5, 4),
        nullable=True,
        comment="Оценка настроения (-1 до 1)"
    )
    
    urgency_level = Column(
        String(20),
        nullable=True,
        comment="Уровень срочности (low/medium/high)"
    )
    
    # Вложения и медиа
    attachments = Column(
        JSONB,
        nullable=True,
        comment="Информация о вложениях"
    )
    
    has_attachments = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Есть ли вложения"
    )
    
    # Метрики качества
    response_time_seconds = Column(
        Integer,
        nullable=True,
        comment="Время ответа в секундах"
    )
    
    user_satisfaction = Column(
        Integer,
        nullable=True,
        comment="Оценка пользователя (1-5)"
    )
    
    # Связи
    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User", back_populates="messages")
    seller = relationship("Seller")
    template = relationship("MessageTemplate", back_populates="messages")
    
    # Индексы
    __table_args__ = (
        Index("idx_messages_conversation", "conversation_id"),
        Index("idx_messages_status", "status"),
        Index("idx_messages_type", "message_type"),
        Index("idx_messages_direction", "direction"),
        Index("idx_messages_created_at", "created_at"),
        Index("idx_messages_avito_id", "avito_message_id"),
        Index("idx_messages_sentiment", "sentiment"),
    )
    
    @hybrid_property
    def is_incoming(self) -> bool:
        """Входящее ли сообщение"""
        return self.direction == MessageDirection.INCOMING
    
    @hybrid_property
    def is_outgoing(self) -> bool:
        """Исходящее ли сообщение"""
        return self.direction == MessageDirection.OUTGOING
    
    @hybrid_property
    def is_processed(self) -> bool:
        """Обработано ли сообщение"""
        return self.status in [MessageStatus.RESPONDED, MessageStatus.FAILED, MessageStatus.IGNORED]
    
    @hybrid_property
    def word_count(self) -> int:
        """Количество слов в сообщении"""
        return len(self.content.split()) if self.content else 0
    
    def mark_as_sent(self) -> None:
        """Отметить как отправленное"""
        self.sent_at = datetime.now(timezone.utc)
        if self.status == MessageStatus.PROCESSING:
            self.status = MessageStatus.RESPONDED
    
    def mark_as_delivered(self) -> None:
        """Отметить как доставленное"""
        self.delivered_at = datetime.now(timezone.utc)
    
    def mark_as_read(self) -> None:
        """Отметить как прочитанное"""
        self.read_at = datetime.now(timezone.utc)
    
    def set_ai_analysis(self, analysis_data: Dict[str, Any], confidence: float) -> None:
        """
        Установить результаты анализа ИИ
        
        Args:
            analysis_data: Данные анализа
            confidence: Уверенность (0-1)
        """
        self.ai_analysis = analysis_data
        self.ai_confidence = confidence
        
        # Извлекаем основные поля из анализа
        if 'message_type' in analysis_data:
            self.message_type = MessageType(analysis_data['message_type'])
        
        if 'sentiment' in analysis_data:
            self.sentiment = analysis_data['sentiment']
        
        if 'sentiment_score' in analysis_data:
            self.sentiment_score = analysis_data['sentiment_score']
        
        if 'urgency' in analysis_data:
            self.urgency_level = analysis_data['urgency']
    
    @validates('sentiment_score')
    def validate_sentiment_score(self, key: str, score: Optional[float]) -> Optional[float]:
        """Валидация оценки настроения"""
        if score is not None and (score < -1 or score > 1):
            raise ValueError("Оценка настроения должна быть от -1 до 1")
        return score
    
    @validates('user_satisfaction')
    def validate_satisfaction(self, key: str, rating: Optional[int]) -> Optional[int]:
        """Валидация оценки пользователя"""
        if rating is not None and (rating < 1 or rating > 5):
            raise ValueError("Оценка должна быть от 1 до 5")
        return rating


class Conversation(BaseModel, AnalyticsMixin):
    """
    💬 Модель диалога/чата
    
    Представляет диалог между покупателем и продавцом по конкретному товару
    """
    
    __tablename__ = "conversations"
    
    # Связи
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID пользователя (покупателя)"
    )
    
    seller_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sellers.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID продавца"
    )
    
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID товара"
    )
    
    # Идентификаторы Авито
    avito_chat_id = Column(
        String(100),
        nullable=True,
        unique=True,
        comment="ID чата в Авито"
    )
    
    avito_item_id = Column(
        String(100),
        nullable=True,
        comment="ID объявления в Авито"
    )
    
    # Основная информация
    title = Column(
        String(500),
        nullable=True,
        comment="Заголовок диалога"
    )
    
    status = Column(
        ENUM(ConversationStatus, name="conversation_status_enum"),
        nullable=False,
        default=ConversationStatus.ACTIVE,
        comment="Статус диалога"
    )
    
    priority = Column(
        String(20),
        nullable=False,
        default=PriorityEnum.MEDIUM,
        comment="Приоритет диалога"
    )
    
    # Статистика сообщений
    message_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Общее количество сообщений"
    )
    
    incoming_message_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Количество входящих сообщений"
    )
    
    outgoing_message_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Количество исходящих сообщений"
    )
    
    automated_response_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Количество автоответов"
    )
    
    # Временные метки
    first_message_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время первого сообщения"
    )
    
    last_message_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время последнего сообщения"
    )
    
    last_user_message_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время последнего сообщения от пользователя"
    )
    
    last_response_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время последнего ответа"
    )
    
    # Настройки и состояние
    is_ai_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Включен ли ИИ для этого диалога"
    )
    
    is_auto_respond_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Включены ли автоответы"
    )
    
    is_monitored = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Отслеживается ли диалог"
    )
    
    # Результат диалога
    outcome = Column(
        String(50),
        nullable=True,
        comment="Результат диалога (sale/no_sale/pending)"
    )
    
    sale_amount = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Сумма продажи"
    )
    
    conversion_score = Column(
        Numeric(5, 4),
        nullable=True,
        comment="Оценка конверсии (0-1)"
    )
    
    # Качество диалога
    avg_response_time = Column(
        Integer,
        nullable=True,
        comment="Среднее время ответа в секундах"
    )
    
    user_satisfaction_avg = Column(
        Numeric(3, 2),
        nullable=True,
        comment="Средняя оценка пользователя"
    )
    
    ai_effectiveness_score = Column(
        Numeric(5, 4),
        nullable=True,
        comment="Оценка эффективности ИИ"
    )
    
    # Теги и категоризация
    tags = Column(
        JSONB,
        nullable=True,
        comment="Теги диалога"
    )
    
    conversation_summary = Column(
        Text,
        nullable=True,
        comment="Краткое содержание диалога"
    )
    
    # Связи
    user = relationship("User", back_populates="conversations")
    seller = relationship("Seller", back_populates="conversations") 
    product = relationship("Product", back_populates="conversations")
    messages = relationship(
        "Message", 
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
    
    # Индексы
    __table_args__ = (
        Index("idx_conversations_user", "user_id"),
        Index("idx_conversations_seller", "seller_id"),
        Index("idx_conversations_product", "product_id"),
        Index("idx_conversations_status", "status"),
        Index("idx_conversations_avito_chat", "avito_chat_id"),
        Index("idx_conversations_last_message", "last_message_at"),
        Index("idx_conversations_outcome", "outcome"),
        UniqueConstraint("avito_chat_id", name="uq_conversations_avito_chat"),
    )
    
    @hybrid_property
    def is_active(self) -> bool:
        """Активен ли диалог"""
        return self.status == ConversationStatus.ACTIVE
    
    @hybrid_property
    def is_stale(self) -> bool:
        """Устаревший ли диалог (нет активности > 7 дней)"""
        if not self.last_message_at:
            return True
        
        days_since_last_message = (
            datetime.now(timezone.utc) - self.last_message_at
        ).days
        
        return days_since_last_message > 7
    
    @hybrid_property
    def response_rate(self) -> float:
        """Коэффициент ответов"""
        if self.incoming_message_count == 0:
            return 0.0
        return self.outgoing_message_count / self.incoming_message_count
    
    @hybrid_property
    def automation_rate(self) -> float:
        """Коэффициент автоматизации"""
        if self.outgoing_message_count == 0:
            return 0.0
        return self.automated_response_count / self.outgoing_message_count
    
    def add_message(self, message: 'Message') -> None:
        """Добавление сообщения в диалог"""
        
        # Обновляем счетчики
        self.message_count += 1
        
        if message.direction == MessageDirection.INCOMING:
            self.incoming_message_count += 1
            self.last_user_message_at = message.created_at
        else:
            self.outgoing_message_count += 1
            self.last_response_at = message.created_at
            
            if message.is_automated:
                self.automated_response_count += 1
        
        # Обновляем временные метки
        if not self.first_message_at:
            self.first_message_at = message.created_at
        
        self.last_message_at = message.created_at
        
        # Устанавливаем заголовок если его нет
        if not self.title and message.content:
            self.title = message.content[:100] + ("..." if len(message.content) > 100 else "")
    
    def calculate_avg_response_time(self) -> None:
        """Расчет среднего времени ответа"""
        
        # Здесь должна быть логика расчета на основе сообщений
        # Упрощенная версия - можно расширить
        if self.outgoing_message_count > 0:
            # Получаем все исходящие сообщения с временем ответа
            total_response_time = sum(
                msg.response_time_seconds for msg in self.messages
                if msg.response_time_seconds and msg.direction == MessageDirection.OUTGOING
            )
            
            count_with_response_time = len([
                msg for msg in self.messages
                if msg.response_time_seconds and msg.direction == MessageDirection.OUTGOING
            ])
            
            if count_with_response_time > 0:
                self.avg_response_time = total_response_time // count_with_response_time
    
    def archive(self, reason: Optional[str] = None) -> None:
        """Архивирование диалога"""
        self.status = ConversationStatus.ARCHIVED
        
        if reason:
            self.set_metadata("archive_reason", reason)
        
        self.set_metadata("archived_at", datetime.now(timezone.utc).isoformat())
    
    def mark_as_sale(self, amount: Optional[float] = None) -> None:
        """Отметить как продажу"""
        self.outcome = "sale"
        self.sale_amount = amount
        self.conversion_score = 1.0
        
        # Обновляем статистику продавца
        if self.seller:
            self.seller.total_sales += 1
    
    def block(self, reason: str) -> None:
        """Блокировка диалога"""
        self.status = ConversationStatus.BLOCKED
        self.is_ai_enabled = False
        self.is_auto_respond_enabled = False
        
        self.set_metadata("block_reason", reason)
        self.set_metadata("blocked_at", datetime.now(timezone.utc).isoformat())


class MessageTemplate(BaseModel):
    """
    📝 Шаблон сообщения
    
    Готовые шаблоны ответов для разных ситуаций
    """
    
    __tablename__ = "message_templates"
    
    # Связь с продавцом
    seller_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sellers.id", ondelete="CASCADE"),
        nullable=True,
        comment="ID продавца (NULL для системных шаблонов)"
    )
    
    # Основная информация
    name = Column(
        String(200),
        nullable=False,
        comment="Название шаблона"
    )
    
    description = Column(
        Text,
        nullable=True,
        comment="Описание шаблона"
    )
    
    template_text = Column(
        Text,
        nullable=False,
        comment="Текст шаблона с переменными"
    )
    
    # Категоризация
    message_type = Column(
        ENUM(MessageType, name="template_message_type_enum"),
        nullable=False,
        comment="Тип сообщения для шаблона"
    )
    
    category = Column(
        String(100),
        nullable=True,
        comment="Категория шаблона"
    )
    
    # Настройки использования
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Активен ли шаблон"
    )
    
    is_system = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Системный ли шаблон"
    )
    
    priority = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Приоритет использования"
    )
    
    # Статистика использования
    usage_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Количество использований"
    )
    
    success_rate = Column(
        Numeric(5, 4),
        nullable=True,
        comment="Коэффициент успешности"
    )
    
    avg_user_rating = Column(
        Numeric(3, 2),
        nullable=True,
        comment="Средняя оценка пользователей"
    )
    
    last_used_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время последнего использования"
    )
    
    # Переменные шаблона
    template_variables = Column(
        JSONB,
        nullable=True,
        comment="Список переменных в шаблоне"
    )
    
    # Условия применения
    conditions = Column(
        JSONB,
        nullable=True,
        comment="Условия применения шаблона"
    )
    
    # Связи
    seller = relationship("Seller")
    messages = relationship("Message", back_populates="template")
    
    # Индексы
    __table_args__ = (
        Index("idx_templates_seller", "seller_id"),
        Index("idx_templates_type", "message_type"),
        Index("idx_templates_active", "is_active"),
        Index("idx_templates_system", "is_system"),
        Index("idx_templates_usage", "usage_count"),
    )
    
    def increment_usage(self) -> None:
        """Увеличение счетчика использования"""
        self.usage_count += 1
        self.last_used_at = datetime.now(timezone.utc)
    
    def update_success_rate(self, success: bool) -> None:
        """Обновление коэффициента успешности"""
        
        # Простой расчет скользящего среднего
        if self.success_rate is None:
            self.success_rate = 1.0 if success else 0.0
        else:
            # Вес новых данных
            weight = 0.1
            new_value = 1.0 if success else 0.0
            self.success_rate = (1 - weight) * self.success_rate + weight * new_value
    
    def format_template(self, variables: Dict[str, Any]) -> str:
        """
        Форматирование шаблона с переменными
        
        Args:
            variables: Словарь переменных
            
        Returns:
            str: Отформатированный текст
        """
        
        try:
            return self.template_text.format(**variables)
        except KeyError as e:
            raise ValueError(f"Отсутствует переменная для шаблона: {e}")
        except Exception as e:
            raise ValueError(f"Ошибка форматирования шаблона: {e}")


# Экспорт
__all__ = [
    # Енумы
    "MessageType",
    "MessageStatus", 
    "MessageDirection",
    "ConversationStatus",
    
    # Модели
    "Message",
    "Conversation",
    "MessageTemplate"
]