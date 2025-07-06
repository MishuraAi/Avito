    def test_crud_operations(self) -> bool:
        """Проверить основные CRUD операции"""
        try:
            with self.engine.connect() as conn:
                if "sqlite" in self.settings.database_url.lower():
                    # SQLite: временная таблица, все операции в одном соединении
                    conn.execute(text("""
                        CREATE TEMPORARY TABLE test_table (
                            id INTEGER PRIMARY KEY,
                            name TEXT,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    conn.execute(text("""
                        INSERT INTO test_table (name) VALUES ('test')
                    """))
                    result = conn.execute(text("SELECT name FROM test_table WHERE name = 'test'"))
                    row = result.fetchone()
                    if not row:
                        raise Exception("Не удалось вставить или прочитать данные")
                    conn.execute(text("""
                        UPDATE test_table SET name = 'updated' WHERE name = 'test'
                    """))
                    result = conn.execute(text("SELECT name FROM test_table WHERE name = 'updated'"))
                    updated_row = result.fetchone()
                    if not updated_row:
                        raise Exception("Не удалось обновить данные")
                    conn.execute(text("DELETE FROM test_table WHERE name = 'updated'"))
                    result = conn.execute(text("SELECT COUNT(*) FROM test_table"))
                    count = result.fetchone()[0]
                    if count != 0:
                        raise Exception("Не удалось удалить данные")
                    # Временная таблица удалится автоматически, но можно явно удалить
                    conn.execute(text("DROP TABLE test_table"))
                else:
                    # PostgreSQL синтаксис
                    conn.execute(text("""
                        CREATE TEMPORARY TABLE test_table (
                            id SERIAL PRIMARY KEY,
                            name VARCHAR(50),
                            created_at TIMESTAMP DEFAULT NOW()
                        )
                    """))
                    conn.execute(text("""
                        INSERT INTO test_table (name) VALUES ('test')
                    """))
                    result = conn.execute(text("SELECT name FROM test_table WHERE name = 'test'"))
                    row = result.fetchone()
                    if not row:
                        raise Exception("Не удалось вставить или прочитать данные")
                    conn.execute(text("""
                        UPDATE test_table SET name = 'updated' WHERE name = 'test'
                    """))
                    result = conn.execute(text("SELECT name FROM test_table WHERE name = 'updated'"))
                    updated_row = result.fetchone()
                    if not updated_row:
                        raise Exception("Не удалось обновить данные")
                    conn.execute(text("DELETE FROM test_table WHERE name = 'updated'"))
                    result = conn.execute(text("SELECT COUNT(*) FROM test_table"))
                    count = result.fetchone()[0]
                    if count != 0:
                        raise Exception("Не удалось удалить данные")
                    conn.commit()
            print("✅ CRUD операции выполняются успешно")
            return True
        except Exception as e:
            print(f"❌ Ошибка CRUD операций: {e}")
            return False 