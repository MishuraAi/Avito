"""
🔧 Dependency Injection для FastAPI

Этот модуль содержит все dependencies для FastAPI endpoints:
- Аутентификация и авторизация
- Подключения к базе данных
- Rate limiting
- Валидация прав доступа
- Инъекция сервисов

Местоположение: src/api/dependencies.py
"""

import jwt
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Generator, Dict, Any

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db, db_manager
from ..database.crud.users import seller_crud, SellerCRUD
from ..database.models.users import Seller, SellerTier
from ..core import create_ai_consultant, AIConsultant
from ..integrations import integration_manager

# Настройки JWT
JWT_SECRET_KEY = "your-secret-key-change-in-production"  # TODO: Из переменных окружения
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# HTTP Bearer схема для JWT токенов
security = HTTPBearer()


class TokenData(BaseModel):
    """Данные из JWT токена"""
    seller_id: str
    email: str
    tier: str
    exp: int


class RateLimitInfo(BaseModel):
    """Информация о лимитах запросов"""
    requests_remaining: int
    reset_time: int
    limit: int


# Dependency для получения сессии БД
def get_database() -> Generator[Session, None, None]:
    """
    🗄️ Dependency для получения сессии базы данных
    
    Yields:
        Session: Сессия SQLAlchemy
    """
    return get_db()


# Dependency для получения текущего пользователя
async def get_current_seller(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_database)
) -> Seller:
    """
    👤 Dependency для получения текущего продавца
    
    Args:
        credentials: JWT токен из заголовка Authorization
        db: Сессия базы данных
        
    Returns:
        Seller: Текущий аутентифицированный продавец
        
    Raises:
        HTTPException: Если токен недействителен или продавец не найден
    """
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Недействительные учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Декодируем JWT токен
        payload = jwt.decode(
            credentials.credentials, 
            JWT_SECRET_KEY, 
            algorithms=[JWT_ALGORITHM]
        )
        
        # Извлекаем данные
        seller_id: str = payload.get("sub")
        if seller_id is None:
            raise credentials_exception
        
        # Проверяем срок действия
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Токен истек",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = TokenData(
            seller_id=seller_id,
            email=payload.get("email"),
            tier=payload.get("tier"),
            exp=exp
        )
        
    except jwt.PyJWTError:
        raise credentials_exception
    
    # Находим продавца в базе данных
    seller = seller_crud.get(db, id=token_data.seller_id)
    if seller is None:
        raise credentials_exception
    
    # Проверяем статус продавца
    if seller.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован"
        )
    
    # Обновляем время последнего входа
    seller.last_login_at = datetime.now(timezone.utc)
    db.commit()
    
    return seller


# Dependency для проверки активной подписки
def require_active_subscription(
    current_seller: Seller = Depends(get_current_seller)
) -> Seller:
    """
    💳 Dependency для проверки активной подписки
    
    Args:
        current_seller: Текущий продавец
        
    Returns:
        Seller: Продавец с активной подпиской
        
    Raises:
        HTTPException: Если подписка неактивна
    """
    
    if not current_seller.is_subscription_active:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Требуется активная подписка"
        )
    
    return current_seller


# Dependency для проверки квоты сообщений
def check_message_quota(
    current_seller: Seller = Depends(require_active_subscription),
    db: Session = Depends(get_database)
) -> Seller:
    """
    📨 Dependency для проверки квоты сообщений
    
    Args:
        current_seller: Текущий продавец
        db: Сессия базы данных
        
    Returns:
        Seller: Продавец с доступной квотой
        
    Raises:
        HTTPException: Если квота исчерпана
    """
    
    if not current_seller.can_send_messages:
        remaining_quota = current_seller.messages_remaining
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Исчерпана квота сообщений. Осталось: {remaining_quota}"
        )
    
    return current_seller


# Dependency для проверки тарифного плана
def require_tier(required_tiers: list[SellerTier]):
    """
    🎯 Фабрика dependency для проверки тарифного плана
    
    Args:
        required_tiers: Список требуемых тарифов
        
    Returns:
        Dependency function
    """
    
    def tier_dependency(
        current_seller: Seller = Depends(get_current_seller)
    ) -> Seller:
        """Проверка тарифного плана"""
        
        if current_seller.tier not in required_tiers:
            tier_names = [tier.value for tier in required_tiers]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Требуется тариф: {', '.join(tier_names)}"
            )
        
        return current_seller
    
    return tier_dependency


# Shortcut dependencies для разных тарифов
require_premium = require_tier([SellerTier.PREMIUM, SellerTier.ENTERPRISE])
require_enterprise = require_tier([SellerTier.ENTERPRISE])


# Dependency для Rate Limiting
class RateLimiter:
    """
    ⏱️ Rate Limiter для ограничения запросов
    """
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = {}  # В продакшене использовать Redis
    
    def __call__(self, request: Request) -> RateLimitInfo:
        """
        Проверка лимита запросов
        
        Args:
            request: HTTP запрос
            
        Returns:
            RateLimitInfo: Информация о лимитах
            
        Raises:
            HTTPException: Если лимит превышен
        """
        
        # Получаем идентификатор клиента
        client_id = self._get_client_id(request)
        current_time = int(time.time())
        window_start = current_time - 60  # Окно в 1 минуту
        
        # Инициализируем если нужно
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Очищаем старые запросы
        self.requests[client_id] = [
            timestamp for timestamp in self.requests[client_id]
            if timestamp > window_start
        ]
        
        # Проверяем лимит
        current_requests = len(self.requests[client_id])
        
        if current_requests >= self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Превышен лимит запросов",
                headers={"Retry-After": "60"}
            )
        
        # Добавляем текущий запрос
        self.requests[client_id].append(current_time)
        
        return RateLimitInfo(
            requests_remaining=self.requests_per_minute - current_requests - 1,
            reset_time=window_start + 60,
            limit=self.requests_per_minute
        )
    
    def _get_client_id(self, request: Request) -> str:
        """Получение идентификатора клиента"""
        
        # В продакшене можно использовать JWT sub или API key
        return request.client.host if request.client else "unknown"


# Экземпляры rate limiter для разных endpoints
standard_rate_limiter = RateLimiter(requests_per_minute=60)
strict_rate_limiter = RateLimiter(requests_per_minute=10)


# Dependency для получения ИИ консультанта
async def get_ai_consultant() -> AIConsultant:
    """
    🤖 Dependency для получения ИИ консультанта
    
    Returns:
        AIConsultant: Инициализированный ИИ консультант
        
    Raises:
        HTTPException: Если консультант недоступен
    """
    
    try:
        # TODO: Получать API ключ из переменных окружения
        api_key = "your-gemini-api-key"  
        consultant = await create_ai_consultant(api_key)
        return consultant
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ИИ консультант недоступен: {str(e)}"
        )


# Dependency для получения менеджера интеграций
def get_integration_manager():
    """
    🔗 Dependency для получения менеджера интеграций
    
    Returns:
        IntegrationManager: Менеджер интеграций
        
    Raises:
        HTTPException: Если менеджер недоступен
    """
    
    if not integration_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Интеграции не инициализированы"
        )
    
    return integration_manager


# Utility функции для работы с JWT
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    🔐 Создание JWT токена
    
    Args:
        data: Данные для включения в токен
        expires_delta: Время жизни токена
        
    Returns:
        str: JWT токен
    """
    
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    🔍 Проверка JWT токена
    
    Args:
        token: JWT токен
        
    Returns:
        Optional[Dict]: Данные из токена или None
    """
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


# Dependency для административного доступа
def require_admin(current_seller: Seller = Depends(get_current_seller)) -> Seller:
    """
    👑 Dependency для проверки административных прав
    
    Args:
        current_seller: Текущий продавец
        
    Returns:
        Seller: Продавец с правами администратора
        
    Raises:
        HTTPException: Если нет прав администратора
    """
    
    # TODO: Добавить поле is_admin в модель Seller
    # if not current_seller.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Требуются права администратора"
    #     )
    
    return current_seller


# Экспорт
__all__ = [
    # Основные dependencies
    "get_database",
    "get_current_seller",
    "require_active_subscription",
    "check_message_quota",
    "get_ai_consultant",
    "get_integration_manager",
    
    # Проверка тарифов
    "require_tier",
    "require_premium", 
    "require_enterprise",
    "require_admin",
    
    # Rate limiting
    "RateLimiter",
    "standard_rate_limiter",
    "strict_rate_limiter",
    
    # JWT утилиты
    "create_access_token",
    "verify_token",
    
    # Модели данных
    "TokenData",
    "RateLimitInfo"
]