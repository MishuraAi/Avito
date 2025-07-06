"""
🔌 API клиент для работы с Авито API

Этот модуль содержит официальный клиент для Авито API:
- Аутентификация и получение токенов
- Получение списка сообщений и объявлений
- Отправка ответов покупателям
- Управление статусами сообщений
- Обработка rate limiting и ошибок

Документация API: https://developers.avito.ru/

Местоположение: src/integrations/avito/api_client.py
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientSession, ClientTimeout

from ..base import BaseIntegration
from . import (
    AvitoIntegrationConfig,
    AvitoMessage, 
    AvitoAd,
    AvitoChat,
    AvitoMessageStatus,
    AvitoAdStatus,
    AvitoAPIException,
    AvitoRateLimitException
)


# Настройка логгера
logger = logging.getLogger(__name__)


class AvitoAPIClient(BaseIntegration):
    """
    🔌 Официальный API клиент для Авито
    
    Предоставляет методы для работы с Авито API:
    - Аутентификация через OAuth 2.0
    - Получение сообщений и объявлений
    - Отправка ответов
    - Управление статусами
    """
    
    def __init__(self, config: AvitoIntegrationConfig):
        """
        Инициализация API клиента
        
        Args:
            config: Конфигурация интеграции с Авито
        """
        
        super().__init__("avito_api", config.__dict__)
        
        self.config = config
        self.session: Optional[ClientSession] = None
        
        # Токены аутентификации
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        
        # Rate limiting
        self.requests_made = 0
        self.rate_limit_reset_time = datetime.now()
        
        logger.info("Авито API клиент инициализирован")
    
    async def connect(self) -> bool:
        """Подключение к Авито API"""
        
        try:
            # Создаем HTTP сессию
            timeout = ClientTimeout(total=self.config.request_timeout)
            self.session = ClientSession(timeout=timeout)
            
            # Получаем токен доступа
            success = await self._authenticate()
            
            if success:
                self.is_connected = True
                self.connection_time = datetime.now()
                logger.info("✅ Подключение к Авито API успешно")
            else:
                logger.error("❌ Ошибка аутентификации в Авито API")
            
            return success
            
        except Exception as e:
            self.last_error = str(e)
            logger.error("❌ Ошибка подключения к Авито API: %s", e)
            return False
    
    async def disconnect(self) -> None:
        """Отключение от Авито API"""
        
        if self.session:
            await self.session.close()
            self.session = None
        
        self.is_connected = False
        self.access_token = None
        self.refresh_token = None
        
        logger.info("Отключение от Авито API")
    
    async def health_check(self) -> bool:
        """Проверка состояния API"""
        
        try:
            # Проверяем валидность токена
            if not await self._ensure_valid_token():
                return False
            
            # Делаем простой запрос для проверки
            response = await self._make_request("GET", "/core/v1/accounts/self/")
            return response is not None
            
        except Exception as e:
            logger.error("Ошибка health check Авито API: %s", e)
            return False
    
    async def get_messages(
        self,
        limit: int = 50,
        unread_only: bool = False,
        chat_id: Optional[str] = None
    ) -> List[AvitoMessage]:
        """
        Получение списка сообщений
        
        Args:
            limit: Максимальное количество сообщений
            unread_only: Только непрочитанные сообщения
            chat_id: ID конкретного чата (опционально)
            
        Returns:
            List[AvitoMessage]: Список сообщений
        """
        
        start_time = datetime.now()
        
        try:
            # Формируем параметры запроса
            params = {
                "limit": min(limit, 100),  # API ограничение
            }
            
            if unread_only:
                params["unread_only"] = "true"
            
            if chat_id:
                params["chat_id"] = chat_id
            
            # Делаем запрос
            endpoint = "/messenger/v1/accounts/self/chats/messages/"
            response = await self._make_request("GET", endpoint, params=params)
            
            if not response:
                return []
            
            # Парсим ответ
            messages = []
            for message_data in response.get("messages", []):
                try:
                    message = self._parse_message(message_data)
                    messages.append(message)
                except Exception as e:
                    logger.warning("Ошибка парсинга сообщения: %s", e)
            
            # Обновляем метрики
            processing_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(True, processing_time)
            
            logger.info("Получено %d сообщений", len(messages))
            return messages
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(False, processing_time)
            logger.error("Ошибка получения сообщений: %s", e)
            return []
    
    async def send_message(
        self,
        chat_id: str,
        text: str
    ) -> bool:
        """
        Отправка сообщения в чат
        
        Args:
            chat_id: ID чата
            text: Текст сообщения
            
        Returns:
            bool: True если сообщение отправлено успешно
        """
        
        start_time = datetime.now()
        
        try:
            # Подготовка данных
            payload = {
                "message": {
                    "text": text,
                    "type": "text"
                }
            }
            
            # Отправка запроса
            endpoint = f"/messenger/v1/accounts/self/chats/{chat_id}/messages/"
            response = await self._make_request("POST", endpoint, json=payload)
            
            success = response is not None
            
            # Обновляем метрики
            processing_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(success, processing_time)
            
            if success:
                logger.info("✅ Сообщение отправлено в чат %s", chat_id)
            else:
                logger.error("❌ Ошибка отправки сообщения в чат %s", chat_id)
            
            return success
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(False, processing_time)
            logger.error("Ошибка отправки сообщения: %s", e)
            return False
    
    async def mark_message_as_read(self, message_id: str) -> bool:
        """
        Отметка сообщения как прочитанного
        
        Args:
            message_id: ID сообщения
            
        Returns:
            bool: True если успешно
        """
        
        try:
            endpoint = f"/messenger/v1/accounts/self/chats/messages/{message_id}/read/"
            response = await self._make_request("POST", endpoint)
            
            success = response is not None
            
            if success:
                logger.debug("Сообщение %s отмечено как прочитанное", message_id)
            
            return success
            
        except Exception as e:
            logger.error("Ошибка отметки сообщения как прочитанного: %s", e)
            return False
    
    async def get_ads(
        self,
        limit: int = 50,
        status: Optional[AvitoAdStatus] = None
    ) -> List[AvitoAd]:
        """
        Получение списка объявлений
        
        Args:
            limit: Максимальное количество объявлений
            status: Фильтр по статусу (опционально)
            
        Returns:
            List[AvitoAd]: Список объявлений
        """
        
        start_time = datetime.now()
        
        try:
            # Параметры запроса
            params = {
                "limit": min(limit, 100)
            }
            
            if status:
                params["status"] = status.value
            
            # Запрос
            endpoint = "/core/v1/accounts/self/items/"
            response = await self._make_request("GET", endpoint, params=params)
            
            if not response:
                return []
            
            # Парсинг
            ads = []
            for ad_data in response.get("items", []):
                try:
                    ad = self._parse_ad(ad_data)
                    ads.append(ad)
                except Exception as e:
                    logger.warning("Ошибка парсинга объявления: %s", e)
            
            # Метрики
            processing_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(True, processing_time)
            
            logger.info("Получено %d объявлений", len(ads))
            return ads
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(False, processing_time)
            logger.error("Ошибка получения объявлений: %s", e)
            return []
    
    async def get_chats(self, limit: int = 50) -> List[AvitoChat]:
        """
        Получение списка чатов
        
        Args:
            limit: Максимальное количество чатов
            
        Returns:
            List[AvitoChat]: Список чатов
        """
        
        try:
            params = {"limit": min(limit, 100)}
            
            endpoint = "/messenger/v1/accounts/self/chats/"
            response = await self._make_request("GET", endpoint, params=params)
            
            if not response:
                return []
            
            chats = []
            for chat_data in response.get("chats", []):
                try:
                    chat = self._parse_chat(chat_data)
                    chats.append(chat)
                except Exception as e:
                    logger.warning("Ошибка парсинга чата: %s", e)
            
            logger.info("Получено %d чатов", len(chats))
            return chats
            
        except Exception as e:
            logger.error("Ошибка получения чатов: %s", e)
            return []
    
    async def _authenticate(self) -> bool:
        """Аутентификация в Авито API"""
        
        try:
            # Данные для получения токена
            auth_data = {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "grant_type": "client_credentials"
            }
            
            # Запрос токена
            url = urljoin(self.config.api_base_url, "/token/")
            
            async with self.session.post(url, data=auth_data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    
                    self.access_token = token_data.get("access_token")
                    self.refresh_token = token_data.get("refresh_token")
                    
                    # Рассчитываем время истечения
                    expires_in = token_data.get("expires_in", 3600)
                    self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                    
                    logger.info("✅ Аутентификация в Авито API успешна")
                    return True
                    
                else:
                    error_text = await response.text()
                    logger.error("❌ Ошибка аутентификации: %d - %s", response.status, error_text)
                    return False
                    
        except Exception as e:
            logger.error("❌ Исключение при аутентификации: %s", e)
            return False
    
    async def _ensure_valid_token(self) -> bool:
        """Проверка и обновление токена если необходимо"""
        
        if not self.access_token:
            return await self._authenticate()
        
        # Проверяем истечение токена (с запасом 5 минут)
        if self.token_expires_at and datetime.now() >= self.token_expires_at - timedelta(minutes=5):
            logger.info("Токен истекает, обновляем...")
            return await self._authenticate()
        
        return True
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Выполнение HTTP запроса к API
        
        Args:
            method: HTTP метод
            endpoint: Конечная точка API
            params: Параметры запроса
            json: JSON данные
            
        Returns:
            Optional[Dict]: Ответ API или None при ошибке
        """
        
        # Проверяем rate limiting
        await self._check_rate_limit()
        
        # Обеспечиваем валидный токен
        if not await self._ensure_valid_token():
            raise AvitoAPIException("Невозможно получить валидный токен", 401)
        
        # Формируем URL
        url = urljoin(self.config.api_base_url, endpoint)
        
        # Заголовки
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with self.session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                headers=headers
            ) as response:
                
                # Обновляем счетчик запросов
                self.requests_made += 1
                
                # Обрабатываем успешные ответы
                if response.status == 200:
                    return await response.json()
                
                # Обрабатываем ошибки
                elif response.status == 429:
                    # Rate limiting
                    retry_after = int(response.headers.get("Retry-After", 60))
                    raise AvitoRateLimitException(
                        "Превышен лимит запросов", 
                        retry_after
                    )
                
                else:
                    error_text = await response.text()
                    raise AvitoAPIException(
                        f"Ошибка API: {error_text}",
                        response.status
                    )
                    
        except aiohttp.ClientError as e:
            raise AvitoAPIException(f"Ошибка сети: {e}", 0)
    
    async def _check_rate_limit(self) -> None:
        """Проверка и соблюдение rate limiting"""
        
        now = datetime.now()
        
        # Сброс счетчика если прошло окно
        if now >= self.rate_limit_reset_time:
            self.requests_made = 0
            self.rate_limit_reset_time = now + timedelta(seconds=self.config.rate_limit_window)
        
        # Проверяем лимит
        if self.requests_made >= self.config.rate_limit_requests:
            sleep_time = (self.rate_limit_reset_time - now).total_seconds()
            if sleep_time > 0:
                logger.warning("Rate limit достигнут, ожидание %.1f сек", sleep_time)
                await asyncio.sleep(sleep_time)
                
                # Сбрасываем после ожидания
                self.requests_made = 0
                self.rate_limit_reset_time = datetime.now() + timedelta(
                    seconds=self.config.rate_limit_window
                )
    
    def _parse_message(self, data: Dict[str, Any]) -> AvitoMessage:
        """Парсинг сообщения из API ответа"""
        
        # Парсинг даты
        created_at = datetime.fromisoformat(
            data["created"].replace("Z", "+00:00")
        )
        
        # Определение статуса
        status = AvitoMessageStatus.READ if data.get("read", False) else AvitoMessageStatus.UNREAD
        
        return AvitoMessage(
            message_id=data["id"],
            chat_id=data["chat_id"],
            ad_id=data["item_id"],
            user_id=data["author_id"],
            text=data["text"],
            created_at=created_at,
            status=status,
            is_from_seller=data.get("direction") == "to_user",
            attachments=data.get("attachments", []),
            raw_data=data
        )
    
    def _parse_ad(self, data: Dict[str, Any]) -> AvitoAd:
        """Парсинг объявления из API ответа"""
        
        # Парсинг дат
        created_at = datetime.fromisoformat(
            data["created_at"].replace("Z", "+00:00")
        )
        updated_at = datetime.fromisoformat(
            data["updated_at"].replace("Z", "+00:00")
        )
        
        # Определение статуса
        status = AvitoAdStatus(data.get("status", "active"))
        
        return AvitoAd(
            ad_id=data["id"],
            title=data["title"],
            price=data.get("price"),
            description=data.get("description", ""),
            category=data.get("category", {}).get("name", ""),
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            images=data.get("images", []),
            location=data.get("location", {}).get("name"),
            views_count=data.get("stats", {}).get("views", 0),
            contacts_count=data.get("stats", {}).get("contacts", 0),
            raw_data=data
        )
    
    def _parse_chat(self, data: Dict[str, Any]) -> AvitoChat:
        """Парсинг чата из API ответа"""
        
        # Парсинг последнего сообщения
        last_message_at = None
        if data.get("last_message", {}).get("created"):
            last_message_at = datetime.fromisoformat(
                data["last_message"]["created"].replace("Z", "+00:00")
            )
        
        return AvitoChat(
            chat_id=data["id"],
            ad_id=data["item_id"],
            user_id=data["user_id"],
            user_name=data.get("user_name"),
            messages_count=data.get("messages_count", 0),
            last_message_at=last_message_at,
            unread_count=data.get("unread_count", 0),
            is_blocked=data.get("blocked", False),
            is_archived=data.get("archived", False)
        )


# Фабричная функция
async def create_avito_api_client(config: AvitoIntegrationConfig) -> AvitoAPIClient:
    """
    🏭 Создание и подключение API клиента Авито
    
    Args:
        config: Конфигурация интеграции
        
    Returns:
        AvitoAPIClient: Готовый к работе клиент
    """
    
    if not config.validate():
        raise ValueError("Некорректная конфигурация Авито API")
    
    client = AvitoAPIClient(config)
    
    # Подключаемся к API
    success = await client.connect()
    if not success:
        raise AvitoAPIException("Не удалось подключиться к Авито API", 0)
    
    logger.info("Авито API клиент создан и подключен")
    return client