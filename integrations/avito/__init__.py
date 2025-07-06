"""
🏠 Интеграция с платформой Авито

Этот пакет содержит все компоненты для работы с Авито:
- api_client.py      - API клиент для работы с официальным API
- selenium_client.py - Selenium автоматизация как fallback решение  
- webhook_handler.py - Обработчик вебхуков от Авито
- models.py         - Модели данных для Авито API
- exceptions.py     - Специфичные исключения

Местоположение: src/integrations/avito/__init__.py
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# Будут импортироваться по мере создания файлов
try:
    from .api_client import AvitoAPIClient
    API_CLIENT_AVAILABLE = True
except ImportError:
    API_CLIENT_AVAILABLE = False

try:
    from .selenium_client import AvitoSeleniumClient
    SELENIUM_CLIENT_AVAILABLE = True
except ImportError:
    SELENIUM_CLIENT_AVAILABLE = False

try:
    from .webhook_handler import AvitoWebhookHandler
    WEBHOOK_HANDLER_AVAILABLE = True
except ImportError:
    WEBHOOK_HANDLER_AVAILABLE = False


class AvitoMessageStatus(str, Enum):
    """Статусы сообщений в Авито"""
    
    UNREAD = "unread"           # Непрочитанное
    READ = "read"               # Прочитанное
    REPLIED = "replied"         # Отвечено
    ARCHIVED = "archived"       # Архивировано


class AvitoAdStatus(str, Enum):
    """Статусы объявлений в Авито"""
    
    ACTIVE = "active"           # Активно
    PAUSED = "paused"          # Приостановлено
    BLOCKED = "blocked"        # Заблокировано
    EXPIRED = "expired"        # Истекло
    REMOVED = "removed"        # Удалено


@dataclass
class AvitoMessage:
    """Модель сообщения от Авито"""
    
    message_id: str
    chat_id: str
    ad_id: str
    user_id: str
    text: str
    created_at: datetime
    
    # Дополнительная информация
    status: AvitoMessageStatus = AvitoMessageStatus.UNREAD
    is_from_seller: bool = False
    attachments: List[str] = None
    
    # Метаданные
    raw_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []


@dataclass
class AvitoAd:
    """Модель объявления из Авито"""
    
    ad_id: str
    title: str
    price: Optional[int]
    description: str
    category: str
    
    # Статус и состояние
    status: AvitoAdStatus
    created_at: datetime
    updated_at: datetime
    
    # Дополнительная информация
    images: List[str] = None
    location: Optional[str] = None
    views_count: int = 0
    contacts_count: int = 0
    
    # Метаданные
    raw_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.images is None:
            self.images = []


@dataclass
class AvitoChat:
    """Модель чата с покупателем"""
    
    chat_id: str
    ad_id: str
    user_id: str
    user_name: Optional[str]
    
    # Статистика чата
    messages_count: int = 0
    last_message_at: Optional[datetime] = None
    unread_count: int = 0
    
    # Статус
    is_blocked: bool = False
    is_archived: bool = False
    
    def get_display_name(self) -> str:
        """Получить отображаемое имя пользователя"""
        return self.user_name or f"Пользователь {self.user_id[:8]}"


class AvitoIntegrationConfig:
    """Конфигурация интеграции с Авито"""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        api_base_url: str = "https://api.avito.ru",
        use_selenium_fallback: bool = True,
        selenium_headless: bool = True,
        request_timeout: int = 30,
        rate_limit_requests: int = 100,
        rate_limit_window: int = 3600
    ):
        """
        Инициализация конфигурации
        
        Args:
            client_id: ID клиента Авито API
            client_secret: Секрет клиента Авито API
            api_base_url: Базовый URL API
            use_selenium_fallback: Использовать Selenium как fallback
            selenium_headless: Запускать браузер в headless режиме
            request_timeout: Таймаут запросов в секундах
            rate_limit_requests: Лимит запросов
            rate_limit_window: Окно лимита в секундах
        """
        
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_base_url = api_base_url
        self.use_selenium_fallback = use_selenium_fallback
        self.selenium_headless = selenium_headless
        self.request_timeout = request_timeout
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_window = rate_limit_window
    
    def validate(self) -> bool:
        """Валидация конфигурации"""
        
        if not self.client_id or not self.client_secret:
            return False
        
        if self.request_timeout <= 0:
            return False
        
        if self.rate_limit_requests <= 0 or self.rate_limit_window <= 0:
            return False
        
        return True


class AvitoException(Exception):
    """Базовое исключение для Авито интеграции"""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code


class AvitoAPIException(AvitoException):
    """Исключение API Авито"""
    
    def __init__(self, message: str, status_code: int, error_code: Optional[str] = None):
        super().__init__(message, error_code)
        self.status_code = status_code


class AvitoSeleniumException(AvitoException):
    """Исключение Selenium автоматизации"""
    pass


class AvitoRateLimitException(AvitoException):
    """Исключение превышения лимита запросов"""
    
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after


# Информация о доступности компонентов
AVAILABLE_COMPONENTS = {
    "api_client": API_CLIENT_AVAILABLE,
    "selenium_client": SELENIUM_CLIENT_AVAILABLE,
    "webhook_handler": WEBHOOK_HANDLER_AVAILABLE
}

# Версия интеграции
__version__ = "0.1.0"

# Экспортируемые компоненты
__all__ = [
    # Конфигурация
    "AvitoIntegrationConfig",
    
    # Модели данных
    "AvitoMessage",
    "AvitoAd", 
    "AvitoChat",
    
    # Енумы
    "AvitoMessageStatus",
    "AvitoAdStatus",
    
    # Исключения
    "AvitoException",
    "AvitoAPIException",
    "AvitoSeleniumException", 
    "AvitoRateLimitException",
    
    # Информация о компонентах
    "AVAILABLE_COMPONENTS",
    "__version__"
]

# Добавляем доступные компоненты в экспорт
if API_CLIENT_AVAILABLE:
    __all__.append("AvitoAPIClient")

if SELENIUM_CLIENT_AVAILABLE:
    __all__.append("AvitoSeleniumClient")

if WEBHOOK_HANDLER_AVAILABLE:
    __all__.append("AvitoWebhookHandler")


def get_avito_integration_info() -> Dict[str, Any]:
    """Получить информацию об интеграции с Авито"""
    
    return {
        "version": __version__,
        "available_components": AVAILABLE_COMPONENTS,
        "supported_features": [
            "API клиент для работы с Авито API",
            "Selenium автоматизация как fallback",
            "Обработка вебхуков",
            "Модели данных для сообщений и объявлений",
            "Rate limiting и обработка ошибок"
        ]
    }