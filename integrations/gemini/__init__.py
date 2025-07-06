"""
🤖 Интеграция с Google Gemini AI

Этот пакет содержит компоненты для работы с Google Gemini:
- client.py  - Клиент для Gemini API с расширенными возможностями
- prompts.py - Библиотека промптов для разных сценариев
- models.py  - Модели данных для работы с Gemini

Местоположение: src/integrations/gemini/__init__.py
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum

# Будут импортироваться по мере создания файлов
try:
    from .client import GeminiAPIClient
    CLIENT_AVAILABLE = True
except ImportError:
    CLIENT_AVAILABLE = False

try:
    from .prompts import GeminiPromptLibrary
    PROMPTS_AVAILABLE = True
except ImportError:
    PROMPTS_AVAILABLE = False


class GeminiModel(str, Enum):
    """Доступные модели Gemini"""
    
    GEMINI_PRO = "gemini-pro"                    # Основная модель
    GEMINI_PRO_VISION = "gemini-pro-vision"     # С поддержкой изображений
    GEMINI_ULTRA = "gemini-ultra"               # Самая мощная (когда доступна)


class GeminiRole(str, Enum):
    """Роли в диалоге с Gemini"""
    
    USER = "user"           # Пользователь
    MODEL = "model"         # Модель Gemini
    SYSTEM = "system"       # Системные инструкции


@dataclass
class GeminiMessage:
    """Сообщение в диалоге с Gemini"""
    
    role: GeminiRole
    content: str
    
    # Дополнительные параметры
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для API"""
        return {
            "role": self.role.value,
            "parts": [{"text": self.content}]
        }


@dataclass
class GeminiResponse:
    """Ответ от Gemini API"""
    
    text: str
    model_used: str
    
    # Метрики ответа
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    
    # Дополнительная информация
    finish_reason: Optional[str] = None
    safety_ratings: Optional[List[Dict]] = None
    raw_response: Optional[Dict[str, Any]] = None


class GeminiIntegrationConfig:
    """Конфигурация интеграции с Gemini"""
    
    def __init__(
        self,
        api_key: str,
        model: GeminiModel = GeminiModel.GEMINI_PRO,
        temperature: float = 0.7,
        max_output_tokens: int = 2048,
        top_p: float = 0.9,
        top_k: int = 40,
        request_timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Инициализация конфигурации Gemini
        
        Args:
            api_key: API ключ Google Gemini
            model: Модель для использования
            temperature: Творческость ответов (0.0-1.0)
            max_output_tokens: Максимум токенов в ответе
            top_p: Nucleus sampling параметр
            top_k: Top-K sampling параметр
            request_timeout: Таймаут запросов в секундах
            max_retries: Максимум попыток повтора
            retry_delay: Задержка между попытками
        """
        
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.top_p = top_p
        self.top_k = top_k
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def validate(self) -> bool:
        """Валидация конфигурации"""
        
        if not self.api_key:
            return False
        
        if not (0.0 <= self.temperature <= 1.0):
            return False
        
        if self.max_output_tokens <= 0:
            return False
        
        if not (0.0 <= self.top_p <= 1.0):
            return False
        
        if self.top_k <= 0:
            return False
        
        return True
    
    def get_generation_config(self) -> Dict[str, Any]:
        """Получить конфигурацию генерации для API"""
        
        return {
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
            "top_p": self.top_p,
            "top_k": self.top_k
        }


class GeminiException(Exception):
    """Базовое исключение для Gemini интеграции"""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code


class GeminiAPIException(GeminiException):
    """Исключение Gemini API"""
    
    def __init__(self, message: str, status_code: int, error_code: Optional[str] = None):
        super().__init__(message, error_code)
        self.status_code = status_code


class GeminiRateLimitException(GeminiException):
    """Исключение превышения лимита запросов Gemini"""
    
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class GeminiSafetyException(GeminiException):
    """Исключение фильтров безопасности Gemini"""
    
    def __init__(self, message: str, safety_ratings: List[Dict]):
        super().__init__(message)
        self.safety_ratings = safety_ratings


# Информация о доступности компонентов
AVAILABLE_COMPONENTS = {
    "client": CLIENT_AVAILABLE,
    "prompts": PROMPTS_AVAILABLE
}

# Версия интеграции
__version__ = "0.1.0"

# Экспортируемые компоненты
__all__ = [
    # Конфигурация
    "GeminiIntegrationConfig",
    
    # Модели данных
    "GeminiMessage",
    "GeminiResponse",
    
    # Енумы
    "GeminiModel",
    "GeminiRole",
    
    # Исключения
    "GeminiException",
    "GeminiAPIException",
    "GeminiRateLimitException",
    "GeminiSafetyException",
    
    # Информация о компонентах
    "AVAILABLE_COMPONENTS",
    "__version__"
]

# Добавляем доступные компоненты в экспорт
if CLIENT_AVAILABLE:
    __all__.append("GeminiAPIClient")

if PROMPTS_AVAILABLE:
    __all__.append("GeminiPromptLibrary")


def get_gemini_integration_info() -> Dict[str, Any]:
    """Получить информацию об интеграции с Gemini"""
    
    return {
        "version": __version__,
        "available_components": AVAILABLE_COMPONENTS,
        "supported_models": [model.value for model in GeminiModel],
        "supported_features": [
            "Текстовая генерация с настраиваемыми параметрами",
            "Библиотека промптов для Авито сценариев",
            "Обработка ошибок и retry логика",
            "Мониторинг использования токенов",
            "Фильтры безопасности"
        ]
    }


def create_default_config(api_key: str) -> GeminiIntegrationConfig:
    """
    Создать конфигурацию по умолчанию
    
    Args:
        api_key: API ключ Gemini
        
    Returns:
        GeminiIntegrationConfig: Конфигурация с оптимальными настройками для Авито
    """
    
    return GeminiIntegrationConfig(
        api_key=api_key,
        model=GeminiModel.GEMINI_PRO,
        temperature=0.7,         # Баланс между креативностью и предсказуемостью
        max_output_tokens=1024,  # Достаточно для ответов в Авито
        top_p=0.9,              # Хорошее разнообразие ответов
        top_k=40,               # Ограничение для качества
        request_timeout=20,      # Быстрые ответы важны
        max_retries=2,          # Минимум повторов для скорости
        retry_delay=1.0         # Быстрое восстановление
    )