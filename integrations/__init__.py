"""
🔗 Пакет интеграций с внешними сервисами Avito AI Responder

Этот пакет содержит интеграции с внешними API и сервисами:
- avito/   - Интеграция с API Авито и Selenium автоматизация
- gemini/  - Клиент и промпты для Google Gemini API
- base/    - Базовые классы для всех интеграций

Местоположение: src/integrations/__init__.py
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from datetime import datetime
import logging

# Настройка логгера для интеграций
logger = logging.getLogger(__name__)


class BaseIntegration(ABC):
    """
    🏗️ Базовый класс для всех интеграций
    
    Определяет общий интерфейс и функциональность:
    - Управление подключением
    - Обработка ошибок
    - Сбор метрик
    - Логирование
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Инициализация интеграции
        
        Args:
            name: Название интеграции
            config: Конфигурация интеграции
        """
        self.name = name
        self.config = config
        self.is_connected = False
        self.last_error: Optional[str] = None
        self.connection_time: Optional[datetime] = None
        
        # Метрики
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "last_request_time": None
        }
        
        logger.info("Интеграция %s инициализирована", self.name)
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Подключение к внешнему сервису
        
        Returns:
            bool: True если подключение успешно
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Отключение от внешнего сервиса"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Проверка состояния соединения
        
        Returns:
            bool: True если сервис доступен
        """
        pass
    
    def update_metrics(self, success: bool, response_time: float = 0.0) -> None:
        """Обновление метрик интеграции"""
        
        self.metrics["total_requests"] += 1
        self.metrics["last_request_time"] = datetime.now()
        
        if success:
            self.metrics["successful_requests"] += 1
        else:
            self.metrics["failed_requests"] += 1
        
        # Обновляем среднее время ответа
        if response_time > 0:
            current_avg = self.metrics["avg_response_time"]
            total_requests = self.metrics["total_requests"]
            
            self.metrics["avg_response_time"] = (
                (current_avg * (total_requests - 1) + response_time) / total_requests
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получение метрик интеграции"""
        
        success_rate = 0.0
        if self.metrics["total_requests"] > 0:
            success_rate = self.metrics["successful_requests"] / self.metrics["total_requests"]
        
        return {
            **self.metrics,
            "success_rate": success_rate,
            "is_connected": self.is_connected,
            "last_error": self.last_error,
            "connection_time": self.connection_time
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Получение статуса интеграции"""
        
        return {
            "name": self.name,
            "connected": self.is_connected,
            "last_error": self.last_error,
            "uptime": (
                (datetime.now() - self.connection_time).total_seconds()
                if self.connection_time else 0
            )
        }


class IntegrationManager:
    """
    🎛️ Менеджер всех интеграций
    
    Управляет жизненным циклом интеграций:
    - Регистрация и инициализация
    - Мониторинг состояния
    - Координация между интеграциями
    """
    
    def __init__(self):
        """Инициализация менеджера интеграций"""
        
        self.integrations: Dict[str, BaseIntegration] = {}
        self.startup_time = datetime.now()
        
        logger.info("Менеджер интеграций инициализирован")
    
    def register_integration(self, integration: BaseIntegration) -> None:
        """
        Регистрация новой интеграции
        
        Args:
            integration: Экземпляр интеграции
        """
        
        if integration.name in self.integrations:
            logger.warning("Интеграция %s уже зарегистрирована", integration.name)
            return
        
        self.integrations[integration.name] = integration
        logger.info("Интеграция %s зарегистрирована", integration.name)
    
    async def connect_all(self) -> Dict[str, bool]:
        """
        Подключение всех интеграций
        
        Returns:
            Dict[str, bool]: Результаты подключения по интеграциям
        """
        
        results = {}
        
        for name, integration in self.integrations.items():
            try:
                logger.info("Подключение к %s...", name)
                success = await integration.connect()
                results[name] = success
                
                if success:
                    logger.info("✅ %s подключен успешно", name)
                else:
                    logger.error("❌ Ошибка подключения к %s", name)
                    
            except Exception as e:
                logger.error("❌ Исключение при подключении к %s: %s", name, e)
                results[name] = False
        
        return results
    
    async def disconnect_all(self) -> None:
        """Отключение всех интеграций"""
        
        for name, integration in self.integrations.items():
            try:
                logger.info("Отключение от %s...", name)
                await integration.disconnect()
                logger.info("✅ %s отключен", name)
                
            except Exception as e:
                logger.error("❌ Ошибка отключения от %s: %s", name, e)
    
    async def health_check_all(self) -> Dict[str, bool]:
        """
        Проверка состояния всех интеграций
        
        Returns:
            Dict[str, bool]: Статус каждой интеграции
        """
        
        results = {}
        
        for name, integration in self.integrations.items():
            try:
                is_healthy = await integration.health_check()
                results[name] = is_healthy
                
            except Exception as e:
                logger.error("Ошибка проверки %s: %s", name, e)
                results[name] = False
        
        return results
    
    def get_integration(self, name: str) -> Optional[BaseIntegration]:
        """
        Получение интеграции по имени
        
        Args:
            name: Название интеграции
            
        Returns:
            Optional[BaseIntegration]: Интеграция или None
        """
        
        return self.integrations.get(name)
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Получение метрик всех интеграций"""
        
        return {
            name: integration.get_metrics()
            for name, integration in self.integrations.items()
        }
    
    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Получение статусов всех интеграций"""
        
        return {
            name: integration.get_status()
            for name, integration in self.integrations.items()
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Получение сводной информации"""
        
        total_integrations = len(self.integrations)
        connected_count = sum(
            1 for integration in self.integrations.values()
            if integration.is_connected
        )
        
        return {
            "total_integrations": total_integrations,
            "connected_integrations": connected_count,
            "uptime": (datetime.now() - self.startup_time).total_seconds(),
            "integrations": list(self.integrations.keys())
        }


# Глобальный менеджер интеграций
integration_manager = IntegrationManager()

# Версия пакета интеграций
__version__ = "0.1.0"

# Экспортируемые классы и объекты
__all__ = [
    # Базовые классы
    "BaseIntegration",
    "IntegrationManager",
    
    # Глобальный менеджер
    "integration_manager",
    
    # Версия
    "__version__"
]