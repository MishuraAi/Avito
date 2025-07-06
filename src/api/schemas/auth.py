"""
Pydantic схемы для аутентификации.

Определяет модели данных для регистрации, входа в систему,
токенов и ответов аутентификации.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from uuid import UUID

from .base import BaseResponse


# ============================================================================
# СХЕМЫ ДЛЯ ТОКЕНОВ
# ============================================================================

class Token(BaseModel):
    """Схема JWT токена."""
    access_token: str
    token_type: str = "bearer"
    user_type: str = Field(..., description="Тип пользователя: user или seller")
    expires_in: int = Field(..., description="Время жизни токена в секундах")


class TokenData(BaseModel):
    """Данные из JWT токена."""
    user_id: Optional[UUID] = None
    user_type: Optional[str] = None


# ============================================================================
# СХЕМЫ ДЛЯ РЕГИСТРАЦИИ
# ============================================================================

class UserRegister(BaseModel):
    """Схема регистрации покупателя."""
    email: EmailStr = Field(..., description="Email адрес")
    password: str = Field(..., min_length=8, max_length=128, description="Пароль")
    avito_user_id: str = Field(..., min_length=1, max_length=100, description="ID пользователя в Авито")
    first_name: str = Field(..., min_length=1, max_length=100, description="Имя")
    last_name: Optional[str] = Field(None, max_length=100, description="Фамилия")
    phone: Optional[str] = Field(None, max_length=20, description="Номер телефона")
    
    @validator('password')
    def validate_password(cls, v):
        """Валидация пароля."""
        if len(v) < 8:
            raise ValueError('Пароль должен содержать минимум 8 символов')
        if not any(c.isupper() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not any(c.islower() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну строчную букву')
        if not any(c.isdigit() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        """Валидация номера телефона."""
        if v and not v.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit():
            raise ValueError('Некорректный формат номера телефона')
        return v

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123",
                "avito_user_id": "12345678",
                "first_name": "Иван",
                "last_name": "Петров",
                "phone": "+7-900-123-45-67"
            }
        }


class SellerRegister(BaseModel):
    """Схема регистрации продавца."""
    email: EmailStr = Field(..., description="Email адрес")
    password: str = Field(..., min_length=8, max_length=128, description="Пароль")
    avito_user_id: str = Field(..., min_length=1, max_length=100, description="ID продавца в Авито")
    company_name: str = Field(..., min_length=1, max_length=200, description="Название компании")
    contact_person: Optional[str] = Field(None, max_length=100, description="Контактное лицо")
    phone: Optional[str] = Field(None, max_length=20, description="Номер телефона")
    subscription_plan: str = Field(
        default="basic", 
        regex="^(basic|pro|enterprise)$",
        description="Тарифный план"
    )
    
    @validator('password')
    def validate_password(cls, v):
        """Валидация пароля."""
        if len(v) < 8:
            raise ValueError('Пароль должен содержать минимум 8 символов')
        if not any(c.isupper() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not any(c.islower() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну строчную букву')
        if not any(c.isdigit() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        return v

    class Config:
        schema_extra = {
            "example": {
                "email": "seller@company.com",
                "password": "SecurePass123",
                "avito_user_id": "87654321",
                "company_name": "ООО Торговая компания",
                "contact_person": "Петр Сидоров",
                "phone": "+7-495-123-45-67",
                "subscription_plan": "pro"
            }
        }


# ============================================================================
# СХЕМЫ ДЛЯ ОТВЕТОВ
# ============================================================================

class UserResponse(BaseResponse):
    """Схема ответа с данными покупателя."""
    id: UUID
    email: EmailStr
    avito_user_id: str
    first_name: str
    last_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    reputation_score: float
    total_messages: int
    last_activity: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "avito_user_id": "12345678",
                "first_name": "Иван",
                "last_name": "Петров", 
                "phone": "+7-900-123-45-67",
                "is_active": True,
                "reputation_score": 4.5,
                "total_messages": 42,
                "last_activity": "2025-01-06T12:00:00Z",
                "created_at": "2025-01-01T10:00:00Z",
                "updated_at": "2025-01-06T12:00:00Z"
            }
        }


class SellerResponse(BaseResponse):
    """Схема ответа с данными продавца."""
    id: UUID
    email: EmailStr
    avito_user_id: str
    company_name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    subscription_plan: str
    subscription_expires: Optional[datetime] = None
    monthly_message_limit: int
    monthly_messages_used: int
    auto_reply_enabled: bool
    ai_enabled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "email": "seller@company.com",
                "avito_user_id": "87654321",
                "company_name": "ООО Торговая компания",
                "contact_person": "Петр Сидоров",
                "phone": "+7-495-123-45-67",
                "is_active": True,
                "subscription_plan": "pro",
                "subscription_expires": "2025-12-31T23:59:59Z",
                "monthly_message_limit": 10000,
                "monthly_messages_used": 2500,
                "auto_reply_enabled": True,
                "ai_enabled": True,
                "created_at": "2025-01-01T10:00:00Z",
                "updated_at": "2025-01-06T12:00:00Z"
            }
        }


# ============================================================================
# СХЕМЫ ДЛЯ ВХОДА В СИСТЕМУ
# ============================================================================

class LoginRequest(BaseModel):
    """Схема запроса входа в систему."""
    email: EmailStr = Field(..., description="Email адрес")
    password: str = Field(..., description="Пароль")
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123"
            }
        }


class LoginResponse(BaseModel):
    """Схема ответа при успешном входе."""
    access_token: str
    token_type: str = "bearer"
    user_type: str
    expires_in: int
    user_info: UserResponse | SellerResponse
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user_type": "seller",
                "expires_in": 3600,
                "user_info": {
                    "id": "123e4567-e89b-12d3-a456-426614174001",
                    "email": "seller@company.com",
                    "company_name": "ООО Торговая компания"
                }
            }
        }


# ============================================================================
# СХЕМЫ ДЛЯ СБРОСА ПАРОЛЯ
# ============================================================================

class PasswordResetRequest(BaseModel):
    """Схема запроса сброса пароля."""
    email: EmailStr = Field(..., description="Email адрес для сброса пароля")
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class PasswordResetConfirm(BaseModel):
    """Схема подтверждения сброса пароля."""
    token: str = Field(..., description="Токен сброса пароля")
    new_password: str = Field(..., min_length=8, max_length=128, description="Новый пароль")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Валидация нового пароля."""
        if len(v) < 8:
            raise ValueError('Пароль должен содержать минимум 8 символов')
        if not any(c.isupper() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not any(c.islower() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну строчную букву')
        if not any(c.isdigit() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "token": "reset_token_here",
                "new_password": "NewSecurePass123"
            }
        }


# ============================================================================
# СХЕМЫ ДЛЯ ПОДТВЕРЖДЕНИЯ EMAIL
# ============================================================================

class EmailVerificationRequest(BaseModel):
    """Схема запроса подтверждения email."""
    token: str = Field(..., description="Токен подтверждения email")
    
    class Config:
        schema_extra = {
            "example": {
                "token": "verification_token_here"
            }
        }