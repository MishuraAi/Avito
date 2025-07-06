"""
Сервис аутентификации и авторизации.

Обрабатывает всю логику, связанную с безопасностью:
регистрацию, вход, управление токенами и проверку прав доступа.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Union, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.database.crud.users import user_crud, seller_crud
from src.database.models.users import User, Seller
from src.utils.exceptions import AuthenticationError, AuthorizationError

settings = get_settings()


class AuthService:
    """
    Сервис для управления аутентификацией и авторизацией пользователей.
    
    Предоставляет методы для регистрации, входа в систему, 
    создания и валидации JWT токенов.
    """
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    
    # ========================================================================
    # МЕТОДЫ ХЕШИРОВАНИЯ ПАРОЛЕЙ
    # ========================================================================
    
    def hash_password(self, password: str) -> str:
        """Хеширует пароль с использованием bcrypt."""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Проверяет соответствие пароля хешу."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    # ========================================================================
    # МЕТОДЫ РАБОТЫ С JWT ТОКЕНАМИ
    # ========================================================================
    
    def create_access_token(
        self, 
        user_id: str, 
        user_type: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Создает JWT access token для пользователя.
        
        Args:
            user_id: ID пользователя
            user_type: Тип пользователя ("user" или "seller")
            expires_delta: Время жизни токена
            
        Returns:
            JWT токен в виде строки
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode = {
            "sub": str(user_id),
            "type": user_type,
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(16)  # Уникальный ID токена
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def decode_access_token(self, token: str) -> dict:
        """
        Декодирует и валидирует JWT токен.
        
        Args:
            token: JWT токен
            
        Returns:
            Payload токена
            
        Raises:
            AuthenticationError: При невалидном токене
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            raise AuthenticationError(f"Недействительный токен: {str(e)}")
    
    def create_refresh_token(self, user_id: str, user_type: str) -> str:
        """
        Создает refresh token с длительным сроком действия.
        
        Args:
            user_id: ID пользователя
            user_type: Тип пользователя
            
        Returns:
            Refresh токен
        """
        expire = datetime.utcnow() + timedelta(days=30)  # 30 дней
        
        to_encode = {
            "sub": str(user_id),
            "type": user_type,
            "exp": expire,
            "iat": datetime.utcnow(),
            "token_type": "refresh",
            "jti": secrets.token_urlsafe(16)
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    # ========================================================================
    # МЕТОДЫ АУТЕНТИФИКАЦИИ
    # ========================================================================
    
    def authenticate_user(
        self, 
        db: Session, 
        email: str, 
        password: str
    ) -> Tuple[Optional[Union[User, Seller]], str]:
        """
        Аутентифицирует пользователя по email и паролю.
        
        Args:
            db: Сессия базы данных
            email: Email пользователя
            password: Пароль
            
        Returns:
            Кортеж (пользователь, тип_пользователя) или (None, "")
        """
        # Сначала ищем среди обычных пользователей
        user = user_crud.get_by_email(db, email=email)
        if user and self.verify_password(password, user.hashed_password):
            if not user.is_active:
                raise AuthenticationError("Аккаунт пользователя деактивирован")
            return user, "user"
        
        # Затем ищем среди продавцов
        seller = seller_crud.get_by_email(db, email=email)
        if seller and self.verify_password(password, seller.hashed_password):
            if not seller.is_active:
                raise AuthenticationError("Аккаунт продавца деактивирован")
            return seller, "seller"
        
        return None, ""
    
    def get_current_user(
        self, 
        db: Session, 
        token: str
    ) -> Tuple[Union[User, Seller], str]:
        """
        Получает текущего пользователя по JWT токену.
        
        Args:
            db: Сессия базы данных
            token: JWT токен
            
        Returns:
            Кортеж (пользователь, тип_пользователя)
            
        Raises:
            AuthenticationError: При проблемах с токеном или пользователем
        """
        try:
            payload = self.decode_access_token(token)
            user_id = payload.get("sub")
            user_type = payload.get("type")
            
            if not user_id or not user_type:
                raise AuthenticationError("Некорректный токен")
            
            # Получаем пользователя из базы данных
            if user_type == "user":
                user = user_crud.get(db, id=user_id)
                if not user:
                    raise AuthenticationError("Пользователь не найден")
                if not user.is_active:
                    raise AuthenticationError("Аккаунт деактивирован")
                return user, "user"
            
            elif user_type == "seller":
                seller = seller_crud.get(db, id=user_id)
                if not seller:
                    raise AuthenticationError("Продавец не найден")
                if not seller.is_active:
                    raise AuthenticationError("Аккаунт деактивирован")
                return seller, "seller"
            
            else:
                raise AuthenticationError("Неизвестный тип пользователя")
                
        except JWTError:
            raise AuthenticationError("Недействительный токен")
    
    # ========================================================================
    # МЕТОДЫ РЕГИСТРАЦИИ
    # ========================================================================
    
    def register_user(
        self,
        db: Session,
        user_data: dict
    ) -> User:
        """
        Регистрирует нового пользователя.
        
        Args:
            db: Сессия базы данных
            user_data: Данные пользователя
            
        Returns:
            Созданный пользователь
            
        Raises:
            AuthenticationError: При проблемах с регистрацией
        """
        # Проверяем уникальность email
        existing_user = user_crud.get_by_email(db, email=user_data["email"])
        if existing_user:
            raise AuthenticationError("Пользователь с таким email уже существует")
        
        # Проверяем уникальность avito_user_id
        existing_avito_user = user_crud.get_by_avito_id(
            db, 
            avito_user_id=user_data["avito_user_id"]
        )
        if existing_avito_user:
            raise AuthenticationError("Пользователь с таким Avito ID уже существует")
        
        # Хешируем пароль
        user_data["hashed_password"] = self.hash_password(user_data.pop("password"))
        
        # Создаем пользователя
        user = user_crud.create(db, obj_in=user_data)
        return user
    
    def register_seller(
        self,
        db: Session,
        seller_data: dict
    ) -> Seller:
        """
        Регистрирует нового продавца.
        
        Args:
            db: Сессия базы данных
            seller_data: Данные продавца
            
        Returns:
            Созданный продавец
            
        Raises:
            AuthenticationError: При проблемах с регистрацией
        """
        # Проверяем уникальность email
        existing_seller = seller_crud.get_by_email(db, email=seller_data["email"])
        if existing_seller:
            raise AuthenticationError("Продавец с таким email уже существует")
        
        # Проверяем уникальность avito_user_id
        existing_avito_seller = seller_crud.get_by_avito_id(
            db,
            avito_user_id=seller_data["avito_user_id"]
        )
        if existing_avito_seller:
            raise AuthenticationError("Продавец с таким Avito ID уже существует")
        
        # Хешируем пароль
        seller_data["hashed_password"] = self.hash_password(seller_data.pop("password"))
        
        # Создаем продавца
        seller = seller_crud.create(db, obj_in=seller_data)
        return seller
    
    # ========================================================================
    # МЕТОДЫ АВТОРИЗАЦИИ
    # ========================================================================
    
    def check_user_permission(
        self,
        current_user: Union[User, Seller],
        required_user_type: str,
        resource_owner_id: Optional[str] = None
    ) -> None:
        """
        Проверяет права доступа пользователя к ресурсу.
        
        Args:
            current_user: Текущий пользователь
            required_user_type: Требуемый тип пользователя
            resource_owner_id: ID владельца ресурса (для проверки владения)
            
        Raises:
            AuthorizationError: При недостатке прав
        """
        user_type = "seller" if hasattr(current_user, "company_name") else "user"
        
        # Проверяем тип пользователя
        if required_user_type != "any" and user_type != required_user_type:
            raise AuthorizationError(f"Доступ разрешен только для {required_user_type}")
        
        # Проверяем владение ресурсом
        if resource_owner_id and str(current_user.id) != resource_owner_id:
            raise AuthorizationError("Нет доступа к чужому ресурсу")
    
    def check_subscription_limits(
        self,
        seller: Seller,
        operation: str
    ) -> None:
        """
        Проверяет лимиты подписки продавца.
        
        Args:
            seller: Продавец
            operation: Тип операции для проверки лимитов
            
        Raises:
            AuthorizationError: При превышении лимитов
        """
        if operation == "message" and seller.monthly_messages_used >= seller.monthly_message_limit:
            raise AuthorizationError("Превышен лимит сообщений в месяц")
        
        if operation == "ai_generation" and not seller.ai_enabled:
            raise AuthorizationError("ИИ-функции отключены в тарифе")
        
        # Проверяем срок действия подписки
        if seller.subscription_expires and seller.subscription_expires < datetime.utcnow():
            raise AuthorizationError("Подписка истекла")
    
    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ========================================================================
    
    def generate_password_reset_token(self, user_id: str) -> str:
        """
        Генерирует токен для сброса пароля.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Токен сброса пароля
        """
        expire = datetime.utcnow() + timedelta(hours=1)  # 1 час
        
        to_encode = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.utcnow(),
            "token_type": "password_reset",
            "jti": secrets.token_urlsafe(16)
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_password_reset_token(self, token: str) -> Optional[str]:
        """
        Проверяет токен сброса пароля.
        
        Args:
            token: Токен сброса пароля
            
        Returns:
            ID пользователя или None при невалидном токене
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if payload.get("token_type") != "password_reset":
                return None
            return payload.get("sub")
        except JWTError:
            return None


# Глобальный экземпляр сервиса аутентификации
auth_service = AuthService()