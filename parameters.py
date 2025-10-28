import os
from dotenv import load_dotenv

load_dotenv()

DB_SERVER_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'Введите Ваш пароль от базы данных'),
    'port': os.getenv('DB_PORT', '5432')
}

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'english_bot_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'Введите Ваш пароль от базы данных'),
    'port': os.getenv('DB_PORT', '5432')
}

BOT_TOKEN = os.getenv('BOT_TOKEN', 'Введите Ваш токен')

MAX_WRONG_OPTIONS = 3
USER_WORD_PROBABILITY = 0.3

INITIAL_WORDS = [
    ('красный', 'red'),
    ('синий', 'blue'),
    ('зеленый', 'green'),
    ('желтый', 'yellow'),
    ('я', 'I'),
    ('ты', 'you'),
    ('он', 'he'),
    ('она', 'she'),
    ('дом', 'house'),
    ('кот', 'cat')
]