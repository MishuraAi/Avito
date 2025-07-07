"""
📋 Базовые Pydantic схемы для API

Этот модуль содержит базовые схемы и миксины:
- BaseSchema - базовая схема для всех моделей
- PaginatedResponse - схема для пагинированных ответов  
- ErrorResponse - схема для ошибок
- SuccessResponse - схема для успешных ответов
- Общие валидаторы и утилиты

Местоположение: src/api/schemas/base.py
"""

import uuid
from datetime import datetime
from typing import Generic, TypeVar, Optional, List, Dict, Any, Union

from pydantic import BaseModel, Field, validator, root_validator
from pydantic.generics import GenericModel


# TypeVar для Generic схем
T = TypeVar('T')


class BaseSchema(BaseModel):
    """
    📋 Базовая схема для всех API моделей
    
    Включает общие поля и настройки
    """
    
    class Config:
        # Разрешить ORM модели
        orm_mode = True
        
        # Использовать enum значения
        use_enum_values = True
        
        # Валидация при присваивании
        validate_assignment = True
        
        # Разрешить изменение полей
        allow_mutation = True
        
        # Сериализация datetime в ISO формат
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            uuid.UUID: lambda v: str(v) if v else None
        }
        
        # Пример схемы для документации
        schema_extra = {
            "example": {}
        }


class TimestampSchema(BaseSchema):
    """
    🕒 Миксин для схем с временными метками
    """
    
    created_at: datetime = Field(..., description="Время создания записи")
    updated_at: datetime = Field(..., description="Время последнего обновления")
    
    class Config:
        schema_extra = {
            "example": {
                "created_at": "2025-01-06T12:00:00Z",
                "updated_at": "2025-01-06T12:30:00Z"
            }
        }


class UUIDSchema(BaseSchema):
    """
    🆔 Миксин для схем с UUID идентификатором
    """
    
    id: uuid.UUID = Field(..., description="Уникальный идентификатор")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }


class SoftDeleteSchema(BaseSchema):
    """
    🗑️ Миксин для схем с мягким удалением
    """
    
    is_deleted: bool = Field(False, description="Флаг мягкого удаления")
    deleted_at: Optional[datetime] = Field(None, description="Время удаления")


class MetadataSchema(BaseSchema):
    """
    📊 Миксин для схем с метаданными
    """
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Дополнительные метаданные")
    version: int = Field(1, description="Версия записи")


class PaginationParams(BaseSchema):
    """
    📄 Параметры пагинации
    """
    
    skip: int = Field(0, ge=0, description="Количество записей для пропуска")
    limit: int = Field(100, ge=1, le=1000, description="Максимальное количество записей")
    
    class Config:
        schema_extra = {
            "example": {
                "skip": 0,
                "limit": 20
            }
        }


class SortParams(BaseSchema):
    """
    🔄 Параметры сортировки
    """
    
    sort_by: Optional[str] = Field(None, description="Поле для сортировки")
    sort_order: Optional[str] = Field("asc", pattern="^(asc|desc)$", description="Направление сортировки")
    
    class Config:
        schema_extra = {
            "example": {
                "sort_by": "created_at",
                "sort_order": "desc"
            }
        }


class FilterParams(BaseSchema):
    """
    🔍 Параметры фильтрации
    """
    
    search: Optional[str] = Field(None, description="Поисковый запрос")
    filters: Optional[Dict[str, Any]] = Field(None, description="Дополнительные фильтры")
    
    class Config:
        schema_extra = {
            "example": {
                "search": "текст для поиска",
                "filters": {
                    "status": "active",
                    "created_after": "2025-01-01T00:00:00Z"
                }
            }
        }


class PaginatedResponse(GenericModel, Generic[T]):
    """
    📄 Схема пагинированного ответа
    """
    
    items: List[T] = Field(..., description="Список элементов")
    total: int = Field(..., ge=0, description="Общее количество элементов")
    skip: int = Field(..., ge=0, description="Количество пропущенных элементов")
    limit: int = Field(..., ge=1, description="Лимит элементов на страницу")
    has_next: bool = Field(..., description="Есть ли следующая страница")
    has_prev: bool = Field(..., description="Есть ли предыдущая страница")
    
    class Config:
        schema_extra = {
            "example": {
                "items": [],
                "total": 150,
                "skip": 0,
                "limit": 20,
                "has_next": True,
                "has_prev": False
            }
        }


class SuccessResponse(BaseSchema):
    """
    ✅ Схема успешного ответа
    """
    
    success: bool = Field(True, description="Флаг успешности")
    message: str = Field(..., description="Сообщение об успехе")
    data: Optional[Dict[str, Any]] = Field(None, description="Дополнительные данные")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Операция выполнена успешно",
                "data": {"id": "123e4567-e89b-12d3-a456-426614174000"}
            }
        }


class ErrorResponse(BaseSchema):
    """
    ❌ Схема ответа с ошибкой
    """
    
    error: bool = Field(True, description="Флаг ошибки")
    status_code: int = Field(..., description="HTTP код ошибки")
    message: str = Field(..., description="Сообщение об ошибке")
    details: Optional[Dict[str, Any]] = Field(None, description="Детали ошибки")
    path: Optional[str] = Field(None, description="Путь запроса")
    timestamp: float = Field(..., description="Временная метка ошибки")
    
    class Config:
        schema_extra = {
            "example": {
                "error": True,
                "status_code": 400,
                "message": "Некорректные данные запроса",
                "details": {"field": "email", "issue": "неверный формат"},
                "path": "/api/v1/users",
                "timestamp": 1641472800.0
            }
        }


class ValidationErrorDetail(BaseSchema):
    """
    🔍 Детали ошибки валидации
    """
    
    field: str = Field(..., description="Поле с ошибкой")
    message: str = Field(..., description="Сообщение об ошибке")
    value: Optional[Any] = Field(None, description="Некорректное значение")
    
    class Config:
        schema_extra = {
            "example": {
                "field": "email",
                "message": "неверный формат email",
                "value": "invalid-email"
            }
        }


class ValidationErrorResponse(ErrorResponse):
    """
    📝 Схема ответа с ошибкой валидации
    """
    
    validation_errors: List[ValidationErrorDetail] = Field(..., description="Список ошибок валидации")
    
    class Config:
        schema_extra = {
            "example": {
                "error": True,
                "status_code": 422,
                "message": "Ошибка валидации данных",
                "validation_errors": [
                    {
                        "field": "email",
                        "message": "неверный формат email",
                        "value": "invalid-email"
                    }
                ],
                "path": "/api/v1/users",
                "timestamp": 1641472800.0
            }
        }


class HealthCheckResponse(BaseSchema):
    """
    🏥 Схема ответа health check
    """
    
    status: str = Field(..., description="Статус системы")
    version: str = Field(..., description="Версия приложения")
    timestamp: float = Field(..., description="Временная метка проверки")
    components: Dict[str, Dict[str, Any]] = Field(..., description="Статус компонентов")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": 1641472800.0,
                "components": {
                    "database": {"status": "healthy"},
                    "redis": {"status": "healthy"},
                    "integrations": {"status": "healthy"}
                }
            }
        }


class CountResponse(BaseSchema):
    """
    🔢 Схема ответа с количеством
    """
    
    count: int = Field(..., ge=0, description="Количество элементов")
    
    class Config:
        schema_extra = {
            "example": {
                "count": 42
            }
        }


class BulkOperationResponse(BaseSchema):
    """
    📦 Схема ответа для массовых операций
    """
    
    total: int = Field(..., ge=0, description="Общее количество элементов")
    processed: int = Field(..., ge=0, description="Количество обработанных элементов")
    errors: int = Field(..., ge=0, description="Количество ошибок")
    success_rate: float = Field(..., ge=0, le=1, description="Коэффициент успешности")
    
    @validator('success_rate')
    def validate_success_rate(cls, v, values):
        """Валидация коэффициента успешности"""
        if 'total' in values and values['total'] > 0:
            expected = values.get('processed', 0) / values['total']
            if abs(v - expected) > 0.01:  # Допуск 1%
                raise ValueError('success_rate не соответствует processed/total')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "total": 100,
                "processed": 95,
                "errors": 5,
                "success_rate": 0.95
            }
        }


# Общие валидаторы
def validate_uuid(cls, v):
    """Валидатор для UUID"""
    if isinstance(v, str):
        try:
            return uuid.UUID(v)
        except ValueError:
            raise ValueError('Некорректный формат UUID')
    return v


def validate_email(cls, v):
    """Валидатор для email"""
    if v and '@' not in v:
        raise ValueError('Некорректный формат email')
    return v


def validate_phone(cls, v):
    """Валидатор для телефона"""
    if v and not v.replace('+', '').replace('-', '').replace(' ', '').isdigit():
        raise ValueError('Некорректный формат телефона')
    return v


# Экспорт
__all__ = [
    # Базовые схемы
    "BaseSchema",
    "TimestampSchema",
    "UUIDSchema",
    "SoftDeleteSchema",
    "MetadataSchema",
    
    # Параметры запросов
    "PaginationParams",
    "SortParams", 
    "FilterParams",
    
    # Ответы
    "PaginatedResponse",
    "SuccessResponse",
    "ErrorResponse",
    "ValidationErrorDetail",
    "ValidationErrorResponse",
    "HealthCheckResponse",
    "CountResponse",
    "BulkOperationResponse",
    
    # Валидаторы
    "validate_uuid",
    "validate_email",
    "validate_phone"
]