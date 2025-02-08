import random
import sqlite3

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import openai
import os

from vocabulary_menu import generate_words

env_path = os.path.join(os.path.dirname(__file__), '.env')


load_dotenv(env_path)

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("API ключ OpenAI не найден. Убедитесь, что переменная окружения OPENAI_API_KEY задана.")

openai.api_key = os.getenv("OPENAI_API_KEY")
connection = sqlite3.connect("language_learning.db")
cursor = connection.cursor()

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

async def start_test(update, context):
    query = update.callback_query
    await query.answer()

    selected_topic = context.user_data.get("selected_topic")

    if not selected_topic:
        await query.edit_message_text(text="Ошибка: тема не выбрана.")
        return

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Generate a list of 10 random Spanish words related to the topic '{selected_topic}', with their Russian translations formatted as 'Spanish - Russian'"}
        ]
    )

    words = response["choices"][0]["message"]["content"].strip().split("\n")

    if not words:
        await query.edit_message_text(text="Ошибка: нет слов для теста.")
        return

    context.user_data["words_for_test"] = words
    context.user_data["current_question_index"] = 0
    context.user_data["correct_count"] = 0
    context.user_data["incorrect_count"] = 0

    await ask_question(update, context)


async def handle_topic_selection(update, context):
    query = update.callback_query
    await query.answer()

    topic_index = int(query.data.split("_")[1])

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

    selected_topic = topics[topic_index]

    context.user_data["selected_topic"] = selected_topic

    await query.edit_message_text(
        text=f"Вы выбрали тему: {selected_topic}. Начинаем тест!"
    )

    await generate_words(update, context)  

async def handle_vocabulary_action(update, context):
    query = update.callback_query
    await query.answer()

    action_type = query.data.split("_")[1]  # Это может быть "generate" или "select"
    topic_index = int(query.data.split("_")[2])

    topics = [
        "Приветствия", "Семья", "Еда", "Цвета", "Числа",
        "Дни недели", "Месяцы", "Погода", "Животные", "Одежда"
    ]

    selected_topic = topics[topic_index]

    if action_type == "generate":
        await generate_words(update, context)
    elif action_type == "select":
        context.user_data["selected_topic"] = selected_topic
        await query.edit_message_text(
            text=f"Вы выбрали тему: {selected_topic}. Начинаем тест!"
        )
        await start_test(update, context)

async def ask_question(update, context):
    words = context.user_data.get("generated_words", [])
    current_index = context.user_data.get("current_question_index", 0)

    if current_index >= len(words):
        await end_test(update, context)
        return

    current_word = words[current_index]

    correct_answer = current_word.split(' - ')[1]
    incorrect_answers = random.sample([word.split(' - ')[1] for word in words if word != current_word], 3)
    options = [correct_answer] + incorrect_answers
    random.shuffle(options)

    context.user_data["correct_answer"] = correct_answer

    buttons = [[InlineKeyboardButton(text=option, callback_data=f"answer_{option}")] for option in options]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.edit_message_text(
        text=f"Какой перевод слова '{current_word.split(' - ')[0]}'?",
        reply_markup=keyboard
    )

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

    context.user_data["current_question_index"] += 1
    await ask_question(update, context)

async def end_test(update, context):
    correct_count = context.user_data.get("correct_count", 0)
    total_questions = len(context.user_data.get("generated_words", []))
    correct_percentage = (correct_count / total_questions) * 100

    user_id = update.callback_query.from_user.id

    if correct_percentage >= 80:
        response_text = f"🎉 Поздравляем! Вы правильно ответили на {correct_count} из {total_questions} вопросов. Слова добавлены в ваш словарь."
        save_words_to_db(context.user_data.get("generated_words", []), user_id)  
    else:
        response_text = f"😞 Вы правильно ответили на {correct_count} из {total_questions} вопросов. Попробуйте еще раз, чтобы улучшить результат."

    update_vocab_progress(user_id)

    update_grammar_progress(user_id)

    context.user_data.clear()

    await update.callback_query.edit_message_text(
        text=response_text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="🔙 Назад к темам", callback_data="vocabulary")]])
    )

def update_progress(user_id, vocab_progress=None, grammar_progress=None):
    connection = sqlite3.connect("language_learning.db")
    cursor = connection.cursor()

    if vocab_progress is not None:
        cursor.execute("UPDATE users SET vocab_progress = ? WHERE user_id = ?", (vocab_progress, user_id))

    if grammar_progress is not None:
        cursor.execute("UPDATE users SET grammar_progress = ? WHERE user_id = ?", (grammar_progress, user_id))

    connection.commit()
    connection.close()


def update_grammar_progress(user_id):
    grammar_progress = 50  
    update_progress(user_id, grammar_progress=grammar_progress)

def update_vocab_progress(user_id):
    connection = sqlite3.connect("language_learning.db")
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM dictionary WHERE user_id = ?", (user_id,))
    total_words = cursor.fetchone()[0]

    total_goal = 1000

    vocab_progress = min((total_words / total_goal) * 100, 100)

    update_progress(user_id, vocab_progress=vocab_progress)

    connection.close()

def save_words_to_db(words, user_id):
    connection = sqlite3.connect("language_learning.db")
    cursor = connection.cursor()

    for word in words:
        spanish, russian = word.split(" - ")

        cursor.execute("SELECT 1 FROM dictionary WHERE user_id = ? AND spanish_word = ?", (user_id, spanish))
        existing_word = cursor.fetchone()

        if not existing_word:  
            cursor.execute("INSERT INTO dictionary (user_id, spanish_word, russian_translation) VALUES (?, ?, ?)", (user_id, spanish, russian))
        else:
            print(f"Слово '{spanish}' уже существует в словаре.")  

    connection.commit()

    update_vocab_progress(user_id)

    connection.close()


