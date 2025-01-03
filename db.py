import sqlite3

# Создание базы данных и таблиц
def create_db():
    connection = sqlite3.connect('language_learning.db')
    cursor = connection.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            language_level TEXT DEFAULT 'A1',
            profile_type TEXT DEFAULT 'basic',
            grammar_progress INTEGER DEFAULT 0,
            vocab_progress INTEGER DEFAULT 0
        )
    ''')

    connection.commit()
    connection.close()

# Получение профиля пользователя
def get_user_profile(user_id):
    connection = sqlite3.connect('language_learning.db')
    cursor = connection.cursor()

    cursor.execute('SELECT username, profile_type, grammar_progress, vocab_progress FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    connection.close()
    return user_data

# Создание нового пользователя, если его нет в базе
def create_user(user_id, username):
    connection = sqlite3.connect('language_learning.db')
    cursor = connection.cursor()

    cursor.execute('''
        INSERT INTO users (id, username, language_level, profile_type, grammar_progress, vocab_progress)
        VALUES (?, ?, 'A1', 'basic', 0, 0)
    ''', (user_id, username))

    connection.commit()
    connection.close()
