"""
👥 Модели пользователей для Avito AI Responder

Этот модуль содержит модели для управления пользователями:
- User - базовая модель пользователя (покупатель из Авито)
- Seller - модель продавца (наш клиент)
- UserProfile - расширенная информация о пользователе
- SellerSettings - настройки продавца

Местоположение: src/database/models/users.py
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, 
    Numeric, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from .base import BaseModel, AuditMixin, AnalyticsMixin, StatusEnum


class UserType(str, Enum):
    """Типы пользователей"""
    
    BUYER = "buyer"           # Покупатель с Авито
    SELLER = "seller"         # Продавец (наш клиент)
    ADMIN = "admin"           # Администратор системы


class SellerTier(str, Enum):
    """Уровни продавцов"""
    
    FREE = "free"             # Бесплатный план
    BASIC = "basic"           # Базовый план
    PREMIUM = "premium"       # Премиум план
    ENTERPRISE = "enterprise" # Корпоративный план


class ActivityLevel(str, Enum):
    """Уровни активности пользователей"""
    
    INACTIVE = "inactive"     # Неактивен
    LOW = "low"              # Низкая активность
    MEDIUM = "medium"        # Средняя активность  
    HIGH = "high"            # Высокая активность
    VERY_HIGH = "very_high"  # Очень высокая активность


class User(BaseModel, AnalyticsMixin):
    """
    👤 Модель пользователя (покупатель с Авито)
    
    Хранит информацию о покупателях, которые пишут продавцам
    """
    
    __tablename__ = "users"
    
    # Основная информация
    avito_user_id = Column(
        String(50),
        nullable=False,
        unique=True,
        comment="ID пользователя в системе Авито"
    )
    
    username = Column(
        String(100),
        nullable=True,
        comment="Имя пользователя в Авито"
    )
    
    display_name = Column(
        String(200),
        nullable=True,
        comment="Отображаемое имя пользователя"
    )
    
    user_type = Column(
        ENUM(UserType, name="user_type_enum"),
        nullable=False,
        default=UserType.BUYER,
        comment="Тип пользователя"
    )
    
    # Контактная информация
    phone = Column(
        String(20),
        nullable=True,
        comment="Номер телефона"
    )
    
    email = Column(
        String(255),
        nullable=True,
        comment="Email адрес"
    )
    
    # Статус и активность
    status = Column(
        String(20),
        nullable=False,
        default=StatusEnum.ACTIVE,
        comment="Статус пользователя"
    )
    
    activity_level = Column(
        ENUM(ActivityLevel, name="activity_level_enum"),
        nullable=False,
        default=ActivityLevel.LOW,
        comment="Уровень активности"
    )
    
    is_verified = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Подтвержден ли пользователь"
    )
    
    is_blocked = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Заблокирован ли пользователь"
    )
    
    blocked_reason = Column(
        Text,
        nullable=True,
        comment="Причина блокировки"
    )
    
    blocked_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время блокировки"
    )
    
    # Поведенческие данные
    message_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Общее количество сообщений"
    )
    
    conversation_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Количество диалогов"
    )
    
    purchase_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Количество покупок"
    )
    
    last_seen_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время последней активности"
    )
    
    # Оценки и репутация
    rating = Column(
        Numeric(3, 2),
        nullable=True,
        comment="Рейтинг пользователя (0.00-5.00)"
    )
    
    trust_score = Column(
        Numeric(5, 2),
        nullable=False,
        default=50.00,
        comment="Индекс доверия (0.00-100.00)"
    )
    
    spam_score = Column(
        Numeric(5, 2),
        nullable=False,
        default=0.00,
        comment="Индекс спама (0.00-100.00)"
    )
    
    # Связи
    conversations = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    messages = relationship(
        "Message",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    user_profile = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    # Индексы
    __table_args__ = (
        Index("idx_users_avito_id", "avito_user_id"),
        Index("idx_users_status", "status"),
        Index("idx_users_activity", "activity_level"),
        Index("idx_users_last_seen", "last_seen_at"),
    )
    
    @hybrid_property
    def is_active_buyer(self) -> bool:
        """Активный ли покупатель"""
        return (
            self.status == StatusEnum.ACTIVE and
            not self.is_blocked and
            self.activity_level in [ActivityLevel.MEDIUM, ActivityLevel.HIGH, ActivityLevel.VERY_HIGH]
        )
    
    @hybrid_property
    def avg_messages_per_conversation(self) -> float:
        """Среднее количество сообщений на диалог"""
        if self.conversation_count == 0:
            return 0.0
        return self.message_count / self.conversation_count
    
    def update_activity_level(self) -> None:
        """Обновление уровня активности на основе метрик"""
        
        if self.message_count == 0:
            self.activity_level = ActivityLevel.INACTIVE
        elif self.message_count < 5:
            self.activity_level = ActivityLevel.LOW
        elif self.message_count < 20:
            self.activity_level = ActivityLevel.MEDIUM
        elif self.message_count < 50:
            self.activity_level = ActivityLevel.HIGH
        else:
            self.activity_level = ActivityLevel.VERY_HIGH
    
    def block_user(self, reason: str) -> None:
        """Блокировка пользователя"""
        self.is_blocked = True
        self.blocked_reason = reason
        self.blocked_at = datetime.now(timezone.utc)
        self.status = StatusEnum.INACTIVE
    
    def unblock_user(self) -> None:
        """Разблокировка пользователя"""
        self.is_blocked = False
        self.blocked_reason = None
        self.blocked_at = None
        self.status = StatusEnum.ACTIVE
    
    @validates('rating')
    def validate_rating(self, key: str, rating: Optional[float]) -> Optional[float]:
        """Валидация рейтинга"""
        if rating is not None and (rating < 0 or rating > 5):
            raise ValueError("Рейтинг должен быть от 0 до 5")
        return rating
    
    @validates('trust_score', 'spam_score')
    def validate_scores(self, key: str, score: float) -> float:
        """Валидация индексов"""
        if score < 0 or score > 100:
            raise ValueError(f"{key} должен быть от 0 до 100")
        return score


class Seller(BaseModel, AuditMixin):
    """
    🏪 Модель продавца (наш клиент)
    
    Хранит информацию о продавцах, которые используют наш сервис
    """
    
    __tablename__ = "sellers"
    
    # Основная информация
    email = Column(
        String(255),
        nullable=False,
        unique=True,
        comment="Email продавца"
    )
    
    password_hash = Column(
        String(255),
        nullable=False,
        comment="Хеш пароля"
    )
    
    full_name = Column(
        String(200),
        nullable=False,
        comment="Полное имя продавца"
    )
    
    company_name = Column(
        String(200),
        nullable=True,
        comment="Название компании"
    )
    
    phone = Column(
        String(20),
        nullable=True,
        comment="Номер телефона"
    )
    
    # Авито интеграция
    avito_user_id = Column(
        String(50),
        nullable=True,
        comment="ID пользователя в Авито"
    )
    
    avito_client_id = Column(
        String(100),
        nullable=True,
        comment="Client ID для Авито API"
    )
    
    avito_client_secret = Column(
        String(255),
        nullable=True,
        comment="Client Secret для Авито API (зашифрован)"
    )
    
    # Подписка и тариф
    tier = Column(
        ENUM(SellerTier, name="seller_tier_enum"),
        nullable=False,
        default=SellerTier.FREE,
        comment="Тарифный план"
    )
    
    subscription_starts_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Начало подписки"
    )
    
    subscription_ends_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Конец подписки"
    )
    
    # Статус и ограничения
    status = Column(
        String(20),
        nullable=False,
        default=StatusEnum.ACTIVE,
        comment="Статус продавца"
    )
    
    is_email_verified = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Подтвержден ли email"
    )
    
    is_avito_connected = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Подключен ли к Авито API"
    )
    
    monthly_message_limit = Column(
        Integer,
        nullable=False,
        default=100,
        comment="Лимит сообщений в месяц"
    )
    
    monthly_messages_used = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Использовано сообщений в текущем месяце"
    )
    
    # Статистика
    total_conversations = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Общее количество диалогов"
    )
    
    total_messages_sent = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Общее количество отправленных сообщений"
    )
    
    total_sales = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Общее количество продаж"
    )
    
    last_login_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время последнего входа"
    )
    
    # Связи
    products = relationship(
        "Product",
        back_populates="seller",
        cascade="all, delete-orphan"
    )
    
    conversations = relationship(
        "Conversation",
        back_populates="seller",
        cascade="all, delete-orphan"
    )
    
    seller_settings = relationship(
        "SellerSettings",
        back_populates="seller",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    # Индексы
    __table_args__ = (
        Index("idx_sellers_email", "email"),
        Index("idx_sellers_tier", "tier"),
        Index("idx_sellers_status", "status"),
        Index("idx_sellers_subscription", "subscription_ends_at"),
    )
    
    @hybrid_property
    def is_subscription_active(self) -> bool:
        """Активна ли подписка"""
        if not self.subscription_ends_at:
            return self.tier == SellerTier.FREE
        return datetime.now(timezone.utc) < self.subscription_ends_at
    
    @hybrid_property
    def messages_remaining(self) -> int:
        """Оставшееся количество сообщений"""
        return max(0, self.monthly_message_limit - self.monthly_messages_used)
    
    @hybrid_property
    def can_send_messages(self) -> bool:
        """Может ли отправлять сообщения"""
        return (
            self.status == StatusEnum.ACTIVE and
            self.is_subscription_active and
            self.messages_remaining > 0
        )
    
    def use_message_quota(self, count: int = 1) -> bool:
        """
        Использование квоты сообщений
        
        Args:
            count: Количество сообщений
            
        Returns:
            bool: True если квота позволяет
        """
        if self.messages_remaining >= count:
            self.monthly_messages_used += count
            return True
        return False
    
    def reset_monthly_quota(self) -> None:
        """Сброс месячной квоты сообщений"""
        self.monthly_messages_used = 0
    
    def upgrade_tier(self, new_tier: SellerTier, months: int = 1) -> None:
        """
        Повышение тарифа
        
        Args:
            new_tier: Новый тариф
            months: Количество месяцев
        """
        self.tier = new_tier
        
        now = datetime.now(timezone.utc)
        if self.subscription_ends_at and self.subscription_ends_at > now:
            # Продлеваем существующую подписку
            from dateutil.relativedelta import relativedelta
            self.subscription_ends_at += relativedelta(months=months)
        else:
            # Новая подписка
            self.subscription_starts_at = now
            from dateutil.relativedelta import relativedelta
            self.subscription_ends_at = now + relativedelta(months=months)
        
        # Обновляем лимиты
        tier_limits = {
            SellerTier.FREE: 100,
            SellerTier.BASIC: 1000,
            SellerTier.PREMIUM: 5000,
            SellerTier.ENTERPRISE: 50000
        }
        self.monthly_message_limit = tier_limits.get(new_tier, 100)


class UserProfile(BaseModel):
    """
    📝 Расширенный профиль пользователя
    
    Дополнительная информация о покупателе для персонализации
    """
    
    __tablename__ = "user_profiles"
    
    # Связь с пользователем
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="ID пользователя"
    )
    
    # Демографические данные
    age_group = Column(
        String(20),
        nullable=True,
        comment="Возрастная группа"
    )
    
    gender = Column(
        String(10),
        nullable=True,
        comment="Пол"
    )
    
    location = Column(
        String(200),
        nullable=True,
        comment="Местоположение"
    )
    
    # Поведенческие предпочтения
    preferred_communication_style = Column(
        String(20),
        nullable=True,
        comment="Предпочитаемый стиль общения"
    )
    
    typical_response_time = Column(
        Integer,
        nullable=True,
        comment="Типичное время ответа в минутах"
    )
    
    preferred_contact_hours = Column(
        JSONB,
        nullable=True,
        comment="Предпочитаемые часы для контакта"
    )
    
    # Интересы и категории
    interested_categories = Column(
        JSONB,
        nullable=True,
        comment="Интересующие категории товаров"
    )
    
    price_sensitivity = Column(
        String(20),
        nullable=True,
        comment="Чувствительность к цене (low/medium/high)"
    )
    
    buying_patterns = Column(
        JSONB,
        nullable=True,
        comment="Паттерны покупок"
    )
    
    # Связи
    user = relationship("User", back_populates="user_profile")
    
    # Индексы
    __table_args__ = (
        Index("idx_user_profiles_user_id", "user_id"),
        Index("idx_user_profiles_location", "location"),
    )


class SellerSettings(BaseModel):
    """
    ⚙️ Настройки продавца
    
    Персональные настройки каждого продавца для работы бота
    """
    
    __tablename__ = "seller_settings"
    
    # Связь с продавцом
    seller_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sellers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="ID продавца"
    )
    
    # Настройки ИИ
    ai_response_style = Column(
        String(20),
        nullable=False,
        default="friendly",
        comment="Стиль ответов ИИ"
    )
    
    ai_temperature = Column(
        Numeric(3, 2),
        nullable=False,
        default=0.7,
        comment="Температура ИИ (творческость)"
    )
    
    use_templates = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Использовать шаблоны ответов"
    )
    
    template_probability = Column(
        Numeric(3, 2),
        nullable=False,
        default=0.3,
        comment="Вероятность использования шаблона"
    )
    
    # Автоматизация
    auto_respond_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Включены ли автоответы"
    )
    
    auto_respond_delay = Column(
        Integer,
        nullable=False,
        default=60,
        comment="Задержка автоответа в секундах"
    )
    
    working_hours_start = Column(
        Integer,
        nullable=True,
        comment="Начало рабочих часов (0-23)"
    )
    
    working_hours_end = Column(
        Integer,
        nullable=True,
        comment="Конец рабочих часов (0-23)"
    )
    
    weekend_responses = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Отвечать в выходные"
    )
    
    # Фильтрация и модерация
    spam_filter_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Включен ли спам-фильтр"
    )
    
    minimum_message_length = Column(
        Integer,
        nullable=False,
        default=3,
        comment="Минимальная длина сообщения"
    )
    
    blocked_keywords = Column(
        JSONB,
        nullable=True,
        comment="Заблокированные ключевые слова"
    )
    
    # Персонализация
    seller_name = Column(
        String(100),
        nullable=True,
        comment="Имя продавца для ответов"
    )
    
    company_info = Column(
        Text,
        nullable=True,
        comment="Информация о компании"
    )
    
    custom_greeting = Column(
        Text,
        nullable=True,
        comment="Персональное приветствие"
    )
    
    custom_signature = Column(
        Text,
        nullable=True,
        comment="Подпись в сообщениях"
    )
    
    # Уведомления
    email_notifications = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Email уведомления"
    )
    
    notification_types = Column(
        JSONB,
        nullable=True,
        comment="Типы уведомлений"
    )
    
    # Связи
    seller = relationship("Seller", back_populates="seller_settings")
    
    @validates('ai_temperature')
    def validate_temperature(self, key: str, temperature: float) -> float:
        """Валидация температуры ИИ"""
        if temperature < 0 or temperature > 1:
            raise ValueError("Температура должна быть от 0 до 1")
        return temperature
    
    @validates('working_hours_start', 'working_hours_end')
    def validate_working_hours(self, key: str, hour: Optional[int]) -> Optional[int]:
        """Валидация рабочих часов"""
        if hour is not None and (hour < 0 or hour > 23):
            raise ValueError("Час должен быть от 0 до 23")
        return hour


# Экспорт
__all__ = [
    # Енумы
    "UserType",
    "SellerTier", 
    "ActivityLevel",
    
    # Модели
    "User",
    "Seller",
    "UserProfile",
    "SellerSettings"
]