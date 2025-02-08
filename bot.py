import logging
import os
import sqlite3

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler,Updater, ContextTypes, MessageHandler, filters, Updater
import openai
from dotenv import load_dotenv
from db import create_db, get_user_profile, create_user
from test_self_vocabulary import start_test, handle_answer, handle_topic_selection, handle_vocabulary_action
from vocabulary_menu import show_vocabulary_menu, generate_words

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("API ключ OpenAI не найден. Убедитесь, что переменная окружения OPENAI_API_KEY задана.")

openai.api_key = api_key
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def get_base_keyboard():
    buttons = [[InlineKeyboardButton(text="Меню", callback_data="menu")]]
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Нажмите на кнопку "Меню", чтобы продолжить:',
        reply_markup=get_base_keyboard()
    )

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    buttons = [
        [InlineKeyboardButton(text="📘 Словарь", callback_data="dictionary")],
        [InlineKeyboardButton(text="📝 Словарный запас", callback_data="vocabulary")],
        [InlineKeyboardButton(text="📚 Грамматика", callback_data="grammar")],
        [InlineKeyboardButton(text="👥 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🆘 Хелп", callback_data="help")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(text="Выберите опцию:", reply_markup=keyboard)

async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    username = query.from_user.username or "unknown"

    user_data = get_user_profile(user_id)
    if not user_data:
        create_user(user_id, username)
        user_data = (username, 'basic', 0, 0)

    username, profile_type, grammar_progress, vocab_progress = user_data
    profile_info = (
        f"👤 Ник: @{username}\n"
        f"🔖 Тип профиля: {profile_type.capitalize()}\n"
        f"📚 Прогресс грамматики: {grammar_progress}%\n"
        f"📘 Прогресс слов: {vocab_progress}%"
    )

    await query.edit_message_text(text=profile_info, reply_markup=get_base_keyboard())

async def handle_any_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Нажмите на кнопку "Меню", чтобы продолжить:',
        reply_markup=get_base_keyboard()
    )

async def show_dictionary(update, context):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    connection = sqlite3.connect("language_learning.db")
    cursor = connection.cursor()
    cursor.execute("SELECT spanish_word, russian_translation FROM dictionary WHERE user_id = ?", (user_id,))
    words = cursor.fetchall()
    connection.close()

    if words:
        dictionary_text = "📘 Ваш словарь:\n\n" + "\n".join([f"{spanish} - {russian}" for spanish, russian in words])
    else:
        dictionary_text = "Ваш словарь пуст. Пройдите тест, чтобы добавить слова."

    await query.edit_message_text(
        text=dictionary_text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="🔙 Назад в меню", callback_data="menu")]])
    )


def main():
    create_db()  

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(show_menu, pattern="^menu$"))
    application.add_handler(CallbackQueryHandler(handle_profile, pattern="^profile$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_any_message))
    application.add_handler(CallbackQueryHandler(show_vocabulary_menu, pattern="^vocabulary$"))
    application.add_handler(CallbackQueryHandler(handle_topic_selection, pattern="^vocab_\\d+$"))
    application.add_handler(CallbackQueryHandler(start_test, pattern="^check_self$"))
    application.add_handler(CallbackQueryHandler(handle_answer, pattern="^answer_"))

    application.add_handler(CallbackQueryHandler(generate_words, pattern="^vocab_\\d+$"))
    application.add_handler(CallbackQueryHandler(show_dictionary, pattern="^dictionary$"))

    application.run_polling()



if __name__ == "__main__":
    main()
