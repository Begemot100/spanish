import sqlite3

import openai
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import os

env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# Проверяем наличие ключа API в переменных окружения
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("API ключ OpenAI не найден. Убедитесь, что переменная окружения OPENAI_API_KEY задана.")

# Загрузка ключа OpenAI из переменных окружения
openai.api_key = os.getenv("OPENAI_API_KEY")

# Функция для отображения меню изучения слов
import openai
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CallbackQueryHandler
import os

env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# Проверяем наличие ключа API в переменных окружения
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("API ключ OpenAI не найден. Убедитесь, что переменная окружения OPENAI_API_KEY задана.")

# Загрузка ключа OpenAI из переменных окружения
openai.api_key = os.getenv("OPENAI_API_KEY")

# Функция для отображения меню изучения слов
async def show_vocabulary_menu(update, context):
    query = update.callback_query
    await query.answer()

    # Темы для изучения слов
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

    # Создание кнопок из списка тем
    buttons = [[InlineKeyboardButton(text=topic, callback_data=f"vocab_{i}")] for i, topic in enumerate(topics)]

    # Добавляем кнопку для возврата в главное меню
    buttons.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data="menu")])

    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(
        text="Выберите тему для изучения:",
        reply_markup=keyboard
    )

# Функция для генерации слов на выбранную тему
async def generate_words(update, context):
    query = update.callback_query

    # Загружаем выбранную тему
    selected_topic = context.user_data.get("selected_topic")

    if not selected_topic:
        await query.edit_message_text(text="Ошибка: тема не выбрана.")
        return

    # Получаем список уже существующих слов для пользователя
    user_id = update.callback_query.from_user.id
    connection = sqlite3.connect("language_learning.db")
    cursor = connection.cursor()

    cursor.execute("SELECT spanish_word FROM dictionary WHERE user_id = ?", (user_id,))
    existing_words = set(row[0] for row in cursor.fetchall())
    connection.close()

    # Запрос к OpenAI для генерации случайных слов на основе выбранной темы
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Generate a list of 10 random Spanish words related to the topic '{selected_topic}', with their Russian translations formatted as 'Spanish - Russian'"}
        ]
    )

    words = response["choices"][0]["message"]["content"].strip().split("\n")

    # Фильтруем уже существующие слова
    unique_words = [word for word in words if word.split(" - ")[0] not in existing_words]

    if len(unique_words) < 10:
        await query.edit_message_text(text="Ошибка: недостаточно уникальных слов для этой темы. Попробуйте выбрать другую тему.")
        return

    # Сохраняем уникальные слова в контексте
    context.user_data["generated_words"] = unique_words[:10]  # Ограничиваем до 10 слов

    # Формируем текст с сгенерированными словами
    generated_words_text = f"Вот 10 случайных слов по теме '{selected_topic}':\n\n" + "\n".join(unique_words[:10])

    # Добавляем кнопку для начала теста
    buttons = [
        [InlineKeyboardButton(text="Проверь себя", callback_data="check_self")],
        [InlineKeyboardButton(text="🔙 Назад к темам", callback_data="vocabulary")]
    ]

    # Отправляем сгенерированные слова пользователю
    await query.edit_message_text(
        text=generated_words_text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# Функция для обработки выбора темы

# Создание экземпляра Updater
# updater = Updater("YOUR_BOT_API_KEY")

# Регистрация обработчиков
# updater.dispatcher.add_handler(CallbackQueryHandler(show_vocabulary_menu, pattern="^vocabulary$"))
# updater.dispatcher.add_handler(CallbackQueryHandler(handle_topic_selection, pattern="^vocab_\\d+$"))

# Запуск бота
# updater.start_polling()
# updater.idle()
