"""
Сервис для работы с сообщениями и диалогами.

Обрабатывает всю бизнес-логику, связанную с сообщениями:
создание, обработка, ИИ-анализ, автоответы и управление диалогами.
"""

import asyncio
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.core.ai_consultant import AIConsultant
from src.core.message_handler import MessageHandler
from src.core.response_generator import ResponseGenerator
from src.database.crud import message_crud, conversation_crud, template_crud
from src.database.models.users import User, Seller
from src.database.models.messages import Message, Conversation, MessageTemplate
from src.utils.exceptions import BusinessLogicError, NotFoundError, ValidationError
from src.utils.validators import validate_message_content
from src.utils.formatters import format_message_for_ai, format_ai_response


class MessageService:
    """
    Сервис для управления сообщениями, диалогами и ИИ-взаимодействиями.
    
    Координирует работу между пользователями, ИИ-анализом и автоответами.
    """
    
    def __init__(self):
        self.ai_consultant = AIConsultant()
        self.message_handler = MessageHandler()
        self.response_generator = ResponseGenerator()
    
    # ========================================================================
    # МЕТОДЫ РАБОТЫ С СООБЩЕНИЯМИ
    # ========================================================================
    
    async def create_message(
        self,
        db: Session,
        sender_id: UUID,
        recipient_id: UUID,
        content: str,
        conversation_id: Optional[UUID] = None,
        message_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Создает новое сообщение с автоматическим ИИ-анализом.
        
        Args:
            db: Сессия базы данных
            sender_id: ID отправителя
            recipient_id: ID получателя
            content: Содержимое сообщения
            conversation_id: ID диалога (создается автоматически если не указан)
            message_type: Тип сообщения
            metadata: Дополнительные метаданные
            
        Returns:
            Созданное сообщение
            
        Raises:
            ValidationError: При ошибках валидации
            BusinessLogicError: При нарушении бизнес-правил
        """
        # Валидируем содержимое сообщения
        if not validate_message_content(content):
            raise ValidationError("Некорректное содержимое сообщения")
        
        # Создаем или получаем диалог
        if not conversation_id:
            conversation = await self._get_or_create_conversation(
                db, sender_id, recipient_id, metadata
            )
            conversation_id = conversation.id
        
        # Создаем сообщение
        message_data = {
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "content": content.strip(),
            "message_type": message_type,
            "metadata": metadata or {},
            "status": "sent"
        }
        
        message = message_crud.create(db, obj_in=message_data)
        
        # Запускаем ИИ-анализ в фоновом режиме
        asyncio.create_task(self._analyze_message_async(db, message.id))
        
        # Обновляем статистику диалога
        await self._update_conversation_stats(db, conversation_id)
        
        return message
    
    async def get_message_by_id(self, db: Session, message_id: UUID) -> Message:
        """
        Получает сообщение по ID.
        
        Args:
            db: Сессия базы данных
            message_id: ID сообщения
            
        Returns:
            Сообщение
            
        Raises:
            NotFoundError: Если сообщение не найдено
        """
        message = message_crud.get(db, id=message_id)
        if not message:
            raise NotFoundError("Сообщение не найдено")
        return message
    
    async def get_messages_by_conversation(
        self,
        db: Session,
        conversation_id: UUID,
        skip: int = 0,
        limit: int = 50,
        include_metadata: bool = False
    ) -> List[Message]:
        """
        Получает сообщения диалога с пагинацией.
        
        Args:
            db: Сессия базы данных
            conversation_id: ID диалога
            skip: Количество пропускаемых сообщений
            limit: Максимальное количество сообщений
            include_metadata: Включать ли метаданные
            
        Returns:
            Список сообщений
        """
        messages = message_crud.get_by_conversation(
            db,
            conversation_id=conversation_id,
            skip=skip,
            limit=limit
        )
        
        if not include_metadata:
            # Очищаем чувствительные метаданные для обычных пользователей
            for message in messages:
                if message.metadata:
                    message.metadata = self._filter_metadata_for_user(message.metadata)
        
        return messages
    
    async def update_message(
        self,
        db: Session,
        message_id: UUID,
        update_data: Dict[str, Any],
        user_id: UUID
    ) -> Message:
        """
        Обновляет сообщение.
        
        Args:
            db: Сессия базы данных
            message_id: ID сообщения
            update_data: Данные для обновления
            user_id: ID пользователя, который обновляет
            
        Returns:
            Обновленное сообщение
            
        Raises:
            NotFoundError: Если сообщение не найдено
            BusinessLogicError: При нарушении прав доступа
        """
        message = await self.get_message_by_id(db, message_id)
        
        # Проверяем права на редактирование
        if str(message.sender_id) != str(user_id):
            raise BusinessLogicError("Можно редактировать только свои сообщения")
        
        # Валидируем новое содержимое
        if "content" in update_data:
            if not validate_message_content(update_data["content"]):
                raise ValidationError("Некорректное содержимое сообщения")
            update_data["content"] = update_data["content"].strip()
        
        # Добавляем информацию о редактировании
        if "content" in update_data and update_data["content"] != message.content:
            metadata = message.metadata or {}
            metadata.update({
                "edited": True,
                "edit_time": datetime.utcnow().isoformat(),
                "original_content": message.content
            })
            update_data["metadata"] = metadata
        
        updated_message = message_crud.update(db, db_obj=message, obj_in=update_data)
        
        # Повторный ИИ-анализ для отредактированных сообщений
        if "content" in update_data:
            asyncio.create_task(self._analyze_message_async(db, message.id))
        
        return updated_message
    
    async def delete_message(
        self,
        db: Session,
        message_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Удаляет сообщение (мягкое удаление).
        
        Args:
            db: Сессия базы данных
            message_id: ID сообщения
            user_id: ID пользователя
            
        Returns:
            True при успешном удалении
        """
        message = await self.get_message_by_id(db, message_id)
        
        # Проверяем права на удаление
        if str(message.sender_id) != str(user_id):
            raise BusinessLogicError("Можно удалять только свои сообщения")
        
        message_crud.remove(db, id=message_id)
        
        # Обновляем статистику диалога
        await self._update_conversation_stats(db, message.conversation_id)
        
        return True
    
    # ========================================================================
    # МЕТОДЫ РАБОТЫ С ДИАЛОГАМИ
    # ========================================================================
    
    async def get_conversation_by_id(
        self,
        db: Session,
        conversation_id: UUID,
        include_messages: bool = False
    ) -> Conversation:
        """
        Получает диалог по ID.
        
        Args:
            db: Сессия базы данных
            conversation_id: ID диалога
            include_messages: Включать ли сообщения
            
        Returns:
            Диалог
            
        Raises:
            NotFoundError: Если диалог не найден
        """
        if include_messages:
            conversation = conversation_crud.get_with_messages(db, id=conversation_id)
        else:
            conversation = conversation_crud.get(db, id=conversation_id)
        
        if not conversation:
            raise NotFoundError("Диалог не найден")
        
        return conversation
    
    async def get_user_conversations(
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
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей
            
        Returns:
            Список диалогов
        """
        conversations = conversation_crud.get_user_conversations(
            db,
            user_id=user_id,
            status=status,
            skip=skip,
            limit=limit
        )
        
        return conversations
    
    async def update_conversation_status(
        self,
        db: Session,
        conversation_id: UUID,
        new_status: str,
        user_id: UUID
    ) -> Conversation:
        """
        Обновляет статус диалога.
        
        Args:
            db: Сессия базы данных
            conversation_id: ID диалога
            new_status: Новый статус
            user_id: ID пользователя
            
        Returns:
            Обновленный диалог
        """
        conversation = await self.get_conversation_by_id(db, conversation_id)
        
        # Проверяем права на изменение статуса
        if (str(conversation.user_id) != str(user_id) and 
            str(conversation.seller_id) != str(user_id)):
            raise BusinessLogicError("Нет прав для изменения статуса диалога")
        
        valid_statuses = ["active", "closed", "archived", "blocked"]
        if new_status not in valid_statuses:
            raise ValidationError(f"Некорректный статус. Доступны: {', '.join(valid_statuses)}")
        
        update_data = {"status": new_status}
        
        # Добавляем время закрытия для закрытых диалогов
        if new_status == "closed":
            update_data["closed_at"] = datetime.utcnow()
        
        updated_conversation = conversation_crud.update(
            db,
            db_obj=conversation,
            obj_in=update_data
        )
        
        return updated_conversation
    
    # ========================================================================
    # МЕТОДЫ ИИ-АНАЛИЗА И АВТООТВЕТОВ
    # ========================================================================
    
    async def analyze_message_with_ai(
        self,
        db: Session,
        message_id: UUID
    ) -> Dict[str, Any]:
        """
        Выполняет ИИ-анализ сообщения.
        
        Args:
            db: Сессия базы данных
            message_id: ID сообщения
            
        Returns:
            Результат анализа
        """
        message = await self.get_message_by_id(db, message_id)
        
        # Форматируем сообщение для ИИ
        formatted_message = format_message_for_ai(message)
        
        # Выполняем анализ
        analysis = await self.ai_consultant.analyze_message(
            content=formatted_message["content"],
            context=formatted_message["context"]
        )
        
        # Сохраняем результаты анализа
        message_crud.update_ai_analysis(db, message_id=message_id, analysis=analysis)
        
        return analysis
    
    async def generate_auto_reply(
        self,
        db: Session,
        message_id: UUID,
        seller_id: UUID,
        template_id: Optional[UUID] = None,
        custom_context: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Генерирует автоматический ответ на сообщение.
        
        Args:
            db: Сессия базы данных
            message_id: ID исходного сообщения
            seller_id: ID продавца
            template_id: ID шаблона (опционально)
            custom_context: Дополнительный контекст
            
        Returns:
            Сгенерированное сообщение-ответ
        """
        # Получаем исходное сообщение
        original_message = await self.get_message_by_id(db, message_id)
        
        # Получаем настройки продавца
        from .user_service import user_service
        seller_settings = user_service.get_seller_settings(db, seller_id)
        
        # Проверяем, включен ли автоответчик
        if not seller_settings.auto_reply_enabled:
            raise BusinessLogicError("Автоответчик отключен в настройках")
        
        # Получаем шаблон, если указан
        template_content = None
        if template_id:
            template = template_crud.get(db, id=template_id)
            if template and template.seller_id == seller_id:
                template_content = template.content
        
        # Подготавливаем контекст для генерации
        context = {
            "original_message": original_message.content,
            "message_type": original_message.message_type,
            "sender_info": await self._get_sender_context(db, original_message.sender_id),
            "seller_settings": {
                "creativity": seller_settings.ai_creativity,
                "formality": seller_settings.ai_formality,
                "response_length": seller_settings.ai_response_length
            }
        }
        
        if custom_context:
            context.update(custom_context)
        
        # Генерируем ответ
        if template_content:
            response_content = await self.response_generator.generate_from_template(
                template=template_content,
                context=context
            )
        else:
            response_content = await self.response_generator.generate_response(
                message=original_message.content,
                context=context,
                seller_settings=seller_settings
            )
        
        # Создаем сообщение-ответ
        reply_message = await self.create_message(
            db=db,
            sender_id=seller_id,
            recipient_id=original_message.sender_id,
            content=response_content,
            conversation_id=original_message.conversation_id,
            message_type="automated_reply",
            metadata={
                "ai_generated": True,
                "template_id": str(template_id) if template_id else None,
                "generation_context": context
            }
        )
        
        # Обновляем статистику использования шаблона
        if template_id:
            template_crud.increment_usage(db, template_id=template_id)
        
        # Применяем задержку автоответа
        delay = self._calculate_auto_reply_delay(seller_settings)
        if delay > 0:
            await asyncio.sleep(delay)
        
        return reply_message
    
    async def bulk_analyze_messages(
        self,
        db: Session,
        message_ids: List[UUID]
    ) -> Dict[UUID, Dict[str, Any]]:
        """
        Массовый ИИ-анализ сообщений.
        
        Args:
            db: Сессия базы данных
            message_ids: Список ID сообщений
            
        Returns:
            Словарь с результатами анализа
        """
        results = {}
        
        # Обрабатываем сообщения батчами
        batch_size = 10
        for i in range(0, len(message_ids), batch_size):
            batch = message_ids[i:i + batch_size]
            
            # Параллельный анализ батча
            tasks = [
                self.analyze_message_with_ai(db, message_id) 
                for message_id in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for message_id, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    results[message_id] = {"error": str(result)}
                else:
                    results[message_id] = result
        
        return results
    
    # ========================================================================
    # МЕТОДЫ РАБОТЫ С ШАБЛОНАМИ
    # ========================================================================
    
    async def create_message_template(
        self,
        db: Session,
        seller_id: UUID,
        template_data: Dict[str, Any]
    ) -> MessageTemplate:
        """
        Создает новый шаблон сообщения.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            template_data: Данные шаблона
            
        Returns:
            Созданный шаблон
        """
        # Валидируем данные шаблона
        if not template_data.get("name"):
            raise ValidationError("Название шаблона обязательно")
        
        if not template_data.get("content"):
            raise ValidationError("Содержимое шаблона обязательно")
        
        # Анализируем переменные в шаблоне
        variables = self._extract_template_variables(template_data["content"])
        template_data["variables"] = variables
        template_data["seller_id"] = seller_id
        
        template = template_crud.create(db, obj_in=template_data)
        return template
    
    async def get_seller_templates(
        self,
        db: Session,
        seller_id: UUID,
        category: Optional[str] = None,
        active_only: bool = True
    ) -> List[MessageTemplate]:
        """
        Получает шаблоны сообщений продавца.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            category: Фильтр по категории
            active_only: Только активные шаблоны
            
        Returns:
            Список шаблонов
        """
        templates = template_crud.get_seller_templates(
            db,
            seller_id=seller_id,
            category=category,
            active_only=active_only
        )
        
        return templates
    
    async def update_template(
        self,
        db: Session,
        template_id: UUID,
        seller_id: UUID,
        update_data: Dict[str, Any]
    ) -> MessageTemplate:
        """
        Обновляет шаблон сообщения.
        
        Args:
            db: Сессия базы данных
            template_id: ID шаблона
            seller_id: ID продавца
            update_data: Данные для обновления
            
        Returns:
            Обновленный шаблон
        """
        template = template_crud.get(db, id=template_id)
        if not template:
            raise NotFoundError("Шаблон не найден")
        
        if template.seller_id != seller_id:
            raise BusinessLogicError("Нет прав для редактирования шаблона")
        
        # Обновляем переменные при изменении содержимого
        if "content" in update_data:
            variables = self._extract_template_variables(update_data["content"])
            update_data["variables"] = variables
        
        updated_template = template_crud.update(db, db_obj=template, obj_in=update_data)
        return updated_template
    
    # ========================================================================
    # МЕТОДЫ АНАЛИТИКИ И СТАТИСТИКИ
    # ========================================================================
    
    async def get_conversation_analytics(
        self,
        db: Session,
        conversation_id: UUID
    ) -> Dict[str, Any]:
        """
        Получает аналитику диалога.
        
        Args:
            db: Сессия базы данных
            conversation_id: ID диалога
            
        Returns:
            Аналитика диалога
        """
        conversation = await self.get_conversation_by_id(db, conversation_id, include_messages=True)
        messages = conversation.messages or []
        
        if not messages:
            return {"message_count": 0, "participants": 0}
        
        # Базовая статистика
        analytics = {
            "message_count": len(messages),
            "participants": len(set([msg.sender_id for msg in messages])),
            "duration_hours": self._calculate_conversation_duration(messages),
            "avg_response_time": self._calculate_avg_response_time(messages),
            "sentiment_analysis": await self._analyze_conversation_sentiment(messages),
            "topic_analysis": await self._extract_conversation_topics(messages),
            "ai_usage_stats": self._calculate_ai_usage_stats(messages)
        }
        
        return analytics
    
    async def get_user_messaging_stats(
        self,
        db: Session,
        user_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Получает статистику сообщений пользователя.
        
        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            days: Период для анализа (дни)
            
        Returns:
            Статистика сообщений
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Получаем сообщения пользователя за период
        user_messages = message_crud.get_user_messages_since(
            db,
            user_id=user_id,
            since_date=since_date
        )
        
        stats = {
            "total_messages": len(user_messages),
            "avg_messages_per_day": len(user_messages) / days,
            "most_active_hour": self._find_most_active_hour(user_messages),
            "response_pattern": self._analyze_user_response_pattern(user_messages),
            "conversation_count": len(set([msg.conversation_id for msg in user_messages])),
            "sentiment_trend": await self._analyze_user_sentiment_trend(user_messages)
        }
        
        return stats
    
    async def get_seller_performance_metrics(
        self,
        db: Session,
        seller_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Получает метрики производительности продавца.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            days: Период для анализа
            
        Returns:
            Метрики производительности
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Получаем сообщения продавца
        seller_messages = message_crud.get_user_messages_since(
            db,
            user_id=seller_id,
            since_date=since_date
        )
        
        # Фильтруем автоматические ответы
        auto_replies = [msg for msg in seller_messages if msg.metadata.get("ai_generated")]
        manual_replies = [msg for msg in seller_messages if not msg.metadata.get("ai_generated")]
        
        metrics = {
            "total_messages": len(seller_messages),
            "auto_reply_count": len(auto_replies),
            "manual_reply_count": len(manual_replies),
            "auto_reply_percentage": (len(auto_replies) / len(seller_messages) * 100) if seller_messages else 0,
            "avg_response_time_auto": self._calculate_avg_response_time(auto_replies),
            "avg_response_time_manual": self._calculate_avg_response_time(manual_replies),
            "customer_satisfaction": await self._estimate_customer_satisfaction(seller_messages),
            "conversion_rate": await self._calculate_conversion_rate(db, seller_id, since_date),
            "top_templates": await self._get_top_performing_templates(db, seller_id, days)
        }
        
        return metrics
    
    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ========================================================================
    
    async def _get_or_create_conversation(
        self,
        db: Session,
        user_id: UUID,
        seller_id: UUID,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """Получает существующий диалог или создает новый."""
        # Ищем активный диалог между пользователями
        existing_conversation = conversation_crud.get_active_conversation(
            db,
            user_id=user_id,
            seller_id=seller_id
        )
        
        if existing_conversation:
            return existing_conversation
        
        # Создаем новый диалог
        conversation_data = {
            "user_id": user_id,
            "seller_id": seller_id,
            "status": "active",
            "metadata": metadata or {}
        }
        
        conversation = conversation_crud.create(db, obj_in=conversation_data)
        return conversation
    
    async def _update_conversation_stats(
        self,
        db: Session,
        conversation_id: UUID
    ) -> None:
        """Обновляет статистику диалога."""
        # Подсчитываем количество сообщений
        message_count = message_crud.count_by_conversation(db, conversation_id=conversation_id)
        
        # Обновляем время последнего сообщения
        update_data = {
            "message_count": message_count,
            "last_message_at": datetime.utcnow()
        }
        
        conversation = conversation_crud.get(db, id=conversation_id)
        if conversation:
            conversation_crud.update(db, db_obj=conversation, obj_in=update_data)
    
    async def _analyze_message_async(
        self,
        db: Session,
        message_id: UUID
    ) -> None:
        """Асинхронный ИИ-анализ сообщения."""
        try:
            await self.analyze_message_with_ai(db, message_id)
        except Exception as e:
            # Логируем ошибку, но не прерываем выполнение
            print(f"Ошибка ИИ-анализа сообщения {message_id}: {e}")
    
    def _filter_metadata_for_user(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Фильтрует метаданные для обычных пользователей."""
        # Удаляем чувствительную техническую информацию
        filtered = metadata.copy()
        sensitive_keys = ["generation_context", "ai_analysis_details", "debug_info"]
        
        for key in sensitive_keys:
            filtered.pop(key, None)
        
        return filtered
    
    async def _get_sender_context(
        self,
        db: Session,
        sender_id: UUID
    ) -> Dict[str, Any]:
        """Получает контекст отправителя для ИИ."""
        from .user_service import user_service
        
        try:
            # Пытаемся получить как пользователя
            user = user_service.get_user_by_id(db, sender_id)
            return {
                "type": "user",
                "name": user.first_name,
                "reputation": user.reputation_score
            }
        except NotFoundError:
            try:
                # Пытаемся получить как продавца
                seller = user_service.get_seller_by_id(db, sender_id)
                return {
                    "type": "seller",
                    "company": seller.company_name,
                    "plan": seller.subscription_plan
                }
            except NotFoundError:
                return {"type": "unknown"}
    
    def _calculate_auto_reply_delay(self, seller_settings) -> int:
        """Вычисляет задержку автоответа."""
        import random
        
        if not seller_settings.auto_reply_enabled:
            return 0
        
        min_delay = seller_settings.auto_reply_delay_min
        max_delay = seller_settings.auto_reply_delay_max
        
        return random.randint(min_delay, max_delay)
    
    def _extract_template_variables(self, content: str) -> List[str]:
        """Извлекает переменные из шаблона."""
        import re
        
        # Ищем переменные в формате {variable_name}
        variables = re.findall(r'\{(\w+)\}', content)
        return list(set(variables))  # Удаляем дубликаты
    
    def _calculate_conversation_duration(self, messages: List[Message]) -> float:
        """Вычисляет продолжительность диалога в часах."""
        if len(messages) < 2:
            return 0.0
        
        start_time = min(msg.created_at for msg in messages)
        end_time = max(msg.created_at for msg in messages)
        
        duration = end_time - start_time
        return duration.total_seconds() / 3600  # В часах
    
    def _calculate_avg_response_time(self, messages: List[Message]) -> float:
        """Вычисляет среднее время ответа в секундах."""
        if len(messages) < 2:
            return 0.0
        
        response_times = []
        sorted_messages = sorted(messages, key=lambda x: x.created_at)
        
        for i in range(1, len(sorted_messages)):
            current_msg = sorted_messages[i]
            prev_msg = sorted_messages[i-1]
            
            # Считаем только если это ответ другого пользователя
            if current_msg.sender_id != prev_msg.sender_id:
                time_diff = (current_msg.created_at - prev_msg.created_at).total_seconds()
                response_times.append(time_diff)
        
        return sum(response_times) / len(response_times) if response_times else 0.0
    
    async def _analyze_conversation_sentiment(
        self,
        messages: List[Message]
    ) -> Dict[str, Any]:
        """Анализирует тональность диалога."""
        if not messages:
            return {"overall": "neutral", "trend": "stable"}
        
        # Собираем данные ИИ-анализа из сообщений
        sentiments = []
        for message in messages:
            if message.ai_analysis and "sentiment" in message.ai_analysis:
                sentiments.append(message.ai_analysis["sentiment"])
        
        if not sentiments:
            return {"overall": "neutral", "trend": "stable"}
        
        # Определяем общую тональность
        sentiment_counts = {}
        for sentiment in sentiments:
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
        
        overall_sentiment = max(sentiment_counts, key=sentiment_counts.get)
        
        # Анализируем тренд (улучшение/ухудшение)
        if len(sentiments) >= 3:
            recent_sentiments = sentiments[-3:]
            positive_trend = sum(1 for s in recent_sentiments if s == "positive")
            if positive_trend >= 2:
                trend = "improving"
            elif positive_trend == 0:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return {
            "overall": overall_sentiment,
            "trend": trend,
            "distribution": sentiment_counts
        }
    
    async def _extract_conversation_topics(
        self,
        messages: List[Message]
    ) -> List[str]:
        """Извлекает основные темы диалога."""
        if not messages:
            return []
        
        # Собираем ключевые слова из ИИ-анализа
        all_keywords = []
        for message in messages:
            if message.ai_analysis and "keywords" in message.ai_analysis:
                all_keywords.extend(message.ai_analysis["keywords"])
        
        # Подсчитываем частоту ключевых слов
        keyword_counts = {}
        for keyword in all_keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        # Возвращаем топ-5 самых частых ключевых слов
        top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        return [keyword for keyword, count in top_keywords]
    
    def _calculate_ai_usage_stats(self, messages: List[Message]) -> Dict[str, Any]:
        """Вычисляет статистику использования ИИ."""
        if not messages:
            return {"ai_generated": 0, "total": 0, "percentage": 0}
        
        ai_generated = sum(1 for msg in messages if msg.metadata.get("ai_generated"))
        total = len(messages)
        percentage = (ai_generated / total * 100) if total > 0 else 0
        
        return {
            "ai_generated": ai_generated,
            "total": total,
            "percentage": round(percentage, 2)
        }
    
    def _find_most_active_hour(self, messages: List[Message]) -> int:
        """Находит час наибольшей активности пользователя."""
        if not messages:
            return 12  # По умолчанию полдень
        
        hour_counts = {}
        for message in messages:
            hour = message.created_at.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        return max(hour_counts, key=hour_counts.get)
    
    def _analyze_user_response_pattern(
        self,
        messages: List[Message]
    ) -> Dict[str, Any]:
        """Анализирует паттерн ответов пользователя."""
        if not messages:
            return {"avg_length": 0, "response_rate": 0}
        
        total_length = sum(len(msg.content) for msg in messages)
        avg_length = total_length / len(messages)
        
        return {
            "avg_length": round(avg_length, 2),
            "total_messages": len(messages),
            "avg_words": round(total_length / len(messages) / 5, 2)  # Примерно 5 символов на слово
        }
    
    async def _analyze_user_sentiment_trend(
        self,
        messages: List[Message]
    ) -> Dict[str, Any]:
        """Анализирует тренд тональности пользователя."""
        sentiments = []
        for message in messages:
            if message.ai_analysis and "sentiment" in message.ai_analysis:
                sentiment = message.ai_analysis["sentiment"]
                sentiments.append({
                    "sentiment": sentiment,
                    "date": message.created_at.date()
                })
        
        if not sentiments:
            return {"trend": "neutral", "changes": []}
        
        # Группируем по дням
        daily_sentiments = {}
        for item in sentiments:
            date = item["date"]
            if date not in daily_sentiments:
                daily_sentiments[date] = []
            daily_sentiments[date].append(item["sentiment"])
        
        # Определяем преобладающую тональность по дням
        daily_mood = {}
        for date, day_sentiments in daily_sentiments.items():
            sentiment_counts = {}
            for sentiment in day_sentiments:
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
            daily_mood[date] = max(sentiment_counts, key=sentiment_counts.get)
        
        return {
            "trend": "stable",  # TODO: более сложная логика определения тренда
            "daily_mood": daily_mood
        }
    
    async def _estimate_customer_satisfaction(
        self,
        seller_messages: List[Message]
    ) -> float:
        """Оценивает удовлетворенность клиентов на основе ответов."""
        if not seller_messages:
            return 0.0
        
        # Получаем ответы клиентов на сообщения продавца
        # TODO: реализовать логику анализа ответов клиентов
        
        # Пока возвращаем базовую оценку на основе ИИ-анализа
        total_score = 0
        analyzed_count = 0
        
        for message in seller_messages:
            if message.ai_analysis and "sentiment" in message.ai_analysis:
                sentiment = message.ai_analysis["sentiment"]
                if sentiment == "positive":
                    total_score += 5
                elif sentiment == "neutral":
                    total_score += 3
                else:  # negative
                    total_score += 1
                analyzed_count += 1
        
        return (total_score / analyzed_count) if analyzed_count > 0 else 3.0
    
    async def _calculate_conversion_rate(
        self,
        db: Session,
        seller_id: UUID,
        since_date: datetime
    ) -> float:
        """Вычисляет коэффициент конверсии продавца."""
        # Получаем диалоги продавца за период
        conversations = conversation_crud.get_seller_conversations_since(
            db,
            seller_id=seller_id,
            since_date=since_date
        )
        
        if not conversations:
            return 0.0
        
        # Считаем завершенные диалоги как конверсии
        completed_conversations = [
            c for c in conversations 
            if c.status == "closed" and c.metadata.get("completed_deal")
        ]
        
        return len(completed_conversations) / len(conversations) * 100
    
    async def _get_top_performing_templates(
        self,
        db: Session,
        seller_id: UUID,
        days: int
    ) -> List[Dict[str, Any]]:
        """Получает топ-шаблоны по эффективности."""
        templates = template_crud.get_seller_templates(db, seller_id=seller_id)
        
        # Сортируем по успешности использования
        template_performance = []
        for template in templates:
            success_rate = template_crud.get_template_success_rate(db, template.id, days)
            template_performance.append({
                "id": str(template.id),
                "name": template.name,
                "usage_count": template.usage_count,
                "success_rate": success_rate
            })
        
        # Сортируем по успешности
        template_performance.sort(key=lambda x: x["success_rate"], reverse=True)
        
        return template_performance[:5]  # Топ-5


# Глобальный экземпляр сервиса сообщений
message_service = MessageService()