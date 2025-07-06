"""
Вспомогательные функции для Авито ИИ-бота.

Содержит общие утилиты, которые используются в различных
частях приложения.
"""

import uuid
import hashlib
import secrets
import re
import html
from typing import Any, List, Dict, Optional, Tuple
from datetime import datetime, timezone
from difflib import SequenceMatcher
import phonenumbers
from phonenumbers import NumberParseException


def generate_unique_id() -> str:
    """
    Генерирует уникальный ID.
    
    Returns:
        Уникальный идентификатор в виде строки
    """
    return str(uuid.uuid4())


def generate_short_id(length: int = 8) -> str:
    """
    Генерирует короткий уникальный ID.
    
    Args:
        length: Длина ID
        
    Returns:
        Короткий ID
    """
    return secrets.token_urlsafe(length)[:length]


def generate_hash(data: str, algorithm: str = "sha256") -> str:
    """
    Генерирует хеш строки.
    
    Args:
        data: Данные для хеширования
        algorithm: Алгоритм хеширования
        
    Returns:
        Хеш строки
    """
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data.encode('utf-8'))
    return hash_obj.hexdigest()


def sanitize_html(text: str) -> str:
    """
    Очищает текст от HTML тегов и опасного контента.
    
    Args:
        text: Исходный текст
        
    Returns:
        Очищенный текст
    """
    if not text:
        return ""
    
    # Удаляем HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    
    # Декодируем HTML сущности
    text = html.unescape(text)
    
    # Удаляем потенциально опасные символы
    text = re.sub(r'[<>"\']', '', text)
    
    # Нормализуем пробелы
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Обрезает текст до указанной длины.
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина
        suffix: Суффикс для обрезанного текста
        
    Returns:
        Обрезанный текст
    """
    if not text or len(text) <= max_length:
        return text
    
    # Обрезаем по словам, если возможно
    if ' ' in text[:max_length]:
        truncated = text[:max_length].rsplit(' ', 1)[0]
        return truncated + suffix
    else:
        return text[:max_length - len(suffix)] + suffix


def parse_phone_number(phone: str, region: str = "RU") -> Optional[Dict[str, Any]]:
    """
    Парсит номер телефона с помощью библиотеки phonenumbers.
    
    Args:
        phone: Номер телефона
        region: Регион по умолчанию
        
    Returns:
        Информация о номере телефона или None
    """
    try:
        parsed = phonenumbers.parse(phone, region)
        
        if phonenumbers.is_valid_number(parsed):
            return {
                "international": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
                "national": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
                "e164": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
                "country_code": parsed.country_code,
                "national_number": parsed.national_number,
                "region": phonenumbers.geocoder.description_for_number(parsed, "ru"),
                "carrier": phonenumbers.carrier.name_for_number(parsed, "ru"),
                "is_mobile": phonenumbers.number_type(parsed) == phonenumbers.PhoneNumberType.MOBILE
            }
    except NumberParseException:
        pass
    
    return None


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Вычисляет схожесть двух текстов.
    
    Args:
        text1: Первый текст
        text2: Второй текст
        
    Returns:
        Коэффициент схожести (0.0 - 1.0)
    """
    if not text1 or not text2:
        return 0.0
    
    # Нормализуем тексты
    text1 = text1.lower().strip()
    text2 = text2.lower().strip()
    
    # Используем SequenceMatcher для вычисления схожести
    similarity = SequenceMatcher(None, text1, text2).ratio()
    return similarity


def extract_keywords(text: str, min_length: int = 3, max_keywords: int = 10) -> List[str]:
    """
    Извлекает ключевые слова из текста.
    
    Args:
        text: Исходный текст
        min_length: Минимальная длина слова
        max_keywords: Максимальное количество ключевых слов
        
    Returns:
        Список ключевых слов
    """
    if not text:
        return []
    
    # Очищаем текст
    text = sanitize_html(text.lower())
    
    # Удаляем знаки препинания и разбиваем на слова
    words = re.findall(r'\b[а-яё\w]+\b', text)
    
    # Фильтруем стоп-слова
    stop_words = {
        'и', 'в', 'на', 'с', 'по', 'для', 'от', 'до', 'из', 'к', 'о', 'у', 'за',
        'при', 'над', 'под', 'между', 'через', 'без', 'про', 'это', 'то', 'что',
        'как', 'так', 'все', 'вся', 'всё', 'мне', 'тебе', 'нас', 'вас', 'них',
        'или', 'но', 'а', 'да', 'нет', 'не', 'ни', 'уже', 'еще', 'ещё', 'только',
        'даже', 'ведь', 'же', 'ли', 'бы', 'чтобы', 'если', 'когда', 'где', 'куда'
    }
    
    # Фильтруем слова
    keywords = []
    for word in words:
        if (len(word) >= min_length and 
            word not in stop_words and 
            not word.isdigit()):
            keywords.append(word)
    
    # Подсчитываем частоту и возвращаем самые частые
    word_freq = {}
    for word in keywords:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Сортируем по частоте
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    
    return [word for word, freq in sorted_words[:max_keywords]]


def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Глубоко объединяет два словаря.
    
    Args:
        dict1: Первый словарь
        dict2: Второй словарь
        
    Returns:
        Объединенный словарь
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Разбивает список на чанки заданного размера.
    
    Args:
        lst: Исходный список
        chunk_size: Размер чанка
        
    Returns:
        Список чанков
    """
    chunks = []
    for i in range(0, len(lst), chunk_size):
        chunks.append(lst[i:i + chunk_size])
    return chunks


def safe_get_nested(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Безопасно получает значение из вложенного словаря.
    
    Args:
        data: Словарь с данными
        path: Путь к значению (например, "user.profile.name")
        default: Значение по умолчанию
        
    Returns:
        Значение или default
    """
    keys = path.split('.')
    current = data
    
    try:
        for key in keys:
            current = current[key]
        return current
    except (KeyError, TypeError):
        return default


def flatten_dict(data: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    Превращает вложенный словарь в плоский.
    
    Args:
        data: Исходный словарь
        parent_key: Родительский ключ
        sep: Разделитель ключей
        
    Returns:
        Плоский словарь
    """
    items = []
    
    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        
        if isinstance(value, dict):
            items.extend(flatten_dict(value, new_key, sep=sep).items())
        else:
            items.append((new_key, value))
    
    return dict(items)


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """
    Маскирует чувствительные данные.
    
    Args:
        data: Исходные данные
        mask_char: Символ для маскирования
        visible_chars: Количество видимых символов в начале и конце
        
    Returns:
        Замаскированные данные
    """
    if not data or len(data) <= visible_chars * 2:
        return mask_char * len(data) if data else ""
    
    start = data[:visible_chars]
    end = data[-visible_chars:]
    middle = mask_char * (len(data) - visible_chars * 2)
    
    return f"{start}{middle}{end}"


def convert_timezone(dt: datetime, target_timezone: str = "Europe/Moscow") -> datetime:
    """
    Конвертирует datetime в указанную временную зону.
    
    Args:
        dt: Исходная дата и время
        target_timezone: Целевая временная зона
        
    Returns:
        Конвертированная дата и время
    """
    try:
        import pytz
        
        if dt.tzinfo is None:
            # Если нет timezone info, считаем что это UTC
            dt = dt.replace(tzinfo=timezone.utc)
        
        target_tz = pytz.timezone(target_timezone)
        return dt.astimezone(target_tz)
    except ImportError:
        # Если pytz не установлен, возвращаем как есть
        return dt


def retry_operation(func, max_attempts: int = 3, delay: float = 1.0):
    """
    Декоратор для повторения операций при ошибках.
    
    Args:
        func: Функция для выполнения
        max_attempts: Максимальное количество попыток
        delay: Задержка между попытками
        
    Returns:
        Результат выполнения функции
    """
    import time
    
    def wrapper(*args, **kwargs):
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_attempts - 1:
                    time.sleep(delay * (attempt + 1))  # Экспоненциальная задержка
                
        raise last_exception
    
    return wrapper


def calculate_levenshtein_distance(s1: str, s2: str) -> int:
    """
    Вычисляет расстояние Левенштейна между двумя строками.
    
    Args:
        s1: Первая строка
        s2: Вторая строка
        
    Returns:
        Расстояние Левенштейна
    """
    if len(s1) < len(s2):
        return calculate_levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def normalize_text(text: str) -> str:
    """
    Нормализует текст для сравнения.
    
    Args:
        text: Исходный текст
        
    Returns:
        Нормализованный текст
    """
    if not text:
        return ""
    
    # Приводим к нижнему регистру
    text = text.lower()
    
    # Удаляем лишние пробелы
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Удаляем знаки препинания
    text = re.sub(r'[^\w\s]', '', text)
    
    return text


def get_file_extension(filename: str) -> str:
    """
    Извлекает расширение файла.
    
    Args:
        filename: Имя файла
        
    Returns:
        Расширение файла без точки
    """
    if '.' in filename:
        return filename.split('.')[-1].lower()
    return ""


def is_valid_json(json_string: str) -> bool:
    """
    Проверяет, является ли строка валидным JSON.
    
    Args:
        json_string: JSON строка
        
    Returns:
        True если JSON валидный, False иначе
    """
    try:
        import json
        json.loads(json_string)
        return True
    except (ValueError, TypeError):
        return False


def get_object_size(obj: Any) -> int:
    """
    Вычисляет размер объекта в байтах.
    
    Args:
        obj: Объект для измерения
        
    Returns:
        Размер в байтах
    """
    import sys
    import pickle
    
    try:
        return len(pickle.dumps(obj))
    except (TypeError, AttributeError):
        return sys.getsizeof(obj)


def create_slug(text: str, max_length: int = 50) -> str:
    """
    Создает URL-slug из текста.
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина slug
        
    Returns:
        URL-slug
    """
    if not text:
        return ""
    
    # Транслитерация кириллицы
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
    }
    
    # Приводим к нижнему регистру
    text = text.lower()
    
    # Транслитерируем
    result = ""
    for char in text:
        result += translit_map.get(char, char)
    
    # Заменяем все не-алфавитно-цифровые символы на дефисы
    result = re.sub(r'[^a-z0-9]+', '-', result)
    
    # Удаляем дефисы в начале и конце
    result = result.strip('-')
    
    # Обрезаем до максимальной длины
    if len(result) > max_length:
        result = result[:max_length].rstrip('-')
    
    return result