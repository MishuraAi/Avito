# Пустая миграция (для ручного заполнения)
alembic revision -m "Custom migration"
```

### Применение миграций
```bash
# Применить все до последней версии
alembic upgrade head

# Применить до конкретной ревизии
alembic upgrade ae1027a6acf

# Применить следующую миграцию
alembic upgrade +1

# Откатиться на одну миграцию назад
alembic downgrade -1

# Откатиться до конкретной ревизии
alembic downgrade ae1027a6acf

# Откатиться до базового состояния
alembic downgrade base
```

### Информация о миграциях
```bash
# Текущая версия БД
alembic current

# История всех миграций
alembic history

# Подробная история
alembic history --verbose

# Показать конкретную миграцию
alembic show ae1027a6acf

# Проверить, что миграции соответствуют моделям
alembic check
```

## 🛠️ Структура файлов миграций

После инициализации у вас будет:

```
migrations/
├── versions/                    # 📁 Файлы миграций
│   └── 20250106_initial_migration.py
├── env.py                      # ⚙️ Конфигурация Alembic
├── script.py.mako             # 📝 Шаблон для новых миграций
└── README                     # 📖 Документация Alembic
```

## 📝 Пример файла миграции

```python
"""Initial migration - create all tables

Revision ID: ae1027a6acf
Revises: 
Create Date: 2025-01-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'ae1027a6acf'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Создание таблиц users
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    
    # Создание остальных таблиц...

def downgrade() -> None:
    # Удаление в обратном порядке
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
    # Удаление остальных таблиц...
```

## ⚠️ Важные правила миграций

### ✅ Что НУЖНО делать:
- **Всегда** создавайте резервную копию перед применением миграций в продакшене
- **Проверяйте** сгенерированные миграции перед применением
- **Тестируйте** миграции на копии продакшен данных
- **Используйте** осмысленные имена для миграций
- **Добавляйте** комментарии для сложных изменений

### ❌ Что НЕ нужно делать:
- **Не редактируйте** уже примененные миграции
- **Не удаляйте** файлы миграций из системы контроля версий
- **Не применяйте** миграции в продакшене без тестирования
- **Не забывайте** про downgrade методы

## 🚨 Решение проблем

### Конфликты миграций
```bash
# Если возникли конфликты между ветками
alembic merge -m "Merge heads" head1 head2

# Сброс до чистого состояния (ОСТОРОЖНО!)
alembic stamp base
alembic upgrade head
```

### Проблемы с автогенерацией
```bash
# Если автогенерация не работает
# 1. Проверьте target_metadata в env.py
# 2. Убедитесь что модели импортированы
# 3. Проверьте подключение к БД
```

### Откат проблемной миграции
```bash
# Откатиться на предыдущую версию
alembic downgrade -1

# Исправить миграцию и заново применить
alembic upgrade head
```

## 🔧 Продвинутые возможности

### Работа с данными в миграциях
```python
def upgrade() -> None:
    # Структурные изменения
    op.add_column('users', sa.Column('full_name', sa.String(200)))
    
    # Миграция данных
    connection = op.get_bind()
    result = connection.execute("SELECT id, first_name, last_name FROM users")
    for row in result:
        full_name = f"{row.first_name} {row.last_name}".strip()
        connection.execute(
            "UPDATE users SET full_name = %s WHERE id = %s",
            (full_name, row.id)
        )
```

### Условные миграции
```python
def upgrade() -> None:
    # Проверить существование таблицы
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'old_table' in inspector.get_table_names():
        op.rename_table('old_table', 'new_table')
```

## 📊 Мониторинг миграций

### Проверка состояния БД
```python
# scripts/check_migrations.py
from src.database import get_database_manager
from alembic.config import Config
from alembic import command

def check_migration_status():
    """Проверить статус миграций"""
    alembic_cfg = Config("alembic.ini")
    
    # Получить текущую версию
    current = command.current(alembic_cfg)
    
    # Получить последнюю версию
    heads = command.heads(alembic_cfg)
    
    if current == heads:
        print("✅ База данных актуальна")
    else:
        print("⚠️ Требуется применить миграции")
        print(f"Текущая: {current}")
        print(f"Последняя: {heads}")

if __name__ == "__main__":
    check_migration_status()
```

## 📚 Полезные ссылки

- **Официальная документация Alembic**: https://alembic.sqlalchemy.org/
- **SQLAlchemy документация**: https://docs.sqlalchemy.org/
- **PostgreSQL документация**: https://www.postgresql.org/docs/

---

## 🎯 Следующие шаги

1. **Создайте базу данных** PostgreSQL
2. **Настройте .env файл** с корректными параметрами
3. **Запустите скрипт инициализации**: `python scripts/init_migrations.py`
4. **Создайте первую миграцию**: `alembic revision --autogenerate -m "Initial migration"`
5. **Примените миграции**: `alembic upgrade head`
6. **Проверьте результат**: `alembic current`

🎉 **Готово!** Ваша база данных настроена и готова к работе!