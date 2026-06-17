import logging
import random
import os
import asyncio
import time
import threading
from datetime import datetime, date, timedelta
from http.server import SimpleHTTPRequestHandler, HTTPServer
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, PreCheckoutQueryHandler

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
    {"file": "10.jpg", "name": "𝒎𝒐𝒐𝒏🌳", "rarity": "🔮 Секретная", "price": 150}
]

EMPTY_RESPONSES = [
    "Эта карта оказалась пустой... Открой ещё разок! 😔",
    "Эх, тут ничего не оказалось. Повезет в следующий раз! 💨",
    "Увы, пак пуст. Фортуна сегодня отдыхает 🃏"
]
EMPTY_CARDS = [{"file": None, "name": "Эта карта пуста, открой ещё 😔", "rarity": "⚪ Пустышка", "price": 0}] * 50
CARDS = REAL_CARDS + EMPTY_CARDS

SHOP_TITLES = {
    "title_collector": {"name": "🕶️ Коллекционер", "price": 150},
    "title_rich": {"name": "💵 Магнат DAcards", "price": 500},
    "title_lucky": {"name": "🍀 Любимчик Фортуны", "price": 1000},
    "title_legend": {"name": "🦅 Легенда Леса", "price": 2500},
    "title_overlord": {"name": "🌌 Повелитель Рандома", "price": 5000}
}

PROFILE_THEMES = {
    "default": {"name": "🐜 Стандартный Муравейник", "price": 0},
    "beehive": {"name": "🐝 Золотой Улей", "price": 300},
    "anthill_neon": {"name": "🔮 Кибер-Гнездо (Неон)", "price": 1000}
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN", "8701989939:AAG2z5cJ-kSkTe1k3OizAeTKHFc-OJ97Bfg")
ADMIN_ID = 7501899378

COOLDOWNS = {}
COOLDOWN_TIME = 1.5 

def escape_markdown(text):
    if not text: return ""
    for c in ['_', '*', '`', '[']: text = text.replace(c, f"\\{c}")
    return text

# ==================== КОМПАКТНАЯ КЛАВИАТУРА ====================
def get_main_keyboard():
    buttons = [
        ["📦 Открыть пак", "👤 Профиль", "🗂️ Коллекция"],
        ["⚔️ Походы & Битвы", "🚀 Прокачка & Крафт"],
        ["🎲 Удача & Квесты", "🛍️ Магазин", "🎁 Бонусы & Донат"] # Кнопка переименована
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# ==================== MONGODB ====================
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://tananyandavid5_db_user:7dmj6rMlquxr19c8@david2010.wlbyl1j.mongodb.net/?retryWrites=true&w=majority&appName=David2010")
client = MongoClient(MONGO_URI)
db = client["cards_bot_database"]
users_col = db["users"]
collections_col = db["collections"]

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server_address = ("", port)
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args): pass
    httpd = HTTPServer(server_address, QuietHandler)
    httpd.serve_forever()

# ==================== РЕГИСТРАЦИЯ И СТАТИСТИКА ====================
def register_user(user_id, first_name, username=None):
    update_data = {"first_name": first_name}
    if username: update_data["username"] = username

    users_col.update_one(
        {"user_id": user_id},
        {
            "$set": update_data,
            "$setOnInsert": {
                "coins": 500, 
                "packs_opened": 0, 
                "active_title": "Нет титула", 
                "owned_titles": ["Нет титула"],
                "joined_at": datetime.utcnow().isoformat(),
                "daily_date": "", "daily_packs": 0, "daily_games": 0,
                "daily_reward_packs_claimed": False, "daily_reward_games_claimed": False,
                "colony_level": 1, 
                "last_daily_bonus": "", 
                "bank_deposit": 0, 
                "profile_theme": "default", 
                "owned_themes": ["default"],
                "expedition_end": "", 
                "pvp_wins": 0
            }
        },
        upsert=True
    )

def get_user_all_data(user_id):
    return users_col.find_one({"user_id": user_id})

def update_user_coins(user_id, amount):
    users_col.update_one({"user_id": user_id}, {"$inc": {"coins": amount}})

def add_card_to_db(user_id, card):
    collections_col.insert_one({
        "user_id": user_id, "card_name": card['name'], "rarity": card['rarity'],
        "file_name": card['file'], "price": card['price']
    })

def get_user_cards(user_id):
    return list(collections_col.find({"user_id": user_id}))

# ==================== ОБРАБОТЧИКИ ГЛАВНОГО МЕНЮ ====================
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    await update.message.reply_text("🐜 Симулятор Карточных Колоний запущен! Развивай гнездо, копи монеты и покупай улучшения:", reply_markup=get_main_keyboard())

async def open_pack_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    
    current_time = time.time()
    if user_id in COOLDOWNS and (current_time - COOLDOWNS[user_id] < COOLDOWN_TIME):
        await update.message.reply_text(f"⏳ Подождите еще немного перед открытием пака!")
        return
    COOLDOWNS[user_id] = current_time
    
    ud = get_user_all_data(user_id)
    lvl = ud.get("colony_level", 1)
    
    dropped_card = random.choice(CARDS)
    if dropped_card["file"] is None and random.randint(1, 100) < (lvl * 5):
        dropped_card = random.choice(REAL_CARDS)

    users_col.update_one({"user_id": user_id}, {"$inc": {"packs_opened": 1, "daily_packs": 1}})
    
    if dropped_card["file"] is None:
        await update.message.reply_text(random.choice(EMPTY_RESPONSES))
    else:
        add_card_to_db(user_id, dropped_card)
        update_user_coins(user_id, dropped_card['price'])
        path_to_image = f"cards/{dropped_card['file']}"
        caption_text = f"🎉 Найдена карта!\n\nНазвание: *{dropped_card['name']}*\nРедкость: {dropped_card['rarity']}\nМонеты: +{dropped_card['price']} 🪙"
        if os.path.exists(path_to_image):
            await update.message.reply_photo(photo=open(path_to_image, 'rb'), caption=caption_text, parse_mode="Markdown")
        else:
            await update.message.reply_text(caption_text, parse_mode="Markdown")

async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_
