import logging
import random
import os
import asyncio
import threading  # Для фонового веб-сервера
from http.server import SimpleHTTPRequestHandler, HTTPServer # Для сервера
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from pymongo import MongoClient  # Библиотека для работы с MongoDB

# ==================== СПИСОК КАРТ И ЦЕН ====================
REAL_CARDS = [
    {"file": "1.jpg", "name": "金 sunny🌲 김지ха | DA 🐂", "rarity": "🔮 Секретная", "price": 100},
    {"file": "5.jpg", "name": "Солнечный Самурай ☀️", "rarity": "⭐ Обычная", "price": 10},
    {"file": "4.jpg", "name": "Меха-Бык 🐂", "rarity": "⭐ Редкая", "price": 30},

    {"file": "2.jpg", "name": "👻losnya🐂🌲", "rarity": "🔮 Секретная", "price": 100},
    {"file": "7.jpg", "name": "Призрак Леса 👻", "rarity": "⭐ Редкая", "price": 30},
    {"file": "6.jpg", "name": "Таинственный Лось 🦌", "rarity": "⭐ Обычная", "price": 10},

    {"file": "3.jpg", "name": "Дониёр 🌲", "rarity": "🔮 Секретная", "price": 100},
    {"file": "9.jpg", "name": "Страж Дубравы 🌲", "rarity": "⭐ Обычная", "price": 10},
    {"file": "8.jpg", "name": "Лесной Хакер 💻", "rarity": "⭐ Редкая", "price": 30},
    
    # Новая карта
    {"file": "10.jpg", "name": "𝒎𝒐𝒐𝒏🌳", "rarity": "🔮 Секретная", "price": 150}
]

EMPTY_RESPONSES = [
    "Эта карта оказалась пустой... Открой ещё разок! 😔",
    "Эх, тут ничего не оказалось. Повезет в следующий раз! 💨",
    "Увы, пак пуст. Фортуна сегодня отдыхает 🃏",
    "Пустышка! Но не унывай, монеты целы — крути еще! 🪙"
]

EMPTY_CARDS = [{"file": None, "name": "Эта карта пуста, открой ещё 😔", "rarity": "⚪ Пустышка", "price": 0}] * 50
CARDS = REAL_CARDS + EMPTY_CARDS

# ==================== АССОРТИМЕНТ МАГАЗИНА ТИТУЛОВ ====================
SHOP_TITLES = {
    "title_collector": {"name": "🕶️ Коллекционер", "price": 150, "desc": "Выдается истинным ценителям прекрасного."},
    "title_rich": {"name": "💵 Магнат DAcards", "price": 500, "desc": "Для тех, кто сорит монетами направо и налево."},
    "title_lucky": {"name": "🍀 Любимчик Фортуны", "price": 1000, "desc": "Титул, притягивающий удачу (но это неточно)."},
    "title_legend": {"name": "🦅 Легенда Леса", "price": 2500, "desc": "Лимитированный статус величайшего лесного хакера."},
    "title_overlord": {"name": "🌌 Повелитель Рандома", "price": 5000, "desc": "Абсолютный статус. Все паки трепещут перед вами."}
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

TOKEN = os.environ.get("BOT_TOKEN", "8701989939:AAG2z5cJ-kSkTe1k3OizAeTKHFc-OJ97Bfg")
ADMIN_ID = 7501899378
LOG_CHAT_ID = ADMIN_ID  
DB_FILE = "bot_database.db"

# ==================== ПОДКЛЮЧЕНИЕ К MONGODB ATLAS ====================
# Код автоматически возьмет строку из переменных окружения Render
MONGO_URI = os.environ.get("MONGO_URI", "ВСТАВЬТЕ_СЮДА_ВАШУ_СТРОКУ_ИЗ_ШАГА_1_ДЛЯ_ЛОКАЛЬНЫХ_ТЕСТОВ")
client = MongoClient(MONGO_URI)
db = client["cards_bot_database"]

users_col = db["users"]
collections_col = db["collections"]


# ==================== ВЕБ-СЕРВЕР ДЛЯ RENDER ====================
def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server_address = ("", port)
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass
            
    httpd = HTTPServer(server_address, QuietHandler)
    print(f"Встроенный веб-сервер запущен на порту {port}")
    httpd.serve_forever()


# ==================== РАБОТА С БАЗОЙ ДАННЫХ MONGODB ====================
def register_user(user_id, first_name):
    users_col.update_one(
        {"user_id": user_id},
        {
            "$set": {"first_name": first_name},
            "$setOnInsert": {"coins": 0, "packs_opened": 0, "active_title": "Нет титула"}
        },
        upsert=True
    )


def get_user_stats(user_id):
    user = users_col.find_one({"user_id": user_id})
    if user:
        return user.get("coins", 0), user.get("packs_opened", 0), user.get("active_title", "Нет титула")
    return 0, 0, "Нет титула"


def increment_packs(user_id):
    users_col.update_one({"user_id": user_id}, {"$inc": {"packs_opened": 1}})


def add_card_to_db(user_id, card):
    collections_col.insert_one({
        "user_id": user_id,
        "card_name": card['name'],
        "rarity": card['rarity'],
        "file_name": card['file'],
        "price": card['price']
    })


def get_user_cards(user_id):
    cursor = collections_col.find({"user_id": user_id})
    cards_list = list(cursor)
    
    from collections import Counter
    card_names = [c["card_name"] for c in cards_list]
    counts = Counter(card_names)
    
    unique_cards = []
    seen = set()
    for c in cards_list:
        if c["card_name"] not in seen:
            seen.add(c["card_name"])
            unique_cards.append((c["card_name"], c["rarity"], counts[c["card_name"]]))
            
    return unique_cards


# ==================== ЛОГИКА ОТПРАВКИ КАРТ ====================
async def open_pack_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name)
    
    dropped_card = random.choice(CARDS)
    increment_packs(user_id)

    if dropped_card["file"] is None:
        response_text = random.choice(EMPTY_RESPONSES)
        await update.message.reply_text(response_text)
    else:
        add_card_to_db(user_id, dropped_card)
        path_to_image = f"cards/{dropped_card['file']}"
        
        caption_text = (
            f"🎉 Вы открыли пак и нашли карту!\n\n"
            f"Название: *{dropped_card['name']}*\n"
            f"Редкость: {dropped_card['rarity']}\n"
            f"Стоимость: {dropped_card['price']} 🪙"
        )
        
        if os.path.exists(path_to_image):
            await update.message.reply_photo(
                photo=open(path_to_image, 'rb'), 
                caption=caption_text, 
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"Картинка не найдена, но карта добавлена!\n\n{caption_text}", 
                parse_mode="Markdown"
            )

# Допишите инициализацию Application (main поток) внизу при необходимости...
