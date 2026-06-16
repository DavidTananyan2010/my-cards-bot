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
    
    # Ваша новая карта
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

# ==================== ГЛАВНАЯ КЛАВИАТУРА КНОПОК ====================
def get_main_keyboard():
    buttons = [
        ["📦 Открыть пак", "🛍️ Магазин титулов"],
        ["👤 Мой профиль"]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# ==================== ПОДКЛЮЧЕНИЕ К MONGODB ATLAS ====================
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://tananyandavid5_db_user:7dmj6rMlquxr19c8@david2010.wlbyl1j.mongodb.net/?retryWrites=true&w=majority&appName=David2010")
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
            "$setOnInsert": {"coins": 500, "packs_opened": 0, "active_title": "Нет титула"}
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

def update_user_coins(user_id, amount):
    users_col.update_one({"user_id": user_id}, {"$inc": {"coins": amount}})

def set_user_title(user_id, title_name):
    users_col.update_one({"user_id": user_id}, {"$set": {"active_title": title_name}})

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
        await update.message.reply_text(response_text, reply_markup=get_main_keyboard())
    else:
        add_card_to_db(user_id, dropped_card)
        update_user_coins(user_id, dropped_card['price'])
        
        path_to_image = f"cards/{dropped_card['file']}"
        caption_text = (
            f"🎉 Вы открыли пак и нашли карту!\n\n"
            f"Название: *{dropped_card['name']}*\n"
            f"Редкость: {dropped_card['rarity']}\n"
            f"Вам начислено: +{dropped_card['price']} 🪙"
        )
        
        if os.path.exists(path_to_image):
            await update.message.reply_photo(
                photo=open(path_to_image, 'rb'), 
                caption=caption_text, 
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                f"Картинка не найдена, но карта добавлена!\n\n{caption_text}", 
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )


# ==================== ЛОГИКА МАГАЗИНА ТИТУЛОВ ====================
async def open_shop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name)
    
    coins, _, active_title = get_user_stats(user_id)
    
    text = (
        f"🛍️ *Магазин уникальных титулов DAcards*\n"
        f"Ваш текущий титул: *{active_title}*\n"
        f"Ваш баланс: {coins} 🪙\n\n"
        f"Выберите титул для покупки:"
    )
    
    keyboard = []
    for key, info in SHOP_TITLES.items():
        keyboard.append([InlineKeyboardButton(f"{info['name']} — {info['price']} 🪙", callback_data=f"buy_{key}")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def shop_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith("buy_"):
        title_key = data.replace("buy_", "")
        
        if title_key in SHOP_TITLES:
            title_info = SHOP_TITLES[title_key]
            coins, _, active_title = get_user_stats(user_id)
            
            # Если у пользователя уже есть этот титул
            if active_title == title_info['name']:
                await query.message.reply_text(
                    f"🛑 У вас уже активен титул *{title_info['name']}*!", 
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
                return
                
            # Если не хватает денег
            if coins < title_info['price']:
                await query.message.reply_text(
                    f"❌ Недостаточно монет! {title_info['name']} стоит *{title_info['price']}* 🪙, а у вас только *{coins}* 🪙.", 
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
            else:
                # Покупка успешна
                update_user_coins(user_id, -title_info['price'])
                set_user_title(user_id, title_info['name'])
                
                await query.message.reply_text(
                    f"🎉 Успешная покупка!\nУстановлен новый статус: *{title_info['name']}*\n"
                    f"Списано: -{title_info['price']} 🪙", 
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )


# ==================== КОМАНДА /START И ПРОФИЛЬ ====================
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name)
    await update.message.reply_text("Добро пожаловать в DAcards! Пользуйтесь меню ниже для игры:", reply_markup=get_main_keyboard())


async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name)
    
    coins, packs, title = get_user_stats(user_id)
    cards = get_user_cards(user_id)
    
    cards_text = ""
    if not cards:
        cards_text = "У вас пока нет карт в коллекции. Откройте свой первый пак!"
    else:
        for name, rarity, count in cards:
            cards_text += f"• {name} ({rarity}) — {count} шт.\n"
            
    profile_text = (
        f"👤 *Профиль игрока {update.effective_user.first_name}*\n"
        f"🎖️ Титул: *{title}*\n"
        f"🪙 Баланс: {coins} монеток\n"
        f"📦 Открыто паков: {packs}\n\n"
        f"🗂️ *Ваша коллекция карт:*\n{cards_text}"
    )
    await update.message.reply_text(profile_text, parse_mode="Markdown", reply_markup=get_main_keyboard())


# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================
def main():
    threading.Thread(target=run_health_server, daemon=True).start()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(MessageHandler(filters.Text("📦 Открыть пак"), open_pack_handler))
    application.add_handler(MessageHandler(filters.Text("🛍️ Магазин титулов"), open_shop_handler))
    application.add_handler(MessageHandler(filters.Text("👤 Мой профиль"), profile_handler))
    
    application.add_handler(CallbackQueryHandler(shop_callback_handler))

    print("Бот успешно запущен и слушает обновления...")
    application.run_polling()

if __name__ == '__main__':
    main()
