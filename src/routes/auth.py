"""
Роуты аутентификации для Авито ИИ-бота.

Обрабатывает регистрацию, вход в систему, выход и обновление токенов.
Поддерживает аутентификацию как для покупателей (User), так и для продавцов (Seller).
"""

from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse
import logging

from ..dependencies import get_db, get_current_user, get_current_seller
from ..schemas.auth import (
    Token, 
    UserRegister, 
    SellerRegister,
    UserResponse,
    SellerResponse,
)
from src.database.crud.users import user_crud, seller_crud
from src.database.models.users import User, Seller
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


@router.post("/register/user", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db)
) -> Any:
    """
    Регистрация нового покупателя.
    
    - **email**: Уникальный email адрес
    - **password**: Пароль (минимум 8 символов)
    - **avito_user_id**: ID пользователя в Авито
    - **first_name**: Имя пользователя
    """
    # Проверяем существование пользователя с таким email
    existing_user = user_crud.get_by_email(db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    
    # Проверяем существование пользователя с таким avito_user_id
    existing_avito_user = user_crud.get_by_avito_id(db, avito_user_id=user_data.avito_user_id)
    if existing_avito_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким Avito ID уже существует"
        )
    
    # Создаем нового пользователя
    user = user_crud.create(db, obj_in=user_data)
    return user


@router.post("/register/seller", response_model=SellerResponse, status_code=status.HTTP_201_CREATED)
async def register_seller(
    seller_data: SellerRegister,
    db: Session = Depends(get_db)
) -> Any:
    """
    Регистрация нового продавца.
    
    - **email**: Уникальный email адрес
    - **password**: Пароль (минимум 8 символов)
    - **avito_user_id**: ID продавца в Авито
    - **company_name**: Название компании
    - **subscription_plan**: Тарифный план (basic, pro, enterprise)
    """
    # Проверяем существование продавца с таким email
    existing_seller = seller_crud.get_by_email(db, email=seller_data.email)
    if existing_seller:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Продавец с таким email уже существует"
        )
    
    # Проверяем существование продавца с таким avito_user_id
    existing_avito_seller = seller_crud.get_by_avito_id(db, avito_user_id=seller_data.avito_user_id)
    if existing_avito_seller:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Продавец с таким Avito ID уже существует"
        )
    
    # Создаем нового продавца
    seller = seller_crud.create(db, obj_in=seller_data)
    return seller


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """
    Вход в систему для пользователей и продавцов.
    
    Возвращает JWT токен для аутентификации.
    Автоматически определяет тип пользователя (покупатель или продавец).
    """
    # Сначала пытаемся найти среди пользователей
    user = user_crud.authenticate(db, email=form_data.username, password=form_data.password)
    user_type = "user"
    
    # Если не найден среди пользователей, ищем среди продавцов
    if not user:
        user = seller_crud.authenticate(db, email=form_data.username, password=form_data.password)
        user_type = "seller"
    
    # Если не найден вообще
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Проверяем активность пользователя
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Аккаунт неактивен"
        )
    
    # Создаем JWT токен
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = user_crud.create_access_token(
        data={"sub": str(user.id), "type": user_type},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_type": user_type,
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: User | Seller = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Обновление JWT токена.
    
    Позволяет получить новый токен без повторного ввода пароля.
    """
    # Определяем тип пользователя
    user_type = "seller" if isinstance(current_user, Seller) else "user"
    
    # Создаем новый токен
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = user_crud.create_access_token(
        data={"sub": str(current_user.id), "type": user_type},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_type": user_type,
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.get("/me/user", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Получение информации о текущем покупателе.
    
    Возвращает полную информацию о профиле пользователя.
    """
    return current_user


@router.get("/me/seller", response_model=SellerResponse)
async def get_current_seller_info(
    current_seller: Seller = Depends(get_current_seller)
) -> Any:
    """
    Получение информации о текущем продавце.
    
    Возвращает полную информацию о профиле продавца.
    """
    return current_seller


@router.post("/logout")
async def logout() -> Any:
    """
    Выход из системы.
    
    В текущей реализации JWT токены не могут быть отозваны на сервере.
    Клиент должен удалить токен локально.
    """
    return {"message": "Успешный выход из системы"}


@router.post("/verify-email")
async def verify_email(
    token: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    Подтверждение email адреса.
    
    Принимает токен подтверждения и активирует аккаунт пользователя.
    """
    # TODO: Реализовать логику подтверждения email
    # Для MVP версии все аккаунты считаются подтвержденными
    return {"message": "Email успешно подтвержден"}


@router.post("/reset-password")
async def reset_password(
    email: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    Сброс пароля.
    
    Отправляет email с инструкциями по сбросу пароля.
    """
    # TODO: Реализовать логику сброса пароля
    # Для MVP версии возвращаем заглушку
    return {"message": "Инструкции по сбросу пароля отправлены на email"}


@router.get("/avito/callback")
async def avito_oauth_callback(
    code: str = Query(..., description="Authorization code from Avito"),
    state: str = Query(None, description="State parameter for security")
):
    """
    Callback endpoint для OAuth авторизации Avito
    """
    try:
        logger.info(f"Получен Avito OAuth callback: code={code[:10]}..., state={state}")
        
        success_html = f"""
        <html>
            <head>
                <title>Avito AI Responder - Успешная авторизация</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .success {{ color: green; font-size: 24px; margin: 20px 0; }}
                    .info {{ color: #666; font-size: 16px; margin: 10px 0; }}
                    .code {{ background: #f0f0f0; padding: 10px; border-radius: 5px; font-family: monospace; }}
                </style>
            </head>
            <body>
                <h1>🎉 Авторизация Avito успешна!</h1>
                <div class="success">✅ Подключение к Avito API установлено</div>
                <div class="info">Получен код авторизации:</div>
                <div class="code">{code[:20]}...</div>
                <div class="info">State: {state or 'не указан'}</div>
                <div class="info">
                    <p>Теперь ваш автоответчик может получать доступ к сообщениям Avito!</p>
                    <p>Вы можете закрыть это окно.</p>
                </div>
            </body>
        </html>
        """
        
        return HTMLResponse(content=success_html, status_code=200)
        
    except Exception as e:
        error_html = f"""
        <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>❌ Ошибка авторизации Avito</h1>
                <p>Ошибка: {str(e)}</p>
            </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=400)

@router.get("/avito/status")
async def avito_auth_status():
    """Проверка статуса авторизации Avito"""
    return {
        "status": "ready",
        "callback_url": "https://avito-joq9.onrender.com/auth/avito/callback",
        "message": "Готов к получению OAuth callback от Avito"
    }