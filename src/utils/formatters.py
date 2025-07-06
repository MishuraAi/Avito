"""
Форматтеры для преобразования данных.

Содержит функции для форматирования различных типов данных
для отображения, API ответов и интеграций.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import re


def format_user_activity(activity_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Форматирует данные активности пользователя для отображения.
    
    Args:
        activity_data: Сырые данные активности
        
    Returns:
        Отформатированные данные активности
    """
    if not activity_data:
        return {
            "total_messages": 0,
            "avg_response_time": "Нет данных",
            "activity_level": "Низкая",
            "last_activity": "Никогда",
            "engagement_score": 0
        }
    
    # Форматируем время ответа
    avg_response_time = activity_data.get("avg_response_time", 0)
    if avg_response_time > 0:
        formatted_response_time = format_duration(avg_response_time)
    else:
        formatted_response_time = "Нет данных"
    
    # Форматируем последнюю активность
    last_activity = activity_data.get("last_activity")
    if last_activity:
        if isinstance(last_activity, str):
            last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
        formatted_last_activity = format_relative_time(last_activity)
    else:
        formatted_last_activity = "Никогда"
    
    # Определяем уровень активности
    total_messages = activity_data.get("total_messages", 0)
    if total_messages > 100:
        activity_level = "Высокая"
    elif total_messages > 20:
        activity_level = "Средняя"
    else:
        activity_level = "Низкая"
    
    return {
        "total_messages": total_messages,
        "total_conversations": activity_data.get("total_conversations", 0),
        "avg_response_time": formatted_response_time,
        "activity_level": activity_level,
        "last_activity": formatted_last_activity,
        "engagement_score": round(activity_data.get("engagement_score", 0), 1),
        "most_active_hours": activity_data.get("most_active_hours", []),
        "response_rate": f"{activity_data.get('response_rate', 0) * 100:.1f}%"
    }


def format_seller_stats(stats_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Форматирует статистику продавца для отображения.
    
    Args:
        stats_data: Сырые данные статистики
        
    Returns:
        Отформатированная статистика
    """
    if not stats_data:
        return {
            "total_messages": 0,
            "ai_usage": "0%",
            "conversion_rate": "0%",
            "avg_response_time": "Нет данных",
            "customer_satisfaction": 0
        }
    
    # Форматируем использование ИИ
    total_messages = stats_data.get("total_messages", 0)
    ai_messages = stats_data.get("ai_generated_messages", 0)
    ai_usage_percent = (ai_messages / total_messages * 100) if total_messages > 0 else 0
    
    # Форматируем коэффициент конверсии
    conversion_rate = stats_data.get("conversion_rate", 0)
    
    # Форматируем время ответа
    avg_response_time = stats_data.get("avg_response_time", 0)
    formatted_response_time = format_duration(avg_response_time) if avg_response_time > 0 else "Нет данных"
    
    return {
        "total_messages": total_messages,
        "ai_generated_messages": ai_messages,
        "manual_messages": total_messages - ai_messages,
        "ai_usage": f"{ai_usage_percent:.1f}%",
        "total_conversations": stats_data.get("total_conversations", 0),
        "active_conversations": stats_data.get("active_conversations", 0),
        "conversion_rate": f"{conversion_rate:.1f}%",
        "avg_response_time": formatted_response_time,
        "customer_satisfaction": round(stats_data.get("customer_satisfaction", 0), 1),
        "monthly_stats": stats_data.get("monthly_stats", {}),
        "performance_metrics": stats_data.get("performance_metrics", {})
    }


def format_message_for_ai(message) -> Dict[str, Any]:
    """
    Форматирует сообщение для передачи в ИИ.
    
    Args:
        message: Объект сообщения
        
    Returns:
        Отформатированное сообщение для ИИ
    """
    return {
        "content": message.content.strip(),
        "message_type": message.message_type,
        "context": {
            "sender_id": str(message.sender_id),
            "recipient_id": str(message.recipient_id),
            "conversation_id": str(message.conversation_id),
            "created_at": message.created_at.isoformat(),
            "metadata": message.metadata or {}
        },
        "previous_analysis": message.ai_analysis
    }


def format_ai_response(ai_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Форматирует ответ от ИИ для сохранения.
    
    Args:
        ai_response: Сырой ответ от ИИ
        
    Returns:
        Отформатированный ответ
    """
    return {
        "sentiment": ai_response.get("sentiment", "neutral"),
        "intent": ai_response.get("intent", "unknown"),
        "urgency": ai_response.get("urgency", "medium"),
        "keywords": ai_response.get("keywords", []),
        "confidence_score": round(ai_response.get("confidence_score", 0.5), 3),
        "suggested_response": ai_response.get("suggested_response"),
        "analysis_details": {
            "language": ai_response.get("language", "ru"),
            "formality": ai_response.get("formality", "neutral"),
            "emotion_scores": ai_response.get("emotion_scores", {}),
            "topics": ai_response.get("topics", [])
        },
        "processed_at": datetime.utcnow().isoformat()
    }


def format_avito_message(avito_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Форматирует сообщение из Avito API для нашей системы.
    
    Args:
        avito_data: Данные сообщения от Avito
        
    Returns:
        Отформатированное сообщение
    """
    return {
        "sender_id": avito_data.get("from", {}).get("id"),
        "content": avito_data.get("content", {}).get("text", ""),
        "avito_message_id": avito_data.get("id"),
        "listing_id": avito_data.get("item", {}).get("id"),
        "created_at": avito_data.get("created"),
        "message_type": "text",
        "metadata": {
            "source": "avito",
            "original_data": avito_data
        }
    }


def format_avito_listing(listing_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Форматирует объявление из Avito API.
    
    Args:
        listing_data: Данные объявления от Avito
        
    Returns:
        Отформатированное объявление
    """
    return {
        "avito_id": listing_data.get("id"),
        "title": listing_data.get("title", ""),
        "description": listing_data.get("description", ""),
        "price": listing_data.get("price", {}).get("value", 0),
        "currency": listing_data.get("price", {}).get("currency", "RUB"),
        "category": listing_data.get("category", {}).get("name", ""),
        "location": listing_data.get("geo", {}).get("name", ""),
        "status": listing_data.get("status", ""),
        "images": [img.get("url") for img in listing_data.get("images", [])],
        "created_at": listing_data.get("time_created"),
        "updated_at": listing_data.get("time_updated"),
        "views": listing_data.get("stats", {}).get("views", 0),
        "contacts": listing_data.get("stats", {}).get("contacts", 0),
        "url": listing_data.get("url", ""),
        "metadata": {
            "source": "avito",
            "original_data": listing_data
        }
    }


def format_phone_number(phone: str, format_type: str = "international") -> str:
    """
    Форматирует номер телефона в различные форматы.
    
    Args:
        phone: Номер телефона
        format_type: Тип форматирования ("international", "national", "e164")
        
    Returns:
        Отформатированный номер телефона
    """
    if not phone:
        return ""
    
    # Удаляем все символы кроме цифр и +
    digits = re.sub(r'[^\d+]', '', phone)
    
    # Нормализуем российские номера
    if digits.startswith('8') and len(digits) == 11:
        digits = '+7' + digits[1:]
    elif digits.startswith('7') and len(digits) == 11:
        digits = '+7' + digits[1:]
    elif not digits.startswith('+') and len(digits) == 10:
        digits = '+7' + digits
    
    if format_type == "international":
        # +7 (XXX) XXX-XX-XX
        if digits.startswith('+7') and len(digits) == 12:
            return f"+7 ({digits[2:5]}) {digits[5:8]}-{digits[8:10]}-{digits[10:12]}"
    elif format_type == "national":
        # 8 (XXX) XXX-XX-XX
        if digits.startswith('+7') and len(digits) == 12:
            return f"8 ({digits[2:5]}) {digits[5:8]}-{digits[8:10]}-{digits[10:12]}"
    elif format_type == "e164":
        # +7XXXXXXXXXX
        return digits
    
    return digits


def format_price(amount: float, currency: str = "RUB") -> str:
    """
    Форматирует цену с валютой.
    
    Args:
        amount: Сумма
        currency: Валюта
        
    Returns:
        Отформатированная цена
    """
    if amount is None:
        return "Цена не указана"
    
    currency_symbols = {
        "RUB": "₽",
        "USD": "$",
        "EUR": "€"
    }
    
    symbol = currency_symbols.get(currency, currency)
    
    # Форматируем с разделителями тысяч
    formatted_amount = f"{amount:,.0f}".replace(",", " ")
    
    return f"{formatted_amount} {symbol}"


def format_duration(seconds: float) -> str:
    """
    Форматирует продолжительность в читаемый формат.
    
    Args:
        seconds: Количество секунд
        
    Returns:
        Отформатированная продолжительность
    """
    if seconds < 60:
        return f"{int(seconds)} сек"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} мин"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        if minutes > 0:
            return f"{hours}ч {minutes}м"
        else:
            return f"{hours}ч"
    else:
        days = int(seconds / 86400)
        hours = int((seconds % 86400) / 3600)
        if hours > 0:
            return f"{days}д {hours}ч"
        else:
            return f"{days}д"


def format_relative_time(dt: datetime) -> str:
    """
    Форматирует время относительно текущего момента.
    
    Args:
        dt: Datetime объект
        
    Returns:
        Относительное время
    """
    now = datetime.utcnow()
    if dt.tzinfo is not None:
        # Если есть timezone info, приводим к UTC
        now = now.replace(tzinfo=dt.tzinfo)
    
    diff = now - dt
    
    if diff.total_seconds() < 60:
        return "Только что"
    elif diff.total_seconds() < 3600:
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} мин назад"
    elif diff.total_seconds() < 86400:
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} ч назад"
    elif diff.days == 1:
        return "Вчера"
    elif diff.days < 7:
        return f"{diff.days} дн назад"
    elif diff.days < 30:
        weeks = diff.days // 7
        return f"{weeks} нед назад"
    elif diff.days < 365:
        months = diff.days // 30
        return f"{months} мес назад"
    else:
        years = diff.days // 365
        return f"{years} г назад"


def format_file_size(size_bytes: int) -> str:
    """
    Форматирует размер файла в читаемый формат.
    
    Args:
        size_bytes: Размер в байтах
        
    Returns:
        Отформатированный размер файла
    """
    if size_bytes < 1024:
        return f"{size_bytes} Б"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} КБ"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} МБ"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} ГБ"


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Форматирует число как процент.
    
    Args:
        value: Значение (0.0 - 1.0)
        decimals: Количество знаков после запятой
        
    Returns:
        Отформатированный процент
    """
    return f"{value * 100:.{decimals}f}%"


def format_json_pretty(data: Any) -> str:
    """
    Форматирует JSON для красивого отображения.
    
    Args:
        data: Данные для форматирования
        
    Returns:
        Отформатированная JSON строка
    """
    return json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
        default=str  # Для обработки datetime и других объектов
    )


def format_search_highlight(text: str, query: str) -> str:
    """
    Подсвечивает поисковый запрос в тексте.
    
    Args:
        text: Исходный текст
        query: Поисковый запрос
        
    Returns:
        Текст с подсветкой
    """
    if not query or not text:
        return text
    
    # Экранируем специальные символы в запросе
    escaped_query = re.escape(query)
    
    # Подсвечиваем совпадения (без учета регистра)
    highlighted = re.sub(
        f'({escaped_query})',
        r'<mark>\1</mark>',
        text,
        flags=re.IGNORECASE
    )
    
    return highlighted


def format_user_mention(username: str, user_id: str) -> str:
    """
    Форматирует упоминание пользователя.
    
    Args:
        username: Имя пользователя
        user_id: ID пользователя
        
    Returns:
        Отформатированное упоминание
    """
    return f"@{username} (ID: {user_id[:8]}...)"


def format_error_message(error: Exception) -> Dict[str, Any]:
    """
    Форматирует сообщение об ошибке для API ответа.
    
    Args:
        error: Объект исключения
        
    Returns:
        Отформатированное сообщение об ошибке
    """
    error_type = type(error).__name__
    error_message = str(error)
    
    # Специальная обработка для кастомных исключений
    if hasattr(error, 'to_dict'):
        return error.to_dict()
    
    return {
        "error_type": error_type,
        "message": error_message,
        "timestamp": datetime.utcnow().isoformat()
    }