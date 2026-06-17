import logging
import random
import os
import asyncio
import time
import threading
from datetime import datetime, timedelta
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pymongo import MongoClient
from bson.objectid import ObjectId
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ==================== ТАБЛИЦА РЕДКОСТЕЙ С УРЕЗАННЫМИ ЦЕНАМИ ====================
REAL_CARDS_POOL = {
    "⚪ Обычная": [
        {"file": "5.jpg", "name": "Солнечный Самурай ☀️", "price": 2, "hp": 65, "atk": 13, "def": 5},
        {"file": "6.jpg", "name": "Таинственный Лось 🦌", "price": 3, "hp": 75, "atk": 14, "def": 6}
    ],
    "🟢 Необычная": [
        {"file": "9.jpg", "name": "Страж Дубравы 🌲", "price": 5, "hp": 90, "atk": 18, "def": 8}
    ],
    "🔵 Редкая": [
        {"file": "4.jpg", "name": "Меха-Бык 🐂", "price": 10, "hp": 110, "atk": 24, "def": 12},
        {"file": "7.jpg", "name": "Призрак Леса 👻", "price": 12, "hp": 105, "atk": 26, "def": 11}
    ],
    "🟣 Эпическая": [
        {"file": "8.jpg", "name": "Лесной Хакер 💻", "price": 20, "hp": 145, "atk": 32, "def": 15}
    ],
    "🟠 Легендарная": [
        {"file": "2.jpg", "name": "👻losnya🐂🌲", "price": 35, "hp": 200, "atk": 42, "def": 20}
    ],
    "🔴 Мифическая": [
        {"file": "3.jpg", "name": "Дониёр 🌲", "price": 55, "hp": 270, "atk": 55, "def": 26}
    ],
    "✨ Древняя": [
        {"file": "1.jpg", "name": "金 sunny🌲 김지ха | DA 🐂", "price": 90, "hp": 390, "atk": 72, "def": 36}
    ],
    "💎 Секретная": [
        {"file": "10.jpg", "name": "𝒎𝒐𝒐𝒏🌳", "price": 150, "hp": 500, "atk": 92, "def": 48}
    ],
    "🌟 Божественная": [
        {"file": "10.jpg", "name": "Божественный Аспект Муравья 👑", "price": 300, "hp": 720, "atk": 135, "def": 62}
    ],
    "👑 Эксклюзивная": [
        {"file": "1.jpg", "name": "👑 Абсолютный Оверлорд Колонии", "price": 1000, "hp": 1150, "atk": 200, "def": 95}
    ]
}

# Стоимость улучшения карты в зависимости от её редкости
UPGRADE_CARD_COSTS = {
    "⚪ Обычная": 25, "🟢 Необычная": 45, "🔵 Редкая": 80, "🟣 Эпическая": 150,
    "🟠 Легендарная": 300, "🔴 Мифическая": 500, "✨ Древняя": 900, "💎 Секретная": 1500,
    "🌟 Божественная": 3000, "👑 Эксклюзивная": 6000
}

EMPTY_RESPONSES = [
    "Эта карта оказалась пустой... Открой ещё разок! 😔",
    "Эх, тут ничего не оказалось. Повезет в следующий раз! 💨",
    "Увы, пак пуст. Фортуна сегодня отдыхает 🃏"
]

SHOP_TITLES = {
    "title_collector": {"name": "🕶️ Коллекционер", "price": 100},
    "title_rich": {"name": "💵 Магнат DAcards", "price": 350},
    "title_lucky": {"name": "🍀 Любимчик Фортуны", "price": 700},
    "title_legend": {"name": "🦅 Легенда Леса", "price": 1500},
    "title_overlord": {"name": "🌌 Повелитель Рандома", "price": 3000}
}

PROFILE_THEMES = {
    "default": {"name": "🐜 Стандартный Муравейник", "price": 0},
    "beehive": {"name": "🐝 Золотой Улей", "price": 150},
    "anthill_neon": {"name": "🔮 Кибер-Гнездо (Неон)", "price": 500}
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN", "8701989939:AAG2z5cJ-kSkTe1k3OizAeTKHFc-OJ97Bfg")

COOLDOWNS = {}
COOLDOWN_TIME = 1.5 

def get_main_keyboard():
    buttons = [
        ["📦 Открыть пак", "👤 Профиль", "🗂️ Коллекция"],
        ["⚔️ Походы & Битвы", "🚀 Прокачка & Крафт"],
        ["🎲 Удача & Квесты", "🛍️ Магазин", "🎁 Бонусы & Донат"]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# ==================== MONGODB СВЯЗЬ ====================
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://tananyandavid5_db_user:7dmj6rMlquxr19c8@david2010.wlbyl1j.mongodb.net/?retryWrites=true&w=majority&appName=David2010")
client = MongoClient(MONGO_URI)
db = client["cards_bot_database"]
users_col = db["users"]
collections_col = db["collections"]

battle_sessions = {} 

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server_address = ("", port)
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args): pass
    httpd = HTTPServer(server_address, QuietHandler)
    httpd.serve_forever()

# ==================== СИСТЕМА ИГРОКОВ ====================
def register_user(user_id, first_name, username=None):
    update_data = {"first_name": first_name}
    if username: update_data["username"] = username

    users_col.update_one(
        {"user_id": user_id},
        {
            "$set": update_data,
            "$setOnInsert": {
                "coins": 100, 
                "packs_opened": 0, 
                "active_title": "Нет титула", 
                "owned_titles": ["Нет титула"],
                "joined_at": datetime.utcnow().isoformat(),
                "colony_level": 1, 
                "bank_deposit": 0, 
                "profile_theme": "default", 
                "owned_themes": ["default"],
                "pvp_wins": 0,
                "last_wheel_time": 0,
                "last_arena_time": 0,
                "expedition_start_time": 0,
                "expedition_active": False
            }
        },
        upsert=True
    )

def get_user_all_data(user_id):
    return users_col.find_one({"user_id": user_id})

def update_user_coins(user_id, amount):
    users_col.update_one({"user_id": user_id}, {"$inc": {"coins": amount}})

def get_user_cards(user_id):
    return list(collections_col.find({"user_id": user_id}))

def add_card_to_db(user_id, card):
    collections_col.insert_one({
        "user_id": user_id, 
        "card_name": card['name'], 
        "rarity": card['rarity'],
        "file_name": card['file'], 
        "price": card['price'],
        "hp": card['hp'],
        "atk": card['atk'],
        "def": card['def'],
        "level": card.get('level', 1)
    })

def get_upgrade_cost(current_level):
    return int(150 * (current_level ** 1.8))

# ==================== МЕНЮ ОТКРЫТИЯ ПАКОВ ====================
async def open_pack_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    
    current_time = time.time()
    if user_id in COOLDOWNS and (current_time - COOLDOWNS[user_id] < COOLDOWN_TIME):
        await update.message.reply_text(f"⏳ Пакеты охлаждаются! Подождите немного.")
        return
    COOLDOWNS[user_id] = current_time
    
    rarities = ["🗑️ Пустышка", "⚪ Обычная", "🟢 Необычная", "🔵 Редкая", "🟣 Эпическая", "🟠 Легендарная", "🔴 Мифическая", "✨ Древняя", "💎 Секретная", "🌟 Божественная", "👑 Эксклюзивная"]
    weights = [55.0, 35.0, 25.0, 15.0, 10.0, 5.0, 3.0, 1.0, 0.8, 0.5, 0.01]
    
    chosen_rarity = random.choices(rarities, weights=weights, k=1)[0]
    users_col.update_one({"user_id": user_id}, {"$inc": {"packs_opened": 1}})
    
    if chosen_rarity == "🗑️ Пустышка":
        await update.message.reply_text(random.choice(EMPTY_RESPONSES))
    else:
        card_data = random.choice(REAL_CARDS_POOL[chosen_rarity])
        dropped_card = {
            "file": card_data["file"], "name": card_data["name"], "rarity": chosen_rarity,
            "price": card_data["price"], "hp": card_data["hp"], "atk": card_data["atk"], "def": card_data["def"],
            "level": 1
        }
        
        add_card_to_db(user_id, dropped_card)
        update_user_coins(user_id, dropped_card['price'])
        
        path_to_image = f"cards/{dropped_card['file']}"
        caption_text = (
            f"🎉 **ВЫПАЛА КАРТА!** 🎉\n\n"
            f"👤 Название: *{dropped_card['name']}*\n"
            f"✨ Редкость: *{dropped_card['rarity']}*\n"
            f"⭐ Уровень: `1`⭐\n"
            f"❤️ HP: `{dropped_card['hp']}` | ⚔️ ATK: `{dropped_card['atk']}` | 🛡️ DEF: `{dropped_card['def']}`\n\n"
            f"🪙 Продажа в банк: +*{dropped_card['price']}* 🪙"
        )
        if os.path.exists(path_to_image):
            await update.message.reply_photo(photo=open(path_to_image, 'rb'), caption=caption_text, parse_mode="Markdown")
        else:
            await update.message.reply_text(caption_text, parse_mode="Markdown")

# ==================== ОСНОВНЫЕ ТЕКСТОВЫЕ КНОПКИ ====================
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    await update.message.reply_text("🐜 Симулятор Карточных Колоний запущен! Управляй своей империей:", reply_markup=get_main_keyboard())

async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    ud = get_user_all_data(user_id)
    theme_name = PROFILE_THEMES.get(ud.get("profile_theme", "default"), PROFILE_THEMES["default"])["name"]
    
    profile_text = (
        f"👤 *Профиль: {update.effective_user.first_name}*\n"
        f"🌐 Локация: *{theme_name}*\n"
        f"🎖️ Титул: *{ud.get('active_title', 'Нет титула')}*\n"
        f"🚀 Уровень Эволюции: *{ud.get('colony_level', 1)}*\n"
        f"🪙 Баланс: {ud.get('coins')} 🪙\n"
        f"🏦 В Сбережениях: {ud.get('bank_deposit', 0)} 🪙\n"
        f"⚔️ Побед на Арене: {ud.get('pvp_wins', 0)}\n"
        f"📦 Всего открыто паков: {ud.get('packs_opened')}\n"
    )
    await update.message.reply_text(profile_text, parse_mode="Markdown")

async def collection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cards = get_user_cards(user_id)
    if not cards:
        await update.message.reply_text("🗂️ Твоя коллекция пока пуста. Открой свой первый пак!")
        return
    text = "🗂️ *ТВОЙ ИНВЕНТАРЬ КАРТ С ХАРАКТЕРИСТИКАМИ:*\n\n"
    for c in cards:
        lvl = c.get('level', 1)
        text += f"• *{c['card_name']}* [Ур. {lvl}] ({c.get('rarity', '⚪ Обычная')}) — [⚔️{c.get('atk', 15)} 🛡️{c.get('def', 5)} ❤️{c.get('hp', 60)}]\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ==================== ХАБЫ УПРАВЛЕНИЯ ИГРОЙ ====================
async def pvp_and_expeditions_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "⚔️ *ВОЕННЫЙ ШТАБ КОЛОНИИ* 🗺️\n\n"
        "🗺️ *Экспедиция (Поход)* длится **2 минуты**. Вы можете отменить поход в любой момент, но тогда награда будет потеряна."
    )
    kb = [[InlineKeyboardButton("🗺️ Управление Походом (Экспедиция)", callback_data="hub_expedition")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def upgrade_and_craft_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ud = get_user_all_data(user_id)
    lvl = ud.get("colony_level", 1)
    cost = get_upgrade_cost(lvl)
    text = (
        f"🚀 *ЛАБОРАТОРИЯ ЭВОЛЮЦИИ И МОДИФИКАЦИИ*\n\n"
        f"🧬 Уровень колонии: *{lvl}* (Мутация: {cost} 🪙)\n\n"
        f"📈 *Улучшение Карт:* Тратьте монеты, чтобы повысить характеристики ваших насекомых на +20%!"
    )
    kb = [
        [InlineKeyboardButton(f"🧬 Повысить уровень ({cost} 🪙)", callback_data="buy_colony_upgrade")],
        [InlineKeyboardButton("📈 Улучшить характеристики карт", callback_data="menu_card_upgrade_list")],
        [InlineKeyboardButton("🔮 Войти в Крафт-Машину", callback_data="menu_craft")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def lucky_and_quests_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎲 *ИГРОВАЯ ЗОНА И ИСПЫТАНИЯ* 📜\n\n"
        "⚠️ *Внимание:* На Колесо Фортуны и Арену установлен жесткий кулдаун в **2 минуты**!"
    )
    kb = [
        [InlineKeyboardButton("🎡 Колесо Фортуны", callback_data="menu_wheel"),
         InlineKeyboardButton("🏟️ Арена Карт (Интерактивная)", callback_data="menu_card_arena")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def shop_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🛍️ *ТОРГОВАЯ ЛАВКА КОЛОНИИ*"
    kb = [
        [InlineKeyboardButton("💰 Сдача дубликатов", callback_data="shop_sell_duplicates")],
        [InlineKeyboardButton("🎖️ Магазин Титулов", callback_data="shop_titles_menu")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def bonuses_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🎁 *ЦЕНТР РАЗВИТИЯ КОЛОНИИ* 💎"
    kb = [
        [InlineKeyboardButton("🏦 Муравьиный Банк", callback_data="menu_bank"),
         InlineKeyboardButton("🎨 Кастомизация", callback_data="menu_themes_list")],
        [InlineKeyboardButton("💎 донат тут", url="https://t.me/davit2010yt")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


# ==================== ИНЛАЙН ОБРАБОТЧИК (ОСНОВНАЯ ЛОГИКА) ====================
async def main_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    ud = get_user_all_data(user_id)
    if not ud: return

    now = time.time()

    # ==================== МЕХАНИКА УЛУЧШЕНИЯ КАРТ ====================
    if data == "menu_card_upgrade_list":
        cards = get_user_cards(user_id)
        if not cards:
            await query.message.reply_text("❌ У вас нет карт для улучшения.")
            return
        
        text = "📈 *ВЫБЕРИТЕ КАРТУ ДЛЯ УЛУЧШЕНИЯ (+20% к статам):*\n"
        kb = []
        for c in cards:
            rarity = c.get("rarity", "⚪ Обычная")
            cost = UPGRADE_CARD_COSTS.get(rarity, 50)
            lvl = c.get("level", 1)
            kb.append([InlineKeyboardButton(f"{c['card_name']} [Ур.{lvl}] — {cost} 🪙", callback_data=f"upcard_{c['_id']}")])
        
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data.startswith("upcard_"):
        card_id = data.replace("upcard_", "")
        card = collections_col.find_one({"_id": ObjectId(card_id), "user_id": user_id})
        if not card:
            await query.message.reply_text("❌ Карта не найдена.")
            return
        
        rarity = card.get("rarity", "⚪ Обычная")
        cost = UPGRADE_CARD_COSTS.get(rarity, 50)
        
        if ud.get("coins", 0) < cost:
            await query.message.reply_text(f"❌ Недостаточно монет! Улучшение этой карты стоит {cost} 🪙.")
            return
            
        # Рассчитываем прирост +20%
        new_hp = int(card.get("hp", 50) * 1.2)
        new_atk = int(card.get("atk", 10) * 1.2)
        new_def = int(card.get("def", 5) * 1.2)
        new_lvl = card.get("level", 1) + 1
        
        # Обновляем в БД
        collections_col.update_one(
            {"_id": ObjectId(card_id)},
            {"$set": {"hp": new_hp, "atk": new_atk, "def": new_def, "level": new_lvl}}
        )
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -cost}})
        
        await query.message.reply_text(
            f"🔥 **УСПЕШНОЕ УЛУЧШЕНИЕ!** 🔥\n\n"
            f"🐜 Карта: *{card['card_name']}*\n"
            f"⭐ Новый уровень: `{new_lvl}` ⭐\n"
            f"❤️ HP: {card.get('hp')} ➡️ `{new_hp}`\n"
            f"⚔️ ATK: {card.get('atk')} ➡️ `{new_atk}`\n"
            f"🛡️ DEF: {card.get('def')} ➡️ `{new_def}`\n\n"
            f"Списано: -{cost} 🪙"
        , parse_mode="Markdown")
        return

    # ==================== КОЛЕCО ФОРТУНЫ ====================
    elif data == "menu_wheel":
        last_wheel = ud.get("last_wheel_time", 0)
        passed = now - last_wheel
        if passed < 120:
            await query.message.reply_text(f"⏳ Колесо Фортуны остывает. Подождите еще `{int(120 - passed)}` сек.", parse_mode="Markdown")
            return
        if ud.get("coins", 0) < 30:
            await query.message.reply_text("❌ Не хватает 30 🪙.")
            return

        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -30}, "$set": {"last_wheel_time": now}})
        win = random.choices([0, 10, 25, 60, 150], weights=[40, 30, 15, 10, 5])[0]
        update_user_coins(user_id, win)
        await query.message.reply_text(f"🎡 Выигрыш: *{win}* 🪙!", parse_mode="Markdown")
        return

    # ==================== ЛОГИКА ПОХОДОВ ====================
    elif data == "hub_expedition":
        is_active = ud.get("expedition_active", False)
        if not is_active:
            text = "🗺️ *ВАШ ОТРЯД В КАЗАРМАХ*\n\nВы можете отправить муравьев в поход на **2 минуты** за сокровищами."
            kb = [[InlineKeyboardButton("🚀 Отправиться в Поход", callback_data="expedition_start")]]
        else:
            start_time = ud.get("expedition_start_time", 0)
            elapsed = now - start_time
            if elapsed >= 120:
                text = "🎉 *ПОХОД ЗАВЕРШЕН!* \nЗаберите награду!"
                kb = [[InlineKeyboardButton("💰 Забрать Добычу", callback_data="expedition_claim")]]
            else:
                text = f"🗺️ *ОТРЯД В ПУТИ*\nОсталось: `{int(120 - elapsed)}` сек.\n\nВы можете отменить поход, но награда сгорит."
                kb = [
                    [InlineKeyboardButton("🔄 Проверить Статус", callback_data="hub_expedition")],
                    [InlineKeyboardButton("❌ Отменить Поход", callback_data="expedition_cancel")]
                ]
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data == "expedition_start":
        if ud.get("expedition_active", False): return
        users_col.update_one({"user_id": user_id}, {"$set": {"expedition_active": True, "expedition_start_time": now}})
        await query.message.reply_text("🚀 Отряд выдвинулся в поход! Возвращение через 2 минуты.")
        return

    elif data == "expedition_cancel":
        if not ud.get("expedition_active", False): return
        users_col.update_one({"user_id": user_id}, {"$set": {"expedition_active": False, "expedition_start_time": 0}})
        await query.message.reply_text("❌ Поход отменен! Награда потеряна.")
        return

    elif data == "expedition_claim":
        if not ud.get("expedition_active", False): return
        start_time = ud.get("expedition_start_time", 0)
        if now - start_time < 120: return
        
        reward = random.randint(20, 45) + (ud.get("colony_level", 1) * 3)
        users_col.update_one({"user_id": user_id}, {"$set": {"expedition_active": False, "expedition_start_time": 0}})
        update_user_coins(user_id, reward)
        await query.message.reply_text(f"💰 Из похода принесено +{reward} 🪙")
        return

    # ==================== АРЕНА (ОСЛАБЛЕННЫЕ ПРОТИВНИКИ) ====================
    elif data == "menu_card_arena":
        last_arena = ud.get("last_arena_time", 0)
        passed = now - last_arena
        if passed < 120:
            await query.message.reply_text(f"⏳ Кулдаун Арены: `{int(120 - passed)}` сек.", parse_mode="Markdown")
            return
        if ud.get("coins", 0) < 20:
            await query.message.reply_text("❌ Вход стоит 20 🪙.")
            return

        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -20}, "$set": {"last_arena_time": now}})
        
        user_cards = get_user_cards(user_id)
        if user_cards:
            my_card = random.choice(user_cards)
            p_name, p_hp, p_atk, p_def = my_card["card_name"], my_card.get("hp", 65), my_card.get("atk", 13), my_card.get("def", 5)
        else:
            p_name, p_hp, p_atk, p_def = "🐜 Муравей-Рядовой", 65, 13, 5

        # НАСТРОЙКА СЛАБЫХ ВРАГОВ ПО ТВОЕМУ ЗАПРОСУ: HP=65, DEF=30, ATK=35
        b_name = random.choice(["🦟 Ослабленный Комар", "🐝 Сонный Шершень", "🕷️ Хрупкий Паучок"])
        b_hp = 65
        b_atk = 35
        b_def = 30

        battle_sessions[user_id] = {
            "p_name": p_name, "p_hp": p_hp, "p_atk": p_atk, "p_def": p_def,
            "b_name": b_name, "b_hp": b_hp, "b_atk": b_atk, "b_def": b_def,
            "round": 1
        }

        text = (
            f"🏟️ *НАЧАЛО БОЯ (Враги ослаблены!)*\n\n"
            f"🟢 *Ты:* {p_name} [❤️{p_hp} HP | ⚔️{p_atk} | 🛡️{p_def}]\n"
            f"🔴 *Враг:* {b_name} [❤️{b_hp} HP | ⚔️{b_atk} | 🛡️{b_def}]\n\n"
            f"Управляйте поединком:"
        )
        kb = [
            [InlineKeyboardButton("⚔️ Сделать Ход", callback_data="arena_action_hit")],
            [InlineKeyboardButton("🏳️ Сдаться", callback_data="arena_action_surrender")]
        ]
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data.startswith("arena_action_"):
        if user_id not in battle_sessions: return
        session = battle_sessions[user_id]
        action = data.replace("arena_action_", "")

        if action == "surrender":
            del battle_sessions[user_id]
            await query.message.reply_text("🏳️ Вы сбежали с поля боя!")
            return

        if action == "hit":
            # Твой урон по боссу
            dmg_to_boss = max(1, session["p_atk"] - session["b_def"])
            session["b_hp"] -= dmg_to_boss
            log = f"🥊 *Раунд {session['round']}:*\nВы нанесли врагу `{dmg_to_boss}` урона.\n"

            if session["b_hp"] <= 0:
                reward = random.randint(25, 50) + (ud.get("colony_level", 1) * 5)
                update_user_coins(user_id, reward)
                users_col.update_one({"user_id": user_id}, {"$inc": {"pvp_wins": 1}})
                await query.message.reply_text(f"{log}\n🎉 *ПОБЕДА!* {session['b_name']} повержен!\nНаграда: +*{reward}* 🪙", parse_mode="Markdown")
                del battle_sessions[user_id]
                return

            # Контратака ослабленного босса
            dmg_to_player = max(1, session["b_atk"] - session["p_def"])
            session["p_hp"] -= dmg_to_player
            log += f"💥 Противник наносит в ответ `{dmg_to_player}` урона.\n"

            if session["p_hp"] <= 0:
                await query.message.reply_text(f"{log}\n💀 *ПОРАЖЕНИЕ!* Твоя карта повержена.", parse_mode="Markdown")
                del battle_sessions[user_id]
                return

            session["round"] += 1
            if session["round"] > 10:
                await query.message.reply_text("⏳ Ничья!")
                del battle_sessions[user_id]
                return

            status_text = f"{log}\n🟢 *Вы:* ❤️ `{session['p_hp']}` HP\n🔴 *Враг:* ❤️ `{session['b_hp']}` HP"
            kb = [
                [InlineKeyboardButton("⚔️ Сделать Следующий Ход", callback_data="arena_action_hit")],
                [InlineKeyboardButton("🏳️ Сдаться", callback_data="arena_action_surrender")]
            ]
            await query.message.reply_text(status_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
            return

    # ==================== ОСТАЛЬНЫЕ МЕНЮ СИСТЕМЫ ====================
    elif data == "shop_sell_duplicates":
        cards = get_user_cards(user_id)
        counts = {}
        for c in cards: counts[c['card_name']] = counts.get(c['card_name'], []) + [c]
        total_earnings, sold_count = 0, 0
        for name, card_list in counts.items():
            if len(card_list) > 1:
                for duplicate in card_list[1:]:
                    collections_col.delete_one({"_id": duplicate["_id"]})
                    total_earnings += duplicate.get("price", 2)
                    sold_count += 1
        if sold_count > 0:
            update_user_coins(user_id, total_earnings)
            await query.message.reply_text(f"💰 Продано дубликатов: {sold_count} шт. Получено: +{total_earnings} 🪙")
        else:
            await query.message.reply_text("🔍 Повторяющихся карт не найдено.")
        return

    elif data == "shop_titles_menu":
        text = "🎖️ *МАГАЗИН ВНУТРИИГРОВЫХ ТИТУЛОВ:*"
        kb = []
        owned_titles = ud.get("owned_titles", ["Нет титула"])
        for tid, tinfo in SHOP_TITLES.items():
            status = " (Куплен)" if tinfo["name"] in owned_titles else f" — {tinfo['price']} 🪙"
            kb.append([InlineKeyboardButton(f"{tinfo['name']}{status}", callback_data=f"buy_title_{tid}")])
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data.startswith("buy_title_"):
        tid = data.replace("buy_title_", "")
        title_info = SHOP_TITLES[tid]
        owned_titles = ud.get("owned_titles", ["Нет титула"])
        if title_info["name"] in owned_titles:
            users_col.update_one({"user_id": user_id}, {"$set": {"active_title": title_info["name"]}})
            await query.message.reply_text(f"✅ Титул *{title_info['name']}* активирован!", parse_mode="Markdown")
        else:
            if ud.get("coins", 0) < title_info["price"]:
                await query.message.reply_text("❌ Недостаточно монет.")
            else:
                users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -title_info["price"]}, "$addToSet": {"owned_titles": title_info["name"]}, "$set": {"active_title": title_info["name"]}})
                await query.message.reply_text(f"🎉 Куплен титул *{title_info['name']}*!", parse_mode="Markdown")
        return

    elif data == "buy_colony_upgrade":
        lvl = ud.get("colony_level", 1)
        cost = get_upgrade_cost(lvl)
        if ud.get("coins", 0) < cost: 
            await query.message.reply_text("❌ Недостаточно монет.")
            return
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -cost, "colony_level": 1}})
        await query.message.reply_text(f"🧬 Эволюция колонии повышена до уровня *{lvl + 1}*!")
        return

    elif data == "menu_craft":
        cards = get_user_cards(user_id)
        if len(cards) < 3: 
            await query.message.reply_text("❌ Нужно минимум 3 карты.")
            return
        for bc in cards[:3]: collections_col.delete_one({"_id": bc["_id"]})
        available_rarities = list(REAL_CARDS_POOL.keys())
        chosen_r = random.choice(available_rarities)
        new_card = random.choice(REAL_CARDS_POOL[chosen_r])
        final_card = {**new_card, "rarity": chosen_r, "level": 1}
        add_card_to_db(user_id, final_card)
        await query.message.reply_text(f"🔥 Синтезирован боец: *{final_card['name']}*!")
        return

    elif data == "menu_bank":
        dep = ud.get("bank_deposit", 0)
        text = f"🏦 *БАНК ГНЕЗДА*\nВклад: *{dep} 🪙*"
        kb = []
        if ud.get("coins", 0) >= 20: kb.append([InlineKeyboardButton("💰 Положить 20 🪙", callback_data="bank_deposit_100")])
        if dep >= 20: kb.append([InlineKeyboardButton("💸 Снять 20 🪙", callback_data="bank_withdraw_100")])
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data == "bank_deposit_100":
        if ud.get("coins", 0) < 20: return
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -20, "bank_deposit": 20}})
        await query.message.reply_text("✅ Вклад пополнен.")
        return

    elif data == "bank_withdraw_100":
        if ud.get("bank_deposit", 0) < 20: return
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": 20, "bank_deposit": -20}})
        await query.message.reply_text("✅ Монеты сняты.")
        return

    elif data == "menu_themes_list":
        owned = ud.get("owned_themes", ["default"])
        kb = []
        for key, info in PROFILE_THEMES.items():
            status = " (Куплено)" if key in owned else f" — {info['price']} 🪙"
            kb.append([InlineKeyboardButton(f"{info['name']}{status}", callback_data=f"theme_act_{key}")])
        await query.message.reply_text("🎨 Стиль локации:", reply_markup=InlineKeyboardMarkup(kb))
        return

    elif data.startswith("theme_act_"):
        th_key = data.replace("theme_act_", "")
        owned = ud.get("owned_themes", ["default"])
        if th_key in owned:
            users_col.update_one({"user_id": user_id}, {"$set": {"profile_theme": th_key}})
            await query.message.reply_text("✨ Стиль профиля обновлен!")
        else:
            price = PROFILE_THEMES[th_key]["price"]
            if ud.get("coins", 0) < price: return
            users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -price}, "$addToSet": {"owned_themes": th_key}, "$set": {"profile_theme": th_key}})
            await query.message.reply_text("🎉 Приобретено!")
        return

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Используйте меню кнопок для управления.")

# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================
def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(MessageHandler(filters.Text("📦 Открыть пак"), open_pack_handler))
    application.add_handler(MessageHandler(filters.Text("👤 Профиль"), profile_handler))
    application.add_handler(MessageHandler(filters.Text("🗂️ Коллекция"), collection_handler))
    
    application.add_handler(MessageHandler(filters.Text("⚔️ Походы & Битвы"), pvp_and_expeditions_main_handler))
    application.add_handler(MessageHandler(filters.Text("🚀 Прокачка & Крафт"), upgrade_and_craft_main_handler))
    application.add_handler(MessageHandler(filters.Text("🎲 Удача & Квесты"), lucky_and_quests_main_handler))
    application.add_handler(MessageHandler(filters.Text("🛍️ Магазин"), shop_main_handler))
    application.add_handler(MessageHandler(filters.Text("🎁 Бонусы & Донат"), bonuses_main_handler))
    
    application.add_handler(CallbackQueryHandler(main_callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    application.run_polling()

if __name__ == '__main__':
    main()
