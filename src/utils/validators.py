"""
Валидаторы для проверки данных.

Содержит функции для валидации различных типов данных:
email, телефонов, сообщений, учетных данных и т.д.
"""

import re
from typing import Dict, Any, List, Optional
from email_validator import validate_email as email_validator, EmailNotValidError


def validate_email(email: str) -> bool:
    """
    Валидирует email адрес.
    
    Args:
        email: Email адрес для проверки
        
    Returns:
        True если email корректный, False иначе
    """
    if not email or not isinstance(email, str):
        return False
    
    try:
        # Используем библиотеку email-validator для проверки
        email_validator(email)
        return True
    except EmailNotValidError:
        return False


def validate_phone(phone: str) -> bool:
    """
    Валидирует номер телефона.
    
    Поддерживает российские и международные форматы.
    
    Args:
        phone: Номер телефона для проверки
        
    Returns:
        True если номер корректный, False иначе
    """
    if not phone or not isinstance(phone, str):
        return False
    
    # Удаляем все символы кроме цифр и +
    cleaned_phone = re.sub(r'[^\d+]', '', phone)
    
    # Паттерны для различных форматов
    patterns = [
        r'^\+7\d{10}$',           # +7XXXXXXXXXX (Россия)
        r'^8\d{10}$',             # 8XXXXXXXXXX (Россия)
        r'^7\d{10}$',             # 7XXXXXXXXXX (Россия)
        r'^\+\d{10,15}$',         # Международный формат
        r'^\d{10,11}$'            # Локальный формат
    ]
    
    for pattern in patterns:
        if re.match(pattern, cleaned_phone):
            return True
    
    return False


def validate_message_content(content: str) -> bool:
    """
    Валидирует содержимое сообщения.
    
    Проверяет длину, наличие запрещенного контента и формат.
    
    Args:
        content: Содержимое сообщения
        
    Returns:
        True если сообщение корректно, False иначе
    """
    if not content or not isinstance(content, str):
        return False
    
    # Проверяем длину
    content = content.strip()
    if len(content) < 1:
        return False
    if len(content) > 4000:  # Максимальная длина сообщения
        return False
    
    # Проверяем на спам-паттерны
    spam_patterns = [
        r'(https?://\S+\.\S+){3,}',  # Много ссылок
        r'[A-ZА-Я]{10,}',            # Много заглавных букв подряд
        r'(.)\1{5,}',                # Повторяющиеся символы
        r'\d{4,}\s*\d{4,}\s*\d{4,}', # Подозрительные номера
    ]
    
    for pattern in spam_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return False
    
    # Проверяем на запрещенные слова (базовый список)
    forbidden_words = [
        'спам', 'развод', 'мошенник', 'кидала',
        'xxx', 'секс', 'проститутка', 'наркотик'
    ]
    
    content_lower = content.lower()
    for word in forbidden_words:
        if word in content_lower:
            return False
    
    return True


def validate_password(password: str) -> Dict[str, Any]:
    """
    Валидирует пароль с детальной информацией.
    
    Args:
        password: Пароль для проверки
        
    Returns:
        Словарь с результатами валидации
    """
    result = {
        "valid": False,
        "score": 0,
        "errors": [],
        "suggestions": []
    }
    
    if not password or not isinstance(password, str):
        result["errors"].append("Пароль не может быть пустым")
        return result
    
    # Проверка длины
    if len(password) < 8:
        result["errors"].append("Пароль должен содержать минимум 8 символов")
    elif len(password) >= 12:
        result["score"] += 2
    else:
        result["score"] += 1
    
    # Проверка наличия заглавных букв
    if not re.search(r'[A-ZА-Я]', password):
        result["errors"].append("Пароль должен содержать заглавные буквы")
    else:
        result["score"] += 1
    
    # Проверка наличия строчных букв
    if not re.search(r'[a-zа-я]', password):
        result["errors"].append("Пароль должен содержать строчные буквы")
    else:
        result["score"] += 1
    
    # Проверка наличия цифр
    if not re.search(r'\d', password):
        result["errors"].append("Пароль должен содержать цифры")
    else:
        result["score"] += 1
    
    # Проверка наличия специальных символов
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        result["suggestions"].append("Добавьте специальные символы для большей безопасности")
    else:
        result["score"] += 2
    
    # Проверка на общие пароли
    common_passwords = [
        'password', '123456', 'qwerty', 'abc123', 'password123',
        'admin', 'letmein', 'welcome', 'monkey', 'dragon'
    ]
    
    if password.lower() in common_passwords:
        result["errors"].append("Пароль слишком простой и часто используется")
        result["score"] = 0
    
    # Проверка на повторяющиеся символы
    if re.search(r'(.)\1{2,}', password):
        result["suggestions"].append("Избегайте повторяющихся символов")
        result["score"] = max(0, result["score"] - 1)
    
    # Определяем валидность
    result["valid"] = len(result["errors"]) == 0 and result["score"] >= 3
    
    # Добавляем общие рекомендации
    if result["score"] < 5:
        result["suggestions"].append("Используйте комбинацию букв, цифр и символов")
    
    return result


def validate_avito_credentials(credentials: Dict[str, str]) -> bool:
    """
    Валидирует учетные данные для Avito API.
    
    Args:
        credentials: Словарь с учетными данными
        
    Returns:
        True если учетные данные корректны, False иначе
    """
    if not isinstance(credentials, dict):
        return False
    
    required_fields = ['client_id', 'client_secret']
    
    # Проверяем наличие обязательных полей
    for field in required_fields:
        if field not in credentials:
            return False
        if not credentials[field] or not isinstance(credentials[field], str):
            return False
        if len(credentials[field].strip()) < 10:  # Минимальная длина ключей
            return False
    
    # Проверяем формат client_id (обычно числовой)
    client_id = credentials['client_id'].strip()
    if not client_id.isdigit():
        return False
    
    # Проверяем формат client_secret (обычно алфавитно-цифровой)
    client_secret = credentials['client_secret'].strip()
    if not re.match(r'^[a-zA-Z0-9_-]+$', client_secret):
        return False
    
    return True


def validate_uuid(uuid_string: str) -> bool:
    """
    Валидирует UUID строку.
    
    Args:
        uuid_string: Строка UUID для проверки
        
    Returns:
        True если UUID корректен, False иначе
    """
    if not uuid_string or not isinstance(uuid_string, str):
        return False
    
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(uuid_pattern, uuid_string.lower()))


def validate_json_data(data: Any, schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Валидирует JSON данные по схеме.
    
    Args:
        data: Данные для валидации
        schema: Схема валидации
        
    Returns:
        Результат валидации с ошибками
    """
    result = {
        "valid": True,
        "errors": [],
        "warnings": []
    }
    
    def validate_field(value: Any, field_schema: Dict[str, Any], field_name: str):
        # Проверка типа
        expected_type = field_schema.get('type')
        if expected_type and not isinstance(value, expected_type):
            result["errors"].append(f"Поле '{field_name}' должно быть типа {expected_type.__name__}")
            result["valid"] = False
            return
        
        # Проверка обязательности
        if field_schema.get('required', False) and (value is None or value == ""):
            result["errors"].append(f"Поле '{field_name}' обязательно для заполнения")
            result["valid"] = False
            return
        
        # Проверка длины для строк
        if isinstance(value, str):
            min_length = field_schema.get('min_length')
            max_length = field_schema.get('max_length')
            
            if min_length and len(value) < min_length:
                result["errors"].append(f"Поле '{field_name}' должно содержать минимум {min_length} символов")
                result["valid"] = False
            
            if max_length and len(value) > max_length:
                result["errors"].append(f"Поле '{field_name}' должно содержать максимум {max_length} символов")
                result["valid"] = False
        
        # Проверка диапазона для чисел
        if isinstance(value, (int, float)):
            min_value = field_schema.get('min_value')
            max_value = field_schema.get('max_value')
            
            if min_value is not None and value < min_value:
                result["errors"].append(f"Поле '{field_name}' должно быть не менее {min_value}")
                result["valid"] = False
            
            if max_value is not None and value > max_value:
                result["errors"].append(f"Поле '{field_name}' должно быть не более {max_value}")
                result["valid"] = False
        
        # Проверка допустимых значений
        allowed_values = field_schema.get('allowed_values')
        if allowed_values and value not in allowed_values:
            result["errors"].append(f"Поле '{field_name}' должно быть одним из: {', '.join(map(str, allowed_values))}")
            result["valid"] = False
        
        # Кастомный валидатор
        custom_validator = field_schema.get('validator')
        if custom_validator and callable(custom_validator):
            try:
                if not custom_validator(value):
                    result["errors"].append(f"Поле '{field_name}' не прошло валидацию")
                    result["valid"] = False
            except Exception as e:
                result["errors"].append(f"Ошибка валидации поля '{field_name}': {str(e)}")
                result["valid"] = False
    
    # Валидируем каждое поле
    if isinstance(data, dict):
        for field_name, field_schema in schema.items():
            value = data.get(field_name)
            validate_field(value, field_schema, field_name)
        
        # Проверяем наличие неожиданных полей
        unexpected_fields = set(data.keys()) - set(schema.keys())
        if unexpected_fields:
            result["warnings"].append(f"Неожиданные поля: {', '.join(unexpected_fields)}")
    else:
        result["errors"].append("Данные должны быть объектом (словарем)")
        result["valid"] = False
    
    return result


def validate_business_hours(start_time: str, end_time: str) -> bool:
    """
    Валидирует рабочие часы.
    
    Args:
        start_time: Время начала в формате "HH:MM"
        end_time: Время окончания в формате "HH:MM"
        
    Returns:
        True если время корректно, False иначе
    """
    time_pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
    
    if not re.match(time_pattern, start_time) or not re.match(time_pattern, end_time):
        return False
    
    # Преобразуем в минуты для сравнения
    def time_to_minutes(time_str: str) -> int:
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes
    
    start_minutes = time_to_minutes(start_time)
    end_minutes = time_to_minutes(end_time)
    
    # Время начала должно быть раньше времени окончания
    return start_minutes < end_minutes


def validate_url(url: str) -> bool:
    """
    Валидирует URL адрес.
    
    Args:
        url: URL для проверки
        
    Returns:
        True если URL корректен, False иначе
    """
    if not url or not isinstance(url, str):
        return False
    
    url_pattern = r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?$'
    return bool(re.match(url_pattern, url))


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """
    Валидирует расширение файла.
    
    Args:
        filename: Имя файла
        allowed_extensions: Список разрешенных расширений
        
    Returns:
        True если расширение разрешено, False иначе
    """
    if not filename or not isinstance(filename, str):
        return False
    
    if not allowed_extensions:
        return True
    
    file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
    return file_extension in [ext.lower().lstrip('.') for ext in allowed_extensions]


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Очищает пользовательский ввод от потенциально опасного контента.
    
    Args:
        text: Текст для очистки
        max_length: Максимальная длина текста
        
    Returns:
        Очищенный текст
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Удаляем HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    
    # Удаляем потенциально опасные символы
    text = re.sub(r'[<>"\']', '', text)
    
    # Обрезаем до максимальной длины
    text = text[:max_length]
    
    # Удаляем лишние пробелы
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text