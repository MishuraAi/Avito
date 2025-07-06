"""
🧪 Unit тесты для моделей базы данных

Тестируем:
- Создание моделей
- Валидацию полей
- Отношения между моделями
- Методы моделей
"""

import pytest
from datetime import datetime, timezone
from uuid import UUID

from src.database.models.users import User, Seller, UserProfile, SellerSettings
from src.database.models.messages import Message, Conversation, MessageTemplate
from src.utils.helpers import hash_password


class TestUserModel:
    """Тесты модели User"""
    
    def test_create_user(self, test_db_session):
        """Тест создания пользователя"""
        user = User(
            email="test@example.com",
            password_hash=hash_password("password123"),
            first_name="John",
            last_name="Doe",
            phone="+7900123456"
        )
        
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)
        
        assert user.id is not None
        assert isinstance(user.id, UUID)
        assert user.email == "test@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.phone == "+7900123456"
        assert user.is_active is True
        assert user.created_at is not None
        assert user.updated_at is not None
    
    def test_user_unique_email(self, test_db_session):
        """Тест уникальности email"""
        # Создаем первого пользователя
        user1 = User(
            email="unique@example.com",
            password_hash=hash_password("password123"),
            first_name="First"
        )
        test_db_session.add(user1)
        test_db_session.commit()
        
        # Пытаемся создать второго с тем же email
        user2 = User(
            email="unique@example.com",
            password_hash=hash_password("password456"),
            first_name="Second"
        )
        test_db_session.add(user2)
        
        # Должна возникнуть ошибка
        with pytest.raises(Exception):
            test_db_session.commit()
    
    def test_user_timestamps(self, test_db_session):
        """Тест автоматических временных меток"""
        user = User(
            email="timestamps@example.com",
            password_hash=hash_password("password123"),
            first_name="Test"
        )
        
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)
        
        # Проверяем что временные метки установлены
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.created_at == user.updated_at
        
        # Обновляем пользователя
        original_created = user.created_at
        user.first_name = "Updated"
        test_db_session.commit()
        test_db_session.refresh(user)
        
        # created_at не должен измениться, updated_at должен
        assert user.created_at == original_created
        assert user.updated_at > original_created


class TestSellerModel:
    """Тесты модели Seller"""
    
    def test_create_seller(self, test_db_session):
        """Тест создания продавца"""
        seller = Seller(
            email="seller@example.com",
            password_hash=hash_password("password123"),
            first_name="Jane",
            last_name="Smith",
            company_name="Test Company",
            subscription_type="premium"
        )
        
        test_db_session.add(seller)
        test_db_session.commit()
        test_db_session.refresh(seller)
        
        assert seller.id is not None
        assert seller.company_name == "Test Company"
        assert seller.subscription_type == "premium"
        assert seller.daily_message_limit == 1000  # Default для premium
        assert seller.api_requests_used == 0
        assert seller.ai_enabled is True
    
    def test_seller_subscription_limits(self, test_db_session):
        """Тест лимитов по типам подписки"""
        # Free подписка
        free_seller = Seller(
            email="free@example.com",
            password_hash=hash_password("password123"),
            first_name="Free",
            subscription_type="free"
        )
        
        test_db_session.add(free_seller)
        test_db_session.commit()
        test_db_session.refresh(free_seller)
        
        assert free_seller.daily_message_limit == 50  # Default для free
        
        # Enterprise подписка
        enterprise_seller = Seller(
            email="enterprise@example.com",
            password_hash=hash_password("password123"),
            first_name="Enterprise",
            subscription_type="enterprise"
        )
        
        test_db_session.add(enterprise_seller)
        test_db_session.commit()
        test_db_session.refresh(enterprise_seller)
        
        assert enterprise_seller.daily_message_limit == 10000  # Default для enterprise


class TestMessageModel:
    """Тесты модели Message"""
    
    def test_create_message(self, test_db_session, create_test_user, create_test_seller):
        """Тест создания сообщения"""
        user = create_test_user()
        seller = create_test_seller()
        
        message = Message(
            content="Тестовое сообщение",
            sender_id=user.id,
            recipient_id=seller.id,
            message_type="user_to_seller",
            platform="avito",
            external_message_id="ext_123"
        )
        
        test_db_session.add(message)
        test_db_session.commit()
        test_db_session.refresh(message)
        
        assert message.id is not None
        assert message.content == "Тестовое сообщение"
        assert message.sender_id == user.id
        assert message.recipient_id == seller.id
        assert message.message_type == "user_to_seller"
        assert message.status == "sent"  # Default
        assert message.platform == "avito"
        assert message.is_ai_processed is False
        assert message.created_at is not None
    
    def test_message_ai_analysis(self, test_db_session, create_test_user, create_test_seller):
        """Тест ИИ анализа сообщения"""
        user = create_test_user()
        seller = create_test_seller()
        
        message = Message(
            content="Интересует ваш товар, есть скидки?",
            sender_id=user.id,
            recipient_id=seller.id,
            message_type="user_to_seller",
            ai_analysis={
                "intent": "price_inquiry",
                "sentiment": "positive",
                "urgency": "medium",
                "suggested_response": "Да, могу предложить скидку 10%"
            },
            ai_confidence=0.85,
            is_ai_processed=True
        )
        
        test_db_session.add(message)
        test_db_session.commit()
        test_db_session.refresh(message)
        
        assert message.is_ai_processed is True
        assert message.ai_confidence == 0.85
        assert message.ai_analysis["intent"] == "price_inquiry"
        assert message.ai_analysis["sentiment"] == "positive"


class TestConversationModel:
    """Тесты модели Conversation"""
    
    def test_create_conversation(self, test_db_session, create_test_user, create_test_seller):
        """Тест создания диалога"""
        user = create_test_user()
        seller = create_test_seller()
        
        conversation = Conversation(
            user_id=user.id,
            seller_id=seller.id,
            platform="avito",
            external_conversation_id="conv_123",
            status="active"
        )
        
        test_db_session.add(conversation)
        test_db_session.commit()
        test_db_session.refresh(conversation)
        
        assert conversation.id is not None
        assert conversation.user_id == user.id
        assert conversation.seller_id == seller.id
        assert conversation.platform == "avito"
        assert conversation.status == "active"
        assert conversation.message_count == 0
        assert conversation.last_activity_at is not None
    
    def test_conversation_messages_relationship(self, test_db_session, create_test_user, create_test_seller):
        """Тест связи диалога с сообщениями"""
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
        
        # Создаем сообщения в диалоге
        message1 = Message(
            content="Первое сообщение",
            sender_id=user.id,
            recipient_id=seller.id,
            conversation_id=conversation.id,
            message_type="user_to_seller"
        )
        
        message2 = Message(
            content="Ответ продавца",
            sender_id=seller.id,
            recipient_id=user.id,
            conversation_id=conversation.id,
            message_type="seller_to_user"
        )
        
        test_db_session.add_all([message1, message2])
        test_db_session.commit()
        
        # Обновляем счетчик сообщений
        conversation.message_count = 2
        test_db_session.commit()
        test_db_session.refresh(conversation)
        
        assert conversation.message_count == 2


class TestMessageTemplateModel:
    """Тесты модели MessageTemplate"""
    
    def test_create_template(self, test_db_session, create_test_seller):
        """Тест создания шаблона сообщения"""
        seller = create_test_seller()
        
        template = MessageTemplate(
            seller_id=seller.id,
            name="Приветствие",
            content="Здравствуйте! Спасибо за интерес к нашему товару. {product_name}",
            category="greeting",
            variables=["product_name"],
            is_active=True
        )
        
        test_db_session.add(template)
        test_db_session.commit()
        test_db_session.refresh(template)
        
        assert template.id is not None
        assert template.seller_id == seller.id
        assert template.name == "Приветствие"
        assert "product_name" in template.content
        assert template.category == "greeting"
        assert template.variables == ["product_name"]
        assert template.usage_count == 0
        assert template.is_active is True
    
    def test_template_usage_tracking(self, test_db_session, create_test_seller):
        """Тест отслеживания использования шаблона"""
        seller = create_test_seller()
        
        template = MessageTemplate(
            seller_id=seller.id,
            name="Тест шаблон",
            content="Тестовое содержимое",
            usage_count=5,
            success_rate=0.8
        )
        
        test_db_session.add(template)
        test_db_session.commit()
        test_db_session.refresh(template)
        
        assert template.usage_count == 5
        assert template.success_rate == 0.8
        assert template.last_used_at is None
        
        # Обновляем время последнего использования
        template.last_used_at = datetime.now(timezone.utc)
        template.usage_count += 1
        test_db_session.commit()
        test_db_session.refresh(template)
        
        assert template.usage_count == 6
        assert template.last_used_at is not None


class TestModelRelationships:
    """Тесты связей между моделями"""
    
    def test_user_profile_relationship(self, test_db_session, create_test_user):
        """Тест связи пользователя с профилем"""
        user = create_test_user()
        
        profile = UserProfile(
            user_id=user.id,
            preferred_communication_style="formal",
            interests=["electronics", "cars"],
            purchase_history_summary="Активный покупатель техники"
        )
        
        test_db_session.add(profile)
        test_db_session.commit()
        test_db_session.refresh(profile)
        
        assert profile.user_id == user.id
        assert profile.preferred_communication_style == "formal"
        assert "electronics" in profile.interests
    
    def test_seller_settings_relationship(self, test_db_session, create_test_seller):
        """Тест связи продавца с настройками"""
        seller = create_test_seller()
        
        settings = SellerSettings(
            seller_id=seller.id,
            auto_reply_enabled=True,
            ai_personality="friendly",
            response_delay_min=1,
            response_delay_max=5,
            working_hours_start="09:00",
            working_hours_end="18:00"
        )
        
        test_db_session.add(settings)
        test_db_session.commit()
        test_db_session.refresh(settings)
        
        assert settings.seller_id == seller.id
        assert settings.auto_reply_enabled is True
        assert settings.ai_personality == "friendly"
        assert settings.working_hours_start == "09:00"