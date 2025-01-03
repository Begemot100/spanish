import random
import sqlite3

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import openai
import os

from vocabulary_menu import generate_words

env_path = os.path.join(os.path.dirname(__file__), '.env')


load_dotenv(env_path)

# Проверяем наличие ключа API в переменных окружения
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("API ключ OpenAI не найден. Убедитесь, что переменная окружения OPENAI_API_KEY задана.")

# Загрузка ключа OpenAI из переменных окружения
openai.api_key = os.getenv("OPENAI_API_KEY")
# Инициализация базы данных
connection = sqlite3.connect("language_learning.db")
cursor = connection.cursor()

# Создание таблицы для словаря, если не существует
cursor.execute('''
    CREATE TABLE IF NOT EXISTS dictionary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        spanish_word TEXT,
        russian_translation TEXT
    )
''')
connection.commit()
connection.close()

# Функция для начала теста "Проверь себя"
async def start_test(update, context):
    query = update.callback_query
    await query.answer()

    # Загружаем выбранную тему
    selected_topic = context.user_data.get("selected_topic")

    # Если тема не выбрана, выводим ошибку
    if not selected_topic:
        await query.edit_message_text(text="Ошибка: тема не выбрана.")
        return

    # Запрос к OpenAI для генерации 10 случайных слов на выбранную тему
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Generate a list of 10 random Spanish words related to the topic '{selected_topic}', with their Russian translations formatted as 'Spanish - Russian'"}
        ]
    )

    words = response["choices"][0]["message"]["content"].strip().split("\n")

    # Проверяем наличие слов для теста
    if not words:
        await query.edit_message_text(text="Ошибка: нет слов для теста.")
        return

    # Сохраняем слова для теста
    context.user_data["words_for_test"] = words
    context.user_data["current_question_index"] = 0
    context.user_data["correct_count"] = 0
    context.user_data["incorrect_count"] = 0

    # Переходим к первому вопросу
    await ask_question(update, context)


# Функция для обработки выбора темы
async def handle_topic_selection(update, context):
    query = update.callback_query
    await query.answer()

    # Получаем индекс темы из callback_data
    topic_index = int(query.data.split("_")[1])

    # Список тем
    topics = [
        "Приветствия",
        "Семья",
        "Еда",
        "Цвета",
        "Числа",
        "Дни недели",
        "Месяцы",
        "Погода",
        "Животные",
        "Одежда"
    ]

    # Выбираем тему по индексу
    selected_topic = topics[topic_index]

    # Сохраняем выбранную тему в контексте пользователя
    context.user_data["selected_topic"] = selected_topic

    await query.edit_message_text(
        text=f"Вы выбрали тему: {selected_topic}. Начинаем тест!"
    )

    # Переходим к генерации слов
    await generate_words(update, context)  # Запускаем функцию генерации слов

async def handle_vocabulary_action(update, context):
    query = update.callback_query
    await query.answer()

    # Получаем данные из callback_data
    action_type = query.data.split("_")[1]  # Это может быть "generate" или "select"
    topic_index = int(query.data.split("_")[2])

    topics = [
        "Приветствия", "Семья", "Еда", "Цвета", "Числа",
        "Дни недели", "Месяцы", "Погода", "Животные", "Одежда"
    ]

    selected_topic = topics[topic_index]

    if action_type == "generate":
        # Здесь вызывается генерация слов
        await generate_words(update, context)
    elif action_type == "select":
        # Здесь вызывается выбор темы
        context.user_data["selected_topic"] = selected_topic
        await query.edit_message_text(
            text=f"Вы выбрали тему: {selected_topic}. Начинаем тест!"
        )
        await start_test(update, context)

# Функция для задания вопроса
async def ask_question(update, context):
    words = context.user_data.get("generated_words", [])
    current_index = context.user_data.get("current_question_index", 0)

    if current_index >= len(words):
        await end_test(update, context)
        return

    current_word = words[current_index]

    # Генерируем варианты ответов
    correct_answer = current_word.split(' - ')[1]
    incorrect_answers = random.sample([word.split(' - ')[1] for word in words if word != current_word], 3)
    options = [correct_answer] + incorrect_answers
    random.shuffle(options)

    # Сохраняем правильный ответ в контексте
    context.user_data["correct_answer"] = correct_answer

    # Создаем кнопки с вариантами ответов
    buttons = [[InlineKeyboardButton(text=option, callback_data=f"answer_{option}")] for option in options]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.edit_message_text(
        text=f"Какой перевод слова '{current_word.split(' - ')[0]}'?",
        reply_markup=keyboard
    )

# Функция для обработки ответа пользователя
async def handle_answer(update, context):
    query = update.callback_query
    await query.answer()

    selected_answer = query.data.split("answer_")[1]
    correct_answer = context.user_data.get("correct_answer")

    if selected_answer == correct_answer:
        context.user_data["correct_count"] += 1
        response_text = "✅ Правильно!"
    else:
        context.user_data["incorrect_count"] += 1
        response_text = f"❌ Неправильно. Правильный ответ: {correct_answer}"

    # Переходим к следующему вопросу
    context.user_data["current_question_index"] += 1
    await ask_question(update, context)

# Функция для завершения теста
async def end_test(update, context):
    correct_count = context.user_data.get("correct_count", 0)
    total_questions = len(context.user_data.get("generated_words", []))
    correct_percentage = (correct_count / total_questions) * 100

    user_id = update.callback_query.from_user.id

    # Если прогресс по словарю должен быть обновлен
    if correct_percentage >= 80:
        response_text = f"🎉 Поздравляем! Вы правильно ответили на {correct_count} из {total_questions} вопросов. Слова добавлены в ваш словарь."
        save_words_to_db(context.user_data.get("generated_words", []), user_id)  # Добавляем слова и обновляем прогресс
    else:
        response_text = f"😞 Вы правильно ответили на {correct_count} из {total_questions} вопросов. Попробуйте еще раз, чтобы улучшить результат."

    # Обновляем прогресс по словам
    update_vocab_progress(user_id)

    # Обновляем прогресс по грамматике (пример)
    update_grammar_progress(user_id)

    # Сброс данных теста
    context.user_data.clear()

    await update.callback_query.edit_message_text(
        text=response_text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="🔙 Назад к темам", callback_data="vocabulary")]])
    )

def update_progress(user_id, vocab_progress=None, grammar_progress=None):
    connection = sqlite3.connect("language_learning.db")
    cursor = connection.cursor()

    # Если прогресс слов обновляется
    if vocab_progress is not None:
        cursor.execute("UPDATE users SET vocab_progress = ? WHERE user_id = ?", (vocab_progress, user_id))

    # Если прогресс грамматики обновляется
    if grammar_progress is not None:
        cursor.execute("UPDATE users SET grammar_progress = ? WHERE user_id = ?", (grammar_progress, user_id))

    connection.commit()
    connection.close()


def update_grammar_progress(user_id):
    # Пример логики для обновления прогресса грамматики
    # Вы можете использовать свой алгоритм для расчета прогресса грамматики
    grammar_progress = 50  # Например, если пользователь выполнил 50% тестов
    update_progress(user_id, grammar_progress=grammar_progress)

def update_vocab_progress(user_id):
    connection = sqlite3.connect("language_learning.db")
    cursor = connection.cursor()

    # Получаем количество слов в словаре для пользователя
    cursor.execute("SELECT COUNT(*) FROM dictionary WHERE user_id = ?", (user_id,))
    total_words = cursor.fetchone()[0]

    # Цель для 100% прогресса — 1000 слов
    total_goal = 1000

    # Вычисляем процент прогресса
    vocab_progress = min((total_words / total_goal) * 100, 100)

    # Обновляем прогресс в базе данных
    update_progress(user_id, vocab_progress=vocab_progress)

    connection.close()

# Функция для сохранения слов в базу данных
def save_words_to_db(words, user_id):
    connection = sqlite3.connect("language_learning.db")
    cursor = connection.cursor()

    for word in words:
        spanish, russian = word.split(" - ")

        # Проверка на уникальность слова
        cursor.execute("SELECT 1 FROM dictionary WHERE user_id = ? AND spanish_word = ?", (user_id, spanish))
        existing_word = cursor.fetchone()

        if not existing_word:  # Если слово еще не существует в словаре
            cursor.execute("INSERT INTO dictionary (user_id, spanish_word, russian_translation) VALUES (?, ?, ?)", (user_id, spanish, russian))
        else:
            print(f"Слово '{spanish}' уже существует в словаре.")  # Для отладки

    connection.commit()

    # После добавления новых слов обновляем прогресс
    update_vocab_progress(user_id)

    connection.close()


# Регистрация обработчиков в основном файле (пример в bot.py)
# application.add_handler(CallbackQueryHandler(start_test, pattern="^check_self$"))
# application.add_handler(CallbackQueryHandler(handle_answer, pattern="^answer_"))
