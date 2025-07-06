"""
Роуты для работы с сообщениями и диалогами Авито ИИ-бота.

Обрабатывает отправку/получение сообщений, управление диалогами,
ИИ-анализ сообщений и автоматические ответы.
"""

from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_user, get_current_seller
from ..schemas.messages import (
    MessageResponse,
    MessageCreate,
    MessageUpdate,
    ConversationResponse,
    ConversationCreate,
    ConversationUpdate,
    MessageTemplateResponse,
    MessageTemplateCreate,
    MessageTemplateUpdate,
    AutoReplyRequest,
    AIAnalysisResponse,
)
from src.database.crud import message_crud, conversation_crud, template_crud
from src.database.models.users import User, Seller
from src.core.ai_consultant import AIConsultant
from src.core.message_handler import MessageHandler
from src.core.response_generator import ResponseGenerator

router = APIRouter()


# ============================================================================
# РОУТЫ ДЛЯ СООБЩЕНИЙ
# ============================================================================

@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    message_data: MessageCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User | Seller = Depends(get_current_user)
) -> Any:
    """
    Создать новое сообщение.
    
    Автоматически запускает ИИ-анализ сообщения в фоновом режиме.
    """
    # Создаем сообщение
    message = message_crud.create(db, obj_in=message_data)
    
    # Добавляем задачу ИИ-анализа в фоновый режим
    background_tasks.add_task(
        analyze_message_with_ai,
        message_id=message.id,
        db_session=db
    )
    
    return message


@router.get("/", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: Optional[UUID] = Query(None, description="Фильтр по диалогу"),
    sender_id: Optional[UUID] = Query(None, description="Фильтр по отправителю"),
    recipient_id: Optional[UUID] = Query(None, description="Фильтр по получателю"),
    message_type: Optional[str] = Query(None, description="Тип сообщения"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User | Seller = Depends(get_current_user)
) -> Any:
    """
    Получить список сообщений с фильтрацией.
    
    Поддерживает фильтрацию по диалогу, участникам и типу сообщения.
    """
    messages = message_crud.get_filtered(
        db,
        conversation_id=conversation_id,
        sender_id=sender_id,
        recipient_id=recipient_id,
        message_type=message_type,
        skip=skip,
        limit=limit
    )
    return messages


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: UUID,
    db: Session = Depends(get_db),
    current_user: User | Seller = Depends(get_current_user)
) -> Any:
    """
    Получить конкретное сообщение по ID.
    """
    message = message_crud.get(db, id=message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сообщение не найдено"
        )
    
    # Проверяем доступ к сообщению
    if not _has_message_access(current_user, message):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому сообщению"
        )
    
    return message


@router.put("/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: UUID,
    message_update: MessageUpdate,
    db: Session = Depends(get_db),
    current_user: User | Seller = Depends(get_current_user)
) -> Any:
    """
    Обновить сообщение.
    
    Доступно только отправителю сообщения.
    """
    message = message_crud.get(db, id=message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сообщение не найдено"
        )
    
    if message.sender_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Можно редактировать только свои сообщения"
        )
    
    message = message_crud.update(db, db_obj=message, obj_in=message_update)
    return message


@router.delete("/{message_id}")
async def delete_message(
    message_id: UUID,
    db: Session = Depends(get_db),
    current_user: User | Seller = Depends(get_current_user)
) -> Any:
    """
    Удалить сообщение (мягкое удаление).
    """
    message = message_crud.get(db, id=message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сообщение не найдено"
        )
    
    if message.sender_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Можно удалять только свои сообщения"
        )
    
    message_crud.remove(db, id=message_id)
    return {"message": "Сообщение успешно удалено"}


# ============================================================================
# РОУТЫ ДЛЯ ДИАЛОГОВ
# ============================================================================

@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User | Seller = Depends(get_current_user)
) -> Any:
    """
    Создать новый диалог.
    """
    conversation = conversation_crud.create(db, obj_in=conversation_data)
    return conversation


@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    user_id: Optional[UUID] = Query(None, description="Фильтр по участнику"),
    seller_id: Optional[UUID] = Query(None, description="Фильтр по продавцу"),
    status: Optional[str] = Query(None, description="Статус диалога"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User | Seller = Depends(get_current_user)
) -> Any:
    """
    Получить список диалогов пользователя.
    """
    conversations = conversation_crud.get_user_conversations(
        db,
        user_id=current_user.id,
        status=status,
        skip=skip,
        limit=limit
    )
    return conversations


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User | Seller = Depends(get_current_user)
) -> Any:
    """
    Получить конкретный диалог со всеми сообщениями.
    """
    conversation = conversation_crud.get_with_messages(db, id=conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Диалог не найден"
        )
    
    # Проверяем доступ к диалогу
    if not _has_conversation_access(current_user, conversation):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому диалогу"
        )
    
    return conversation


@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    conversation_update: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User | Seller = Depends(get_current_user)
) -> Any:
    """
    Обновить диалог (статус, метаданные).
    """
    conversation = conversation_crud.get(db, id=conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Диалог не найден"
        )
    
    if not _has_conversation_access(current_user, conversation):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому диалогу"
        )
    
    conversation = conversation_crud.update(db, db_obj=conversation, obj_in=conversation_update)
    return conversation


# ============================================================================
# РОУТЫ ДЛЯ АВТООТВЕТЧИКА И ИИ
# ============================================================================

@router.post("/auto-reply", response_model=MessageResponse)
async def generate_auto_reply(
    request: AutoReplyRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
) -> Any:
    """
    Сгенерировать автоматический ответ на сообщение с помощью ИИ.
    
    Доступно только для продавцов с активированным ИИ-консультантом.
    """
    # Проверяем настройки продавца
    settings = seller_crud.get_settings(db, seller_id=current_seller.id)
    if not settings or not settings.ai_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ИИ-консультант отключен в настройках"
        )
    
    # Получаем исходное сообщение
    original_message = message_crud.get(db, id=request.message_id)
    if not original_message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Исходное сообщение не найдено"
        )
    
    # Генерируем ответ с помощью ИИ
    response_generator = ResponseGenerator()
    reply_content = await response_generator.generate_response(
        message=original_message.content,
        context=request.context,
        seller_settings=settings
    )
    
    # Создаем сообщение-ответ
    reply_data = MessageCreate(
        conversation_id=original_message.conversation_id,
        sender_id=current_seller.id,
        recipient_id=original_message.sender_id,
        content=reply_content,
        message_type="automated_reply",
        is_ai_generated=True
    )
    
    reply = message_crud.create(db, obj_in=reply_data)
    
    # Запускаем анализ сгенерированного ответа в фоне
    background_tasks.add_task(
        analyze_message_with_ai,
        message_id=reply.id,
        db_session=db
    )
    
    return reply


@router.post("/analyze/{message_id}", response_model=AIAnalysisResponse)
async def analyze_message(
    message_id: UUID,
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
) -> Any:
    """
    Запустить ИИ-анализ сообщения.
    
    Анализирует тональность, интент, ключевые слова и рекомендации.
    """
    message = message_crud.get(db, id=message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сообщение не найдено"
        )
    
    # Запускаем ИИ-анализ
    ai_consultant = AIConsultant()
    analysis = await ai_consultant.analyze_message(
        content=message.content,
        context=message.metadata
    )
    
    # Обновляем сообщение с результатами анализа
    message_crud.update_ai_analysis(db, message_id=message_id, analysis=analysis)
    
    return analysis


# ============================================================================
# РОУТЫ ДЛЯ ШАБЛОНОВ СООБЩЕНИЙ
# ============================================================================

@router.post("/templates", response_model=MessageTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_message_template(
    template_data: MessageTemplateCreate,
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
) -> Any:
    """
    Создать новый шаблон сообщения.
    """
    template_data.seller_id = current_seller.id
    template = template_crud.create(db, obj_in=template_data)
    return template


@router.get("/templates", response_model=List[MessageTemplateResponse])
async def get_message_templates(
    category: Optional[str] = Query(None, description="Категория шаблона"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
) -> Any:
    """
    Получить шаблоны сообщений текущего продавца.
    """
    templates = template_crud.get_seller_templates(
        db,
        seller_id=current_seller.id,
        category=category,
        skip=skip,
        limit=limit
    )
    return templates


@router.get("/templates/{template_id}", response_model=MessageTemplateResponse)
async def get_message_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
) -> Any:
    """
    Получить конкретный шаблон сообщения.
    """
    template = template_crud.get(db, id=template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Шаблон не найден"
        )
    
    if template.seller_id != current_seller.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому шаблону"
        )
    
    return template


@router.put("/templates/{template_id}", response_model=MessageTemplateResponse)
async def update_message_template(
    template_id: UUID,
    template_update: MessageTemplateUpdate,
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
) -> Any:
    """
    Обновить шаблон сообщения.
    """
    template = template_crud.get(db, id=template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Шаблон не найден"
        )
    
    if template.seller_id != current_seller.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Можно редактировать только свои шаблоны"
        )
    
    template = template_crud.update(db, db_obj=template, obj_in=template_update)
    return template


@router.delete("/templates/{template_id}")
async def delete_message_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
) -> Any:
    """
    Удалить шаблон сообщения.
    """
    template = template_crud.get(db, id=template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Шаблон не найден"
        )
    
    if template.seller_id != current_seller.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Можно удалять только свои шаблоны"
        )
    
    template_crud.remove(db, id=template_id)
    return {"message": "Шаблон успешно удален"}


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def _has_message_access(user: User | Seller, message) -> bool:
    """Проверить доступ пользователя к сообщению."""
    return (
        message.sender_id == user.id or 
        message.recipient_id == user.id
    )


def _has_conversation_access(user: User | Seller, conversation) -> bool:
    """Проверить доступ пользователя к диалогу."""
    return (
        conversation.user_id == user.id or 
        conversation.seller_id == user.id
    )


async def analyze_message_with_ai(message_id: UUID, db_session: Session) -> None:
    """Фоновая задача для ИИ-анализа сообщения."""
    try:
        message = message_crud.get(db_session, id=message_id)
        if message:
            ai_consultant = AIConsultant()
            analysis = await ai_consultant.analyze_message(
                content=message.content,
                context=message.metadata
            )
            message_crud.update_ai_analysis(db_session, message_id=message_id, analysis=analysis)
    except Exception as e:
        # Логируем ошибку, но не прерываем выполнение
        print(f"Ошибка ИИ-анализа сообщения {message_id}: {e}")