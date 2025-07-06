"""
CRUD операции для диалогов.

Обрабатывает создание, чтение, обновление и удаление диалогов,
а также аналитику и статистику по диалогам.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func, case

from .base import CRUDBase
from ..models.messages import Conversation, Message
from src.utils.exceptions import NotFoundError


class CRUDConversation(CRUDBase[Conversation, dict, dict]):
    """CRUD операции для диалогов."""
    
    def get_with_messages(
        self,
        db: Session,
        id: UUID,
        message_limit: int = 50
    ) -> Optional[Conversation]:
        """
        Получает диалог вместе с сообщениями.
        
        Args:
            db: Сессия базы данных
            id: ID диалога
            message_limit: Максимальное количество сообщений
            
        Returns:
            Диалог с сообщениями или None
        """
        conversation = db.query(self.model).options(
            joinedload(self.model.messages).options(
                # Загружаем только последние сообщения
                joinedload(Message).load_only(
                    Message.id,
                    Message.sender_id,
                    Message.recipient_id,
                    Message.content,
                    Message.message_type,
                    Message.status,
                    Message.created_at
                )
            )
        ).filter(
            and_(
                self.model.id == id,
                self.model.deleted_at.is_(None)
            )
        ).first()
        
        if conversation and conversation.messages:
            # Ограничиваем количество сообщений и сортируем
            conversation.messages = sorted(
                conversation.messages,
                key=lambda x: x.created_at,
                reverse=True
            )[:message_limit]
        
        return conversation
    
    def get_user_conversations(
        self,
        db: Session,
        user_id: UUID,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Conversation]:
        """
        Получает диалоги пользователя.
        
        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            status: Фильтр по статусу
            skip: Пропуск записей
            limit: Лимит записей
            
        Returns:
            Диалоги пользователя
        """
        query = db.query(self.model).filter(
            and_(
                or_(
                    self.model.user_id == user_id,
                    self.model.seller_id == user_id
                ),
                self.model.deleted_at.is_(None)
            )
        )
        
        if status:
            query = query.filter(self.model.status == status)
        
        # Сортируем по последней активности
        query = query.order_by(desc(self.model.last_message_at))
        
        return query.offset(skip).limit(limit).all()
    
    def get_seller_conversations(
        self,
        db: Session,
        seller_id: UUID,
        status: Optional[str] = None,
        since_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Conversation]:
        """
        Получает диалоги продавца с фильтрацией.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            status: Фильтр по статусу
            since_date: Фильтр по дате
            skip: Пропуск записей
            limit: Лимит записей
            
        Returns:
            Диалоги продавца
        """
        query = db.query(self.model).filter(
            and_(
                self.model.seller_id == seller_id,
                self.model.deleted_at.is_(None)
            )
        )
        
        if status:
            query = query.filter(self.model.status == status)
        
        if since_date:
            query = query.filter(self.model.created_at >= since_date)
        
        return query.order_by(desc(self.model.last_message_at)).offset(skip).limit(limit).all()
    
    def get_seller_conversations_since(
        self,
        db: Session,
        seller_id: UUID,
        since_date: datetime
    ) -> List[Conversation]:
        """
        Получает диалоги продавца с определенной даты.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            since_date: Начальная дата
            
        Returns:
            Диалоги с указанной даты
        """
        return db.query(self.model).filter(
            and_(
                self.model.seller_id == seller_id,
                self.model.created_at >= since_date,
                self.model.deleted_at.is_(None)
            )
        ).order_by(desc(self.model.created_at)).all()
    
    def get_active_conversation(
        self,
        db: Session,
        user_id: UUID,
        seller_id: UUID
    ) -> Optional[Conversation]:
        """
        Получает активный диалог между пользователем и продавцом.
        
        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            seller_id: ID продавца
            
        Returns:
            Активный диалог или None
        """
        return db.query(self.model).filter(
            and_(
                self.model.user_id == user_id,
                self.model.seller_id == seller_id,
                self.model.status == "active",
                self.model.deleted_at.is_(None)
            )
        ).first()
    
    def search_conversations(
        self,
        db: Session,
        search_query: str,
        user_id: Optional[UUID] = None,
        limit: int = 20
    ) -> List[Conversation]:
        """
        Поиск диалогов по заголовку или метаданным.
        
        Args:
            db: Сессия базы данных
            search_query: Поисковый запрос
            user_id: ID пользователя для фильтрации
            limit: Максимальное количество результатов
            
        Returns:
            Найденные диалоги
        """
        query = db.query(self.model).filter(
            and_(
                or_(
                    self.model.title.ilike(f"%{search_query}%"),
                    self.model.metadata['item_title'].astext.ilike(f"%{search_query}%")
                ),
                self.model.deleted_at.is_(None)
            )
        )
        
        if user_id:
            query = query.filter(
                or_(
                    self.model.user_id == user_id,
                    self.model.seller_id == user_id
                )
            )
        
        return query.order_by(desc(self.model.last_message_at)).limit(limit).all()
    
    def update_conversation_stats(
        self,
        db: Session,
        conversation_id: UUID,
        message_count: Optional[int] = None,
        last_message_at: Optional[datetime] = None
    ) -> Optional[Conversation]:
        """
        Обновляет статистику диалога.
        
        Args:
            db: Сессия базы данных
            conversation_id: ID диалога
            message_count: Новое количество сообщений
            last_message_at: Время последнего сообщения
            
        Returns:
            Обновленный диалог или None
        """
        conversation = self.get(db, id=conversation_id)
        if not conversation:
            return None
        
        update_data = {}
        
        if message_count is not None:
            update_data["message_count"] = message_count
        
        if last_message_at is not None:
            update_data["last_message_at"] = last_message_at
        
        if update_data:
            return self.update(db, db_obj=conversation, obj_in=update_data)
        
        return conversation
    
    def calculate_conversion_score(
        self,
        db: Session,
        conversation_id: UUID
    ) -> float:
        """
        Вычисляет оценку конверсии диалога.
        
        Args:
            db: Сессия базы данных
            conversation_id: ID диалога
            
        Returns:
            Оценка конверсии (0.0 - 1.0)
        """
        conversation = self.get(db, id=conversation_id)
        if not conversation:
            return 0.0
        
        # Базовые факторы конверсии
        score = 0.0
        
        # Длительность диалога
        if conversation.last_message_at and conversation.created_at:
            duration_hours = (conversation.last_message_at - conversation.created_at).total_seconds() / 3600
            if duration_hours > 1:
                score += 0.2  # Длительный диалог = больше заинтересованности
        
        # Количество сообщений
        message_count = conversation.message_count or 0
        if message_count > 5:
            score += 0.3
        elif message_count > 2:
            score += 0.1
        
        # Статус диалога
        if conversation.status == "closed":
            # Проверяем причину закрытия в метаданных
            metadata = conversation.metadata or {}
            if metadata.get("closure_reason") == "deal_completed":
                score += 0.5
            elif metadata.get("closure_reason") == "customer_satisfied":
                score += 0.3
        elif conversation.status == "active":
            score += 0.2  # Активный диалог имеет потенциал
        
        # Наличие контактной информации в метаданных
        metadata = conversation.metadata or {}
        if metadata.get("contact_exchanged"):
            score += 0.2
        
        return min(1.0, score)
    
    def get_conversation_analytics(
        self,
        db: Session,
        seller_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Получает аналитику диалогов продавца.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            days: Период анализа в днях
            
        Returns:
            Аналитика диалогов
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Базовая статистика
        total_conversations = db.query(self.model).filter(
            and_(
                self.model.seller_id == seller_id,
                self.model.created_at >= since_date,
                self.model.deleted_at.is_(None)
            )
        ).count()
        
        # Статистика по статусам
        status_stats = db.query(
            self.model.status,
            func.count(self.model.id)
        ).filter(
            and_(
                self.model.seller_id == seller_id,
                self.model.created_at >= since_date,
                self.model.deleted_at.is_(None)
            )
        ).group_by(self.model.status).all()
        
        # Средняя продолжительность диалогов
        avg_duration = db.query(
            func.avg(
                func.extract('epoch', self.model.last_message_at - self.model.created_at) / 3600
            )
        ).filter(
            and_(
                self.model.seller_id == seller_id,
                self.model.created_at >= since_date,
                self.model.last_message_at.isnot(None),
                self.model.deleted_at.is_(None)
            )
        ).scalar() or 0
        
        # Среднее количество сообщений в диалоге
        avg_messages = db.query(
            func.avg(self.model.message_count)
        ).filter(
            and_(
                self.model.seller_id == seller_id,
                self.model.created_at >= since_date,
                self.model.deleted_at.is_(None)
            )
        ).scalar() or 0
        
        # Конверсия (диалоги со статусом "closed" и причиной "deal_completed")
        completed_deals = db.query(self.model).filter(
            and_(
                self.model.seller_id == seller_id,
                self.model.created_at >= since_date,
                self.model.status == "closed",
                self.model.metadata['closure_reason'].astext == 'deal_completed',
                self.model.deleted_at.is_(None)
            )
        ).count()
        
        conversion_rate = (completed_deals / total_conversations * 100) if total_conversations > 0 else 0
        
        return {
            "total_conversations": total_conversations,
            "active_conversations": sum(count for status, count in status_stats if status == "active"),
            "closed_conversations": sum(count for status, count in status_stats if status == "closed"),
            "archived_conversations": sum(count for status, count in status_stats if status == "archived"),
            "avg_duration_hours": round(float(avg_duration), 2),
            "avg_messages_per_conversation": round(float(avg_messages), 1),
            "completed_deals": completed_deals,
            "conversion_rate": round(conversion_rate, 2),
            "daily_average": round(total_conversations / days, 2),
            "period_days": days,
            "status_distribution": dict(status_stats)
        }
    
    def get_trending_conversations(
        self,
        db: Session,
        seller_id: UUID,
        limit: int = 10
    ) -> List[Conversation]:
        """
        Получает самые активные диалоги продавца.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            limit: Количество диалогов
            
        Returns:
            Активные диалоги
        """
        # Диалоги с наибольшим количеством сообщений за последние 24 часа
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        return db.query(self.model).filter(
            and_(
                self.model.seller_id == seller_id,
                self.model.status == "active",
                self.model.last_message_at >= yesterday,
                self.model.deleted_at.is_(None)
            )
        ).order_by(
            desc(self.model.message_count),
            desc(self.model.last_message_at)
        ).limit(limit).all()
    
    def bulk_update_status(
        self,
        db: Session,
        conversation_ids: List[UUID],
        new_status: str,
        closure_reason: Optional[str] = None
    ) -> int:
        """
        Массовое обновление статуса диалогов.
        
        Args:
            db: Сессия базы данных
            conversation_ids: Список ID диалогов
            new_status: Новый статус
            closure_reason: Причина закрытия (для статуса "closed")
            
        Returns:
            Количество обновленных диалогов
        """
        if not conversation_ids:
            return 0
        
        update_data = {
            "status": new_status,
            "updated_at": datetime.utcnow()
        }
        
        # Добавляем время закрытия для закрытых диалогов
        if new_status == "closed":
            update_data["closed_at"] = datetime.utcnow()
            
            # Обновляем метаданные с причиной закрытия
            if closure_reason:
                # Это требует отдельной обработки для каждого диалога
                for conv_id in conversation_ids:
                    conversation = self.get(db, id=conv_id)
                    if conversation:
                        metadata = conversation.metadata or {}
                        metadata["closure_reason"] = closure_reason
                        self.update(db, db_obj=conversation, obj_in={
                            **update_data,
                            "metadata": metadata
                        })
                return len(conversation_ids)
        
        result = db.query(self.model).filter(
            and_(
                self.model.id.in_(conversation_ids),
                self.model.deleted_at.is_(None)
            )
        ).update(update_data, synchronize_session=False)
        
        db.commit()
        return result
    
    def cleanup_old_conversations(
        self,
        db: Session,
        days_threshold: int = 90
    ) -> int:
        """
        Архивирует старые неактивные диалоги.
        
        Args:
            db: Сессия базы данных
            days_threshold: Порог в днях для архивирования
            
        Returns:
            Количество заархивированных диалогов
        """
        threshold_date = datetime.utcnow() - timedelta(days=days_threshold)
        
        result = db.query(self.model).filter(
            and_(
                self.model.status.in_(["closed", "inactive"]),
                self.model.updated_at < threshold_date,
                self.model.deleted_at.is_(None)
            )
        ).update(
            {"status": "archived", "updated_at": datetime.utcnow()},
            synchronize_session=False
        )
        
        db.commit()
        return result


# Создаем экземпляр CRUD класса
conversation_crud = CRUDConversation(Conversation)