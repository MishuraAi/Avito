"""
Роуты управления пользователями для Авито ИИ-бота.

Обрабатывает CRUD операции для покупателей и продавцов,
управление профилями и настройками.
"""

from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_user, get_current_seller
from ..schemas.users import (
    UserResponse,
    UserUpdate,
    UserProfileResponse,
    UserProfileUpdate,
    SellerResponse,
    SellerUpdate,
    SellerSettingsResponse,
    SellerSettingsUpdate,
)
from src.database.crud.users import user_crud, seller_crud
from src.database.models.users import User, Seller

router = APIRouter()


# ============================================================================
# РОУТЫ ДЛЯ ПОКУПАТЕЛЕЙ (USERS)
# ============================================================================

@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(100, ge=1, le=1000, description="Максимальное количество записей"),
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
) -> Any:
    """
    Получить список всех покупателей.
    
    Доступно только для продавцов.
    Поддерживает пагинацию.
    """
    users = user_crud.get_multi(db, skip=skip, limit=limit)
    return users


@router.get("/search", response_model=List[UserResponse])
async def search_users(
    q: str = Query(..., min_length=1, description="Поисковый запрос"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
) -> Any:
    """
    Поиск покупателей по имени или email.
    
    Доступно только для продавцов.
    """
    users = user_crud.search(db, query=q, skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
) -> Any:
    """
    Получить информацию о конкретном покупателе.
    
    Доступно только для продавцов.
    """
    user = user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    return user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Обновить информацию о текущем пользователе.
    
    Пользователь может обновлять только свой профиль.
    """
    user = user_crud.update(db, db_obj=current_user, obj_in=user_update)
    return user


@router.delete("/me")
async def delete_current_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Удалить аккаунт текущего пользователя.
    
    Выполняется мягкое удаление (soft delete).
    """
    user_crud.remove(db, id=current_user.id)
    return {"message": "Аккаунт успешно удален"}


# ============================================================================
# РОУТЫ ДЛЯ ПРОФИЛЕЙ ПОКУПАТЕЛЕЙ
# ============================================================================

@router.get("/me/profile", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Получить расширенный профиль текущего пользователя.
    """
    profile = user_crud.get_profile(db, user_id=current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )
    return profile


@router.put("/me/profile", response_model=UserProfileResponse)
async def update_current_user_profile(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Обновить расширенный профиль текущего пользователя.
    """
    profile = user_crud.update_profile(
        db, 
        user_id=current_user.id, 
        obj_in=profile_update
    )
    return profile


# ============================================================================
# РОУТЫ ДЛЯ ПРОДАВЦОВ (SELLERS)
# ============================================================================

@router.get("/sellers/", response_model=List[SellerResponse])
async def get_sellers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
) -> Any:
    """
    Получить список всех продавцов.
    
    Доступно только для продавцов (для партнерских программ).
    """
    sellers = seller_crud.get_multi(db, skip=skip, limit=limit)
    return sellers


@router.get("/sellers/search", response_model=List[SellerResponse])
async def search_sellers(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
) -> Any:
    """
    Поиск продавцов по названию компании или email.
    """
    sellers = seller_crud.search(db, query=q, skip=skip, limit=limit)
    return sellers


@router.get("/sellers/{seller_id}", response_model=SellerResponse)
async def get_seller(
    seller_id: UUID,
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
) -> Any:
    """
    Получить информацию о конкретном продавце.
    """
    seller = seller_crud.get(db, id=seller_id)
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Продавец не найден"
        )
    return seller


@router.put("/sellers/me", response_model=SellerResponse)
async def update_current_seller(
    seller_update: SellerUpdate,
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
) -> Any:
    """
    Обновить информацию о текущем продавце.
    """
    seller = seller_crud.update(db, db_obj=current_seller, obj_in=seller_update)
    return seller


@router.delete("/sellers/me")
async def delete_current_seller(
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
) -> Any:
    """
    Удалить аккаунт текущего продавца.
    
    Выполняется мягкое удаление (soft delete).
    """
    seller_crud.remove(db, id=current_seller.id)
    return {"message": "Аккаунт продавца успешно удален"}


# ============================================================================
# РОУТЫ ДЛЯ НАСТРОЕК ПРОДАВЦОВ
# ============================================================================

@router.get("/sellers/me/settings", response_model=SellerSettingsResponse)
async def get_current_seller_settings(
    current_seller: Seller = Depends(get_current_seller),
    db: Session = Depends(get_db)
) -> Any:
    """
    Получить настройки текущего продавца.
    """
    settings = seller_crud.get_settings(db, seller_id=current_seller.id)
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Настройки не найдены"
        )
    return settings


@router.put("/sellers/me/settings", response_model=SellerSettingsResponse)
async def update_current_seller_settings(
    settings_update: SellerSettingsUpdate,
    current_seller: Seller = Depends(get_current_seller),
    db: Session = Depends(get_db)
) -> Any:
    """
    Обновить настройки текущего продавца.
    
    Включает настройки автоответчика, ИИ-консультанта и интеграций.
    """
    settings = seller_crud.update_settings(
        db,
        seller_id=current_seller.id,
        obj_in=settings_update
    )
    return settings


# ============================================================================
# РОУТЫ ДЛЯ СТАТИСТИКИ И АНАЛИТИКИ
# ============================================================================

@router.get("/sellers/me/stats")
async def get_current_seller_stats(
    current_seller: Seller = Depends(get_current_seller),
    db: Session = Depends(get_db)
) -> Any:
    """
    Получить статистику текущего продавца.
    
    Включает количество сообщений, конверсию, активность бота и т.д.
    """
    stats = seller_crud.get_stats(db, seller_id=current_seller.id)
    return stats


@router.get("/me/activity")
async def get_current_user_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Получить активность текущего пользователя.
    
    Включает историю сообщений, взаимодействий и поведенческие данные.
    """
    activity = user_crud.get_activity(db, user_id=current_user.id)
    return activity