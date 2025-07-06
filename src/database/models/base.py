"""
📋 Базовые модели для SQLAlchemy

Этот модуль содержит базовые классы для всех моделей данных:
- Base - декларативная база SQLAlchemy  
- BaseModel - базовая модель с общими полями
- TimestampMixin - миксин для автоматических временных меток
- Общие типы данных и утилиты

Местоположение: src/database/models/base.py
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates

# Создаем декларативную базу SQLAlchemy
Base = declarative_base()


class TimestampMixin:
    """
    🕒 Миксин для автоматических временных меток
    
    Добавляет поля:
    - created_at: время создания записи
    - updated_at: время последнего обновления
    """
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Время создания записи"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Время последнего обновления"
    )
    
    @hybrid_property
    def age_seconds(self) -> int:
        """Возраст записи в секундах"""
        return int((datetime.now(timezone.utc) - self.created_at).total_seconds())
    
    @hybrid_property
    def is_fresh(self) -> bool:
        """Свежая ли запись (младше 24 часов)"""
        return self.age_seconds < 86400  # 24 часа


class SoftDeleteMixin:
    """
    🗑️ Миксин для мягкого удаления
    
    Добавляет поля:
    - is_deleted: флаг удаления
    - deleted_at: время удаления
    """
    
    is_deleted = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Флаг мягкого удаления"
    )
    
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время удаления записи"
    )
    
    def soft_delete(self) -> None:
        """Мягкое удаление записи"""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
    
    def restore(self) -> None:
        """Восстановление удаленной записи"""
        self.is_deleted = False
        self.deleted_at = None


class BaseModel(Base, TimestampMixin, SoftDeleteMixin):
    """
    📋 Базовая модель для всех таблиц
    
    Включает:
    - Уникальный UUID идентификатор
    - Временные метки создания/обновления
    - Мягкое удаление
    - Метаданные в JSON
    - Общие методы
    """
    
    __abstract__ = True
    
    # Первичный ключ UUID
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Уникальный идентификатор записи"
    )
    
    # Метаданные в JSON формате
    metadata_ = Column(
        "metadata",  # Избегаем конфликта с SQLAlchemy metadata
        JSONB,
        nullable=True,
        default=dict,
        comment="Дополнительные метаданные в JSON"
    )
    
    # Версия записи для оптимистичных блокировок
    version = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Версия записи"
    )
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Автоматическое именование таблиц"""
        # Преобразуем CamelCase в snake_case
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
    
    def to_dict(self, include_relations: bool = False) -> Dict[str, Any]:
        """
        Конвертация модели в словарь
        
        Args:
            include_relations: Включать связанные объекты
            
        Returns:
            Dict[str, Any]: Словарь с данными модели
        """
        
        result = {}
        
        # Добавляем обычные поля
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            # Конвертируем специальные типы
            if isinstance(value, uuid.UUID):
                value = str(value)
            elif isinstance(value, datetime):
                value = value.isoformat()
            
            result[column.name] = value
        
        # Добавляем связанные объекты если нужно
        if include_relations:
            for relationship in self.__mapper__.relationships:
                related_obj = getattr(self, relationship.key)
                
                if related_obj is not None:
                    if hasattr(related_obj, 'to_dict'):
                        result[relationship.key] = related_obj.to_dict()
                    elif isinstance(related_obj, list):
                        result[relationship.key] = [
                            obj.to_dict() if hasattr(obj, 'to_dict') else str(obj)
                            for obj in related_obj
                        ]
                    else:
                        result[relationship.key] = str(related_obj)
        
        return result
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Обновление модели из словаря
        
        Args:
            data: Словарь с новыми данными
        """
        
        for key, value in data.items():
            if hasattr(self, key) and key not in ['id', 'created_at']:
                setattr(self, key, value)
        
        # Увеличиваем версию
        self.version += 1
    
    def set_metadata(self, key: str, value: Any) -> None:
        """
        Установка значения в метаданных
        
        Args:
            key: Ключ метаданных
            value: Значение
        """
        
        if self.metadata_ is None:
            self.metadata_ = {}
        
        self.metadata_[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Получение значения из метаданных
        
        Args:
            key: Ключ метаданных
            default: Значение по умолчанию
            
        Returns:
            Any: Значение или default
        """
        
        if self.metadata_ is None:
            return default
        
        return self.metadata_.get(key, default)
    
    def add_tag(self, tag: str) -> None:
        """
        Добавление тега в метаданные
        
        Args:
            tag: Тег для добавления
        """
        
        if self.metadata_ is None:
            self.metadata_ = {}
        
        if 'tags' not in self.metadata_:
            self.metadata_['tags'] = []
        
        if tag not in self.metadata_['tags']:
            self.metadata_['tags'].append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """
        Удаление тега из метаданных
        
        Args:
            tag: Тег для удаления
        """
        
        if (self.metadata_ and 
            'tags' in self.metadata_ and 
            tag in self.metadata_['tags']):
            self.metadata_['tags'].remove(tag)
    
    def has_tag(self, tag: str) -> bool:
        """
        Проверка наличия тега
        
        Args:
            tag: Тег для проверки
            
        Returns:
            bool: True если тег есть
        """
        
        return (self.metadata_ and 
                'tags' in self.metadata_ and 
                tag in self.metadata_['tags'])
    
    def get_tags(self) -> List[str]:
        """
        Получение всех тегов
        
        Returns:
            List[str]: Список тегов
        """
        
        if self.metadata_ and 'tags' in self.metadata_:
            return self.metadata_['tags'].copy()
        
        return []
    
    @validates('version')
    def validate_version(self, key: str, version: int) -> int:
        """Валидация версии записи"""
        if version < 1:
            raise ValueError("Версия должна быть больше 0")
        return version
    
    def __repr__(self) -> str:
        """Строковое представление модели"""
        return f"<{self.__class__.__name__}(id={self.id})>"
    
    def __str__(self) -> str:
        """Пользовательское строковое представление"""
        return f"{self.__class__.__name__} {str(self.id)[:8]}"


class AuditMixin:
    """
    📝 Миксин для аудита изменений
    
    Добавляет поля:
    - created_by: кто создал запись
    - updated_by: кто последний изменил
    """
    
    created_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID пользователя создавшего запись"
    )
    
    updated_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID пользователя последний раз изменившего запись"
    )


class AnalyticsMixin:
    """
    📊 Миксин для аналитических данных
    
    Добавляет поля:
    - view_count: количество просмотров
    - interaction_count: количество взаимодействий
    - last_accessed: время последнего доступа
    """
    
    view_count = Column(
        BigInteger,
        nullable=False,
        default=0,
        comment="Количество просмотров"
    )
    
    interaction_count = Column(
        BigInteger,
        nullable=False,
        default=0,
        comment="Количество взаимодействий"
    )
    
    last_accessed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время последнего доступа"
    )
    
    def increment_views(self) -> None:
        """Увеличение счетчика просмотров"""
        self.view_count += 1
        self.last_accessed_at = datetime.now(timezone.utc)
    
    def increment_interactions(self) -> None:
        """Увеличение счетчика взаимодействий"""
        self.interaction_count += 1
        self.last_accessed_at = datetime.now(timezone.utc)


# Общие константы и енумы для использования в моделях
class StatusEnum:
    """Общие статусы для моделей"""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PriorityEnum:
    """Уровни приоритета"""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# Экспорт
__all__ = [
    # Основные классы
    "Base",  # Добавляем Base в экспорт
    "BaseModel",
    
    # Миксины
    "TimestampMixin",
    "SoftDeleteMixin", 
    "AuditMixin",
    "AnalyticsMixin",
    
    # Енумы
    "StatusEnum",
    "PriorityEnum"
]