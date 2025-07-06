"""
Pydantic схемы для сообщений, диалогов и шаблонов.

Определяет модели данных для работы с сообщениями,
ИИ-анализом и автоматическими ответами.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from datetime import datetime
from uuid import UUID
from enum import Enum

from .base import BaseResponse


# ============================================================================
# ЕНУМЫ ДЛЯ ТИПОВ И СТАТУСОВ
# ============================================================================

class MessageType(str, Enum):
    """Типы сообщений."""
    text = "text"
    image = "image"
    voice = "voice"
    automated_reply = "automated_reply"
    template = "template"


class MessageStatus(str, Enum):
    """Статусы сообщений."""
    sent = "sent"
    delivered = "delivered"
    read = "read"
    failed = "failed"


class ConversationStatus(str, Enum):
    """Статусы диалогов."""
    active = "active"
    closed = "closed"
    archived = "archived"
    blocked = "blocked"


class TemplateCategory(str, Enum):
    """Категории шаблонов."""
    greeting = "greeting"
    price_inquiry = "price_inquiry"
    availability = "availability"
    delivery = "delivery"
    payment = "payment"
    closing = "closing"
    custom = "custom"


# ============================================================================
# СХЕМЫ ДЛЯ СОЗДАНИЯ И ОБНОВЛЕНИЯ СООБЩЕНИЙ
# ============================================================================

class MessageCreate(BaseModel):
    """Схема создания сообщения."""
    conversation_id: UUID = Field(..., description="ID диалога")
    sender_id: UUID = Field(..., description="ID отправителя")
    recipient_id: UUID = Field(..., description="ID получателя")
    content: str = Field(..., min_length=1, max_length=4000, description="Текст сообщения")
    message_type: MessageType = Field(default=MessageType.text, description="Тип сообщения")
    is_ai_generated: bool = Field(default=False, description="Сгенерировано ли ИИ")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Дополнительные метаданные")
    
    @validator('content')
    def validate_content(cls, v):
        """Валидация содержимого сообщения."""
        if not v.strip():
            raise ValueError('Сообщение не может быть пустым')
        return v.strip()

    class Config:
        schema_extra = {
            "example": {
                "conversation_id": "123e4567-e89b-12d3-a456-426614174030",
                "sender_id": "123e4567-e89b-12d3-a456-426614174000",
                "recipient_id": "123e4567-e89b-12d3-a456-426614174001",
                "content": "Здравствуйте! Интересует ваш товар, возможна ли скидка?",
                "message_type": "text",
                "is_ai_generated": False,
                "metadata": {
                    "source": "avito_chat",
                    "device": "mobile"
                }
            }
        }


class MessageUpdate(BaseModel):
    """Схема обновления сообщения."""
    content: Optional[str] = Field(None, min_length=1, max_length=4000)
    status: Optional[MessageStatus] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('content')
    def validate_content(cls, v):
        """Валидация содержимого сообщения."""
        if v is not None and not v.strip():
            raise ValueError('Сообщение не может быть пустым')
        return v.strip() if v else v

    class Config:
        schema_extra = {
            "example": {
                "content": "Здравствуйте! Интересует ваш товар, возможна ли скидка при покупке двух штук?",
                "status": "read",
                "metadata": {
                    "edited": True,
                    "edit_reason": "clarification"
                }
            }
        }


# ============================================================================
# СХЕМЫ ДЛЯ ОТВЕТОВ СООБЩЕНИЙ
# ============================================================================

class MessageResponse(BaseResponse):
    """Схема ответа с данными сообщения."""
    id: UUID
    conversation_id: UUID
    sender_id: UUID
    recipient_id: UUID
    content: str
    message_type: MessageType
    status: MessageStatus
    is_ai_generated: bool
    response_time_ms: Optional[int] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174040",
                "conversation_id": "123e4567-e89b-12d3-a456-426614174030",
                "sender_id": "123e4567-e89b-12d3-a456-426614174000",
                "recipient_id": "123e4567-e89b-12d3-a456-426614174001",
                "content": "Здравствуйте! Интересует ваш товар, возможна ли скидка?",
                "message_type": "text",
                "status": "delivered",
                "is_ai_generated": False,
                "response_time_ms": 1250,
                "ai_analysis": {
                    "sentiment": "positive",
                    "intent": "price_inquiry", 
                    "urgency": "medium",
                    "keywords": ["товар", "скидка"]
                },
                "metadata": {
                    "source": "avito_chat",
                    "device": "mobile"
                },
                "created_at": "2025-01-06T12:30:00Z",
                "updated_at": "2025-01-06T12:30:15Z"
            }
        }


# ============================================================================
# СХЕМЫ ДЛЯ ДИАЛОГОВ
# ============================================================================

class ConversationCreate(BaseModel):
    """Схема создания диалога."""
    user_id: UUID = Field(..., description="ID покупателя")
    seller_id: UUID = Field(..., description="ID продавца")
    item_id: Optional[str] = Field(None, description="ID товара в Авито")
    title: Optional[str] = Field(None, max_length=200, description="Заголовок диалога")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Метаданные диалога")

    class Config:
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "seller_id": "123e4567-e89b-12d3-a456-426614174001",
                "item_id": "2742847569",
                "title": "Обсуждение iPhone 15 Pro",
                "metadata": {
                    "item_category": "electronics",
                    "item_price": 95000
                }
            }
        }


class ConversationUpdate(BaseModel):
    """Схема обновления диалога."""
    status: Optional[ConversationStatus] = None
    title: Optional[str] = Field(None, max_length=200)
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        schema_extra = {
            "example": {
                "status": "closed",
                "title": "Продажа iPhone 15 Pro - завершено",
                "metadata": {
                    "closure_reason": "deal_completed",
                    "final_price": 90000
                }
            }
        }


class ConversationResponse(BaseResponse):
    """Схема ответа с данными диалога."""
    id: UUID
    user_id: UUID
    seller_id: UUID
    item_id: Optional[str] = None
    title: Optional[str] = None
    status: ConversationStatus
    message_count: int
    last_message_at: Optional[datetime] = None
    conversion_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    messages: Optional[List[MessageResponse]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174030",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "seller_id": "123e4567-e89b-12d3-a456-426614174001",
                "item_id": "2742847569",
                "title": "Обсуждение iPhone 15 Pro",
                "status": "active",
                "message_count": 8,
                "last_message_at": "2025-01-06T12:30:00Z",
                "conversion_score": 0.75,
                "metadata": {
                    "item_category": "electronics",
                    "item_price": 95000
                },
                "messages": [],
                "created_at": "2025-01-06T10:00:00Z",
                "updated_at": "2025-01-06T12:30:00Z"
            }
        }


# ============================================================================
# СХЕМЫ ДЛЯ АВТООТВЕТЧИКА И ИИ
# ============================================================================

class AutoReplyRequest(BaseModel):
    """Схема запроса автоматического ответа."""
    message_id: UUID = Field(..., description="ID сообщения для ответа")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Дополнительный контекст")
    template_id: Optional[UUID] = Field(None, description="ID шаблона для использования")
    
    class Config:
        schema_extra = {
            "example": {
                "message_id": "123e4567-e89b-12d3-a456-426614174040",
                "context": {
                    "item_price": 95000,
                    "item_condition": "новый",
                    "delivery_available": True
                },
                "template_id": "123e4567-e89b-12d3-a456-426614174050"
            }
        }


class AIAnalysisResponse(BaseResponse):
    """Схема ответа с ИИ-анализом сообщения."""
    message_id: UUID
    sentiment: str = Field(..., description="Тональность: positive, negative, neutral")
    intent: str = Field(..., description="Намерение: price_inquiry, availability, etc.")
    urgency: str = Field(..., description="Срочность: low, medium, high")
    keywords: List[str] = Field(..., description="Ключевые слова")
    suggested_response: Optional[str] = Field(None, description="Предлагаемый ответ")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Уверенность анализа")
    analysis_details: Dict[str, Any] = Field(..., description="Детали анализа")
    
    class Config:
        schema_extra = {
            "example": {
                "message_id": "123e4567-e89b-12d3-a456-426614174040",
                "sentiment": "positive",
                "intent": "price_inquiry",
                "urgency": "medium",
                "keywords": ["товар", "скидка", "цена"],
                "suggested_response": "Здравствуйте! Спасибо за интерес. Скидка возможна при покупке от 2 штук.",
                "confidence_score": 0.89,
                "analysis_details": {
                    "language": "ru",
                    "formality": "informal",
                    "emotion_scores": {
                        "joy": 0.3,
                        "curiosity": 0.7,
                        "concern": 0.1
                    }
                }
            }
        }


# ============================================================================
# СХЕМЫ ДЛЯ ШАБЛОНОВ СООБЩЕНИЙ
# ============================================================================

class MessageTemplateCreate(BaseModel):
    """Схема создания шаблона сообщения."""
    seller_id: Optional[UUID] = Field(None, description="ID продавца (заполняется автоматически)")
    name: str = Field(..., min_length=1, max_length=100, description="Название шаблона")
    content: str = Field(..., min_length=1, max_length=4000, description="Содержимое шаблона")
    category: TemplateCategory = Field(..., description="Категория шаблона")
    variables: Optional[List[str]] = Field(default=None, description="Переменные в шаблоне")
    conditions: Optional[Dict[str, Any]] = Field(default=None, description="Условия применения")
    
    @validator('variables')
    def validate_variables(cls, v):
        """Валидация переменных шаблона."""
        if v and len(v) > 10:
            raise ValueError('Максимум 10 переменных в шаблоне')
        return v

    class Config:
        schema_extra = {
            "example": {
                "name": "Приветствие с ценой",
                "content": "Здравствуйте! Товар {item_name} доступен по цене {price} руб. Готовы ответить на ваши вопросы!",
                "category": "greeting",
                "variables": ["item_name", "price"],
                "conditions": {
                    "time_of_day": ["morning", "afternoon"],
                    "first_message": True
                }
            }
        }


class MessageTemplateUpdate(BaseModel):
    """Схема обновления шаблона сообщения."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    content: Optional[str] = Field(None, min_length=1, max_length=4000)
    category: Optional[TemplateCategory] = None
    variables: Optional[List[str]] = None
    conditions: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    
    @validator('variables')
    def validate_variables(cls, v):
        """Валидация переменных шаблона."""
        if v and len(v) > 10:
            raise ValueError('Максимум 10 переменных в шаблоне')
        return v

    class Config:
        schema_extra = {
            "example": {
                "name": "Приветствие с ценой и скидкой",
                "content": "Здравствуйте! Товар {item_name} по цене {price} руб. При быстрой покупке скидка {discount}%!",
                "variables": ["item_name", "price", "discount"],
                "is_active": True
            }
        }


class MessageTemplateResponse(BaseResponse):
    """Схема ответа с данными шаблона сообщения."""
    id: UUID
    seller_id: UUID
    name: str
    content: str
    category: TemplateCategory
    variables: Optional[List[str]] = None
    conditions: Optional[Dict[str, Any]] = None
    is_active: bool
    usage_count: int
    success_rate: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174050",
                "seller_id": "123e4567-e89b-12d3-a456-426614174001",
                "name": "Приветствие с ценой",
                "content": "Здравствуйте! Товар {item_name} доступен по цене {price} руб. Готовы ответить на ваши вопросы!",
                "category": "greeting",
                "variables": ["item_name", "price"],
                "conditions": {
                    "time_of_day": ["morning", "afternoon"],
                    "first_message": True
                },
                "is_active": True,
                "usage_count": 47,
                "success_rate": 0.83,
                "created_at": "2025-01-01T10:00:00Z",
                "updated_at": "2025-01-06T12:00:00Z"
            }
        }