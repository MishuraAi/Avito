"""
🔧 Конфигурация ядра системы Avito AI Responder

Этот файл содержит основные настройки для работы ИИ-консультанта,
обработки сообщений и генерации ответов.

Местоположение: src/core/config.py
"""

import os
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class ResponseStyle(str, Enum):
    """Стили ответов ИИ-консультанта"""
    PROFESSIONAL = "professional"       # Официальный, деловой стиль
    FRIENDLY = "friendly"              # Дружелюбный, теплый стиль
    CASUAL = "casual"                  # Неформальный, простой стиль
    SALES = "sales"                    # Продающий, убеждающий стиль


class MessageType(str, Enum):
    """Типы входящих сообщений"""
    PRICE_QUESTION = "price_question"           # Вопрос о цене
    AVAILABILITY = "availability"               # Доступность товара
    PRODUCT_INFO = "product_info"              # Информация о товаре
    MEETING_REQUEST = "meeting_request"         # Запрос встречи
    DELIVERY_QUESTION = "delivery_question"    # Вопросы доставки
    GENERAL_QUESTION = "general_question"      # Общие вопросы
    GREETING = "greeting"                      # Приветствие
    COMPLAINT = "complaint"                    # Жалоба
    SPAM = "spam"                             # Спам сообщение


class Settings(BaseSettings):
    """Главные настройки приложения"""
    
    # Основные настройки
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    secret_key: str = Field(env="SECRET_KEY")
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    jwt_access_token_expire_minutes: int = Field(default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # База данных
    database_url: str = Field(env="DATABASE_URL")
    test_database_url: Optional[str] = Field(default=None, env="TEST_DATABASE_URL")
    
    # Redis
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    
    # API ключи
    gemini_api_key: str = Field(env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-pro", env="GEMINI_MODEL")
    
    avito_client_id: Optional[str] = Field(default=None, env="AVITO_CLIENT_ID")
    avito_client_secret: Optional[str] = Field(default=None, env="AVITO_CLIENT_SECRET")
    avito_api_base_url: str = Field(default="https://api.avito.ru", env="AVITO_API_BASE_URL")
    
    # CORS и безопасность
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:8000", env="CORS_ORIGINS")
    cors_methods: str = Field(default="GET,POST,PUT,DELETE,OPTIONS,PATCH", env="CORS_METHODS")
    cors_headers: str = Field(default="*", env="CORS_HEADERS")
    
    # Логирование
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file_path: str = Field(default="data/logs/app.log", env="LOG_FILE_PATH")
    log_max_size_mb: int = Field(default=10, env="LOG_MAX_SIZE_MB")
    log_backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    
    # Rate limiting
    rate_limit_free_requests_per_minute: int = Field(default=10, env="RATE_LIMIT_FREE_REQUESTS_PER_MINUTE")
    rate_limit_premium_requests_per_minute: int = Field(default=100, env="RATE_LIMIT_PREMIUM_REQUESTS_PER_MINUTE")
    rate_limit_enterprise_requests_per_minute: int = Field(default=1000, env="RATE_LIMIT_ENTERPRISE_REQUESTS_PER_MINUTE")
    
    # Сервер
    server_port: int = Field(default=8000, env="SERVER_PORT")
    server_host: str = Field(default="0.0.0.0", env="SERVER_HOST")
    workers_count: int = Field(default=1, env="WORKERS_COUNT")
    
    # Интеграции
    avito_parse_interval_seconds: int = Field(default=300, env="AVITO_PARSE_INTERVAL_SECONDS")
    avito_max_messages_per_request: int = Field(default=50, env="AVITO_MAX_MESSAGES_PER_REQUEST")
    
    # AI обработка
    ai_response_timeout_seconds: int = Field(default=30, env="AI_RESPONSE_TIMEOUT_SECONDS")
    ai_max_tokens_per_request: int = Field(default=1000, env="AI_MAX_TOKENS_PER_REQUEST")
    
    # Мониторинг
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    enable_health_checks: bool = Field(default=True, env="ENABLE_HEALTH_CHECKS")
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    
    # Тестирование
    testing_mode: bool = Field(default=False, env="TESTING_MODE")
    
    # Данные
    upload_folder: str = Field(default="data/uploads", env="UPLOAD_FOLDER")
    max_upload_size_mb: int = Field(default=10, env="MAX_UPLOAD_SIZE_MB")
    temp_folder: str = Field(default="data/temp", env="TEMP_FOLDER")
    
    # Фронтенд
    frontend_url: str = Field(default="http://localhost:3000", env="FRONTEND_URL")
    static_files_dir: str = Field(default="frontend/build", env="STATIC_FILES_DIR")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    @property
    def cors_origins_list(self) -> List[str]:
        """Получить список CORS origins"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def is_development(self) -> bool:
        """Проверить что режим разработки"""
        return self.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Проверить что продакшен режим"""
        return self.environment.lower() == "production"
    
    @property
    def is_testing(self) -> bool:
        """Проверить что режим тестирования"""
        return self.testing_mode or self.environment.lower() == "testing"


class AIConfig(BaseModel):
    """Конфигурация ИИ-консультанта"""

    # Основные параметры Gemini
    model_name: str = Field(default="gemini-pro", description="Модель Gemini")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="Творческость ответов")
    max_tokens: int = Field(default=2048, gt=0, description="Максимум токенов в ответе")

    # Стиль общения
    response_style: ResponseStyle = Field(default=ResponseStyle.FRIENDLY)

    # Ограничения по времени
    response_timeout: int = Field(default=30, gt=0, description="Таймаут ответа в секундах")

    # Кеширование
    cache_responses: bool = Field(default=True, description="Кешировать ответы")
    cache_ttl: int = Field(default=3600, gt=0, description="Время жизни кеша в секундах")


class MessageHandlerConfig(BaseModel):
    """Конфигурация обработчика сообщений"""

    # Фильтрация сообщений
    min_message_length: int = Field(default=2, ge=1, description="Минимальная длина сообщения")
    max_message_length: int = Field(default=1000, gt=0, description="Максимальная длина сообщения")

    # Определение типа сообщения
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    # Антиспам
    spam_detection: bool = Field(default=True, description="Включить детекцию спама")
    rate_limit_messages: int = Field(default=5, gt=0, description="Лимит сообщений от одного пользователя")
    rate_limit_window: int = Field(default=300, gt=0, description="Окно лимита в секундах")


class ResponseGeneratorConfig(BaseModel):
    """Конфигурация генератора ответов"""

    # Шаблоны ответов
    use_templates: bool = Field(default=True, description="Использовать шаблоны")
    template_probability: float = Field(default=0.3, ge=0.0, le=1.0, description="Вероятность использования шаблона")

    # Персонализация
    include_user_name: bool = Field(default=True, description="Включать имя пользователя")
    include_product_details: bool = Field(default=True, description="Включать детали товара")

    # Качество ответов
    min_response_length: int = Field(default=10, ge=1, description="Минимальная длина ответа")
    max_response_length: int = Field(default=500, gt=0, description="Максимальная длина ответа")


class CoreConfig(BaseModel):
    """Основная конфигурация ядра системы"""

    # Компоненты
    ai: AIConfig = Field(default_factory=AIConfig)
    message_handler: MessageHandlerConfig = Field(default_factory=MessageHandlerConfig)
    response_generator: ResponseGeneratorConfig = Field(default_factory=ResponseGeneratorConfig)

    # Общие настройки
    debug_mode: bool = Field(default=False, description="Режим отладки")
    log_level: str = Field(default="INFO", description="Уровень логирования")

    # Метрики
    collect_metrics: bool = Field(default=True, description="Собирать метрики")
    metrics_interval: int = Field(default=60, gt=0, description="Интервал сбора метрик в секундах")


# Словари для классификации сообщений
MESSAGE_KEYWORDS: Dict[MessageType, List[str]] = {
    MessageType.PRICE_QUESTION: [
        "цена", "сколько", "стоимость", "дорого", "дешево", "рубль", "тысяч",
        "торг", "скидка", "цену", "стоит", "руб", "дороже", "дешевле"
    ],

    MessageType.AVAILABILITY: [
        "есть", "доступен", "наличи", "остался", "продан", "забронирован",
        "свободен", "занят", "актуален", "продается", "имеется"
    ],

    MessageType.PRODUCT_INFO: [
        "состояние", "размер", "цвет", "материал", "характеристики", "описание",
        "дефект", "царапин", "новый", "б/у", "подержанный", "качество"
    ],

    MessageType.MEETING_REQUEST: [
        "встреч", "посмотреть", "приехать", "забрать", "осмотр", "когда можно",
        "время", "адрес", "где находится", "встреча", "приезжайте"
    ],

    MessageType.DELIVERY_QUESTION: [
        "доставка", "привезете", "отправка", "почта", "курьер", "самовывоз",
        "доставить", "привезти", "отправить", "получение", "доставляет"
    ],

    MessageType.GREETING: [
        "привет", "здравствуйте", "добрый", "доброе", "добрый день",
        "добрый вечер", "доброе утро", "салют", "хай"
    ],

    MessageType.COMPLAINT: [
        "жалоба", "недоволен", "плохо", "обман", "мошенник", "верните",
        "возврат", "претензия", "некачественный", "сломанный"
    ],

    MessageType.SPAM: [
        "заработок", "инвестиции", "криптовалюта", "займ", "кредит",
        "млм", "сетевой маркетинг", "пирамида", "биткоин"
    ]
}

# Шаблоны ответов по типам сообщений
RESPONSE_TEMPLATES: Dict[MessageType, List[str]] = {
    MessageType.PRICE_QUESTION: [
        "Стоимость указана в объявлении - {price} рублей. Торг возможен при осмотре!",
        "Цена {price} рублей. Могу немного уступить при быстрой покупке.",
        "За {price} рублей отдам. Очень хорошее состояние, не пожалеете!"
    ],

    MessageType.AVAILABILITY: [
        "Да, товар доступен! Когда хотели бы посмотреть?",
        "Есть в наличии. Можете приехать и осмотреть.",
        "Свободен, никто не бронировал. Приезжайте!"
    ],

    MessageType.GREETING: [
        "Здравствуйте! Интересует объявление?",
        "Привет! Что хотели узнать о товаре?",
        "Добро пожаловать! Готов ответить на вопросы."
    ],

    MessageType.MEETING_REQUEST: [
        "Можем встретиться сегодня после 18:00. Адрес отправлю в личку.",
        "Завтра свободен весь день. Во сколько удобно приехать?",
        "Встретимся у метро или могу показать дома. Как удобнее?"
    ]
}

# Настройки по умолчанию
DEFAULT_CORE_CONFIG = CoreConfig()

# Кеширование настроек
@lru_cache()
def get_settings() -> Settings:
    """Получить настройки приложения (с кешированием)"""
    return Settings()


def get_keywords_for_type(message_type: MessageType) -> List[str]:
    """Получить ключевые слова для типа сообщения"""
    return MESSAGE_KEYWORDS.get(message_type, [])


def get_templates_for_type(message_type: MessageType) -> List[str]:
    """Получить шаблоны ответов для типа сообщения"""
    return RESPONSE_TEMPLATES.get(message_type, [])


def validate_config(config: CoreConfig) -> bool:
    """Валидация конфигурации ядра"""
    try:
        # Проверяем что все значения в допустимых пределах
        assert 0.0 <= config.ai.temperature <= 1.0
        assert config.ai.max_tokens > 0
        assert config.message_handler.min_message_length > 0
        assert config.response_generator.min_response_length > 0

        return True
    except (AssertionError, ValueError):
        return False


# Для обратной совместимости
def get_core_config() -> CoreConfig:
    """Получить конфигурацию ядра системы"""
    return DEFAULT_CORE_CONFIG