import psycopg2
import random
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from parameters import DB_SERVER_CONFIG, DB_CONFIG, INITIAL_WORDS, USER_WORD_PROBABILITY, MAX_WRONG_OPTIONS


class Database:
    def __init__(self):
        self.connection = None
        self.create_database_if_not_exists()
        self.connect()
        self.init_database()

    def create_database_if_not_exists(self):
        """Создает базу данных"""
        try:
            conn = psycopg2.connect(**DB_SERVER_CONFIG)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s",
                           (DB_CONFIG['database'],))
            exists = cursor.fetchone()

            if not exists:
                print(f"Создаем базу данных: {DB_CONFIG['database']}")
                create_db_query = sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(DB_CONFIG['database'])
                )
                cursor.execute(create_db_query)
                print("База данных успешно создана")
            else:
                print(f"База данных {DB_CONFIG['database']} уже существует")

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"Ошибка при создании базы данных: {e}")
            raise

    def connect(self):
        """Установка соединения с базой данных"""
        try:
            self.connection = psycopg2.connect(**DB_CONFIG)
            print("Connected to PostgreSQL database")
        except Exception as e:
            print(f"Error connecting to database: {e}")
            raise

    def init_database(self):
        """Инициализация базы данных и заполнение начальными данными"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        telegram_id BIGINT UNIQUE NOT NULL,
                        username VARCHAR(255),
                        first_name VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print("Таблица пользователей создана")

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS common_words (
                        id SERIAL PRIMARY KEY,
                        russian_word VARCHAR(255) NOT NULL,
                        english_word VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print("Таблица общих слов создана")

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_words (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        russian_word VARCHAR(255) NOT NULL,
                        english_word VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print("Таблица пользовательских слов создана")

                cursor.execute("SELECT COUNT(*) FROM common_words")
                count = cursor.fetchone()[0]

                if count == 0:
                    cursor.executemany(
                        "INSERT INTO common_words (russian_word, english_word) VALUES (%s, %s)",
                        INITIAL_WORDS
                    )
                    print(f"Добавлено {len(INITIAL_WORDS)} начальных слов")
                else:
                    print(f"В базе есть {count} слов")

                self.connection.commit()
                print("База данных готова к работе!")

        except Exception as e:
            print(f"Error initializing database: {e}")
            self.connection.rollback()
            raise

    def get_or_create_user(self, telegram_id, username=None, first_name=None):
        """Получение или создание пользователя"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM users WHERE telegram_id = %s",
                    (telegram_id,)
                )
                user = cursor.fetchone()

                if not user:
                    cursor.execute(
                        """INSERT INTO users (telegram_id, username, first_name) 
                         VALUES (%s, %s, %s) RETURNING id""",
                        (telegram_id, username, first_name)
                    )
                    user_id = cursor.fetchone()[0]
                    self.connection.commit()
                    print(f"Создан новый пользователь: {user_id}")
                    return user_id
                else:
                    return user[0]

        except Exception as e:
            print(f"Error getting user: {e}")
            self.connection.rollback()
            return None

    def get_random_word(self, user_id):
        """Получение случайного слова для изучения"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, russian_word, english_word, 'common' as source 
                    FROM common_words 
                    ORDER BY RANDOM() 
                    LIMIT 1
                """)
                common_word = cursor.fetchone()

                cursor.execute("""
                    SELECT id, russian_word, english_word, 'user' as source 
                    FROM user_words 
                    WHERE user_id = %s 
                    ORDER BY RANDOM() 
                    LIMIT 1
                """, (user_id,))
                user_word = cursor.fetchone()

                if user_word and random.random() < USER_WORD_PROBABILITY:
                    return user_word
                else:
                    return common_word

        except Exception as e:
            print(f"Error getting random word: {e}")
            return None

    def get_wrong_options(self, correct_word, limit=None):
        """Получение неправильных вариантов ответа"""
        try:
            if limit is None:
                limit = MAX_WRONG_OPTIONS

            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT english_word FROM common_words 
                    WHERE english_word != %s 
                    ORDER BY RANDOM() 
                    LIMIT %s
                """, (correct_word, limit))

                wrong_options = [row[0] for row in cursor.fetchall()]
                return wrong_options

        except Exception as e:
            print(f"Error getting wrong options: {e}")
            return ['apple', 'book', 'pen']

    def add_user_word(self, user_id, russian_word, english_word):
        """Добавление пользовательского слова"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_words (user_id, russian_word, english_word) 
                    VALUES (%s, %s, %s) 
                    RETURNING id
                """, (user_id, russian_word, english_word))

                word_id = cursor.fetchone()[0]
                self.connection.commit()
                print(
                    f"Добавлено пользовательское слово: {russian_word} - {english_word}")
                return word_id

        except Exception as e:
            print(f"Ошибка при добавлении пользовательского слова: {e}")
            self.connection.rollback()
            return None

    def delete_user_word(self, user_id, word_id):
        """Удаление пользовательского слова"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM user_words 
                    WHERE id = %s AND user_id = %s
                """, (word_id, user_id))

                self.connection.commit()
                success = cursor.rowcount > 0
                if success:
                    print(f"Удалено пользовательское слово с ID: {word_id}")
                return success

        except Exception as e:
            print(f"Error deleting user word: {e}")
            self.connection.rollback()
            return False

    def get_user_words(self, user_id):
        """Получение списка пользовательских слов"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, russian_word, english_word 
                    FROM user_words 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC
                """, (user_id,))

                words = cursor.fetchall()
                print(
                    f"Получено {len(words)} пользовательских слов для пользователя с ID: {user_id}")
                return words

        except Exception as e:
            print(f"Error getting user words: {e}")
            return []

    def close(self):
        """Закрытие соединения с базой данных"""
        if self.connection:
            self.connection.close()
