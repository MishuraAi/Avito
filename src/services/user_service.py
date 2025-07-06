"""
Сервис для управления пользователями и продавцами.

Обрабатывает бизнес-логику, связанную с профилями пользователей,
настройками, статистикой и взаимодействиями между пользователями.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from src.database.crud.users import user_crud, seller_crud
from src.database.models.users import User, Seller, UserProfile, SellerSettings
from src.utils.exceptions import BusinessLogicError, NotFoundError
from src.utils.validators import validate_email, validate_phone
from src.utils.formatters import format_user_activity, format_seller_stats


class UserService:
    """
    Сервис для управления пользователями и их профилями.
    
    Предоставляет высокоуровневые методы для работы с пользователями,
    их профилями, настройками и аналитикой.
    """
    
    # ========================================================================
    # МЕТОДЫ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ
    # ========================================================================
    
    def get_user_by_id(self, db: Session, user_id: UUID) -> User:
        """
        Получает пользователя по ID.
        
        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            
        Returns:
            Пользователь
            
        Raises:
            NotFoundError: Если пользователь не найден
        """
        user = user_crud.get(db, id=user_id)
        if not user:
            raise NotFoundError("Пользователь не найден")
        return user
    
    def get_users_list(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search_query: Optional[str] = None,
        active_only: bool = True
    ) -> List[User]:
        """
        Получает список пользователей с фильтрацией.
        
        Args:
            db: Сессия базы данных
            skip: Количество записей для пропуска
            limit: Максимальное количество записей
            search_query: Поисковый запрос
            active_only: Только активные пользователи
            
        Returns:
            Список пользователей
        """
        if search_query:
            return user_crud.search(db, query=search_query, skip=skip, limit=limit)
        
        users = user_crud.get_multi(db, skip=skip, limit=limit)
        
        if active_only:
            users = [user for user in users if user.is_active]
        
        return users
    
    def update_user_profile(
        self,
        db: Session,
        user_id: UUID,
        profile_data: Dict[str, Any]
    ) -> User:
        """
        Обновляет профиль пользователя.
        
        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            profile_data: Новые данные профиля
            
        Returns:
            Обновленный пользователь
            
        Raises:
            NotFoundError: Если пользователь не найден
            BusinessLogicError: При ошибках валидации
        """
        user = self.get_user_by_id(db, user_id)
        
        # Валидируем данные
        if "email" in profile_data:
            if not validate_email(profile_data["email"]):
                raise BusinessLogicError("Некорректный формат email")
            
            # Проверяем уникальность нового email
            if profile_data["email"] != user.email:
                existing_user = user_crud.get_by_email(db, email=profile_data["email"])
                if existing_user:
                    raise BusinessLogicError("Пользователь с таким email уже существует")
        
        if "phone" in profile_data and profile_data["phone"]:
            if not validate_phone(profile_data["phone"]):
                raise BusinessLogicError("Некорректный формат номера телефона")
        
        # Обновляем пользователя
        updated_user = user_crud.update(db, db_obj=user, obj_in=profile_data)
        
        # Обновляем время последней активности
        user_crud.update_last_activity(db, user_id=user_id)
        
        return updated_user
    
    def deactivate_user(self, db: Session, user_id: UUID) -> User:
        """
        Деактивирует пользователя (мягкое удаление).
        
        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            
        Returns:
            Деактивированный пользователь
        """
        user = self.get_user_by_id(db, user_id)
        
        # Деактивируем пользователя
        updated_user = user_crud.update(db, db_obj=user, obj_in={"is_active": False})
        
        # TODO: Здесь можно добавить логику уведомления пользователя
        
        return updated_user
    
    # ========================================================================
    # МЕТОДЫ РАБОТЫ С РАСШИРЕННЫМИ ПРОФИЛЯМИ
    # ========================================================================
    
    def get_user_profile(self, db: Session, user_id: UUID) -> UserProfile:
        """
        Получает расширенный профиль пользователя.
        
        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            
        Returns:
            Расширенный профиль пользователя
            
        Raises:
            NotFoundError: Если профиль не найден
        """
        profile = user_crud.get_profile(db, user_id=user_id)
        if not profile:
            # Создаем профиль по умолчанию, если не существует
            profile = user_crud.create_profile(db, user_id=user_id, obj_in={})
        return profile
    
    def update_user_extended_profile(
        self,
        db: Session,
        user_id: UUID,
        profile_data: Dict[str, Any]
    ) -> UserProfile:
        """
        Обновляет расширенный профиль пользователя.
        
        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            profile_data: Данные для обновления
            
        Returns:
            Обновленный профиль
        """
        # Валидируем интересы
        if "interests" in profile_data:
            interests = profile_data["interests"]
            if isinstance(interests, list) and len(interests) > 20:
                raise BusinessLogicError("Максимум 20 интересов")
        
        # Валидируем стиль общения
        if "communication_style" in profile_data:
            valid_styles = ["formal", "casual", "friendly"]
            if profile_data["communication_style"] not in valid_styles:
                raise BusinessLogicError(f"Стиль общения должен быть одним из: {', '.join(valid_styles)}")
        
        profile = user_crud.update_profile(db, user_id=user_id, obj_in=profile_data)
        return profile
    
    def analyze_user_behavior(self, db: Session, user_id: UUID) -> Dict[str, Any]:
        """
        Анализирует поведение пользователя для персонализации.
        
        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            
        Returns:
            Данные анализа поведения
        """
        user = self.get_user_by_id(db, user_id)
        activity = user_crud.get_activity(db, user_id=user_id)
        
        analysis = {
            "activity_level": self._calculate_activity_level(activity),
            "preferred_time": self._find_preferred_communication_time(activity),
            "response_pattern": self._analyze_response_pattern(activity),
            "interests_evolution": self._track_interests_change(db, user_id),
            "engagement_score": self._calculate_engagement_score(user, activity)
        }
        
        # Обновляем поведенческие данные в профиле
        profile = self.get_user_profile(db, user_id)
        behavioral_data = profile.behavioral_data or {}
        behavioral_data.update(analysis)
        
        user_crud.update_profile(
            db,
            user_id=user_id,
            obj_in={"behavioral_data": behavioral_data}
        )
        
        return analysis
    
    # ========================================================================
    # МЕТОДЫ РАБОТЫ С ПРОДАВЦАМИ
    # ========================================================================
    
    def get_seller_by_id(self, db: Session, seller_id: UUID) -> Seller:
        """
        Получает продавца по ID.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            
        Returns:
            Продавец
            
        Raises:
            NotFoundError: Если продавец не найден
        """
        seller = seller_crud.get(db, id=seller_id)
        if not seller:
            raise NotFoundError("Продавец не найден")
        return seller
    
    def get_sellers_list(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        subscription_plan: Optional[str] = None,
        active_only: bool = True
    ) -> List[Seller]:
        """
        Получает список продавцов с фильтрацией.
        
        Args:
            db: Сессия базы данных
            skip: Количество записей для пропуска
            limit: Максимальное количество записей
            subscription_plan: Фильтр по тарифному плану
            active_only: Только активные продавцы
            
        Returns:
            Список продавцов
        """
        sellers = seller_crud.get_multi(db, skip=skip, limit=limit)
        
        if subscription_plan:
            sellers = [s for s in sellers if s.subscription_plan == subscription_plan]
        
        if active_only:
            sellers = [s for s in sellers if s.is_active]
        
        return sellers
    
    def update_seller_profile(
        self,
        db: Session,
        seller_id: UUID,
        profile_data: Dict[str, Any]
    ) -> Seller:
        """
        Обновляет профиль продавца.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            profile_data: Новые данные профиля
            
        Returns:
            Обновленный продавец
        """
        seller = self.get_seller_by_id(db, seller_id)
        
        # Валидируем данные
        if "email" in profile_data:
            if not validate_email(profile_data["email"]):
                raise BusinessLogicError("Некорректный формат email")
            
            if profile_data["email"] != seller.email:
                existing_seller = seller_crud.get_by_email(db, email=profile_data["email"])
                if existing_seller:
                    raise BusinessLogicError("Продавец с таким email уже существует")
        
        if "phone" in profile_data and profile_data["phone"]:
            if not validate_phone(profile_data["phone"]):
                raise BusinessLogicError("Некорректный формат номера телефона")
        
        updated_seller = seller_crud.update(db, db_obj=seller, obj_in=profile_data)
        return updated_seller
    
    def upgrade_seller_subscription(
        self,
        db: Session,
        seller_id: UUID,
        new_plan: str
    ) -> Seller:
        """
        Обновляет тарифный план продавца.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            new_plan: Новый тарифный план
            
        Returns:
            Обновленный продавец
        """
        valid_plans = ["basic", "pro", "enterprise"]
        if new_plan not in valid_plans:
            raise BusinessLogicError(f"Неверный тарифный план. Доступны: {', '.join(valid_plans)}")
        
        seller = self.get_seller_by_id(db, seller_id)
        
        # Определяем лимиты для нового плана
        plan_limits = {
            "basic": {"monthly_limit": 1000, "ai_enabled": False},
            "pro": {"monthly_limit": 10000, "ai_enabled": True},
            "enterprise": {"monthly_limit": 100000, "ai_enabled": True}
        }
        
        limits = plan_limits[new_plan]
        
        update_data = {
            "subscription_plan": new_plan,
            "monthly_message_limit": limits["monthly_limit"],
            "ai_enabled": limits["ai_enabled"],
            "subscription_expires": datetime.utcnow() + timedelta(days=30)
        }
        
        updated_seller = seller_crud.update(db, db_obj=seller, obj_in=update_data)
        
        # Сбрасываем счетчик использованных сообщений при апгрейде
        if new_plan != seller.subscription_plan:
            seller_crud.reset_monthly_usage(db, seller_id=seller_id)
        
        return updated_seller
    
    # ========================================================================
    # МЕТОДЫ РАБОТЫ С НАСТРОЙКАМИ ПРОДАВЦОВ
    # ========================================================================
    
    def get_seller_settings(self, db: Session, seller_id: UUID) -> SellerSettings:
        """
        Получает настройки продавца.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            
        Returns:
            Настройки продавца
        """
        settings = seller_crud.get_settings(db, seller_id=seller_id)
        if not settings:
            # Создаем настройки по умолчанию
            settings = seller_crud.create_settings(db, seller_id=seller_id, obj_in={})
        return settings
    
    def update_seller_settings(
        self,
        db: Session,
        seller_id: UUID,
        settings_data: Dict[str, Any]
    ) -> SellerSettings:
        """
        Обновляет настройки продавца.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            settings_data: Новые настройки
            
        Returns:
            Обновленные настройки
        """
        # Валидируем настройки
        if "ai_creativity" in settings_data:
            creativity = settings_data["ai_creativity"]
            if not (0.0 <= creativity <= 1.0):
                raise BusinessLogicError("Креативность ИИ должна быть между 0.0 и 1.0")
        
        if "ai_formality" in settings_data:
            formality = settings_data["ai_formality"]
            if not (0.0 <= formality <= 1.0):
                raise BusinessLogicError("Формальность ИИ должна быть между 0.0 и 1.0")
        
        if "auto_reply_delay_min" in settings_data and "auto_reply_delay_max" in settings_data:
            min_delay = settings_data["auto_reply_delay_min"]
            max_delay = settings_data["auto_reply_delay_max"]
            if min_delay > max_delay:
                raise BusinessLogicError("Минимальная задержка не может быть больше максимальной")
        
        settings = seller_crud.update_settings(db, seller_id=seller_id, obj_in=settings_data)
        return settings
    
    # ========================================================================
    # МЕТОДЫ АНАЛИТИКИ И СТАТИСТИКИ
    # ========================================================================
    
    def get_user_activity_stats(self, db: Session, user_id: UUID) -> Dict[str, Any]:
        """
        Получает статистику активности пользователя.
        
        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            
        Returns:
            Статистика активности
        """
        activity = user_crud.get_activity(db, user_id=user_id)
        return format_user_activity(activity)
    
    def get_seller_performance_stats(self, db: Session, seller_id: UUID) -> Dict[str, Any]:
        """
        Получает статистику производительности продавца.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            
        Returns:
            Статистика производительности
        """
        stats = seller_crud.get_stats(db, seller_id=seller_id)
        return format_seller_stats(stats)
    
    def calculate_user_reputation(self, db: Session, user_id: UUID) -> float:
        """
        Вычисляет репутацию пользователя на основе активности.
        
        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            
        Returns:
            Оценка репутации (0.0 - 5.0)
        """
        user = self.get_user_by_id(db, user_id)
        activity = user_crud.get_activity(db, user_id=user_id)
        
        # Базовые факторы репутации
        factors = {
            "response_rate": 0.3,  # Частота ответов на сообщения
            "politeness": 0.25,    # Вежливость общения (анализ ИИ)
            "activity_level": 0.2, # Уровень активности
            "account_age": 0.15,   # Возраст аккаунта
            "completion_rate": 0.1 # Доля завершенных диалогов
        }
        
        scores = {}
        for factor, weight in factors.items():
            scores[factor] = self._calculate_reputation_factor(factor, user, activity) * weight
        
        total_score = sum(scores.values())
        reputation = min(5.0, max(0.0, total_score))
        
        # Обновляем репутацию пользователя
        user_crud.update(db, db_obj=user, obj_in={"reputation_score": reputation})
        
        return reputation
    
    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ========================================================================
    
    def _calculate_activity_level(self, activity: Dict[str, Any]) -> str:
        """Вычисляет уровень активности пользователя."""
        total_messages = activity.get("total_messages", 0)
        
        if total_messages > 100:
            return "high"
        elif total_messages > 20:
            return "medium"
        else:
            return "low"
    
    def _find_preferred_communication_time(self, activity: Dict[str, Any]) -> str:
        """Находит предпочтительное время общения."""
        # Анализ активности по часам
        most_active_hours = activity.get("most_active_hours", [])
        
        if not most_active_hours:
            return "09:00-18:00"  # По умолчанию рабочие часы
        
        # Группируем часы в периоды
        if any(hour in most_active_hours for hour in range(9, 18)):
            return "09:00-18:00"  # Рабочие часы
        elif any(hour in most_active_hours for hour in range(18, 23)):
            return "18:00-23:00"  # Вечер
        else:
            return "09:00-18:00"  # По умолчанию
    
    def _analyze_response_pattern(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует паттерн ответов пользователя."""
        return {
            "avg_response_time": activity.get("avg_response_time", 3600),
            "response_rate": activity.get("response_rate", 0.8),
            "preferred_length": "medium"  # TODO: анализ длины сообщений
        }
    
    def _track_interests_change(self, db: Session, user_id: UUID) -> Dict[str, Any]:
        """Отслеживает изменение интересов пользователя."""
        # TODO: Реализовать анализ истории изменений интересов
        return {
            "trend": "stable",
            "new_interests": [],
            "declining_interests": []
        }
    
    def _calculate_engagement_score(self, user: User, activity: Dict[str, Any]) -> float:
        """Вычисляет оценку вовлеченности пользователя."""
        factors = [
            activity.get("total_messages", 0) / 100,  # Нормализованное количество сообщений
            activity.get("response_rate", 0),         # Частота ответов
            1.0 if user.last_activity and (datetime.utcnow() - user.last_activity).days < 7 else 0.5  # Недавняя активность
        ]
        
        return min(10.0, sum(factors) * 3.33)  # Оценка от 0 до 10
    
    def _calculate_reputation_factor(
        self,
        factor: str,
        user: User,
        activity: Dict[str, Any]
    ) -> float:
        """Вычисляет отдельный фактор репутации."""
        if factor == "response_rate":
            return activity.get("response_rate", 0.5) * 5
        elif factor == "activity_level":
            total_messages = activity.get("total_messages", 0)
            return min(5.0, total_messages / 20)
        elif factor == "account_age":
            if user.created_at:
                days = (datetime.utcnow() - user.created_at).days
                return min(5.0, days / 30)  # 1 месяц = 5 баллов
            return 0.0
        elif factor == "completion_rate":
            return activity.get("completion_rate", 0.5) * 5
        else:
            return 2.5  # Средняя оценка по умолчанию


# Глобальный экземпляр сервиса пользователей
user_service = UserService()