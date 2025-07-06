"""
📋 Базовый CRUD класс для SQLAlchemy моделей

Этот модуль содержит базовую реализацию CRUD операций:
- Создание, чтение, обновление, удаление
- Пагинация и фильтрация
- Массовые операции
- Мягкое удаление
- Поиск и сортировка

Местоположение: src/database/crud/base.py
"""

import uuid
from datetime import datetime, timezone
from typing import (
    TypeVar, Generic, Type, Optional, List, Dict, Any, 
    Union, Sequence, Tuple
)

from sqlalchemy import and_, or_, desc, asc, func, text
from sqlalchemy.orm import Session, Query
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel

from ..models.base import BaseModel as DBBaseModel

# Типы для Generic CRUD
ModelType = TypeVar("ModelType", bound=DBBaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDFilter(BaseModel):
    """Модель для фильтрации запросов"""
    
    field: str
    value: Any
    operator: str = "eq"  # eq, ne, gt, gte, lt, lte, like, ilike, in, not_in
    
    class Config:
        arbitrary_types_allowed = True


class CRUDSort(BaseModel):
    """Модель для сортировки"""
    
    field: str
    direction: str = "asc"  # asc, desc


class PaginationParams(BaseModel):
    """Параметры пагинации"""
    
    skip: int = 0
    limit: int = 100
    
    class Config:
        validate_assignment = True


class PaginatedResponse(BaseModel, Generic[ModelType]):
    """Ответ с пагинацией"""
    
    items: List[ModelType]
    total: int
    skip: int
    limit: int
    has_next: bool
    has_prev: bool
    
    class Config:
        arbitrary_types_allowed = True


class BaseCRUD(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    📋 Базовый класс CRUD операций
    
    Предоставляет стандартные операции для любой модели:
    - CRUD операции (Create, Read, Update, Delete)
    - Пагинация и фильтрация
    - Поиск и сортировка
    - Массовые операции
    - Мягкое удаление
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        Инициализация CRUD
        
        Args:
            model: SQLAlchemy модель
        """
        self.model = model
        self.model_name = model.__name__
    
    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Создание новой записи
        
        Args:
            db: Сессия базы данных
            obj_in: Данные для создания
            
        Returns:
            ModelType: Созданный объект
        """
        try:
            # Конвертируем Pydantic модель в dict
            if isinstance(obj_in, BaseModel):
                obj_data = obj_in.dict(exclude_unset=True)
            else:
                obj_data = obj_in
            
            # Создаем объект модели
            db_obj = self.model(**obj_data)
            
            # Сохраняем в БД
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            
            return db_obj
            
        except SQLAlchemyError as e:
            db.rollback()
            raise e
    
    def get(self, db: Session, id: uuid.UUID) -> Optional[ModelType]:
        """
        Получение записи по ID
        
        Args:
            db: Сессия базы данных
            id: UUID записи
            
        Returns:
            Optional[ModelType]: Найденный объект или None
        """
        return db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[List[CRUDFilter]] = None,
        sort: Optional[List[CRUDSort]] = None,
        include_deleted: bool = False
    ) -> List[ModelType]:
        """
        Получение множества записей
        
        Args:
            db: Сессия базы данных
            skip: Количество записей для пропуска
            limit: Максимальное количество записей
            filters: Фильтры для применения
            sort: Сортировка
            include_deleted: Включать удаленные записи
            
        Returns:
            List[ModelType]: Список объектов
        """
        query = db.query(self.model)
        
        # Применяем фильтр удаленных записей
        if not include_deleted and hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
        
        # Применяем фильтры
        if filters:
            query = self._apply_filters(query, filters)
        
        # Применяем сортировку
        if sort:
            query = self._apply_sorting(query, sort)
        
        return query.offset(skip).limit(limit).all()
    
    def get_paginated(
        self,
        db: Session,
        *,
        pagination: PaginationParams,
        filters: Optional[List[CRUDFilter]] = None,
        sort: Optional[List[CRUDSort]] = None,
        include_deleted: bool = False
    ) -> PaginatedResponse[ModelType]:
        """
        Получение записей с пагинацией
        
        Args:
            db: Сессия базы данных
            pagination: Параметры пагинации
            filters: Фильтры для применения
            sort: Сортировка
            include_deleted: Включать удаленные записи
            
        Returns:
            PaginatedResponse[ModelType]: Объект с пагинацией
        """
        query = db.query(self.model)
        
        # Применяем фильтр удаленных записей
        if not include_deleted and hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
        
        # Применяем фильтры
        if filters:
            query = self._apply_filters(query, filters)
        
        # Получаем общее количество
        total = query.count()
        
        # Применяем сортировку
        if sort:
            query = self._apply_sorting(query, sort)
        
        # Получаем записи
        items = query.offset(pagination.skip).limit(pagination.limit).all()
        
        return PaginatedResponse(
            items=items,
            total=total,
            skip=pagination.skip,
            limit=pagination.limit,
            has_next=pagination.skip + pagination.limit < total,
            has_prev=pagination.skip > 0
        )
    
    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Обновление записи
        
        Args:
            db: Сессия базы данных
            db_obj: Существующий объект для обновления
            obj_in: Новые данные
            
        Returns:
            ModelType: Обновленный объект
        """
        try:
            # Конвертируем в dict если нужно
            if isinstance(obj_in, BaseModel):
                update_data = obj_in.dict(exclude_unset=True)
            else:
                update_data = obj_in
            
            # Обновляем поля
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            # Обновляем временную метку
            if hasattr(db_obj, 'updated_at'):
                db_obj.updated_at = datetime.now(timezone.utc)
            
            # Увеличиваем версию
            if hasattr(db_obj, 'version'):
                db_obj.version += 1
            
            db.commit()
            db.refresh(db_obj)
            
            return db_obj
            
        except SQLAlchemyError as e:
            db.rollback()
            raise e
    
    def delete(self, db: Session, *, id: uuid.UUID, hard_delete: bool = False) -> Optional[ModelType]:
        """
        Удаление записи
        
        Args:
            db: Сессия базы данных
            id: UUID записи для удаления
            hard_delete: Полное удаление (не мягкое)
            
        Returns:
            Optional[ModelType]: Удаленный объект или None
        """
        try:
            obj = self.get(db, id)
            if not obj:
                return None
            
            if hard_delete or not hasattr(obj, 'soft_delete'):
                # Полное удаление
                db.delete(obj)
            else:
                # Мягкое удаление
                obj.soft_delete()
            
            db.commit()
            return obj
            
        except SQLAlchemyError as e:
            db.rollback()
            raise e
    
    def restore(self, db: Session, *, id: uuid.UUID) -> Optional[ModelType]:
        """
        Восстановление мягко удаленной записи
        
        Args:
            db: Сессия базы данных
            id: UUID записи для восстановления
            
        Returns:
            Optional[ModelType]: Восстановленный объект или None
        """
        try:
            obj = db.query(self.model).filter(
                and_(
                    self.model.id == id,
                    self.model.is_deleted == True
                )
            ).first()
            
            if not obj or not hasattr(obj, 'restore'):
                return None
            
            obj.restore()
            db.commit()
            db.refresh(obj)
            
            return obj
            
        except SQLAlchemyError as e:
            db.rollback()
            raise e
    
    def count(
        self,
        db: Session,
        *,
        filters: Optional[List[CRUDFilter]] = None,
        include_deleted: bool = False
    ) -> int:
        """
        Подсчет записей
        
        Args:
            db: Сессия базы данных
            filters: Фильтры для применения
            include_deleted: Включать удаленные записи
            
        Returns:
            int: Количество записей
        """
        query = db.query(func.count(self.model.id))
        
        # Применяем фильтр удаленных записей
        if not include_deleted and hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
        
        # Применяем фильтры
        if filters:
            query = self._apply_filters(query, filters)
        
        return query.scalar()
    
    def exists(self, db: Session, *, id: uuid.UUID) -> bool:
        """
        Проверка существования записи
        
        Args:
            db: Сессия базы данных
            id: UUID записи
            
        Returns:
            bool: True если запись существует
        """
        return db.query(
            db.query(self.model).filter(self.model.id == id).exists()
        ).scalar()
    
    def bulk_create(self, db: Session, *, objs_in: List[CreateSchemaType]) -> List[ModelType]:
        """
        Массовое создание записей
        
        Args:
            db: Сессия базы данных
            objs_in: Список данных для создания
            
        Returns:
            List[ModelType]: Список созданных объектов
        """
        try:
            db_objs = []
            
            for obj_in in objs_in:
                if isinstance(obj_in, BaseModel):
                    obj_data = obj_in.dict(exclude_unset=True)
                else:
                    obj_data = obj_in
                
                db_obj = self.model(**obj_data)
                db_objs.append(db_obj)
            
            db.add_all(db_objs)
            db.commit()
            
            # Обновляем объекты
            for db_obj in db_objs:
                db.refresh(db_obj)
            
            return db_objs
            
        except SQLAlchemyError as e:
            db.rollback()
            raise e
    
    def bulk_update(
        self,
        db: Session,
        *,
        updates: List[Tuple[uuid.UUID, Dict[str, Any]]]
    ) -> List[ModelType]:
        """
        Массовое обновление записей
        
        Args:
            db: Сессия базы данных
            updates: Список кортежей (id, update_data)
            
        Returns:
            List[ModelType]: Список обновленных объектов
        """
        try:
            updated_objs = []
            
            for obj_id, update_data in updates:
                obj = self.get(db, obj_id)
                if obj:
                    for field, value in update_data.items():
                        if hasattr(obj, field):
                            setattr(obj, field, value)
                    
                    # Обновляем временную метку
                    if hasattr(obj, 'updated_at'):
                        obj.updated_at = datetime.now(timezone.utc)
                    
                    updated_objs.append(obj)
            
            db.commit()
            
            # Обновляем объекты
            for obj in updated_objs:
                db.refresh(obj)
            
            return updated_objs
            
        except SQLAlchemyError as e:
            db.rollback()
            raise e
    
    def search(
        self,
        db: Session,
        *,
        query_text: str,
        search_fields: List[str],
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        Поиск по текстовым полям
        
        Args:
            db: Сессия базы данных
            query_text: Текст для поиска
            search_fields: Поля для поиска
            skip: Количество записей для пропуска
            limit: Максимальное количество записей
            
        Returns:
            List[ModelType]: Список найденных объектов
        """
        query = db.query(self.model)
        
        # Строим условия поиска
        search_conditions = []
        for field in search_fields:
            if hasattr(self.model, field):
                field_attr = getattr(self.model, field)
                search_conditions.append(
                    field_attr.ilike(f"%{query_text}%")
                )
        
        if search_conditions:
            query = query.filter(or_(*search_conditions))
        
        # Фильтруем удаленные записи
        if hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
        
        return query.offset(skip).limit(limit).all()
    
    def _apply_filters(self, query: Query, filters: List[CRUDFilter]) -> Query:
        """Применение фильтров к запросу"""
        
        for filter_item in filters:
            if not hasattr(self.model, filter_item.field):
                continue
            
            field_attr = getattr(self.model, filter_item.field)
            
            if filter_item.operator == "eq":
                query = query.filter(field_attr == filter_item.value)
            elif filter_item.operator == "ne":
                query = query.filter(field_attr != filter_item.value)
            elif filter_item.operator == "gt":
                query = query.filter(field_attr > filter_item.value)
            elif filter_item.operator == "gte":
                query = query.filter(field_attr >= filter_item.value)
            elif filter_item.operator == "lt":
                query = query.filter(field_attr < filter_item.value)
            elif filter_item.operator == "lte":
                query = query.filter(field_attr <= filter_item.value)
            elif filter_item.operator == "like":
                query = query.filter(field_attr.like(f"%{filter_item.value}%"))
            elif filter_item.operator == "ilike":
                query = query.filter(field_attr.ilike(f"%{filter_item.value}%"))
            elif filter_item.operator == "in":
                query = query.filter(field_attr.in_(filter_item.value))
            elif filter_item.operator == "not_in":
                query = query.filter(~field_attr.in_(filter_item.value))
        
        return query
    
    def _apply_sorting(self, query: Query, sort_params: List[CRUDSort]) -> Query:
        """Применение сортировки к запросу"""
        
        for sort_item in sort_params:
            if not hasattr(self.model, sort_item.field):
                continue
            
            field_attr = getattr(self.model, sort_item.field)
            
            if sort_item.direction.lower() == "desc":
                query = query.order_by(desc(field_attr))
            else:
                query = query.order_by(asc(field_attr))
        
        return query
    
    def get_or_create(
        self,
        db: Session,
        *,
        defaults: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Tuple[ModelType, bool]:
        """
        Получение или создание записи
        
        Args:
            db: Сессия базы данных
            defaults: Значения по умолчанию для создания
            **kwargs: Поля для поиска
            
        Returns:
            Tuple[ModelType, bool]: (объект, создан_ли)
        """
        try:
            # Пытаемся найти существующую запись
            filters = [
                CRUDFilter(field=key, value=value, operator="eq")
                for key, value in kwargs.items()
            ]
            
            query = db.query(self.model)
            query = self._apply_filters(query, filters)
            
            obj = query.first()
            
            if obj:
                return obj, False
            
            # Создаем новую запись
            create_data = {**kwargs}
            if defaults:
                create_data.update(defaults)
            
            obj = self.model(**create_data)
            db.add(obj)
            db.commit()
            db.refresh(obj)
            
            return obj, True
            
        except SQLAlchemyError as e:
            db.rollback()
            raise e


# Экспорт
__all__ = [
    "BaseCRUD",
    "CRUDFilter",
    "CRUDSort", 
    "PaginationParams",
    "PaginatedResponse",
    "ModelType",
    "CreateSchemaType",
    "UpdateSchemaType"
]