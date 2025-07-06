"""
🧠 Ядро системы Avito AI Responder

Этот пакет содержит основную бизнес-логику системы:
- ИИ-консультант на базе Google Gemini
- Обработчик входящих сообщений
- Генератор персонализированных ответов
- Конфигурация и настройки

Местоположение: src/core/__init__.py
"""

from .config import (
    # Конфигурации
    CoreConfig,
    AIConfig,
    MessageHandlerConfig,
    ResponseGeneratorConfig,
    
    # Енумы
    ResponseStyle,
    MessageType,
    
    # Константы
    MESSAGE_KEYWORDS,
    RESPONSE_TEMPLATES,
    DEFAULT_CORE_CONFIG,
    
    # Утилиты
    get_keywords_for_type,
    get_templates_for_type,
    validate_config
)

from .ai_consultant import (
    # Основной класс
    AIConsultant,
    
    # Модели данных
    ProductContext,
    UserContext,
    ConversationAnalysis,
    
    # Фабричная функция
    create_ai_consultant
)

from .message_handler import (
    # Основной класс
    MessageHandler,
    
    # Модели данных
    IncomingMessage,
    ProcessedMessage,
    
    # Вспомогательные классы
    RateLimiter,
    SpamDetector,
    MessageClassifier,
    ValidationResult,
    
    # Фабричная функция
    create_message_handler
)

from .response_generator import (
    # Основной класс
    ResponseGenerator,
    
    # Модели данных
    ResponseVariant,
    ResponseMetrics,
    ResponseContext,
    
    # Движки
    PersonalizationEngine,
    TemplateEngine,
    QualityAnalyzer,
    
    # Фабричная функция
    create_response_generator
)


# Версия ядра системы
__version__ = "0.1.0"

# Экспортируемые главные классы
__all__ = [
    # Конфигурация
    "CoreConfig",
    "AIConfig", 
    "MessageHandlerConfig",
    "ResponseGeneratorConfig",
    "ResponseStyle",
    "MessageType",
    "DEFAULT_CORE_CONFIG",
    
    # Основные классы
    "AIConsultant",
    "MessageHandler", 
    "ResponseGenerator",
    
    # Модели данных
    "ProductContext",
    "UserContext",
    "ConversationAnalysis",
    "IncomingMessage",
    "ProcessedMessage",
    "ResponseVariant",
    "ResponseMetrics",
    "ResponseContext",
    
    # Фабричные функции
    "create_ai_consultant",
    "create_message_handler",
    "create_response_generator",
    
    # Утилиты
    "validate_config",
    "get_keywords_for_type",
    "get_templates_for_type"
]