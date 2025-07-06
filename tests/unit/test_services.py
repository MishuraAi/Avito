"""
🧪 Unit тесты для сервисного слоя

Тестируем:
- AuthService - аутентификация и авторизация
- UserService - управление пользователями
- MessageService - обработка сообщений
- AvitoService - интеграция с Avito API
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from src.services.auth_service import AuthService
from src.services.user_service import UserService
from src.services.message_service import MessageService
from src.services.avito_service import AvitoService
from src.utils.exceptions import (
    AuthenticationError, ValidationError, NotFoundError,
    ExternalServiceError, BusinessLogicError
)


class TestAuthService:
    """Тесты сервиса аутентификации"""
    
    def test_hash_password(self):
        """Тест хеширования пароля"""
        password = "testpassword123"
        hashed = AuthService.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hash длиннее 50 символов
        assert hashed.startswith("$2b$")  # bcrypt префикс
    
    def test_verify_password(self):
        """Тест проверки пароля"""
        password = "testpassword123"
        hashed = AuthService.hash_password(password)
        
        # Правильный пароль
        assert AuthService.verify_password(password, hashed) is True
        
        # Неправильный пароль
        assert AuthService.verify_password("wrongpassword", hashed) is False
    
    def test_create_access_token(self):
        """Тест создания JWT токена"""
        user_id = "test-user-id"
        user_type = "user"
        
        token = AuthService.create_access_token(user_id, user_type)
        
        assert isinstance(token, str)
        assert len(token) > 100  # JWT токен достаточно длинный
        assert "." in token  # JWT содержит точки
    
    def test_verify_token_valid(self):
        """Тест проверки валидного токена"""
        user_id = "test-user-id"
        user_type = "seller"
        
        token = AuthService.create_access_token(user_id, user_type)
        payload = AuthService.verify_token(token)
        
        assert payload["sub"] == user_id
        assert payload["user_type"] == user_type
        assert "exp" in payload
    
    def test_verify_token_invalid(self):
        """Тест проверки невалидного токена"""
        invalid_token = "invalid.jwt.token"
        
        with pytest.raises(AuthenticationError):
            AuthService.verify_token(invalid_token)
    
    def test_verify_token_expired(self):
        """Тест проверки истекшего токена"""
        # Создаем токен с истекшим временем
        with patch('src.services.auth_service.datetime') as mock_datetime:
            past_time = datetime.utcnow() - timedelta(hours=2)
            mock_datetime.utcnow.return_value = past_time
            
            token = AuthService.create_access_token("user-id", "user")
        
        # Проверяем что токен истек
        with pytest.raises(AuthenticationError) as exc_info:
            AuthService.verify_token(token)
        
        assert "expired" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, test_db_session, create_test_user):
        """Тест успешной аутентификации пользователя"""
        # Создаем тестового пользователя
        password = "testpassword123"
        user = create_test_user(
            email="auth@example.com",
            password_hash=AuthService.hash_password(password)
        )
        
        # Аутентифицируем
        result_user, user_type = await AuthService.authenticate_user(
            test_db_session, "auth@example.com", password
        )
        
        assert result_user.id == user.id
        assert user_type == "user"
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, test_db_session, create_test_user):
        """Тест аутентификации с неправильным паролем"""
        user = create_test_user(
            email="wrong@example.com",
            password_hash=AuthService.hash_password("correctpassword")
        )
        
        with pytest.raises(AuthenticationError):
            await AuthService.authenticate_user(
                test_db_session, "wrong@example.com", "wrongpassword"
            )
    
    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user(self, test_db_session):
        """Тест аутентификации несуществующего пользователя"""
        with pytest.raises(AuthenticationError):
            await AuthService.authenticate_user(
                test_db_session, "nonexistent@example.com", "password"
            )


class TestUserService:
    """Тесты сервиса пользователей"""
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, test_db_session):
        """Тест успешного создания пользователя"""
        user_data = {
            "email": "newuser@example.com",
            "password": "securepassword123",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+7900123456"
        }
        
        user = await UserService.create_user(test_db_session, user_data)
        
        assert user.email == "newuser@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.phone == "+7900123456"
        assert user.is_active is True
        assert user.password_hash != "securepassword123"  # Пароль должен быть захеширован
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, test_db_session, create_test_user):
        """Тест создания пользователя с существующим email"""
        # Создаем первого пользователя
        create_test_user(email="duplicate@example.com")
        
        # Пытаемся создать второго с тем же email
        user_data = {
            "email": "duplicate@example.com",
            "password": "password123",
            "first_name": "Second"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            await UserService.create_user(test_db_session, user_data)
        
        assert "already exists" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, test_db_session, create_test_user):
        """Тест получения пользователя по ID"""
        user = create_test_user()
        
        found_user = await UserService.get_user_by_id(test_db_session, user.id)
        
        assert found_user is not None
        assert found_user.id == user.id
        assert found_user.email == user.email
    
    @pytest.mark.asyncio
    async def test_get_user_by_nonexistent_id(self, test_db_session):
        """Тест получения несуществующего пользователя"""
        from uuid import uuid4
        
        with pytest.raises(NotFoundError):
            await UserService.get_user_by_id(test_db_session, uuid4())
    
    @pytest.mark.asyncio
    async def test_update_user_profile(self, test_db_session, create_test_user):
        """Тест обновления профиля пользователя"""
        user = create_test_user()
        
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "phone": "+7900999888"
        }
        
        updated_user = await UserService.update_user_profile(
            test_db_session, user.id, update_data
        )
        
        assert updated_user.first_name == "Updated"
        assert updated_user.last_name == "Name"
        assert updated_user.phone == "+7900999888"


class TestMessageService:
    """Тесты сервиса сообщений"""
    
    @pytest.mark.asyncio
    async def test_create_message_basic(self, test_db_session, create_test_user, create_test_seller):
        """Тест создания базового сообщения"""
        user = create_test_user()
        seller = create_test_seller()
        
        message_data = {
            "content": "Тестовое сообщение",
            "sender_id": str(user.id),
            "recipient_id": str(seller.id),
            "message_type": "user_to_seller",
            "platform": "avito"
        }
        
        message = await MessageService.create_message(test_db_session, message_data)
        
        assert message.content == "Тестовое сообщение"
        assert message.sender_id == user.id
        assert message.recipient_id == seller.id
        assert message.message_type == "user_to_seller"
        assert message.platform == "avito"
        assert message.status == "sent"
    
    @pytest.mark.asyncio
    async def test_create_message_with_ai_analysis(self, test_db_session, create_test_user, create_test_seller, mock_gemini_client):
        """Тест создания сообщения с ИИ анализом"""
        user = create_test_user()
        seller = create_test_seller()
        
        message_data = {
            "content": "Интересует цена товара",
            "sender_id": str(user.id),
            "recipient_id": str(seller.id),
            "message_type": "user_to_seller",
            "enable_ai_analysis": True
        }
        
        with patch('src.services.message_service.GeminiClient', return_value=mock_gemini_client):
            message = await MessageService.create_message(test_db_session, message_data)
        
        assert message.is_ai_processed is True
        assert message.ai_analysis is not None
        mock_gemini_client.analyze_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_ai_response(self, test_db_session, create_test_user, create_test_seller, mock_gemini_client):
        """Тест генерации ИИ ответа"""
        user = create_test_user()
        seller = create_test_seller()
        
        # Создаем входящее сообщение
        message_data = {
            "content": "Здравствуйте! Есть ли скидки?",
            "sender_id": str(user.id),
            "recipient_id": str(seller.id),
            "message_type": "user_to_seller"
        }
        
        message = await MessageService.create_message(test_db_session, message_data)
        
        # Генерируем ответ
        with patch('src.services.message_service.GeminiClient', return_value=mock_gemini_client):
            response = await MessageService.generate_ai_response(
                test_db_session, message.id, seller.id
            )
        
        assert response is not None
        assert "content" in response
        mock_gemini_client.generate_response.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_conversation_messages(self, test_db_session, create_test_user, create_test_seller):
        """Тест получения сообщений диалога"""
        from src.database.models.messages import Conversation
        
        user = create_test_user()
        seller = create_test_seller()
        
        # Создаем диалог
        conversation = Conversation(
            user_id=user.id,
            seller_id=seller.id,
            platform="avito"
        )
        test_db_session.add(conversation)
        test_db_session.commit()
        test_db_session.refresh(conversation)
        
        # Создаем несколько сообщений
        for i in range(3):
            message_data = {
                "content": f"Сообщение {i+1}",
                "sender_id": str(user.id),
                "recipient_id": str(seller.id),
                "conversation_id": str(conversation.id),
                "message_type": "user_to_seller"
            }
            await MessageService.create_message(test_db_session, message_data)
        
        # Получаем сообщения
        messages = await MessageService.get_conversation_messages(
            test_db_session, conversation.id
        )
        
        assert len(messages) == 3
        assert messages[0].content == "Сообщение 1"
        assert all(msg.conversation_id == conversation.id for msg in messages)


class TestAvitoService:
    """Тесты сервиса интеграции с Avito"""
    
    @pytest.mark.asyncio
    async def test_sync_seller_messages(self, test_db_session, create_test_seller, mock_avito_client):
        """Тест синхронизации сообщений продавца"""
        seller = create_test_seller(avito_user_id="avito_123")
        
        with patch('src.services.avito_service.AvitoApiClient', return_value=mock_avito_client):
            result = await AvitoService.sync_seller_messages(test_db_session, seller.id)
        
        assert result is not None
        assert "synced_count" in result
        mock_avito_client.get_messages.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_message_to_avito(self, test_db_session, create_test_seller, mock_avito_client):
        """Тест отправки сообщения в Avito"""
        seller = create_test_seller(avito_user_id="avito_123")
        
        message_data = {
            "content": "Тестовый ответ",
            "recipient_id": "avito_user_456",
            "ad_id": "avito_ad_789"
        }
        
        with patch('src.services.avito_service.AvitoApiClient', return_value=mock_avito_client):
            result = await AvitoService.send_message(
                test_db_session, seller.id, message_data
            )
        
        assert result is not None
        assert "id" in result
        mock_avito_client.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_avito_credentials(self, test_db_session, create_test_seller, mock_avito_client):
        """Тест валидации учетных данных Avito"""
        seller = create_test_seller(
            avito_user_id="avito_123",
            avito_client_id="client_123",
            avito_client_secret="secret_123"
        )
        
        mock_avito_client.validate_credentials.return_value = True
        
        with patch('src.services.avito_service.AvitoApiClient', return_value=mock_avito_client):
            is_valid = await AvitoService.validate_credentials(test_db_session, seller.id)
        
        assert is_valid is True
        mock_avito_client.validate_credentials.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_api_error(self, test_db_session, create_test_seller, mock_avito_client):
        """Тест обработки ошибок Avito API"""
        seller = create_test_seller()
        
        # Настраиваем мок для выброса ошибки
        mock_avito_client.get_messages.side_effect = Exception("API Error")
        
        with patch('src.services.avito_service.AvitoApiClient', return_value=mock_avito_client):
            with pytest.raises(ExternalServiceError) as exc_info:
                await AvitoService.sync_seller_messages(test_db_session, seller.id)
        
        assert "avito" in str(exc_info.value).lower()


class TestServiceIntegration:
    """Тесты интеграции между сервисами"""
    
    @pytest.mark.asyncio
    async def test_full_message_flow(self, test_db_session, create_test_user, create_test_seller, 
                                   mock_gemini_client, mock_avito_client):
        """Тест полного потока обработки сообщения"""
        user = create_test_user()
        seller = create_test_seller(avito_user_id="avito_123")
        
        # 1. Получаем сообщение от пользователя
        message_data = {
            "content": "Интересует ваш товар",
            "sender_id": str(user.id),
            "recipient_id": str(seller.id),
            "message_type": "user_to_seller",
            "enable_ai_analysis": True
        }
        
        with patch('src.services.message_service.GeminiClient', return_value=mock_gemini_client):
            message = await MessageService.create_message(test_db_session, message_data)
        
        # 2. Генерируем ИИ ответ
        with patch('src.services.message_service.GeminiClient', return_value=mock_gemini_client):
            ai_response = await MessageService.generate_ai_response(
                test_db_session, message.id, seller.id
            )
        
        # 3. Отправляем ответ через Avito
        with patch('src.services.avito_service.AvitoApiClient', return_value=mock_avito_client):
            send_result = await AvitoService.send_message(
                test_db_session, seller.id, {
                    "content": ai_response["content"],
                    "recipient_id": str(user.id)
                }
            )
        
        # Проверяем что все этапы выполнились
        assert message.is_ai_processed is True
        assert ai_response is not None
        assert send_result is not None
        
        # Проверяем что все сервисы были вызваны
        mock_gemini_client.analyze_message.assert_called()
        mock_gemini_client.generate_response.assert_called()
        mock_avito_client.send_message.assert_called()