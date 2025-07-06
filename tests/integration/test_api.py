"""
🧪 Integration тесты для API эндпоинтов

Тестируем:
- Аутентификация и регистрация
- CRUD операции пользователей
- Обработка сообщений
- Системные эндпоинты
"""

import pytest
from fastapi.testclient import TestClient


class TestAuthEndpoints:
    """Тесты эндпоинтов аутентификации"""
    
    def test_register_user_success(self, test_client):
        """Тест успешной регистрации пользователя"""
        user_data = {
            "email": "newuser@example.com",
            "password": "securepassword123",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+7900123456"
        }
        
        response = test_client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["first_name"] == "John"
        assert "password" not in data  # Пароль не должен возвращаться
        assert "id" in data
    
    def test_register_user_duplicate_email(self, test_client):
        """Тест регистрации с существующим email"""
        user_data = {
            "email": "duplicate@example.com",
            "password": "password123",
            "first_name": "First"
        }
        
        # Первая регистрация
        response = test_client.post("/api/auth/register", json=user_data)
        assert response.status_code == 201
        
        # Повторная регистрация с тем же email
        response = test_client.post("/api/auth/register", json=user_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()
    
    def test_register_user_invalid_data(self, test_client):
        """Тест регистрации с невалидными данными"""
        # Невалидный email
        response = test_client.post("/api/auth/register", json={
            "email": "invalid-email",
            "password": "password123",
            "first_name": "Test"
        })
        assert response.status_code == 422
        
        # Слишком короткий пароль
        response = test_client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "123",
            "first_name": "Test"
        })
        assert response.status_code == 422
    
    def test_login_success(self, test_client):
        """Тест успешного входа"""
        # Сначала регистрируемся
        user_data = {
            "email": "login@example.com",
            "password": "loginpassword123",
            "first_name": "Login"
        }
        test_client.post("/api/auth/register", json=user_data)
        
        # Теперь логинимся
        login_data = {
            "email": "login@example.com",
            "password": "loginpassword123"
        }
        
        response = test_client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == "login@example.com"
    
    def test_login_wrong_password(self, test_client):
        """Тест входа с неправильным паролем"""
        # Регистрируемся
        user_data = {
            "email": "wrong@example.com",
            "password": "correctpassword",
            "first_name": "Test"
        }
        test_client.post("/api/auth/register", json=user_data)
        
        # Логинимся с неправильным паролем
        login_data = {
            "email": "wrong@example.com",
            "password": "wrongpassword"
        }
        
        response = test_client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    def test_login_nonexistent_user(self, test_client):
        """Тест входа несуществующего пользователя"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "password123"
        }
        
        response = test_client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401
    
    def test_register_seller_success(self, test_client):
        """Тест успешной регистрации продавца"""
        seller_data = {
            "email": "seller@example.com",
            "password": "sellerpassword123",
            "first_name": "Jane",
            "last_name": "Smith",
            "company_name": "Test Company",
            "subscription_type": "free"
        }
        
        response = test_client.post("/api/auth/register-seller", json=seller_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "seller@example.com"
        assert data["company_name"] == "Test Company"
        assert data["subscription_type"] == "free"
        assert "password" not in data


class TestUserEndpoints:
    """Тесты пользовательских эндпоинтов"""
    
    def test_get_current_user(self, test_client, auth_headers):
        """Тест получения текущего пользователя"""
        response = test_client.get("/api/users/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "password" not in data
    
    def test_get_current_user_unauthorized(self, test_client):
        """Тест получения профиля без аутентификации"""
        response = test_client.get("/api/users/me")
        
        assert response.status_code == 401
    
    def test_update_user_profile(self, test_client, auth_headers):
        """Тест обновления профиля пользователя"""
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "phone": "+7900999888"
        }
        
        response = test_client.patch("/api/users/me", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"
        assert data["phone"] == "+7900999888"
    
    def test_get_user_by_id(self, test_client, auth_headers):
        """Тест получения пользователя по ID"""
        # Сначала получаем ID текущего пользователя
        me_response = test_client.get("/api/users/me", headers=auth_headers)
        user_id = me_response.json()["id"]
        
        # Теперь получаем пользователя по ID
        response = test_client.get(f"/api/users/{user_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
    
    def test_get_nonexistent_user(self, test_client, auth_headers):
        """Тест получения несуществующего пользователя"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = test_client.get(f"/api/users/{fake_id}", headers=auth_headers)
        
        assert response.status_code == 404


class TestMessageEndpoints:
    """Тесты эндпоинтов сообщений"""
    
    def test_create_message(self, test_client, auth_headers):
        """Тест создания сообщения"""
        # Сначала создаем продавца
        seller_data = {
            "email": "msgseller@example.com",
            "password": "password123",
            "first_name": "Seller",
            "company_name": "Company"
        }
        seller_response = test_client.post("/api/auth/register-seller", json=seller_data)
        seller_id = seller_response.json()["id"]
        
        # Создаем сообщение
        message_data = {
            "content": "Тестовое сообщение",
            "recipient_id": seller_id,
            "message_type": "user_to_seller",
            "platform": "avito"
        }
        
        response = test_client.post("/api/messages/", json=message_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "Тестовое сообщение"
        assert data["recipient_id"] == seller_id
        assert data["message_type"] == "user_to_seller"
        assert data["status"] == "sent"
    
    def test_get_user_messages(self, test_client, auth_headers):
        """Тест получения сообщений пользователя"""
        response = test_client.get("/api/messages/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert isinstance(data["items"], list)
    
    def test_get_message_by_id(self, test_client, auth_headers):
        """Тест получения сообщения по ID"""
        # Создаем сообщение сначала
        seller_data = {
            "email": "getmsgseller@example.com",
            "password": "password123",
            "first_name": "Seller",
            "company_name": "Company"
        }
        seller_response = test_client.post("/api/auth/register-seller", json=seller_data)
        seller_id = seller_response.json()["id"]
        
        message_data = {
            "content": "Сообщение для получения",
            "recipient_id": seller_id,
            "message_type": "user_to_seller"
        }
        
        create_response = test_client.post("/api/messages/", json=message_data, headers=auth_headers)
        message_id = create_response.json()["id"]
        
        # Получаем сообщение
        response = test_client.get(f"/api/messages/{message_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == message_id
        assert data["content"] == "Сообщение для получения"
    
    @pytest.mark.external
    def test_generate_ai_response(self, test_client, auth_headers, mock_gemini_client):
        """Тест генерации ИИ ответа"""
        # Создаем продавца
        seller_data = {
            "email": "aiseller@example.com",
            "password": "password123",
            "first_name": "AI",
            "last_name": "Seller",
            "company_name": "AI Company"
        }
        seller_response = test_client.post("/api/auth/register-seller", json=seller_data)
        seller_id = seller_response.json()["id"]
        
        # Создаем сообщение
        message_data = {
            "content": "Интересует цена товара",
            "recipient_id": seller_id,
            "message_type": "user_to_seller"
        }
        
        create_response = test_client.post("/api/messages/", json=message_data, headers=auth_headers)
        message_id = create_response.json()["id"]
        
        # Генерируем ИИ ответ
        with patch('src.services.message_service.GeminiClient', return_value=mock_gemini_client):
            response = test_client.post(
                f"/api/messages/{message_id}/generate-response",
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "ai_analysis" in data


class TestConversationEndpoints:
    """Тесты эндпоинтов диалогов"""
    
    def test_get_user_conversations(self, test_client, auth_headers):
        """Тест получения диалогов пользователя"""
        response = test_client.get("/api/conversations/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
    
    def test_get_conversation_messages(self, test_client, auth_headers):
        """Тест получения сообщений диалога"""
        # Создаем продавца и сообщение для создания диалога
        seller_data = {
            "email": "convseller@example.com",
            "password": "password123",
            "first_name": "Conv",
            "company_name": "Company"
        }
        seller_response = test_client.post("/api/auth/register-seller", json=seller_data)
        seller_id = seller_response.json()["id"]
        
        message_data = {
            "content": "Первое сообщение диалога",
            "recipient_id": seller_id,
            "message_type": "user_to_seller"
        }
        
        test_client.post("/api/messages/", json=message_data, headers=auth_headers)
        
        # Получаем диалоги
        conv_response = test_client.get("/api/conversations/", headers=auth_headers)
        conversations = conv_response.json()["items"]
        
        if conversations:
            conversation_id = conversations[0]["id"]
            
            # Получаем сообщения диалога
            response = test_client.get(
                f"/api/conversations/{conversation_id}/messages",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert isinstance(data["items"], list)


class TestSellerEndpoints:
    """Тесты эндпоинтов продавцов"""
    
    def test_seller_dashboard(self, test_client):
        """Тест дашборда продавца"""
        # Регистрируем продавца
        seller_data = {
            "email": "dashboard@example.com",
            "password": "password123",
            "first_name": "Dashboard",
            "company_name": "Company"
        }
        register_response = test_client.post("/api/auth/register-seller", json=seller_data)
        assert register_response.status_code == 201
        
        # Логинимся как продавец
        login_data = {
            "email": "dashboard@example.com",
            "password": "password123"
        }
        login_response = test_client.post("/api/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        seller_headers = {"Authorization": f"Bearer {token}"}
        
        # Получаем дашборд
        response = test_client.get("/api/sellers/dashboard", headers=seller_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message_stats" in data
        assert "subscription_info" in data
        assert "ai_usage" in data
    
    def test_seller_settings(self, test_client):
        """Тест настроек продавца"""
        # Регистрируем продавца
        seller_data = {
            "email": "settings@example.com",
            "password": "password123",
            "first_name": "Settings",
            "company_name": "Company"
        }
        register_response = test_client.post("/api/auth/register-seller", json=seller_data)
        
        # Логинимся
        login_data = {
            "email": "settings@example.com",
            "password": "password123"
        }
        login_response = test_client.post("/api/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        seller_headers = {"Authorization": f"Bearer {token}"}
        
        # Получаем настройки
        response = test_client.get("/api/sellers/settings", headers=seller_headers)
        assert response.status_code == 200
        
        # Обновляем настройки
        settings_data = {
            "auto_reply_enabled": True,
            "ai_personality": "friendly",
            "response_delay_min": 2,
            "response_delay_max": 5
        }
        
        update_response = test_client.patch(
            "/api/sellers/settings",
            json=settings_data,
            headers=seller_headers
        )
        
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["auto_reply_enabled"] is True
        assert data["ai_personality"] == "friendly"
    
    def test_message_templates(self, test_client):
        """Тест шаблонов сообщений"""
        # Регистрируем продавца
        seller_data = {
            "email": "templates@example.com",
            "password": "password123",
            "first_name": "Templates",
            "company_name": "Company"
        }
        register_response = test_client.post("/api/auth/register-seller", json=seller_data)
        
        # Логинимся
        login_data = {
            "email": "templates@example.com",
            "password": "password123"
        }
        login_response = test_client.post("/api/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        seller_headers = {"Authorization": f"Bearer {token}"}
        
        # Создаем шаблон
        template_data = {
            "name": "Приветствие",
            "content": "Здравствуйте! Спасибо за интерес к {product_name}",
            "category": "greeting",
            "variables": ["product_name"]
        }
        
        create_response = test_client.post(
            "/api/sellers/templates",
            json=template_data,
            headers=seller_headers
        )
        
        assert create_response.status_code == 201
        template = create_response.json()
        assert template["name"] == "Приветствие"
        assert "product_name" in template["content"]
        
        # Получаем все шаблоны
        get_response = test_client.get("/api/sellers/templates", headers=seller_headers)
        assert get_response.status_code == 200
        templates = get_response.json()["items"]
        assert len(templates) >= 1


class TestSystemEndpoints:
    """Тесты системных эндпоинтов"""
    
    def test_health_check(self, test_client):
        """Тест проверки здоровья системы"""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "database" in data
    
    def test_api_info(self, test_client):
        """Тест информации об API"""
        response = test_client.get("/api/info")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "description" in data
    
    def test_metrics_endpoint(self, test_client):
        """Тест эндпоинта метрик"""
        response = test_client.get("/metrics")
        
        # Метрики могут быть недоступны в тестовой среде
        assert response.status_code in [200, 404]
    
    def test_docs_redirect(self, test_client):
        """Тест редиректа на документацию"""
        response = test_client.get("/docs", follow_redirects=False)
        
        # Проверяем что документация доступна
        assert response.status_code in [200, 307]


class TestErrorHandling:
    """Тесты обработки ошибок"""
    
    def test_404_not_found(self, test_client):
        """Тест обработки 404 ошибки"""
        response = test_client.get("/nonexistent/endpoint")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_422_validation_error(self, test_client):
        """Тест обработки ошибок валидации"""
        # Отправляем невалидные данные
        response = test_client.post("/api/auth/register", json={
            "email": "invalid",
            "password": "123"
        })
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
    
    def test_401_unauthorized(self, test_client):
        """Тест обработки неавторизованного доступа"""
        response = test_client.get("/api/users/me")
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_403_forbidden(self, test_client, auth_headers):
        """Тест обработки запрещенного доступа"""
        # Пытаемся получить доступ к эндпоинту продавца как пользователь
        response = test_client.get("/api/sellers/dashboard", headers=auth_headers)
        
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data


class TestRateLimit:
    """Тесты ограничения частоты запросов"""
    
    def test_rate_limit_basic(self, test_client):
        """Тест базового ограничения частоты запросов"""
        # Делаем много запросов подряд
        responses = []
        for i in range(20):
            response = test_client.get("/health")
            responses.append(response.status_code)
        
        # Большинство запросов должны быть успешными
        success_count = sum(1 for status in responses if status == 200)
        assert success_count >= 15  # Разрешаем некоторые 429 ошибки
    
    @pytest.mark.slow
    def test_rate_limit_recovery(self, test_client):
        """Тест восстановления после превышения лимита"""
        import time
        
        # Исчерпываем лимит
        for i in range(15):
            test_client.get("/health")
        
        # Ждем восстановления
        time.sleep(2)
        
        # Проверяем что лимит восстановился
        response = test_client.get("/health")
        assert response.status_code == 200


class TestCORS:
    """Тесты CORS настроек"""
    
    def test_cors_headers(self, test_client):
        """Тест CORS заголовков"""
        response = test_client.options("/api/users/me", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        
        # Проверяем CORS заголовки
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers
    
    def test_cors_preflight(self, test_client):
        """Тест preflight запросов"""
        response = test_client.options("/api/auth/login", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        })
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


# Дополнительные утилиты для тестов
from unittest.mock import patch

@pytest.fixture
def mock_external_apis():
    """Мокирование всех внешних API"""
    with patch('src.integrations.gemini.client.GeminiClient') as mock_gemini, \
         patch('src.integrations.avito.api_client.AvitoApiClient') as mock_avito:
        
        # Настраиваем моки
        mock_gemini.return_value.analyze_message.return_value = {
            "intent": "price_inquiry",
            "sentiment": "positive"
        }
        mock_gemini.return_value.generate_response.return_value = {
            "content": "Тестовый ответ ИИ"
        }
        
        mock_avito.return_value.get_messages.return_value = []
        mock_avito.return_value.send_message.return_value = {"id": "sent_123"}
        
        yield {
            "gemini": mock_gemini.return_value,
            "avito": mock_avito.return_value
        }