import logging
import random
import os
import asyncio
import sqlite3
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Импортируем склад карт из соседнего файла cards.py (запятую в конце убрали)
from cards import CARDS

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

TOKEN = "8701989939:AAGZCFow7KKp9-0WdcEP-af826hVehG2Ck4"
ADMIN_ID = 7501899378
DB_FILE = "bot_database.db"


# ==================== ФУНКЦИИ РАБОТЫ С БАЗОЙ ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS users
                   (
                       user_id INTEGER PRIMARY KEY,
                       first_name TEXT,
                       coins INTEGER DEFAULT 0,
                       packs_opened INTEGER DEFAULT 0
                   )
                   ''')

    # Хак на случай старой БД: добавляем колонку, если её не было
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN packs_opened INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass

    # Таблица сохраненных карточек
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
    cursor.execute('SELECT coins, packs_opened FROM users WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res if res else (0, 0)


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


# ==================== ЛОГИКА РАНГОВ ====================
def get_rank(cards_count):
    if cards_count < 10:
        return "👶 Скиталец"
    elif cards_count < 100:
        return "🔰 Новичок"
    elif cards_count < 1000:
        return "⚔️ Профи"
    elif cards_count < 10000:
        return "👑 Владелец карт"
    elif cards_count < 50000:
        return "⚡ Бог карт"
    else:
        return "🌌 Абсолютное Божество DAcards"


# ==================== ЛОГИКА КОМАНД БОТА ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    register_user(user_id, first_name)

    keyboard = [
        ['🎁 Открыть пак', '🏪 Магазин-Обменник'],
        ['🗂 Моя коллекция', '🏆 Топ игроков'],
        ['👤 Профиль', '🧹 Сбросить прогресс']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"Привет, {first_name}! Рад видеть тебя в игре. Выбирай действие на кнопках ниже 👇",
        reply_markup=reply_markup
    )


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_cards = get_user_cards(user_id)
    total_cards = len(user_cards)

    coins, packs_opened = get_user_stats(user_id)
    rank = get_rank(total_cards)

    profile_text = (
        "━━━━━━━━━━━━━━\n"
        "👤 **ПРОФИЛЬ**\n\n"
        f"🗂 **Карт:** {total_cards}\n"
        f"💰 **Монет:** {coins}\n"
        f"🏆 **Ранг:** {rank}\n\n"
        f"📦 **Паков открыто:** {packs_opened}\n"
        "━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(profile_text, parse_mode="Markdown")


async def show_collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_cards = get_user_cards(user_id)

    if not user_cards:
        await update.message.reply_text("🗂 Твоя коллекция пока пуста. Открой пак! 🎁")
        return

    text = "🗂 **ТВОЯ КОЛЛЕКЦИЯ КАРТ:** [{card['rarity']}] — {card['price']} 🪙\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def open_pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    register_user(user_id, first_name)

    waiting_message = await update.message.reply_text("🃏 Открывается карта...")
    await asyncio.sleep(0.2)

    # Функция генерации редкости
    def get_random_card():
        rarity_roll = random.uniform(0, 100)
        if rarity_roll <= 0.1:
            rarity = "👑 Абсолютная"
        elif rarity_roll <= 1:
            rarity = "✨ Божественная"
        elif rarity_roll <= 10:
            rarity = "🔮 Секретная"
        elif rarity_roll <= 35:
            rarity = "⭐ Редкая"
        else:
            rarity = "⭐ Обычная"

        cards_of_rarity = [
            card for card in CARDS
            if card["rarity"].lower() == rarity.lower()
        ]

        if cards_of_rarity:
            return random.choice(cards_of_rarity)
        return random.choice(CARDS)

    # ВЫЗЫВАЕМ функцию, чтобы получить карту
    random_card = get_random_card()
    path_to_image = random_card.get("file")

    # Счётчик открытий в профиле увеличиваем в любом случае
    increment_packs(user_id)
    await waiting_message.delete()

    # ПРОВЕРКА НА ПУСТЫШКУ: Если цена 0 или в имени есть слово "пуста"
    if random_card['price'] == 0 or "пуста" in random_card['name'].lower():
        await update.message.reply_text(
            f"🃏 **Тебе выпала карта!**\n\n"
            f"😔 _Эта карта пуста, открой ещё..._"
        )
        return  # Конец для пустышки. Она НЕ сохранится в БД!

    # === ЕСЛИ КОД ПОШЕЛ ДАЛЬШЕ — ЗНАЧИТ ЭТО ХОРОШАЯ КАРТА ===
    add_card_to_db(user_id, random_card)

    # Проверяем вид картинки
    if str(path_to_image).startswith("AgAC"):
        await update.message.reply_photo(
            photo=path_to_image,
            caption=f"🃏 **Выпала карта:** {random_card['name']}\n💎 **Редкость:** {random_card['rarity']}"
        )
    else:
        try:
            with open(f"cards/{path_to_image}", "rb") as photo_file:
                await update.message.reply_photo(
                    photo=photo_file,
                    caption=f"🃏 **Выпала карта:** {random_card['name']}\n💎 **Редкость:** {random_card['rarity']}"
                )
        except FileNotFoundError:
            await update.message.reply_text(
                f"Выпала карта: {random_card['name']}, но картинка {path_to_image} не найдена на сервере."
            )


# ==================== ИНТЕРАКТИВНЫЙ МАГАЗИН ====================
async def shop_exchange(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_cards = get_user_cards(user_id)

    if not user_cards:
        await update.message.reply_text("🏪 В обменнике пусто. У тебя пока нет карт для продажи!")
        return

    card_counts = {}
    card_prices = {}
    for card in user_cards:
        name = card['name']
        card_counts[name] = card_counts.get(name, 0) + 1
        card_prices[name] = card['price']

    duplicates = {name: count for name, count in card_counts.items() if count > 1}

    if not duplicates:
        await update.message.reply_text(
            "🏪 **Магазин-Обменник:**\n\nУ тебя нет дубликатов! Карты в единственном экземпляре продать нельзя.")
        return

    first_card = list(duplicates.keys())[0]
    max_count = duplicates[first_card] - 1

    context.user_data['shop_card'] = first_card
    context.user_data['shop_count'] = 1
    context.user_data['shop_max'] = max_count
    context.user_data['shop_price'] = card_prices[first_card]

    await send_shop_message(update.message, first_card, 1, max_count, card_prices[first_card])


async def send_shop_message(message, card_name, current_count, max_count, price, is_edit=False):
    total_earned = current_count * price
    text = (
        f"🏪 **Магазин-Обменник дубликатов**\n\n"
        f"🃏 Карта: `{card_name}`\n"
        f"💰 Цена за шт: {price} 🪙\n\n"
        f"Выбрано для продажи: **{current_count}** из {max_count} шт.\n"
        f"💵 Итого вы получите: **{total_earned}** монет 🪙"
    )

    keyboard = [
        [
            InlineKeyboardButton("➖ 1", callback_data="shop_minus"),
            InlineKeyboardButton(f"Выбрано: {current_count} шт.", callback_data="none"),
            InlineKeyboardButton("➕ 1", callback_data="shop_plus")
        ],
        [
            InlineKeyboardButton("✅ Подтвердить продажу", callback_data="shop_confirm"),
            InlineKeyboardButton("❌ Отмена", callback_data="shop_cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if is_edit:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action = query.data
    card_name = context.user_data.get('shop_card')
    current_count = context.user_data.get('shop_count', 1)
    max_count = context.user_data.get('shop_max', 1)
    price = context.user_data.get('shop_price', 0)

    if not card_name:
        await query.message.edit_text("Сессия продажи завершена или устарела.")
        return

    if action == "shop_plus":
        if current_count < max_count:
            context.user_data['shop_count'] = current_count + 1
            await send_shop_message(query.message, card_name, current_count + 1, max_count, price, is_edit=True)

    elif action == "shop_minus":
        if current_count > 1:
            context.user_data['shop_count'] = current_count - 1
            await send_shop_message(query.message, card_name, current_count - 1, max_count, price, is_edit=True)

    elif action == "shop_cancel":
        context.user_data.clear()
        await query.message.edit_text("❌ Продажа отменена.")

    elif action == "shop_confirm":
        user_id = query.from_user.id
        total_earned = current_count * price

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute('''
                       DELETE FROM collections
                       WHERE id IN (SELECT id FROM collections
                                    WHERE user_id = ? AND card_name = ?
                                    LIMIT ?)
                       ''', (user_id, card_name, current_count))

        cursor.execute('UPDATE users SET coins = coins + ? WHERE user_id = ?', (total_earned, user_id))
        conn.commit()
        conn.close()

        context.user_data.clear()
        await query.message.edit_text(
            f"✅ **Успешная продажа!**\n\n"
            f"📦 Продано карт `{card_name}`: {current_count} шт.\n"
            f"💰 Получено монет: +{total_earned} 🪙"
        )


# ==================== ОСТАЛЬНЫЕ КОМАНДЫ ====================

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, coins FROM users WHERE coins > 0 ORDER BY coins DESC LIMIT 10')
    leaders = cursor.fetchall()
    conn.close()

    if not leaders:
        await update.message.reply_text("🏆 Топ пока пуст.")
        return

    text = "🏆 **ТАБЛИЦА БОГАЧЕЙ:**\n\n"
    for index, leader in enumerate(leaders):
        medal = "🥇" if index == 0 else "🥈" if index == 1 else "🥉" if index == 2 else f"{index + 1}."
        text += f"{medal} **{leader[0]}** — {leader[1]} 🪙\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def reset_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM collections WHERE user_id = ?', (user_id,))
    cursor.execute('UPDATE users SET coins = 0, packs_opened = 0 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text("🧹 Прогресс полностью сброшен!")


async def admin_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ У тебя нет доступа.")
        return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, coins FROM users')
    players = cursor.fetchall()
    conn.close()
    text = "📂 Игроки в БД:\n" + "\n".join([f"• {p[0]} — {p[1]} 🪙" for p in players])
    await update.message.reply_text(text)


#
