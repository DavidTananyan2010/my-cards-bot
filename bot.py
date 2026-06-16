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
    "title_collector": {"name": "🕶️ Коллекционер", "price": 150},
    "title_rich": {"name": "💵 Магнат DAcards", "price": 500},
    "title_lucky": {"name": "🍀 Любимчик Фортуны", "price": 1000},
    "title_legend": {"name": "🦅 Легенда Леса", "price": 2500},
    "title_overlord": {"name": "🌌 Повелитель Рандома", "price": 5000}
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

TOKEN = os.environ.get("BOT_TOKEN", "8701989939:AAG2z5cJ-kSkTe1k3OizAeTKHFc-OJ97Bfg")
ADMIN_ID = 7501899378

# ==================== ГЛАВНАЯ КЛАВИАТУРА КНОПОК ====================
def get_main_keyboard():
    buttons = [
        ["📦 Открыть пак", "🛍️ Магазин"],
        ["🗂️ Моя коллекция", "🏆 ТОП игроков"],
        ["👤 Мой профиль"]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# ==================== ПОДКЛЮЧЕНИЕ К MONGODB ATLAS ====================
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://tananyandavid5_db_user:7dmj6rMlquxr19c8@david2010.wlbyl1j.mongodb.net/?retryWrites=true&w=majority&appName=David2010")
client = MongoClient(MONGO_URI)
db = client["cards_bot_database"]

users_col = db["users"]
collections_col = db["collections"]

# Фоновый веб-сервер для поддержки активности Render
def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server_address = ("", port)
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args): pass
    httpd = HTTPServer(server_address, QuietHandler)
    httpd.serve_forever()

# ==================== ФУНКЦИИ РАБОТЫ С БАЗОЙ ДАННЫХ ====================
def register_user(user_id, first_name):
    users_col.update_one(
        {"user_id": user_id},
        {
            "$set": {"first_name": first_name},
            "$setOnInsert": {"coins": 500, "packs_opened": 0, "active_title": "Нет титула", "owned_titles": ["Нет титула"]}
        },
        upsert=True
    )

def get_user_stats(user_id):
    user = users_col.find_one({"user_id": user_id})
    if user:
        return user.get("coins", 0), user.get("packs_opened", 0), user.get("active_title", "Нет титула"), user.get("owned_titles", ["Нет титула"])
    return 0, 0, "Нет титула", ["Нет титула"]

def increment_packs(user_id):
    users_col.update_one({"user_id": user_id}, {"$inc": {"packs_opened": 1}})

def update_user_coins(user_id, amount):
    users_col.update_one({"user_id": user_id}, {"$inc": {"coins": amount}})

def set_user_title(user_id, title_name):
    users_col.update_one({"user_id": user_id}, {"$set": {"active_title": title_name}})

def add_title_to_owned(user_id, title_name):
    users_col.update_one({"user_id": user_id}, {"$addToSet": {"owned_titles": title_name}})

def add_card_to_db(user_id, card):
    collections_col.insert_one({
        "user_id": user_id,
        "card_name": card['name'],
        "rarity": card['rarity'],
        "file_name": card['file'],
        "price": card['price']
    })

def get_user_cards(user_id):
    return list(collections_col.find({"user_id": user_id}))

# ==================== ОБРАБОТЧИКИ МЕНЮ ПОЛЬЗОВАТЕЛЯ ====================
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name)
    await update.message.reply_text("Добро пожаловать в DAcards! Выберите действие:", reply_markup=get_main_keyboard())

async def open_pack_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name)
    
    dropped_card = random.choice(CARDS)
    increment_packs(user_id)

    if dropped_card["file"] is None:
        await update.message.reply_text(random.choice(EMPTY_RESPONSES), reply_markup=get_main_keyboard())
    else:
        add_card_to_db(user_id, dropped_card)
        update_user_coins(user_id, dropped_card['price'])
        
        path_to_image = f"cards/{dropped_card['file']}"
        caption_text = f"🎉 Вы открыли пак!\n\nНазвание: *{dropped_card['name']}*\nРедкость: {dropped_card['rarity']}\nНачислено: +{dropped_card['price']} 🪙"
        
        if os.path.exists(path_to_image):
            await update.message.reply_photo(photo=open(path_to_image, 'rb'), caption=caption_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text(f"Картинка отсутствует, карта добавлена!\n\n{caption_text}", parse_mode="Markdown", reply_markup=get_main_keyboard())

async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name)
    coins, packs, title, _ = get_user_stats(user_id)
    
    profile_text = f"👤 *Профиль игрока {update.effective_user.first_name}*\nID: `{user_id}`\n🎖️ Титул: *{title}*\n🪙 Баланс: {coins} монеток\n📦 Открыто паков: {packs}\n"
    await update.message.reply_text(profile_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def top_players_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = users_col.find().sort("coins", -1).limit(10)
    text = "🏆 *ТОП-10 БОГАТЕЙШИХ ИГРОКОВ DAcards* 🏆\n\n"
    for index, user in enumerate(top_users, start=1):
        emoji = "🥇" if index == 1 else "🥈" if index == 2 else "🥉" if index == 3 else f"{index}."
        text += f"{emoji} *{user.get('first_name', 'Игрок')}* — {user.get('coins', 0)} 🪙 ({user.get('active_title', 'Нет титула')})\n"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard())

# ==================== ЛОГИКА СТИЛЬНОЙ КОЛЛЕКЦИИ (УДАЛЕНИЕ НА ВЫБОР) ====================
async def collection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name)
    raw_cards = get_user_cards(user_id)
    
    if not raw_cards:
        await update.message.reply_text("🗂️ *Ваша витрина карт пока пуста.*", parse_mode="Markdown", reply_markup=get_main_keyboard())
        return

    card_counts = {}
    for card in raw_cards:
        card_counts[card["card_name"]] = card_counts.get(card["card_name"], 0) + 1

    text = f"✨ *РОСКОШНАЯ ВИТРИНА КАРТ {update.effective_user.first_name.upper()}* ✨\n\n"
    keyboard = []
    
    for name, count in card_counts.items():
        text += f"• *{name}* — количество: `x{count}`\n"
        # Инлайн-кнопка удаления конкретной карты на выбор
        keyboard.append([InlineKeyboardButton(f"❌ Удалить 1 шт: {name}", callback_data=f"delete_card_{name}")])
        
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==================== СТРУКТУРИРОВАННЫЙ МАГАЗИН ====================
async def open_shop_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name)
    
    keyboard = [
        [InlineKeyboardButton("🎫 Магазин титулов", callback_data="menu_titles"),
         InlineKeyboardButton("💰 Продажа карт", callback_data="menu_cards")]
    ]
    await update.message.reply_text("🛍️ *Главное меню Торгового Центра DAcards.*\nВыберите необходимый отдел:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==================== CALLBACK-ОБРАБОТЧИК КНОПОК ====================
async def shop_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    # --- НАВИГАЦИЯ МЕНЮ ---
    if data == "menu_titles":
        kb = [
            [InlineKeyboardButton("🛍️ Купить титул", callback_data="buy_title_list")],
            [InlineKeyboardButton("👗 Гардеробная / Надеть титул", callback_data="wardrobe_list")],
            [InlineKeyboardButton("⬅️ Назад в магазин", callback_data="back_to_shop_main")]
        ]
        await query.edit_message_text("🎫 *Управление титулами DAcards.* Выберите действие:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data == "menu_cards":
        kb = [
            [InlineKeyboardButton("💵 Продать ВСЕ карты", callback_data="sell_all_cards")],
            [InlineKeyboardButton("♻️ Продать дубликаты", callback_data="sell_duplicates")],
            [InlineKeyboardButton("⬅️ Назад в магазин", callback_data="back_to_shop_main")]
        ]
        await query.edit_message_text("💰 *Отдел перепродажи карт.* Выберите вариант сделки:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data == "back_to_shop_main":
        kb = [[InlineKeyboardButton("🎫 Магазин титулов", callback_data="menu_titles"), InlineKeyboardButton("💰 Продажа карт", callback_data="menu_cards")]]
        await query.edit_message_text("🛍️ *Главное меню Торгового Центра DAcards.*\nВыберите необходимый отдел:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    # --- ЛОГИКА КАРТ: УДАЛЕНИЕ НА ВЫБОР ---
    elif data.startswith("delete_card_"):
        card_name = data.replace("delete_card_", "")
        deleted_res = collections_col.find_one_and_delete({"user_id": user_id, "card_name": card_name})
        if deleted_res:
            await query.message.reply_text(f"🗑️ Вы успешно удалили 1 шт. карты *{card_name}* из инвентаря.", parse_mode="Markdown", reply_markup=get_main_keyboard())
        else:
            await query.message.reply_text("🛑 Карта не найдена.", reply_markup=get_main_keyboard())
        return

    # --- ЛОГИКА КАРТ: ПРОДАТЬ ВСЕ ---
    elif data == "sell_all_cards":
        cards = get_user_cards(user_id)
        if not cards:
            await query.message.reply_text("🛑 У вас нет карт для
