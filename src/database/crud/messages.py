"""
CRUD операции для сообщений и шаблонов.

Обрабатывает создание, чтение, обновление и удаление сообщений,
а также работу с шаблонами сообщений и ИИ-анализом.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text

from .base import CRUDBase
from ..models.messages import Message, MessageTemplate
from src.utils.exceptions import NotFoundError


class CRUDMessage(CRUDBase[Message, dict, dict]):
    """CRUD операции для сообщений."""
    
    def get_by_conversation(
        self,
        db: Session,
        conversation_id: UUID,
        skip: int = 0,
        limit: int = 50,
        order_by: str = "created_at"
    ) -> List[Message]:
        """
        Получает сообщения диалога с пагинацией.
        
        Args:
            db: Сессия базы данных
            conversation_id: ID диалога
            skip: Количество пропускаемых сообщений
            limit: Максимальное количество сообщений
            order_by: Поле для сортировки
            
        Returns:
            Список сообщений
        """
        query = db.query(self.model).filter(
            and_(
                self.model.conversation_id == conversation_id,
                self.model.deleted_at.is_(None)
            )
        )
        
        # Определяем порядок сортировки
        if order_by == "created_at":
            query = query.order_by(self.model.created_at)
        elif order_by == "created_at_desc":
            query = query.order_by(desc(self.model.created_at))
        
        return query.offset(skip).limit(limit).all()
    
    def get_filtered(
        self,
        db: Session,
        conversation_id: Optional[UUID] = None,
        sender_id: Optional[UUID] = None,
        recipient_id: Optional[UUID] = None,
        message_type: Optional[str] = None,
        is_ai_generated: Optional[bool] = None,
        since_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """
        Получает сообщения с множественной фильтрацией.
        
        Args:
            db: Сессия базы данных
            conversation_id: Фильтр по диалогу
            sender_id: Фильтр по отправителю
            recipient_id: Фильтр по получателю
            message_type: Фильтр по типу сообщения
            is_ai_generated: Фильтр по ИИ-генерации
            since_date: Фильтр по дате
            skip: Пропуск записей
            limit: Лимит записей
            
        Returns:
            Отфильтрованные сообщения
        """
        query = db.query(self.model).filter(self.model.deleted_at.is_(None))
        
        # Применяем фильтры
        if conversation_id:
            query = query.filter(self.model.conversation_id == conversation_id)
        
        if sender_id:
            query = query.filter(self.model.sender_id == sender_id)
        
        if recipient_id:
            query = query.filter(self.model.recipient_id == recipient_id)
        
        if message_type:
            query = query.filter(self.model.message_type == message_type)
        
        if is_ai_generated is not None:
            query = query.filter(self.model.is_ai_generated == is_ai_generated)
        
        if since_date:
            query = query.filter(self.model.created_at >= since_date)
        
        # Сортируем по времени создания (новые первые)
        query = query.order_by(desc(self.model.created_at))
        
        return query.offset(skip).limit(limit).all()
    
    def get_user_messages_since(
        self,
        db: Session,
        user_id: UUID,
        since_date: datetime,
        limit: int = 1000
    ) -> List[Message]:
        """
        Получает сообщения пользователя с определенной даты.
        
        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            since_date: Начальная дата
            limit: Максимальное количество сообщений
            
        Returns:
            Сообщения пользователя
        """
        query = db.query(self.model).filter(
            and_(
                or_(
                    self.model.sender_id == user_id,
                    self.model.recipient_id == user_id
                ),
                self.model.created_at >= since_date,
                self.model.deleted_at.is_(None)
            )
        ).order_by(desc(self.model.created_at))
        
        return query.limit(limit).all()
    
    def count_by_conversation(
        self,
        db: Session,
        conversation_id: UUID
    ) -> int:
        """
        Подсчитывает количество сообщений в диалоге.
        
        Args:
            db: Сессия базы данных
            conversation_id: ID диалога
            
        Returns:
            Количество сообщений
        """
        return db.query(self.model).filter(
            and_(
                self.model.conversation_id == conversation_id,
                self.model.deleted_at.is_(None)
            )
        ).count()
    
    def search_messages(
        self,
        db: Session,
        search_query: str,
        user_id: Optional[UUID] = None,
        limit: int = 50
    ) -> List[Message]:
        """
        Поиск сообщений по содержимому.
        
        Args:
            db: Сессия базы данных
            search_query: Поисковый запрос
            user_id: ID пользователя для фильтрации
            limit: Максимальное количество результатов
            
        Returns:
            Найденные сообщения
        """
        query = db.query(self.model).filter(
            and_(
                self.model.content.ilike(f"%{search_query}%"),
                self.model.deleted_at.is_(None)
            )
        )
        
        if user_id:
            query = query.filter(
                or_(
                    self.model.sender_id == user_id,
                    self.model.recipient_id == user_id
                )
            )
        
        return query.order_by(desc(self.model.created_at)).limit(limit).all()
    
    def update_ai_analysis(
        self,
        db: Session,
        message_id: UUID,
        analysis: Dict[str, Any]
    ) -> Optional[Message]:
        """
        Обновляет ИИ-анализ сообщения.
        
        Args:
            db: Сессия базы данных
            message_id: ID сообщения
            analysis: Результаты ИИ-анализа
            
        Returns:
            Обновленное сообщение или None
        """
        message = self.get(db, id=message_id)
        if not message:
            return None
        
        # Обновляем анализ и время обработки
        update_data = {
            "ai_analysis": analysis,
            "response_time_ms": analysis.get("processing_time_ms", 0)
        }
        
        return self.update(db, db_obj=message, obj_in=update_data)
    
    def get_latest_in_conversation(
        self,
        db: Session,
        conversation_id: UUID,
        count: int = 10
    ) -> List[Message]:
        """
        Получает последние сообщения в диалоге.
        
        Args:
            db: Сессия базы данных
            conversation_id: ID диалога
            count: Количество сообщений
            
        Returns:
            Последние сообщения
        """
        return db.query(self.model).filter(
            and_(
                self.model.conversation_id == conversation_id,
                self.model.deleted_at.is_(None)
            )
        ).order_by(desc(self.model.created_at)).limit(count).all()
    
    def get_messages_with_ai_analysis(
        self,
        db: Session,
        sentiment: Optional[str] = None,
        intent: Optional[str] = None,
        since_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Message]:
        """
        Получает сообщения с ИИ-анализом по критериям.
        
        Args:
            db: Сессия базы данных
            sentiment: Фильтр по тональности
            intent: Фильтр по намерению
            since_date: Фильтр по дате
            limit: Максимальное количество
            
        Returns:
            Сообщения с анализом
        """
        query = db.query(self.model).filter(
            and_(
                self.model.ai_analysis.isnot(None),
                self.model.deleted_at.is_(None)
            )
        )
        
        if sentiment:
            query = query.filter(
                self.model.ai_analysis['sentiment'].astext == sentiment
            )
        
        if intent:
            query = query.filter(
                self.model.ai_analysis['intent'].astext == intent
            )
        
        if since_date:
            query = query.filter(self.model.created_at >= since_date)
        
        return query.order_by(desc(self.model.created_at)).limit(limit).all()
    
    def get_performance_stats(
        self,
        db: Session,
        user_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Получает статистику производительности сообщений пользователя.
        
        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            days: Период анализа в днях
            
        Returns:
            Статистика производительности
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Базовая статистика
        base_query = db.query(self.model).filter(
            and_(
                or_(
                    self.model.sender_id == user_id,
                    self.model.recipient_id == user_id
                ),
                self.model.created_at >= since_date,
                self.model.deleted_at.is_(None)
            )
        )
        
        total_messages = base_query.count()
        
        # Статистика по типам сообщений
        sent_messages = base_query.filter(self.model.sender_id == user_id).count()
        received_messages = total_messages - sent_messages
        
        # ИИ-сообщения
        ai_messages = base_query.filter(self.model.is_ai_generated == True).count()
        
        # Средний размер сообщений
        avg_length = db.query(func.avg(func.length(self.model.content))).filter(
            and_(
                self.model.sender_id == user_id,
                self.model.created_at >= since_date,
                self.model.deleted_at.is_(None)
            )
        ).scalar() or 0
        
        return {
            "total_messages": total_messages,
            "sent_messages": sent_messages,
            "received_messages": received_messages,
            "ai_generated_messages": ai_messages,
            "ai_usage_percentage": (ai_messages / sent_messages * 100) if sent_messages > 0 else 0,
            "avg_message_length": round(float(avg_length), 2),
            "period_days": days,
            "daily_average": round(total_messages / days, 2)
        }
    
    def bulk_update_status(
        self,
        db: Session,
        message_ids: List[UUID],
        new_status: str
    ) -> int:
        """
        Массовое обновление статуса сообщений.
        
        Args:
            db: Сессия базы данных
            message_ids: Список ID сообщений
            new_status: Новый статус
            
        Returns:
            Количество обновленных сообщений
        """
        if not message_ids:
            return 0
        
        result = db.query(self.model).filter(
            and_(
                self.model.id.in_(message_ids),
                self.model.deleted_at.is_(None)
            )
        ).update(
            {"status": new_status, "updated_at": datetime.utcnow()},
            synchronize_session=False
        )
        
        db.commit()
        return result


class CRUDMessageTemplate(CRUDBase[MessageTemplate, dict, dict]):
    """CRUD операции для шаблонов сообщений."""
    
    def get_seller_templates(
        self,
        db: Session,
        seller_id: UUID,
        category: Optional[str] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[MessageTemplate]:
        """
        Получает шаблоны продавца с фильтрацией.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            category: Фильтр по категории
            active_only: Только активные шаблоны
            skip: Пропуск записей
            limit: Лимит записей
            
        Returns:
            Шаблоны сообщений
        """
        query = db.query(self.model).filter(
            and_(
                self.model.seller_id == seller_id,
                self.model.deleted_at.is_(None)
            )
        )
        
        if category:
            query = query.filter(self.model.category == category)
        
        if active_only:
            query = query.filter(self.model.is_active == True)
        
        # Сортируем по популярности и дате создания
        query = query.order_by(
            desc(self.model.usage_count),
            desc(self.model.created_at)
        )
        
        return query.offset(skip).limit(limit).all()
    
    def get_by_category(
        self,
        db: Session,
        category: str,
        seller_id: Optional[UUID] = None,
        limit: int = 50
    ) -> List[MessageTemplate]:
        """
        Получает шаблоны по категории.
        
        Args:
            db: Сессия базы данных
            category: Категория шаблонов
            seller_id: ID продавца (опционально)
            limit: Максимальное количество
            
        Returns:
            Шаблоны по категории
        """
        query = db.query(self.model).filter(
            and_(
                self.model.category == category,
                self.model.is_active == True,
                self.model.deleted_at.is_(None)
            )
        )
        
        if seller_id:
            query = query.filter(self.model.seller_id == seller_id)
        
        return query.order_by(desc(self.model.usage_count)).limit(limit).all()
    
    def search_templates(
        self,
        db: Session,
        search_query: str,
        seller_id: UUID,
        limit: int = 20
    ) -> List[MessageTemplate]:
        """
        Поиск шаблонов по названию или содержимому.
        
        Args:
            db: Сессия базы данных
            search_query: Поисковый запрос
            seller_id: ID продавца
            limit: Максимальное количество результатов
            
        Returns:
            Найденные шаблоны
        """
        query = db.query(self.model).filter(
            and_(
                self.model.seller_id == seller_id,
                or_(
                    self.model.name.ilike(f"%{search_query}%"),
                    self.model.content.ilike(f"%{search_query}%")
                ),
                self.model.deleted_at.is_(None)
            )
        )
        
        return query.order_by(desc(self.model.usage_count)).limit(limit).all()
    
    def increment_usage(
        self,
        db: Session,
        template_id: UUID
    ) -> Optional[MessageTemplate]:
        """
        Увеличивает счетчик использования шаблона.
        
        Args:
            db: Сессия базы данных
            template_id: ID шаблона
            
        Returns:
            Обновленный шаблон или None
        """
        template = self.get(db, id=template_id)
        if not template:
            return None
        
        template.usage_count = (template.usage_count or 0) + 1
        template.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(template)
        
        return template
    
    def update_success_rate(
        self,
        db: Session,
        template_id: UUID,
        success: bool
    ) -> Optional[MessageTemplate]:
        """
        Обновляет статистику успешности шаблона.
        
        Args:
            db: Сессия базы данных
            template_id: ID шаблона
            success: Был ли успешным результат использования
            
        Returns:
            Обновленный шаблон или None
        """
        template = self.get(db, id=template_id)
        if not template:
            return None
        
        # Обновляем статистику в метаданных
        metadata = template.metadata or {}
        stats = metadata.get("success_stats", {"total": 0, "successful": 0})
        
        stats["total"] += 1
        if success:
            stats["successful"] += 1
        
        # Вычисляем новый процент успешности
        success_rate = (stats["successful"] / stats["total"]) if stats["total"] > 0 else 0
        
        metadata["success_stats"] = stats
        template.metadata = metadata
        template.success_rate = success_rate
        template.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(template)
        
        return template
    
    def get_template_success_rate(
        self,
        db: Session,
        template_id: UUID,
        days: int = 30
    ) -> float:
        """
        Получает коэффициент успешности шаблона за период.
        
        Args:
            db: Сессия базы данных
            template_id: ID шаблона
            days: Период для анализа
            
        Returns:
            Коэффициент успешности (0.0 - 1.0)
        """
        template = self.get(db, id=template_id)
        if not template:
            return 0.0
        
        # Если есть сохраненная статистика
        if template.success_rate is not None:
            return template.success_rate
        
        # Если нет, возвращаем базовую оценку на основе использования
        if template.usage_count and template.usage_count > 0:
            # Чем больше используется, тем выше "успешность"
            return min(1.0, template.usage_count / 100)
        
        return 0.5  # Средняя оценка для новых шаблонов
    
    def get_popular_templates(
        self,
        db: Session,
        seller_id: UUID,
        limit: int = 10
    ) -> List[MessageTemplate]:
        """
        Получает самые популярные шаблоны продавца.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            limit: Количество шаблонов
            
        Returns:
            Популярные шаблоны
        """
        return db.query(self.model).filter(
            and_(
                self.model.seller_id == seller_id,
                self.model.is_active == True,
                self.model.deleted_at.is_(None)
            )
        ).order_by(
            desc(self.model.usage_count),
            desc(self.model.success_rate)
        ).limit(limit).all()


# Создаем экземпляры CRUD классов
message_crud = CRUDMessage(Message)
template_crud = CRUDMessageTemplate(MessageTemplate)