"""
Сервис для интеграции с Avito API.

Обрабатывает всю бизнес-логику взаимодействия с платформой Авито:
синхронизацию объявлений, получение сообщений, отправку ответов.
"""

import asyncio
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.integrations.avito.api_client import AvitoAPIClient
from src.integrations.avito import AvitoError, AvitoAPIError
from src.database.crud.users import seller_crud
from src.database.models.users import Seller
from src.utils.exceptions import BusinessLogicError, ExternalServiceError, ValidationError
from src.utils.validators import validate_avito_credentials
from src.utils.formatters import format_avito_message, format_avito_listing


class AvitoService:
    """
    Сервис для работы с Avito API.
    
    Предоставляет высокоуровневые методы для синхронизации данных,
    управления объявлениями и обработки сообщений.
    """
    
    def __init__(self):
        self.api_client = AvitoAPIClient()
        self._connection_cache = {}  # Кеш подключений для продавцов
    
    # ========================================================================
    # МЕТОДЫ УПРАВЛЕНИЯ ПОДКЛЮЧЕНИЯМИ
    # ========================================================================
    
    async def connect_seller_account(
        self,
        db: Session,
        seller_id: UUID,
        avito_credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Подключает аккаунт продавца к Avito API.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            avito_credentials: Учетные данные Avito
            
        Returns:
            Результат подключения
            
        Raises:
            ValidationError: При некорректных учетных данных
            ExternalServiceError: При ошибках API Avito
        """
        # Валидируем учетные данные
        if not validate_avito_credentials(avito_credentials):
            raise ValidationError("Некорректные учетные данные Avito")
        
        seller = seller_crud.get(db, id=seller_id)
        if not seller:
            raise BusinessLogicError("Продавец не найден")
        
        try:
            # Проверяем подключение к Avito API
            connection_result = await self.api_client.test_connection(avito_credentials)
            
            if connection_result["success"]:
                # Сохраняем учетные данные (зашифрованно)
                encrypted_credentials = self._encrypt_credentials(avito_credentials)
                
                integration_settings = seller.integration_settings or {}
                integration_settings.update({
                    "avito_connected": True,
                    "avito_credentials": encrypted_credentials,
                    "avito_user_id": connection_result.get("user_id"),
                    "connection_date": datetime.utcnow().isoformat(),
                    "last_sync": None
                })
                
                # Обновляем продавца
                seller_crud.update(
                    db,
                    db_obj=seller,
                    obj_in={"integration_settings": integration_settings}
                )
                
                # Добавляем в кеш подключений
                self._connection_cache[str(seller_id)] = {
                    "credentials": avito_credentials,
                    "connected_at": datetime.utcnow()
                }
                
                return {
                    "success": True,
                    "message": "Аккаунт Avito успешно подключен",
                    "user_info": connection_result.get("user_info", {})
                }
            else:
                raise ExternalServiceError(f"Ошибка подключения к Avito: {connection_result['error']}")
                
        except AvitoAPIError as e:
            raise ExternalServiceError(f"Ошибка Avito API: {str(e)}")
        except Exception as e:
            raise ExternalServiceError(f"Неожиданная ошибка при подключении: {str(e)}")
    
    async def disconnect_seller_account(
        self,
        db: Session,
        seller_id: UUID
    ) -> bool:
        """
        Отключает аккаунт продавца от Avito API.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            
        Returns:
            True при успешном отключении
        """
        seller = seller_crud.get(db, id=seller_id)
        if not seller:
            raise BusinessLogicError("Продавец не найден")
        
        # Обновляем настройки интеграции
        integration_settings = seller.integration_settings or {}
        integration_settings.update({
            "avito_connected": False,
            "avito_credentials": None,
            "avito_user_id": None,
            "disconnection_date": datetime.utcnow().isoformat()
        })
        
        seller_crud.update(
            db,
            db_obj=seller,
            obj_in={"integration_settings": integration_settings}
        )
        
        # Удаляем из кеша
        self._connection_cache.pop(str(seller_id), None)
        
        return True
    
    async def check_connection_status(
        self,
        db: Session,
        seller_id: UUID
    ) -> Dict[str, Any]:
        """
        Проверяет статус подключения к Avito API.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            
        Returns:
            Статус подключения
        """
        seller = seller_crud.get(db, id=seller_id)
        if not seller:
            return {"connected": False, "error": "Продавец не найден"}
        
        integration_settings = seller.integration_settings or {}
        
        if not integration_settings.get("avito_connected"):
            return {"connected": False, "error": "Аккаунт не подключен"}
        
        try:
            # Проверяем активность подключения
            credentials = self._decrypt_credentials(integration_settings.get("avito_credentials"))
            if not credentials:
                return {"connected": False, "error": "Отсутствуют учетные данные"}
            
            test_result = await self.api_client.test_connection(credentials)
            
            return {
                "connected": test_result["success"],
                "last_check": datetime.utcnow().isoformat(),
                "user_info": test_result.get("user_info", {}),
                "error": test_result.get("error") if not test_result["success"] else None
            }
            
        except Exception as e:
            return {
                "connected": False,
                "error": f"Ошибка проверки подключения: {str(e)}"
            }
    
    # ========================================================================
    # МЕТОДЫ РАБОТЫ С ОБЪЯВЛЕНИЯМИ
    # ========================================================================
    
    async def sync_seller_listings(
        self,
        db: Session,
        seller_id: UUID,
        force_full_sync: bool = False
    ) -> Dict[str, Any]:
        """
        Синхронизирует объявления продавца с Avito.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            force_full_sync: Принудительная полная синхронизация
            
        Returns:
            Результат синхронизации
        """
        credentials = await self._get_seller_credentials(db, seller_id)
        if not credentials:
            raise BusinessLogicError("Аккаунт Avito не подключен")
        
        try:
            # Получаем последнюю дату синхронизации
            seller = seller_crud.get(db, id=seller_id)
            integration_settings = seller.integration_settings or {}
            last_sync = integration_settings.get("last_sync")
            
            # Определяем период синхронизации
            if force_full_sync or not last_sync:
                # Полная синхронизация
                since_date = None
            else:
                # Инкрементальная синхронизация
                since_date = datetime.fromisoformat(last_sync)
            
            # Получаем объявления от Avito
            listings_result = await self.api_client.get_user_listings(
                credentials,
                since_date=since_date
            )
            
            if not listings_result["success"]:
                raise ExternalServiceError(f"Ошибка получения объявлений: {listings_result['error']}")
            
            listings = listings_result["data"]
            
            # Обрабатываем каждое объявление
            sync_stats = {
                "total_listings": len(listings),
                "new_listings": 0,
                "updated_listings": 0,
                "errors": []
            }
            
            for listing_data in listings:
                try:
                    result = await self._process_listing(db, seller_id, listing_data)
                    if result["action"] == "created":
                        sync_stats["new_listings"] += 1
                    elif result["action"] == "updated":
                        sync_stats["updated_listings"] += 1
                except Exception as e:
                    sync_stats["errors"].append({
                        "listing_id": listing_data.get("id"),
                        "error": str(e)
                    })
            
            # Обновляем время последней синхронизации
            integration_settings["last_sync"] = datetime.utcnow().isoformat()
            seller_crud.update(
                db,
                db_obj=seller,
                obj_in={"integration_settings": integration_settings}
            )
            
            sync_stats["sync_completed_at"] = datetime.utcnow().isoformat()
            return sync_stats
            
        except AvitoAPIError as e:
            raise ExternalServiceError(f"Ошибка Avito API: {str(e)}")
    
    async def get_listing_details(
        self,
        db: Session,
        seller_id: UUID,
        listing_id: str
    ) -> Dict[str, Any]:
        """
        Получает детальную информацию об объявлении.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            listing_id: ID объявления в Avito
            
        Returns:
            Информация об объявлении
        """
        credentials = await self._get_seller_credentials(db, seller_id)
        if not credentials:
            raise BusinessLogicError("Аккаунт Avito не подключен")
        
        try:
            result = await self.api_client.get_listing_details(credentials, listing_id)
            
            if result["success"]:
                return format_avito_listing(result["data"])
            else:
                raise ExternalServiceError(f"Ошибка получения объявления: {result['error']}")
                
        except AvitoAPIError as e:
            raise ExternalServiceError(f"Ошибка Avito API: {str(e)}")
    
    async def update_listing_status(
        self,
        db: Session,
        seller_id: UUID,
        listing_id: str,
        status: str
    ) -> bool:
        """
        Обновляет статус объявления в Avito.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            listing_id: ID объявления
            status: Новый статус
            
        Returns:
            True при успешном обновлении
        """
        credentials = await self._get_seller_credentials(db, seller_id)
        if not credentials:
            raise BusinessLogicError("Аккаунт Avito не подключен")
        
        valid_statuses = ["active", "paused", "archived"]
        if status not in valid_statuses:
            raise ValidationError(f"Некорректный статус. Доступны: {', '.join(valid_statuses)}")
        
        try:
            result = await self.api_client.update_listing_status(
                credentials,
                listing_id,
                status
            )
            
            return result["success"]
            
        except AvitoAPIError as e:
            raise ExternalServiceError(f"Ошибка Avito API: {str(e)}")
    
    # ========================================================================
    # МЕТОДЫ РАБОТЫ С СООБЩЕНИЯМИ
    # ========================================================================
    
    async def sync_seller_messages(
        self,
        db: Session,
        seller_id: UUID,
        hours_back: int = 24
    ) -> Dict[str, Any]:
        """
        Синхронизирует сообщения продавца с Avito.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            hours_back: Количество часов назад для синхронизации
            
        Returns:
            Результат синхронизации сообщений
        """
        credentials = await self._get_seller_credentials(db, seller_id)
        if not credentials:
            raise BusinessLogicError("Аккаунт Avito не подключен")
        
        try:
            since_date = datetime.utcnow() - timedelta(hours=hours_back)
            
            # Получаем сообщения от Avito
            messages_result = await self.api_client.get_messages(
                credentials,
                since_date=since_date
            )
            
            if not messages_result["success"]:
                raise ExternalServiceError(f"Ошибка получения сообщений: {messages_result['error']}")
            
            messages = messages_result["data"]
            
            # Обрабатываем сообщения
            sync_stats = {
                "total_messages": len(messages),
                "new_messages": 0,
                "updated_messages": 0,
                "errors": []
            }
            
            for message_data in messages:
                try:
                    result = await self._process_avito_message(db, seller_id, message_data)
                    if result["action"] == "created":
                        sync_stats["new_messages"] += 1
                    elif result["action"] == "updated":
                        sync_stats["updated_messages"] += 1
                except Exception as e:
                    sync_stats["errors"].append({
                        "message_id": message_data.get("id"),
                        "error": str(e)
                    })
            
            return sync_stats
            
        except AvitoAPIError as e:
            raise ExternalServiceError(f"Ошибка Avito API: {str(e)}")
    
    async def send_message_to_avito(
        self,
        db: Session,
        seller_id: UUID,
        recipient_id: str,
        content: str,
        listing_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Отправляет сообщение через Avito API.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            recipient_id: ID получателя в Avito
            content: Содержимое сообщения
            listing_id: ID объявления (опционально)
            
        Returns:
            Результат отправки
        """
        credentials = await self._get_seller_credentials(db, seller_id)
        if not credentials:
            raise BusinessLogicError("Аккаунт Avito не подключен")
        
        if not content.strip():
            raise ValidationError("Сообщение не может быть пустым")
        
        try:
            # Проверяем лимиты продавца
            await self._check_message_limits(db, seller_id)
            
            # Отправляем сообщение
            result = await self.api_client.send_message(
                credentials,
                recipient_id=recipient_id,
                content=content.strip(),
                listing_id=listing_id
            )
            
            if result["success"]:
                # Обновляем счетчик использованных сообщений
                await self._increment_message_usage(db, seller_id)
                
                return {
                    "success": True,
                    "message_id": result["data"]["message_id"],
                    "sent_at": datetime.utcnow().isoformat()
                }
            else:
                raise ExternalServiceError(f"Ошибка отправки сообщения: {result['error']}")
                
        except AvitoAPIError as e:
            raise ExternalServiceError(f"Ошибка Avito API: {str(e)}")
    
    async def mark_message_as_read(
        self,
        db: Session,
        seller_id: UUID,
        message_id: str
    ) -> bool:
        """
        Отмечает сообщение как прочитанное в Avito.
        
        Args:
            db: Sессия базы данных
            seller_id: ID продавца
            message_id: ID сообщения в Avito
            
        Returns:
            True при успешном выполнении
        """
        credentials = await self._get_seller_credentials(db, seller_id)
        if not credentials:
            raise BusinessLogicError("Аккаунт Avito не подключен")
        
        try:
            result = await self.api_client.mark_message_read(credentials, message_id)
            return result["success"]
            
        except AvitoAPIError as e:
            raise ExternalServiceError(f"Ошибка Avito API: {str(e)}")
    
    # ========================================================================
    # МЕТОДЫ АНАЛИТИКИ И СТАТИСТИКИ
    # ========================================================================
    
    async def get_seller_avito_stats(
        self,
        db: Session,
        seller_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Получает статистику продавца в Avito.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            days: Период для анализа
            
        Returns:
            Статистика Avito
        """
        credentials = await self._get_seller_credentials(db, seller_id)
        if not credentials:
            return {"error": "Аккаунт Avito не подключен"}
        
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Получаем статистику от Avito API
            stats_result = await self.api_client.get_user_stats(
                credentials,
                since_date=since_date
            )
            
            if stats_result["success"]:
                avito_stats = stats_result["data"]
                
                # Дополняем локальной статистикой
                local_stats = await self._get_local_avito_stats(db, seller_id, days)
                
                return {
                    "avito_data": avito_stats,
                    "local_data": local_stats,
                    "period_days": days,
                    "last_updated": datetime.utcnow().isoformat()
                }
            else:
                return {"error": f"Ошибка получения статистики: {stats_result['error']}"}
                
        except AvitoAPIError as e:
            return {"error": f"Ошибка Avito API: {str(e)}"}
    
    async def get_listing_performance(
        self,
        db: Session,
        seller_id: UUID,
        listing_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Получает статистику производительности объявления.
        
        Args:
            db: Сессия базы данных
            seller_id: ID продавца
            listing_id: ID объявления
            days: Период для анализа
            
        Returns:
            Статистика объявления
        """
        credentials = await self._get_seller_credentials(db, seller_id)
        if not credentials:
            return {"error": "Аккаунт Avito не подключен"}
        
        try:
            result = await self.api_client.get_listing_stats(
                credentials,
                listing_id=listing_id,
                days=days
            )
            
            if result["success"]:
                return result["data"]
            else:
                return {"error": f"Ошибка получения статистики: {result['error']}"}
                
        except AvitoAPIError as e:
            return {"error": f"Ошибка Avito API: {str(e)}"}
    
    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ========================================================================
    
    async def _get_seller_credentials(
        self,
        db: Session,
        seller_id: UUID
    ) -> Optional[Dict[str, str]]:
        """Получает учетные данные продавца для Avito API."""
        # Проверяем кеш
        cached = self._connection_cache.get(str(seller_id))
        if cached:
            # Проверяем актуальность кеша (1 час)
            if (datetime.utcnow() - cached["connected_at"]).seconds < 3600:
                return cached["credentials"]
        
        # Получаем из базы данных
        seller = seller_crud.get(db, id=seller_id)
        if not seller:
            return None
        
        integration_settings = seller.integration_settings or {}
        if not integration_settings.get("avito_connected"):
            return None
        
        encrypted_credentials = integration_settings.get("avito_credentials")
        if not encrypted_credentials:
            return None
        
        credentials = self._decrypt_credentials(encrypted_credentials)
        
        # Обновляем кеш
        if credentials:
            self._connection_cache[str(seller_id)] = {
                "credentials": credentials,
                "connected_at": datetime.utcnow()
            }
        
        return credentials
    
    def _encrypt_credentials(self, credentials: Dict[str, str]) -> str:
        """Шифрует учетные данные для хранения."""
        import json
        import base64
        
        # TODO: Реализовать настоящее шифрование в продакшене
        # Сейчас используется базовое кодирование для демонстрации
        credentials_json = json.dumps(credentials)
        encoded = base64.b64encode(credentials_json.encode()).decode()
        return encoded
    
    def _decrypt_credentials(self, encrypted_credentials: str) -> Optional[Dict[str, str]]:
        """Расшифровывает учетные данные."""
        import json
        import base64
        
        try:
            # TODO: Реализовать настоящее расшифрование в продакшене
            decoded = base64.b64decode(encrypted_credentials.encode()).decode()
            credentials = json.loads(decoded)
            return credentials
        except Exception:
            return None
    
    async def _process_listing(
        self,
        db: Session,
        seller_id: UUID,
        listing_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Обрабатывает объявление при синхронизации."""
        # TODO: Реализовать сохранение объявлений в локальную БД
        # Пока возвращаем заглушку
        
        listing_id = listing_data.get("id")
        
        # Проверяем, существует ли объявление в нашей БД
        # existing_listing = listing_crud.get_by_avito_id(db, avito_id=listing_id)
        
        # if existing_listing:
        #     # Обновляем существующее
        #     listing_crud.update(db, db_obj=existing_listing, obj_in=listing_data)
        #     return {"action": "updated", "listing_id": listing_id}
        # else:
        #     # Создаем новое
        #     listing_data["seller_id"] = seller_id
        #     listing_crud.create(db, obj_in=listing_data)
        #     return {"action": "created", "listing_id": listing_id}
        
        return {"action": "processed", "listing_id": listing_id}
    
    async def _process_avito_message(
        self,
        db: Session,
        seller_id: UUID,
        message_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Обрабатывает сообщение при синхронизации."""
        from .message_service import message_service
        
        # Форматируем сообщение из Avito
        formatted_message = format_avito_message(message_data)
        
        try:
            # Создаем сообщение в нашей системе
            message = await message_service.create_message(
                db=db,
                sender_id=UUID(formatted_message["sender_id"]),
                recipient_id=seller_id,
                content=formatted_message["content"],
                message_type="text",
                metadata={
                    "source": "avito",
                    "avito_message_id": message_data.get("id"),
                    "listing_id": message_data.get("listing_id"),
                    "original_data": message_data
                }
            )
            
            return {"action": "created", "message_id": str(message.id)}
            
        except Exception as e:
            return {"action": "error", "error": str(e)}
    
    async def _check_message_limits(self, db: Session, seller_id: UUID) -> None:
        """Проверяет лимиты отправки сообщений."""
        seller = seller_crud.get(db, id=seller_id)
        if not seller:
            raise BusinessLogicError("Продавец не найден")
        
        if seller.monthly_messages_used >= seller.monthly_message_limit:
            raise BusinessLogicError("Превышен месячный лимит сообщений")
    
    async def _increment_message_usage(self, db: Session, seller_id: UUID) -> None:
        """Увеличивает счетчик использованных сообщений."""
        seller = seller_crud.get(db, id=seller_id)
        if seller:
            new_count = seller.monthly_messages_used + 1
            seller_crud.update(
                db,
                db_obj=seller,
                obj_in={"monthly_messages_used": new_count}
            )
    
    async def _get_local_avito_stats(
        self,
        db: Session,
        seller_id: UUID,
        days: int
    ) -> Dict[str, Any]:
        """Получает локальную статистику взаимодействия с Avito."""
        # TODO: Реализовать сбор локальной статистики
        return {
            "sync_frequency": "daily",
            "last_sync": "2025-01-06T12:00:00Z",
            "api_requests_count": 142,
            "sync_errors": 0
        }


# Глобальный экземпляр сервиса Avito
avito_service = AvitoService()