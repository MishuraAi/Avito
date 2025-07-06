"""
Кастомные исключения для Авито ИИ-бота.

Определяет иерархию исключений для различных типов ошибок
в приложении с детальными сообщениями и кодами ошибок.
"""

from typing import Optional, Dict, Any


class BaseAppException(Exception):
    """
    Базовое исключение приложения.
    
    Все кастомные исключения должны наследоваться от этого класса.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Возвращает словарь с информацией об ошибке."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "type": self.__class__.__name__
        }


class ValidationError(BaseAppException):
    """
    Исключение для ошибок валидации данных.
    
    Используется при некорректных входных данных,
    нарушении ограничений или неправильном формате.
    """
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.field = field
        self.value = value
        
        error_details = details or {}
        if field:
            error_details["field"] = field
        if value is not None:
            error_details["invalid_value"] = str(value)
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=error_details
        )


class BusinessLogicError(BaseAppException):
    """
    Исключение для нарушения бизнес-правил.
    
    Используется когда операция технически возможна,
    но нарушает бизнес-логику приложения.
    """
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.operation = operation
        
        error_details = details or {}
        if operation:
            error_details["failed_operation"] = operation
        
        super().__init__(
            message=message,
            error_code="BUSINESS_LOGIC_ERROR",
            details=error_details
        )


class AuthenticationError(BaseAppException):
    """
    Исключение для ошибок аутентификации.
    
    Используется при проблемах с входом в систему,
    недействительными токенами или учетными данными.
    """
    
    def __init__(
        self,
        message: str,
        auth_method: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.auth_method = auth_method
        
        error_details = details or {}
        if auth_method:
            error_details["authentication_method"] = auth_method
        
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details=error_details
        )


class AuthorizationError(BaseAppException):
    """
    Исключение для ошибок авторизации.
    
    Используется при недостатке прав доступа
    к ресурсам или операциям.
    """
    
    def __init__(
        self,
        message: str,
        required_permission: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.required_permission = required_permission
        self.resource = resource
        
        error_details = details or {}
        if required_permission:
            error_details["required_permission"] = required_permission
        if resource:
            error_details["protected_resource"] = resource
        
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details=error_details
        )


class NotFoundError(BaseAppException):
    """
    Исключение для случаев, когда ресурс не найден.
    
    Используется при попытке доступа к несуществующим
    пользователям, сообщениям, диалогам и т.д.
    """
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.resource_type = resource_type
        self.resource_id = resource_id
        
        error_details = details or {}
        if resource_type:
            error_details["resource_type"] = resource_type
        if resource_id:
            error_details["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            error_code="NOT_FOUND_ERROR",
            details=error_details
        )


class ExternalServiceError(BaseAppException):
    """
    Исключение для ошибок внешних сервисов.
    
    Используется при проблемах с Avito API, Gemini API
    и другими внешними интеграциями.
    """
    
    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.service_name = service_name
        self.status_code = status_code
        self.response_data = response_data
        
        error_details = details or {}
        if service_name:
            error_details["service_name"] = service_name
        if status_code:
            error_details["status_code"] = status_code
        if response_data:
            error_details["response_data"] = response_data
        
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=error_details
        )


class RateLimitError(BaseAppException):
    """
    Исключение для превышения лимитов запросов.
    
    Используется при превышении rate limits API
    или лимитов подписки пользователя.
    """
    
    def __init__(
        self,
        message: str,
        limit_type: Optional[str] = None,
        current_usage: Optional[int] = None,
        limit_value: Optional[int] = None,
        reset_time: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.limit_type = limit_type
        self.current_usage = current_usage
        self.limit_value = limit_value
        self.reset_time = reset_time
        
        error_details = details or {}
        if limit_type:
            error_details["limit_type"] = limit_type
        if current_usage is not None:
            error_details["current_usage"] = current_usage
        if limit_value is not None:
            error_details["limit_value"] = limit_value
        if reset_time:
            error_details["reset_time"] = reset_time
        
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            details=error_details
        )


class ConfigurationError(BaseAppException):
    """
    Исключение для ошибок конфигурации.
    
    Используется при проблемах с настройками приложения,
    отсутствующими переменными окружения или неправильной конфигурацией.
    """
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.config_key = config_key
        
        error_details = details or {}
        if config_key:
            error_details["config_key"] = config_key
        
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details=error_details
        )


class AIServiceError(BaseAppException):
    """
    Исключение для ошибок ИИ-сервисов.
    
    Используется при проблемах с Gemini API,
    ошибках генерации ответов или анализа текста.
    """
    
    def __init__(
        self,
        message: str,
        ai_operation: Optional[str] = None,
        model_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.ai_operation = ai_operation
        self.model_name = model_name
        
        error_details = details or {}
        if ai_operation:
            error_details["ai_operation"] = ai_operation
        if model_name:
            error_details["model_name"] = model_name
        
        super().__init__(
            message=message,
            error_code="AI_SERVICE_ERROR",
            details=error_details
        )


class DatabaseError(BaseAppException):
    """
    Исключение для ошибок базы данных.
    
    Используется при проблемах с подключением к БД,
    нарушении ограничений или ошибках транзакций.
    """
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.operation = operation
        self.table = table
        
        error_details = details or {}
        if operation:
            error_details["database_operation"] = operation
        if table:
            error_details["table"] = table
        
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details=error_details
        )


# Функции-помощники для создания исключений

def validation_error(message: str, field: str = None, value: Any = None) -> ValidationError:
    """Создает ValidationError с упрощенным интерфейсом."""
    return ValidationError(message=message, field=field, value=value)


def business_error(message: str, operation: str = None) -> BusinessLogicError:
    """Создает BusinessLogicError с упрощенным интерфейсом."""
    return BusinessLogicError(message=message, operation=operation)


def auth_error(message: str, method: str = None) -> AuthenticationError:
    """Создает AuthenticationError с упрощенным интерфейсом."""
    return AuthenticationError(message=message, auth_method=method)


def permission_error(message: str, permission: str = None, resource: str = None) -> AuthorizationError:
    """Создает AuthorizationError с упрощенным интерфейсом."""
    return AuthorizationError(
        message=message,
        required_permission=permission,
        resource=resource
    )


def not_found_error(message: str, resource_type: str = None, resource_id: str = None) -> NotFoundError:
    """Создает NotFoundError с упрощенным интерфейсом."""
    return NotFoundError(
        message=message,
        resource_type=resource_type,
        resource_id=resource_id
    )


def external_service_error(message: str, service: str = None, status_code: int = None) -> ExternalServiceError:
    """Создает ExternalServiceError с упрощенным интерфейсом."""
    return ExternalServiceError(
        message=message,
        service_name=service,
        status_code=status_code
    )


def ai_error(message: str, operation: str = None, model: str = None) -> AIServiceError:
    """Создает AIServiceError с упрощенным интерфейсом."""
    return AIServiceError(
        message=message,
        ai_operation=operation,
        model_name=model
    )