"""
Pydantic схемы для пользователей и продавцов.

Определяет модели данных для управления профилями, настройками
и обновления информации пользователей.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from uuid import UUID

from .base import BaseResponse


# ============================================================================
# СХЕМЫ ДЛЯ ОБНОВЛЕНИЯ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================================

class UserUpdate(BaseModel):
    """Схема обновления данных покупателя."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    
    @validator('phone')
    def validate_phone(cls, v):
        """Валидация номера телефона."""
        if v and not v.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit():
            raise ValueError('Некорректный формат номера телефона')
        return v

    class Config:
        schema_extra = {
            "example": {
                "first_name": "Иван",
                "last_name": "Петров",
                "phone": "+7-900-123-45-67",
                "email": "newemail@example.com"
            }
        }


class SellerUpdate(BaseModel):
    """Схема обновления данных продавца."""
    company_name: Optional[str] = Field(None, min_length=1, max_length=200)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    
    @validator('phone')
    def validate_phone(cls, v):
        """Валидация номера телефона."""
        if v and not v.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit():
            raise ValueError('Некорректный формат номера телефона')
        return v

    class Config:
        schema_extra = {
            "example": {
                "company_name": "ООО Новая торговая компания",
                "contact_person": "Петр Сидоров",
                "phone": "+7-495-123-45-67",
                "email": "newseller@company.com"
            }
        }


# ============================================================================
# СХЕМЫ ДЛЯ РАСШИРЕННЫХ ПРОФИЛЕЙ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================================

class UserProfileResponse(BaseResponse):
    """Схема ответа с расширенным профилем покупателя."""
    id: UUID
    user_id: UUID
    preferences: Dict[str, Any]
    behavioral_data: Dict[str, Any]
    communication_style: str
    preferred_contact_time: Optional[str] = None
    interests: List[str]
    purchase_history: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174010",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "preferences": {
                    "language": "ru",
                    "notifications": True,
                    "email_frequency": "daily"
                },
                "behavioral_data": {
                    "avg_response_time": 1800,
                    "preferred_categories": ["electronics", "clothing"],
                    "price_sensitivity": "medium"
                },
                "communication_style": "formal",
                "preferred_contact_time": "09:00-18:00",
                "interests": ["smartphones", "laptops", "gaming"],
                "purchase_history": {
                    "total_purchases": 15,
                    "avg_purchase_value": 25000,
                    "last_purchase_date": "2025-01-01T10:00:00Z"
                },
                "created_at": "2025-01-01T10:00:00Z",
                "updated_at": "2025-01-06T12:00:00Z"
            }
        }


class UserProfileUpdate(BaseModel):
    """Схема обновления расширенного профиля покупателя."""
    preferences: Optional[Dict[str, Any]] = None
    communication_style: Optional[str] = Field(None, regex="^(formal|casual|friendly)$")
    preferred_contact_time: Optional[str] = None
    interests: Optional[List[str]] = None
    
    @validator('interests')
    def validate_interests(cls, v):
        """Валидация списка интересов."""
        if v and len(v) > 20:
            raise ValueError('Максимум 20 интересов')
        if v and any(len(interest) > 50 for interest in v):
            raise ValueError('Каждый интерес не должен превышать 50 символов')
        return v

    class Config:
        schema_extra = {
            "example": {
                "preferences": {
                    "language": "ru",
                    "notifications": True,
                    "email_frequency": "weekly"
                },
                "communication_style": "friendly",
                "preferred_contact_time": "10:00-19:00",
                "interests": ["smartphones", "laptops", "gaming", "photography"]
            }
        }


# ============================================================================
# СХЕМЫ ДЛЯ НАСТРОЕК ПРОДАВЦОВ
# ============================================================================

class SellerSettingsResponse(BaseResponse):
    """Схема ответа с настройками продавца."""
    id: UUID
    seller_id: UUID
    auto_reply_enabled: bool
    auto_reply_delay_min: int
    auto_reply_delay_max: int
    ai_enabled: bool
    ai_creativity: float
    ai_formality: float
    ai_response_length: str
    working_hours_start: Optional[str] = None
    working_hours_end: Optional[str] = None
    weekend_auto_reply: bool
    response_templates: Dict[str, str]
    integration_settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174020",
                "seller_id": "123e4567-e89b-12d3-a456-426614174001",
                "auto_reply_enabled": True,
                "auto_reply_delay_min": 5,
                "auto_reply_delay_max": 30,
                "ai_enabled": True,
                "ai_creativity": 0.7,
                "ai_formality": 0.8,
                "ai_response_length": "medium",
                "working_hours_start": "09:00",
                "working_hours_end": "18:00",
                "weekend_auto_reply": False,
                "response_templates": {
                    "greeting": "Здравствуйте! Спасибо за интерес к нашему товару.",
                    "price_inquiry": "Цена актуальна, дополнительные скидки возможны при покупке нескольких товаров."
                },
                "integration_settings": {
                    "avito_api_enabled": True,
                    "sync_frequency": "realtime"
                },
                "created_at": "2025-01-01T10:00:00Z",
                "updated_at": "2025-01-06T12:00:00Z"
            }
        }


class SellerSettingsUpdate(BaseModel):
    """Схема обновления настроек продавца."""
    auto_reply_enabled: Optional[bool] = None
    auto_reply_delay_min: Optional[int] = Field(None, ge=1, le=300)
    auto_reply_delay_max: Optional[int] = Field(None, ge=1, le=300)
    ai_enabled: Optional[bool] = None
    ai_creativity: Optional[float] = Field(None, ge=0.0, le=1.0)
    ai_formality: Optional[float] = Field(None, ge=0.0, le=1.0)
    ai_response_length: Optional[str] = Field(None, regex="^(short|medium|long)$")
    working_hours_start: Optional[str] = Field(None, regex="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    working_hours_end: Optional[str] = Field(None, regex="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    weekend_auto_reply: Optional[bool] = None
    response_templates: Optional[Dict[str, str]] = None
    integration_settings: Optional[Dict[str, Any]] = None
    
    @validator('auto_reply_delay_max')
    def validate_delay_max(cls, v, values):
        """Валидация максимальной задержки автоответа."""
        if v is not None and 'auto_reply_delay_min' in values and values['auto_reply_delay_min'] is not None:
            if v < values['auto_reply_delay_min']:
                raise ValueError('Максимальная задержка должна быть больше минимальной')
        return v

    class Config:
        schema_extra = {
            "example": {
                "auto_reply_enabled": True,
                "auto_reply_delay_min": 10,
                "auto_reply_delay_max": 60,
                "ai_enabled": True,
                "ai_creativity": 0.8,
                "ai_formality": 0.7,
                "ai_response_length": "medium",
                "working_hours_start": "09:00",
                "working_hours_end": "18:00",
                "weekend_auto_reply": False,
                "response_templates": {
                    "greeting": "Добро пожаловать! Рады помочь с выбором.",
                    "price_inquiry": "Цена указана актуальная. Возможен торг при быстрой сделке."
                },
                "integration_settings": {
                    "avito_api_enabled": True,
                    "sync_frequency": "realtime",
                    "auto_publish": False
                }
            }
        }


# ============================================================================
# СХЕМЫ ДЛЯ СТАТИСТИКИ И АНАЛИТИКИ
# ============================================================================

class UserActivityResponse(BaseResponse):
    """Схема ответа с активностью пользователя."""
    user_id: UUID
    total_messages: int
    total_conversations: int
    avg_response_time: float
    last_activity: Optional[datetime] = None
    most_active_hours: List[int]
    behavioral_metrics: Dict[str, Any]
    engagement_score: float
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "total_messages": 156,
                "total_conversations": 23,
                "avg_response_time": 3600.5,
                "last_activity": "2025-01-06T15:30:00Z",
                "most_active_hours": [10, 11, 14, 15, 18, 19],
                "behavioral_metrics": {
                    "avg_session_duration": 1200,
                    "bounce_rate": 0.15,
                    "conversion_rate": 0.08
                },
                "engagement_score": 7.5
            }
        }


class SellerStatsResponse(BaseResponse):
    """Схема ответа со статистикой продавца."""
    seller_id: UUID
    total_messages: int
    ai_generated_messages: int
    total_conversations: int
    active_conversations: int
    conversion_rate: float
    avg_response_time: float
    customer_satisfaction: float
    monthly_stats: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    
    class Config:
        schema_extra = {
            "example": {
                "seller_id": "123e4567-e89b-12d3-a456-426614174001",
                "total_messages": 2847,
                "ai_generated_messages": 1923,
                "total_conversations": 312,
                "active_conversations": 45,
                "conversion_rate": 0.18,
                "avg_response_time": 127.5,
                "customer_satisfaction": 4.3,
                "monthly_stats": {
                    "messages_this_month": 428,
                    "conversations_this_month": 67,
                    "conversions_this_month": 12
                },
                "performance_metrics": {
                    "ai_accuracy": 0.92,
                    "response_rate": 0.98,
                    "customer_retention": 0.76
                }
            }
        }


# ============================================================================
# ПЕРЕЭКСПОРТ СХЕМ ИЗ AUTH
# ============================================================================

from .auth import UserResponse, SellerResponse