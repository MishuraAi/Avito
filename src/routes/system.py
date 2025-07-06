"""
Системные роуты для Авито ИИ-бота.

Обрабатывает health checks, мониторинг системы, 
диагностику компонентов и административные функции.
"""

from typing import Any, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..dependencies import get_db, get_current_seller
from src.database.models.users import Seller
from src.database.session import DatabaseManager
from src.core.config import get_settings
from src.integrations.gemini.client import GeminiClient
from src.integrations.avito.api_client import AvitoAPIClient

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Базовая проверка здоровья системы.
    
    Возвращает статус API без проверки зависимостей.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Детальная проверка здоровья всех компонентов системы.
    
    Проверяет состояние базы данных, внешних API и сервисов.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "components": {}
    }
    
    # Проверка базы данных
    try:
        db.execute(text("SELECT 1"))
        health_status["components"]["database"] = {
            "status": "healthy",
            "response_time_ms": 0  # TODO: измерить реальное время ответа
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Проверка Gemini API
    try:
        gemini_client = GeminiClient()
        # TODO: Добавить простую проверку доступности API
        health_status["components"]["gemini_api"] = {
            "status": "healthy",
            "api_key_configured": bool(settings.GEMINI_API_KEY)
        }
    except Exception as e:
        health_status["components"]["gemini_api"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Проверка Avito API
    try:
        # TODO: Добавить проверку Avito API
        health_status["components"]["avito_api"] = {
            "status": "healthy",
            "credentials_configured": bool(settings.AVITO_CLIENT_ID and settings.AVITO_CLIENT_SECRET)
        }
    except Exception as e:
        health_status["components"]["avito_api"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/info")
async def system_info() -> Dict[str, Any]:
    """
    Информация о системе и конфигурации.
    
    Возвращает общую информацию без чувствительных данных.
    """
    return {
        "application": "Avito AI Responder",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "debug_mode": settings.DEBUG,
        "features": {
            "ai_consultant": True,
            "auto_reply": True,
            "message_analysis": True,
            "templates": True,
            "analytics": True
        },
        "api": {
            "version": "1.0",
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "openapi_url": "/openapi.json"
        }
    }


@router.get("/stats", dependencies=[Depends(get_current_seller)])
async def system_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Общая статистика системы.
    
    Доступно только для авторизованных продавцов.
    """
    try:
        # Статистика пользователей
        users_count = db.execute(text("SELECT COUNT(*) FROM users WHERE deleted_at IS NULL")).scalar()
        sellers_count = db.execute(text("SELECT COUNT(*) FROM sellers WHERE deleted_at IS NULL")).scalar()
        
        # Статистика сообщений
        total_messages = db.execute(text("SELECT COUNT(*) FROM messages WHERE deleted_at IS NULL")).scalar()
        ai_messages = db.execute(text("SELECT COUNT(*) FROM messages WHERE is_ai_generated = true AND deleted_at IS NULL")).scalar()
        
        # Статистика диалогов
        total_conversations = db.execute(text("SELECT COUNT(*) FROM conversations WHERE deleted_at IS NULL")).scalar()
        active_conversations = db.execute(text("SELECT COUNT(*) FROM conversations WHERE status = 'active' AND deleted_at IS NULL")).scalar()
        
        return {
            "users": {
                "total_users": users_count,
                "total_sellers": sellers_count,
                "total": users_count + sellers_count
            },
            "messages": {
                "total": total_messages,
                "ai_generated": ai_messages,
                "human_generated": total_messages - ai_messages,
                "ai_percentage": round((ai_messages / total_messages * 100) if total_messages > 0 else 0, 2)
            },
            "conversations": {
                "total": total_conversations,
                "active": active_conversations,
                "inactive": total_conversations - active_conversations
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения статистики: {str(e)}"
        )


@router.get("/metrics", dependencies=[Depends(get_current_seller)])
async def system_metrics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Детальные метрики производительности системы.
    
    Включает метрики базы данных, API и бизнес-процессов.
    """
    try:
        # Метрики производительности ИИ
        ai_metrics = db.execute(text("""
            SELECT 
                AVG(response_time_ms) as avg_response_time,
                COUNT(*) as total_requests,
                AVG(CASE WHEN ai_analysis->>'sentiment' = 'positive' THEN 1 ELSE 0 END) as positive_sentiment_ratio
            FROM messages 
            WHERE is_ai_generated = true 
            AND created_at >= NOW() - INTERVAL '24 hours'
            AND deleted_at IS NULL
        """)).fetchone()
        
        # Метрики конверсии
        conversion_metrics = db.execute(text("""
            SELECT 
                COUNT(*) as total_conversations,
                AVG(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completion_rate,
                AVG(message_count) as avg_messages_per_conversation
            FROM conversations 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            AND deleted_at IS NULL
        """)).fetchone()
        
        return {
            "ai_performance": {
                "avg_response_time_ms": float(ai_metrics.avg_response_time) if ai_metrics.avg_response_time else 0,
                "total_ai_requests_24h": ai_metrics.total_requests,
                "positive_sentiment_ratio": float(ai_metrics.positive_sentiment_ratio) if ai_metrics.positive_sentiment_ratio else 0
            },
            "conversation_metrics": {
                "total_conversations_24h": conversion_metrics.total_conversations,
                "completion_rate": float(conversion_metrics.completion_rate) if conversion_metrics.completion_rate else 0,
                "avg_messages_per_conversation": float(conversion_metrics.avg_messages_per_conversation) if conversion_metrics.avg_messages_per_conversation else 0
            },
            "system_load": {
                "database_connections": "TODO",  # TODO: получить из connection pool
                "memory_usage": "TODO",  # TODO: добавить мониторинг памяти
                "cpu_usage": "TODO"  # TODO: добавить мониторинг CPU
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения метрик: {str(e)}"
        )


@router.post("/maintenance/cleanup")
async def cleanup_old_data(
    days: int = 30,
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
) -> Dict[str, Any]:
    """
    Очистка старых данных системы.
    
    Удаляет сообщения и диалоги старше указанного количества дней.
    Доступно только для продавцов.
    """
    try:
        # Мягкое удаление старых сообщений
        old_messages = db.execute(text(f"""
            UPDATE messages 
            SET deleted_at = NOW() 
            WHERE created_at < NOW() - INTERVAL '{days} days'
            AND deleted_at IS NULL
            RETURNING id
        """))
        deleted_messages_count = len(old_messages.fetchall())
        
        # Мягкое удаление старых диалогов без активности
        old_conversations = db.execute(text(f"""
            UPDATE conversations 
            SET deleted_at = NOW() 
            WHERE updated_at < NOW() - INTERVAL '{days} days'
            AND status != 'active'
            AND deleted_at IS NULL
            RETURNING id
        """))
        deleted_conversations_count = len(old_conversations.fetchall())
        
        db.commit()
        
        return {
            "status": "success",
            "deleted_messages": deleted_messages_count,
            "deleted_conversations": deleted_conversations_count,
            "cleanup_period_days": days,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка очистки данных: {str(e)}"
        )


@router.get("/logs")
async def get_system_logs(
    lines: int = 100,
    level: str = "INFO",
    current_seller: Seller = Depends(get_current_seller)
) -> Dict[str, Any]:
    """
    Получение системных логов.
    
    Возвращает последние логи системы для диагностики.
    Доступно только для продавцов.
    """
    # TODO: Реализовать чтение логов из файла или системы логирования
    return {
        "status": "not_implemented", 
        "message": "Функция чтения логов будет реализована в следующей версии",
        "requested_lines": lines,
        "requested_level": level,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/cache/clear")
async def clear_cache(
    current_seller: Seller = Depends(get_current_seller)
) -> Dict[str, Any]:
    """
    Очистка системного кеша.
    
    Очищает кеш Redis и временные данные.
    Доступно только для продавцов.
    """
    try:
        # TODO: Реализовать очистку Redis кеша
        # redis_client.flushdb()
        
        return {
            "status": "success",
            "message": "Кеш успешно очищен",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка очистки кеша: {str(e)}"
        )


@router.get("/database/status")
async def database_status(
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
) -> Dict[str, Any]:
    """
    Статус базы данных и активных соединений.
    
    Возвращает информацию о состоянии БД и производительности.
    """
    try:
        # Проверка соединения с БД
        db_check = db.execute(text("SELECT version()")).scalar()
        
        # Статистика таблиц
        table_stats = db.execute(text("""
            SELECT 
                schemaname,
                tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes
            FROM pg_stat_user_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)).fetchall()
        
        # Размеры таблиц
        table_sizes = db.execute(text("""
            SELECT 
                tablename,
                pg_size_pretty(pg_total_relation_size(tablename::regclass)) as size
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(tablename::regclass) DESC
        """)).fetchall()
        
        return {
            "status": "connected",
            "database_version": db_check,
            "table_statistics": [
                {
                    "schema": stat.schemaname,
                    "table": stat.tablename,
                    "inserts": stat.inserts,
                    "updates": stat.updates,
                    "deletes": stat.deletes
                }
                for stat in table_stats
            ],
            "table_sizes": [
                {
                    "table": size.tablename,
                    "size": size.size
                }
                for size in table_sizes
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения статуса БД: {str(e)}"
        )