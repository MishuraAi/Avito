"""
👥 CRUD операции для пользователей Avito AI Responder

Этот модуль содержит специализированные CRUD операции для:
- User - покупатели с Авито
- Seller - продавцы (наши клиенты)  
- UserProfile - профили пользователей
- SellerSettings - настройки продавцов

Местоположение: src/database/crud/users.py
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session
from pydantic import BaseModel

from .base import BaseCRUD, CRUDFilter, PaginationParams
from ..models.users import (
    User, Seller, UserProfile, SellerSettings,
    UserType, SellerTier, ActivityLevel
)


# Pydantic схемы для CRUD операций
class UserCreate(BaseModel):
    """Схема создания пользователя"""
    avito_user_id: str
    username: Optional[str] = None
    display_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class UserUpdate(BaseModel):
    """Схема обновления пользователя"""
    username: Optional[str] = None
    display_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    activity_level: Optional[ActivityLevel] = None
    is_verified: Optional[bool] = None
    trust_score: Optional[float] = None
    spam_score: Optional[float] = None


class SellerCreate(BaseModel):
    """Схема создания продавца"""
    email: str
    password_hash: str
    full_name: str
    company_name: Optional[str] = None
    phone: Optional[str] = None


class SellerUpdate(BaseModel):
    """Схема обновления продавца"""
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None
    avito_client_id: Optional[str] = None
    avito_client_secret: Optional[str] = None
    tier: Optional[SellerTier] = None


class UserCRUD(BaseCRUD[User, UserCreate, UserUpdate]):
    """
    👤 CRUD операции для модели User (покупатели)
    """
    
    def __init__(self):
        super().__init__(User)
    
    def get_by_avito_id(self, db: Session, *, avito_user_id: str) -> Optional[User]:
        """
        Получение пользователя по Avito ID
        
        Args:
            db: Сессия базы данных
            avito_user_id: ID пользователя в Авито
            
        Returns:
            Optional[User]: Найденный пользователь или None
        """
        return db.query(User).filter(
            and_(
                User.avito_user_id == avito_user_id,
                User.is_deleted == False
            )
        ).first()
    
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """
        Получение пользователя по email
        
        Args:
            db: Сессия базы данных
            email: Email пользователя
            
        Returns:
            Optional[User]: Найденный пользователь или None
        """
        return db.query(User).filter(
            and_(
                User.email == email,
                User.is_deleted == False
            )
        ).first()
    
    def get_active_users(
        self,
        db: Session,
        *,
        activity_levels: Optional[List[ActivityLevel]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Получение активных пользователей
        
        Args:
            db: Сессия базы данных
            activity_levels: Уровни активности для фильтрации
            skip: Количество записей для пропуска
            limit: Максимальное количество записей
            
        Returns:
            List[User]: Список активных пользователей
        """
        query = db.query(User).filter(
            and_(
                User.status == "active",
                User.is_blocked == False,
                User.is_deleted == False
            )
        )
        
        if activity_levels:
            query = query.filter(User.activity_level.in_(activity_levels))
        
        return query.offset(skip).limit(limit).all()
    
    def get_by_trust_score_range(
        self,
        db: Session,
        *,
        min_score: float = 0.0,
        max_score: float = 100.0,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Получение пользователей по диапазону индекса доверия
        
        Args:
            db: Сессия базы данных
            min_score: Минимальный индекс доверия
            max_score: Максимальный индекс доверия
            skip: Количество записей для пропуска
            limit: Максимальное количество записей
            
        Returns:
            List[User]: Список пользователей
        """
        return db.query(User).filter(
            and_(
                User.trust_score >= min_score,
                User.trust_score <= max_score,
                User.is_deleted == False
            )
        ).offset(skip).limit(limit).all()
    
    def update_activity_stats(
        self,
        db: Session,
        *,
        user_id: uuid.UUID,
        message_count_increment: int = 1,
        conversation_count_increment: int = 0
    ) -> Optional[User]:
        """
        Обновление статистики активности пользователя
        
        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            message_count_increment: Прирост количества сообщений
            conversation_count_increment: Прирост количества диалогов
            
        Returns:
            Optional[User]: Обновленный пользователь
        """
        user = self.get(db, user_id)
        if not user:
            return None
        
        user.message_count += message_count_increment
        user.conversation_count += conversation_count_increment
        user.last_seen_at = datetime.now(timezone.utc)
        
        # Обновляем уровень активности
        user.update_activity_level()
        
        db.commit()
        db.refresh(user)
        
        return user
    
    def get_spam_candidates(
        self,
        db: Session,
        *,
        spam_threshold: float = 70.0,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Получение пользователей-кандидатов на спам
        
        Args:
            db: Сессия базы данных
            spam_threshold: Порог индекса спама
            skip: Количество записей для пропуска
            limit: Максимальное количество записей
            
        Returns:
            List[User]: Список подозрительных пользователей
        """
        return db.query(User).filter(
            and_(
                User.spam_score >= spam_threshold,
                User.is_blocked == False,
                User.is_deleted == False
            )
        ).order_by(User.spam_score.desc()).offset(skip).limit(limit).all()


class SellerCRUD(BaseCRUD[Seller, SellerCreate, SellerUpdate]):
    """
    🏪 CRUD операции для модели Seller (продавцы)
    """
    
    def __init__(self):
        super().__init__(Seller)
    
    def get_by_email(self, db: Session, *, email: str) -> Optional[Seller]:
        """
        Получение продавца по email
        
        Args:
            db: Сессия базы данных
            email: Email продавца
            
        Returns:
            Optional[Seller]: Найденный продавец или None
        """
        return db.query(Seller).filter(
            and_(
                Seller.email == email,
                Seller.is_deleted == False
            )
        ).first()
    
    def get_by_avito_user_id(self, db: Session, *, avito_user_id: str) -> Optional[Seller]:
        """
        Получение продавца по Avito User ID
        
        Args:
            db: Сессия базы данных
            avito_user_id: ID пользователя в Авито
            
        Returns:
            Optional[Seller]: Найденный продавец или None
        """
        return db.query(Seller).filter(
            and_(
                Seller.avito_user_id == avito_user_id,
                Seller.is_deleted == False
            )
        ).first()
    
    def get_by_tier(
        self,
        db: Session,
        *,
        tier: SellerTier,
        skip: int = 0,
        limit: int = 100
    ) -> List[Seller]:
        """
        Получение продавцов по тарифу
        
        Args:
            db: Сессия базы данных
            tier: Тарифный план
            skip: Количество записей для пропуска
            limit: Максимальное количество записей
            
        Returns:
            List[Seller]: Список продавцов
        """
        return db.query(Seller).filter(
            and_(
                Seller.tier == tier,
                Seller.is_deleted == False
            )
        ).offset(skip).limit(limit).all()
    
    def get_active_subscriptions(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[Seller]:
        """
        Получение продавцов с активными подписками
        
        Args:
            db: Сессия базы данных
            skip: Количество записей для пропуска
            limit: Максимальное количество записей
            
        Returns:
            List[Seller]: Список продавцов с активными подписками
        """
        now = datetime.now(timezone.utc)
        
        return db.query(Seller).filter(
            and_(
                or_(
                    Seller.subscription_ends_at.is_(None),  # Бесплатный план
                    Seller.subscription_ends_at > now       # Активная подписка
                ),
                Seller.status == "active",
                Seller.is_deleted == False
            )
        ).offset(skip).limit(limit).all()
    
    def get_expiring_subscriptions(
        self,
        db: Session,
        *,
        days_ahead: int = 7,
        skip: int = 0,
        limit: int = 100
    ) -> List[Seller]:
        """
        Получение продавцов с истекающими подписками
        
        Args:
            db: Сессия базы данных
            days_ahead: Количество дней до истечения
            skip: Количество записей для пропуска
            limit: Максимальное количество записей
            
        Returns:
            List[Seller]: Список продавцов с истекающими подписками
        """
        now = datetime.now(timezone.utc)
        expiry_date = now + timedelta(days=days_ahead)
        
        return db.query(Seller).filter(
            and_(
                Seller.subscription_ends_at.between(now, expiry_date),
                Seller.status == "active",
                Seller.is_deleted == False
            )
        ).order_by(Seller.subscription_ends_at).offset(skip).limit(limit).all()
    
    def update_message_usage(
        self,
        db: Session,
        *,
        seller_id: uuid.UUID,
        messages_used: int = 1
    ) -> Optional[Seller]:
        """
        Обновление использования квоты сообщений
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            messages_used: Количество использованных сообщений
            
        Returns:
            Optional[Seller]: Обновленный продавец
        """
        seller = self.get(db, seller_id)
        if not seller:
            return None
        
        if seller.use_message_quota(messages_used):
            db.commit()
            db.refresh(seller)
            return seller
        
        return None  # Квота исчерпана
    
    def reset_monthly_quotas(self, db: Session) -> int:
        """
        Сброс месячных квот для всех продавцов
        
        Args:
            db: Сессия базы данных
            
        Returns:
            int: Количество обновленных продавцов
        """
        updated_count = db.query(Seller).filter(
            Seller.is_deleted == False
        ).update({
            "monthly_messages_used": 0
        })
        
        db.commit()
        return updated_count
    
    def get_usage_statistics(self, db: Session) -> Dict[str, Any]:
        """
        Получение статистики использования
        
        Args:
            db: Сессия базы данных
            
        Returns:
            Dict[str, Any]: Статистика использования
        """
        stats = db.query(
            func.count(Seller.id).label("total_sellers"),
            func.sum(Seller.monthly_messages_used).label("total_messages_used"),
            func.sum(Seller.total_conversations).label("total_conversations"),
            func.sum(Seller.total_sales).label("total_sales")
        ).filter(Seller.is_deleted == False).first()
        
        tier_stats = db.query(
            Seller.tier,
            func.count(Seller.id).label("count")
        ).filter(
            Seller.is_deleted == False
        ).group_by(Seller.tier).all()
        
        return {
            "total_sellers": stats.total_sellers or 0,
            "total_messages_used": int(stats.total_messages_used or 0),
            "total_conversations": int(stats.total_conversations or 0),
            "total_sales": int(stats.total_sales or 0),
            "tier_distribution": {tier: count for tier, count in tier_stats}
        }


class UserProfileCRUD(BaseCRUD[UserProfile, Dict[str, Any], Dict[str, Any]]):
    """
    📝 CRUD операции для модели UserProfile
    """
    
    def __init__(self):
        super().__init__(UserProfile)
    
    def get_by_user_id(self, db: Session, *, user_id: uuid.UUID) -> Optional[UserProfile]:
        """
        Получение профиля по ID пользователя
        
        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            
        Returns:
            Optional[UserProfile]: Найденный профиль или None
        """
        return db.query(UserProfile).filter(
            and_(
                UserProfile.user_id == user_id,
                UserProfile.is_deleted == False
            )
        ).first()
    
    def get_or_create_profile(
        self,
        db: Session,
        *,
        user_id: uuid.UUID,
        defaults: Optional[Dict[str, Any]] = None
    ) -> UserProfile:
        """
        Получение или создание профиля пользователя
        
        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            defaults: Значения по умолчанию
            
        Returns:
            UserProfile: Профиль пользователя
        """
        profile = self.get_by_user_id(db, user_id=user_id)
        
        if not profile:
            create_data = {"user_id": user_id}
            if defaults:
                create_data.update(defaults)
            
            profile = UserProfile(**create_data)
            db.add(profile)
            db.commit()
            db.refresh(profile)
        
        return profile


class SellerSettingsCRUD(BaseCRUD[SellerSettings, Dict[str, Any], Dict[str, Any]]):
    """
    ⚙️ CRUD операции для модели SellerSettings
    """
    
    def __init__(self):
        super().__init__(SellerSettings)
    
    def get_by_seller_id(self, db: Session, *, seller_id: uuid.UUID) -> Optional[SellerSettings]:
        """
        Получение настроек по ID продавца
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            
        Returns:
            Optional[SellerSettings]: Найденные настройки или None
        """
        return db.query(SellerSettings).filter(
            and_(
                SellerSettings.seller_id == seller_id,
                SellerSettings.is_deleted == False
            )
        ).first()
    
    def get_or_create_settings(
        self,
        db: Session,
        *,
        seller_id: uuid.UUID,
        defaults: Optional[Dict[str, Any]] = None
    ) -> SellerSettings:
        """
        Получение или создание настроек продавца
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            defaults: Значения по умолчанию
            
        Returns:
            SellerSettings: Настройки продавца
        """
        settings = self.get_by_seller_id(db, seller_id=seller_id)
        
        if not settings:
            create_data = {"seller_id": seller_id}
            if defaults:
                create_data.update(defaults)
            
            settings = SellerSettings(**create_data)
            db.add(settings)
            db.commit()
            db.refresh(settings)
        
        return settings
    
    def get_auto_respond_enabled(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[SellerSettings]:
        """
        Получение настроек с включенными автоответами
        
        Args:
            db: Сессия базы данных
            skip: Количество записей для пропуска
            limit: Максимальное количество записей
            
        Returns:
            List[SellerSettings]: Список настроек
        """
        return db.query(SellerSettings).filter(
            and_(
                SellerSettings.auto_respond_enabled == True,
                SellerSettings.is_deleted == False
            )
        ).offset(skip).limit(limit).all()


# Создание экземпляров CRUD классов
user_crud = UserCRUD()
seller_crud = SellerCRUD()
user_profile_crud = UserProfileCRUD()
seller_settings_crud = SellerSettingsCRUD()

# Экспорт
__all__ = [
    # Схемы
    "UserCreate",
    "UserUpdate",
    "SellerCreate", 
    "SellerUpdate",
    
    # CRUD классы
    "UserCRUD",
    "SellerCRUD",
    "UserProfileCRUD",
    "SellerSettingsCRUD",
    
    # Экземпляры
    "user_crud",
    "seller_crud",
    "user_profile_crud",
    "seller_settings_crud"
]