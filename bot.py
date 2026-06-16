import logging
import random
import os
import asyncio
import sqlite3
import threading  # Для фонового веб-сервера
from http.server import SimpleHTTPRequestHandler, HTTPServer # Для сервера
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ==================== СПИСОК КАРТ И ЦЕН ====================
REAL_CARDS = [
    {"file": "2.jpg", "name": "金 sunny🌲 김지ха | DA 🐂", "rarity": "🔮 Секретная", "price": 100},
    {"file": "5.jpg", "name": "Солнечный Самурай ☀️", "rarity": "⭐ Обычная", "price": 10},
    {"file": "4.jpg", "name": "Меха-Бык 🐂", "rarity": "⭐ Редкая", "price": 30},

    {"file": "1.jpg", "name": "👻losnya🐂🌲", "rarity": "🔮 Секретная", "price": 100},
    {"file": "7.jpg", "name": "Призрак Леса 👻", "rarity": "⭐ Редкая", "price": 30},
    {"file": "6.jpg", "name": "Таинственный Лось 🦌", "rarity": "⭐ Обычная", "price": 10},

    {"file": "3.jpg", "name": "Дониёр 🌲", "rarity": "🔮 Секретная", "price": 100},
    {"file": "9.jpg", "name": "Страж Дубравы 🌲", "rarity": "⭐ Обычная", "price": 10},
    {"file": "8.jpg", "name": "Лесной Хакер 💻", "rarity": "⭐ Редкая", "price": 30}
]

EMPTY_RESPONSES = [
    "Эта карта оказалась пустой... Открой ещё разок! 😔",
    "Эх, тут ничего не оказалось. Повезет в следующий раз! 💨",
    "Увы, пак пуст. Фортуна сегодня отдыхает 🃏",
    "Пустышка! Но не унывай, монеты целы — крути еще! 🪙"
]

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

# Рекомендуется использовать переменные окружения для безопасности
TOKEN = os.environ.get("BOT_TOKEN", "8701989939:AAG2z5cJ-kSkTe1k3OizAeTKHFc-OJ97Bfg")
ADMIN_ID = 7501899378
DB_FILE = "bot_database.db"


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


# ==================== РАБОТА С БАЗОЙ ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS users
                   (
                       user_id INTEGER PRIMARY KEY,
                       first_name TEXT,
                       coins INTEGER DEFAULT 0,
                       packs_opened INTEGER DEFAULT 0,
                       active_title TEXT DEFAULT 'Нет титула'
                   )
                   ''')
    
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN packs_opened INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN active_title TEXT DEFAULT 'Нет титула'")
    except sqlite3.OperationalError:
        pass

    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS collections
                   (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       user_id INTEGER,
                       card_name TEXT,
                       rarity TEXT,
                       file_name TEXT,
                       price INTEGER
                   )
                   ''')
    
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS titles
                   (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       user_id INTEGER,
                       title_id TEXT,
                       title_name TEXT,
                       UNIQUE(user_id, title_id)
                   )
                   ''')
    conn.commit()
    conn.close()


def register_user(user_id, first_name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
                   INSERT INTO users (user_id, first_name, coins)
                   VALUES (?, ?, 0) ON CONFLICT(user_id) DO
                   UPDATE SET first_name=excluded.first_name
                   ''', (user_id, first_name))
    conn.commit()
    conn.close()


def get_user_stats(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT coins, packs_opened, active_title FROM users WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res if res else (0, 0, "Нет титула")


def increment_packs(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET packs_opened = packs_opened + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()


def add_card_to_db(user_id, card):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
                   INSERT INTO collections (user_id, card_name, rarity, file_name, price)
                   VALUES (?, ?, ?, ?, ?)
                   ''', (user_id, card['name'], card['rarity'], card['file'], card['price']))
    conn.commit()
    conn.close()


def get_user_cards(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT card_name, rarity, file_name, price FROM collections WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"name": r[0], "rarity": r[1], "file": r[2], "price": r[3]} for r in rows]


def get_rank(packs_count):
    if packs_count < 10:
        return "👶 Скиталец"
    elif packs_count < 100:
        return "🔰 Новичок"
    elif packs_count < 1000:
        return "⚔️ Профи"
    elif packs_count < 10000:
        return "👑 Владелец карт"
    elif packs_count < 50000:
        return "⚡ Бог карт"
    else:
        return "🌌 Абсолютное Божество DAcards"


def get_owned_titles(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT title_id, title_name FROM titles WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}


def buy_title_db(user_id, title_id, title_name, price):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE users SET coins = coins - ? WHERE user_id = ? AND coins >= ?', (price, user_id, price))
        if cursor.rowcount > 0:
            cursor.execute('INSERT OR IGNORE INTO titles (user_id, title_id, title_name) VALUES (?, ?, ?)', (user_id, title_id, title_name))
            conn.commit()
            return True
        return False
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def set_active_title(user_id, title_name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET active_title = ? WHERE user_id = ?', (title_name, user_id))
    conn.commit()
    conn.close()


# ==================== ЛОГИКА БОТА ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    register_user(user_id, first_name)

    keyboard = [
        ['✨ Открыть пак ✨'],
        ['🗂 Моя Коллекция', '🏪 Магазин'],
        ['👤 Профиль', '🏆 Топ Игроков'],
        ['🧹 Сброс']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, input_field_placeholder="Выберите действие...")

    welcome_text = (
        "👑 **Добро пожаловать в мир DAcards!**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Рад приветствовать тебя, {first_name}! Испытай свою фортуну, "
        "собирай ценные карты, соревнуйся в топе и открывай легендарные префиксы.\n\n"
        "Выбери нужный раздел на панели управления ниже 👇"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_cards = get_user_cards(user_id)
    total_cards = len(user_cards)

    coins, packs_opened, active_title = get_user_stats(user_id)
    rank = get_rank(packs_opened)

    profile_text = (
        "💎 **ЛИЧНЫЙ ПРОФИЛЬ ИГРОКА**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚜️ **Статус-Титул:** {active_title}\n"
        f"🏆 **Ранг коллекции:** {rank}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 **Баланс монет:** {coins} 🪙\n"
        f"🗂 **Карт в наличии:** {total_cards} шт.\n"
        f"📦 **Открыто паков:** {packs_opened} шт.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(profile_text, parse_mode="Markdown")


async def show_collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_cards = get_user_cards(user_id)

    if not user_cards:
        await update.message.reply_text("🗂 **Твоя коллекция пока пуста.** Открой свой первый пак прямо сейчас! 🎁")
        return

    grouped_cards = {}
    for card in user_cards:
        name = card.get('name')
        file_name = card.get('file')
        
        if not name or name.strip() == "":
            found = False
            for rc in REAL_CARDS:
                if rc["file"] == file_name:
                    name = rc["name"]
                    found = True
                    break
            if not found:
                name = "Неизвестная карта 🃏"

        if name not in grouped_cards:
            grouped_cards[name] = {
                "rarity": card.get('rarity', 'Обычная'),
                "price": card.get('price', 0),
                "count": 0
            }
        grouped_cards[name]["count"] += 1

    text = "🗂 **ВАША СЛЕДСТВЕННАЯ КОЛЛЕКЦИЯ:**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    for idx, (name, info) in enumerate(grouped_cards.items(), 1):
        count_str = f" *(x{info['count']})*" if info['count'] > 1 else ""
        text += f"{idx}. **{name}**\n    └ 🏷️ {info['rarity']} | Стоимость: {info['price']} 🪙{count_str}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def open_pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    register_user(user_id, first_name)

    waiting_message = await update.message.reply_text("🪄 *Энергия рандома концентрируется...* \n🃏 Карта открывается...", parse_mode="Markdown")
    await asyncio.sleep(0.3)

    if random.random() <= 0.50:
        increment_packs(user_id)
        await waiting_message.delete()
        fail_text = random.choice(EMPTY_RESPONSES)
        await update.message.reply_text(f"💨 **Пусто!**\n\n{fail_text}")
        return

    def get_random_card():
        rarity_roll = random.uniform(0, 100)
        if rarity_roll <= 1.0:
            target_rarity = "🌌 Абсолютная"
        elif rarity_roll <= 7.0:
            target_rarity = "👑 Божественная"
        elif rarity_roll <= 20.0:
            target_rarity = "🔮 Секретная"
        elif rarity_roll <= 55.0:
            target_rarity = "⭐ Редкая"
        else:
            target_rarity = "⭐ Обычная"

        cards_of_rarity = [
            card for card in REAL_CARDS
            if card["rarity"].strip().lower() == target_rarity.strip().lower()
        ]
        if cards_of_rarity:
            return random.choice(cards_of_rarity)
        return random.choice(REAL_CARDS)

    random_card = get_random_card()
    path_to_image = random_card.get("file")

    increment_packs(user_id)
    await waiting_message.delete()

    add_card_to_db(user_id, random_card)

    caption_text = (
        "✨ **УСПЕШНОЕ ОТКРЫТИЕ ПАКА!** ✨\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🃏 **Название:** {random_card['name']}\n"
        f"💎 **Редкость:** {random_card['rarity']}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Карта добавлена в вашу личную коллекцию!"
    )

    if str(path_to_image).startswith("AgAC"):
        await update.message.reply_photo(photo=path_to_image, caption=caption_text, parse_mode="Markdown")
    else:
        try:
            with open(f"cards/{path_to_image}", "rb") as photo_file:
                await update.message.reply_photo(photo=photo_file, caption=caption_text, parse_mode="Markdown")
        except FileNotFoundError:
            await update.message.reply_text(f"Выпала карта: {random_card['name']}, но картинка {path_to_image} не найдена в папке cards/.")


# ==================== ПРОДВИНУТЫЙ МЕНЮ-МАГАЗИН ====================

async def main_shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🏪 **ЦЕНТРАЛЬНЫЙ МАГАЗИН DACARDS**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Добро пожаловать в торговый квартал! Выберите интересующее вас направление:\n\n"
        "🪙 **Сдать дубликаты** — продажа лишних копий карт за монеты.\n"
        "🏅 **Магазин титулов** — покупка статусных префиксов для профиля."
    )
    keyboard = [
        [InlineKeyboardButton("🪙 Сдать дубликаты", callback_data="mainshop_duplicates")],
        [InlineKeyboardButton("🏅 Магазин титулов", callback_data="mainshop_titles")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def shop_exchange_logic(user_id, message, context, is_callback=False):
    user_cards = get_user_cards(user_id)

    if not user_cards:
        msg = "🏪 **В обменнике пусто.** У вас пока нет карт для заключения торговых сделок!"
        if is_callback:
            await message.edit_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад в магазин", callback_data="mainshop_back")]]))
        else:
            await message.reply_text(msg)
        return False

    card_counts = {}
    card_prices = {}
    for card in user_cards:
        name = card['name'] or "Неизвестная карта 🃏"
        card_counts[name] = card_counts.get(name, 0) + 1
        card_prices[name] = card['price']

    duplicates = {name: count for name, count in card_counts.items() if count > 1}

    if not duplicates:
        msg = "🏪 **Торговая лавка дубликатов**\n\nУ вас отсутствуют копии карт. Карты в единственном экземпляре защищены от продажи!"
        if is_callback:
            await message.edit_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад в магазин", callback_data="mainshop_back")]]))
        else:
            await message.reply_text(msg)
        return False

    first_card = list(duplicates.keys())[0]
    max_count = duplicates[first_card] - 1

    # Исправлено: Записываем сессию прямо здесь во избежание KeyErrors
    context.user
