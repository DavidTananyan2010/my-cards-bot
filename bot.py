import logging
import random
import os
import asyncio
import time
import threading
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pymongo import MongoClient
from bson.objectid import ObjectId
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ==================== ТАБЛИЦА РЕДКОСТЕЙ (КОМПАКТНАЯ) ====================
REAL_CARDS_POOL = {
    "⚪ Обычная": [
        {"file": "5.jpg", "name": "Солнечный Самурай ☀️", "price": 2, "hp": 65, "atk": 13, "def": 5}
    ],
    "🟢 Необычная": [
        {"file": "6.jpg", "name": "Таинственный Лось 🦌", "price": 4, "hp": 75, "atk": 15, "def": 6},
        {"file": "9.jpg", "name": "Страж Дубравы 🌲", "price": 6, "hp": 90, "atk": 18, "def": 8}
    ],
    "🔵 Редкая": [
        {"file": "4.jpg", "name": "Меха-Бык 🐂", "price": 12, "hp": 110, "atk": 24, "def": 12}
    ],
    "🟣 Эпическая": [
        {"file": "7.jpg", "name": "Призрак Леса 👻", "price": 18, "hp": 125, "atk": 28, "def": 13}
    ],
    "🟠 Легендарная": [
        {"file": "8.jpg", "name": "Лесной Хакер 💻", "price": 30, "hp": 155, "atk": 35, "def": 16}
    ],
    "🔴 Мифическая": [
        {"file": "2.jpg", "name": "👻losnya🐂🌲", "price": 50, "hp": 210, "atk": 45, "def": 22}
    ],
    "✨ Древняя": [
        {"file": "3.jpg", "name": "Дониёр 🌲", "price": 85, "hp": 290, "atk": 58, "def": 28}
    ],
    "💎 Секретная": [
        {"file": "1.jpg", "name": "金 sunny🌲 김지ха | DA 🐂", "price": 140, "hp": 410, "atk": 75, "def": 38}
    ],
    "🌟 Божественная": [
        {"file": "10.jpg", "name": "𝒎𝒐𝒐𝒏🌳", "price": 250, "hp": 550, "atk": 100, "def": 52}
    ],
    "👑 Эксклюзивная": [
        {"file": "10.jpg", "name": "Божественный Аспект Муравья 👑", "price": 500, "hp": 800, "atk": 150, "def": 70},
        {"file": "1.jpg", "name": "👑 Абсолютный Оверлорд Колонии", "price": 1200, "hp": 1200, "atk": 220, "def": 100}
    ]
}

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
promo_col = db["promocodes"]

battle_sessions = {} 

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server_address = ("", port)
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args): pass
    httpd = HTTPServer(server_address, QuietHandler)
    httpd.serve_forever()

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

def init_promo_db():
    if not promo_col.find_one({"code": "cosmo"}):
        promo_col.insert_one({
            "code": "cosmo", "uses": 0, "max_uses": 25, "users_activated": []
        })

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
    weights = [50.0, 35.0, 25.0, 15.0, 10.0, 5.0, 3.0, 1.5, 0.8, 0.4, 0.05]
    
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

# ==================== ПРОФИЛЬ ====================
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    await update.message.reply_text("🐜 Симулятор Карточных Колоний запущен!", reply_markup=get_main_keyboard())

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

# ==================== МОДЕРНИЗИРОВАННАЯ КОМПАКТНАЯ КОЛЛЕКЦИЯ ====================
async def collection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cards = get_user_cards(user_id)
    if not cards:
        await update.message.reply_text("🗂️ Твоя коллекция пока пуста. Открой свой первый пак!")
        return
        
    # Группируем карты по ключу (Имя + Уровень), чтобы различать прокачанные и дубликаты
    grouped_cards = {}
    for c in cards:
        key = (c['card_name'], c.get('level', 1))
        if key not in grouped_cards:
            grouped_cards[key] = []
        grouped_cards[key].append(c)

    text = "🗂️ *ТВОЯ КОМПАКТНАЯ КОЛЛЕКЦИЯ:*\nДубликаты сгруппированы. Выберите карту для просмотра или продажи."
    kb = []
    
    for (name, level), list_of_copies in grouped_cards.items():
        count = len(list_of_copies)
        # Берем ID первой карты из пачки для привязки к кнопке
        representative_id = list_of_copies[0]["_id"]
        
        # Если карт больше одной, пишем красивое окончание (xЦифра)
        display_count = f" (x{count})" if count > 1 else ""
        button_text = f"{name} [Ур. {level}]{display_count}"
        
        kb.append([InlineKeyboardButton(button_text, callback_data=f"inspect_card_{representative_id}")])
        
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# ==================== ОСТАЛЬНЫЕ ХАБЫ И МЕНЮ ====================
async def pvp_and_expeditions_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "⚔️ *ВОЕННЫЙ ШТАБ КОЛОНИИ* 🗺️\n\n🗺️ *Экспедиция* длится **2 минуты**."
    kb = [[InlineKeyboardButton("🗺️ Управление Походом (Экспедиция)", callback_data="hub_expedition")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def upgrade_and_craft_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ud = get_user_all_data(user_id)
    lvl = ud.get("colony_level", 1)
    cost = get_upgrade_cost(lvl)
    text = f"🚀 *ЛАБОРАТОРИЯ ЭВОЛЮЦИИ*\n\n🧬 Уровень колонии: *{lvl}* (Мутация: {cost} 🪙)"
    kb = [
        [InlineKeyboardButton(f"🧬 Повысить уровень ({cost} 🪙)", callback_data="buy_colony_upgrade")],
        [InlineKeyboardButton("📈 Улучшить характеристики карт", callback_data="menu_card_upgrade_list")],
        [InlineKeyboardButton("🔮 Войти в Крафт-Машину", callback_data="menu_craft")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def lucky_and_quests_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🎲 *ИГРОВАЯ ЗОНА И ИСПЫТАНИЯ* 📜\n\nКулдаун на Колесо и Арену — **2 минуты**!"
    kb = [[InlineKeyboardButton("🎡 Колесо Фортуны", callback_data="menu_wheel"),
           InlineKeyboardButton("🏟️ Арена Карт (Враги слабые)", callback_data="menu_card_arena")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def shop_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🛍️ *ТОРГОВАЯ ЛАВКА И ГАРДЕРОБ КОЛОНИИ*"
    kb = [
        [InlineKeyboardButton("🧹 Продать ВСЕ дубликаты", callback_data="shop_sell_duplicates")],
        [InlineKeyboardButton("🎖️ Магазин Титулов", callback_data="shop_titles_menu")],
        [InlineKeyboardButton("👤 Гардеробная титулов / Надеть", callback_data="menu_wardrobe")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def bonuses_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🎁 *ЦЕНТР РАЗВИТИЯ КОЛОНИИ И БОНУСЫ* 💎"
    kb = [
        [InlineKeyboardButton("🏦 Муравьиный Банк", callback_data="menu_bank"),
         InlineKeyboardButton("🎨 Кастомизация", callback_data="menu_themes_list")],
        [InlineKeyboardButton("🎟️ Активировать промокод", callback_data="menu_promo_hub")],
        [InlineKeyboardButton("💎 донат тут", url="https://t.me/davit2010yt")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# ==================== ЦЕНТРАЛЬНЫЙ CALLBACK-ОБРАБОТЧИК ====================
async def main_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    ud = get_user_all_data(user_id)
    if not ud: return
    now = time.time()

    # ==================== ПРОСМОТР И УМНАЯ ПРОДАЖА ИЗ СТОПКИ ====================
    if data.startswith("inspect_card_"):
        card_id = data.replace("inspect_card_", "")
        card = collections_col.find_one({"_id": ObjectId(card_id), "user_id": user_id})
        if not card:
            await query.message.reply_text("❌ Карта не найдена в вашей коллекции.")
            return
            
        lvl = card.get('level', 1)
        name = card['card_name']
        
        # Считаем, сколько точно таких же копий (имя + уровень) есть у игрока
        same_copies = list(collections_col.find({"user_id": user_id, "card_name": name, "level": lvl}))
        total_count = len(same_copies)
        sell_price = card.get('price', 2)
        
        text = (
            f"🔍 *ИНФОРМАЦИЯ О КАРТЕ:*\n\n"
            f"🃏 Название: *{name}*\n"
            f"✨ Редкость: *{card.get('rarity', '⚪ Обычная')}*\n"
            f"⭐ Уровень: `{lvl}`\n"
            f"📦 В наличии у вас: **{total_count} шт.**\n\n"
            f"❤️ HP: `{card.get('hp', 60)}` | ⚔️ ATK: `{card.get('atk', 15)}` | 🛡️ DEF: `{card.get('def', 5)}`\n\n"
            f"🪙 Стоимость продажи (1 шт): *{sell_price}* 🪙"
        )
        
        kb = [[InlineKeyboardButton(f"💰 Продать 1 шт. (+{sell_price} 🪙)", callback_data=f"sell_one_{card_id}")]]
        # Если есть дубликаты, выводим кнопку «Продать все копии»
        if total_count > 1:
            kb.append([InlineKeyboardButton(f"💥 Продать ВСЕ {total_count} шт. (+{sell_price * total_count} 🪙)", callback_data=f"sell_bulk_{name}_{lvl}")])
            
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data.startswith("sell_one_"):
        card_id = data.replace("sell_one_", "")
        card = collections_col.find_one({"_id": ObjectId(card_id), "user_id": user_id})
        if not card:
            await query.message.reply_text("❌ Карта уже продана или не существует.")
            return
            
        sell_price = card.get('price', 2)
        collections_col.delete_one({"_id": ObjectId(card_id)})
        update_user_coins(user_id, sell_price)
        
        await query.message.reply_text(f"✅ Вы успешно продали 1 копию карты *{card['card_name']}* за +{sell_price} 🪙!")
        return

    elif data.startswith("sell_bulk_"):
        # Формат: sell_bulk_[name]_[level]
        parts = data.replace("sell_bulk_", "").rsplit("_", 1)
        name_target = parts[0]
        lvl_target = int(parts[1])
        
        all_matches = list(collections_col.find({"user_id": user_id, "card_name": name_target, "level": lvl_target}))
        if not all_matches:
            await query.message.reply_text("❌ Копии карт не найдены.")
            return
            
        count = len(all_matches)
        single_price = all_matches[0].get("price", 2)
        total_payout = single_price * count
        
        # Удаляем всю пачку
        collections_col.delete_many({"user_id": user_id, "card_name": name_target, "level": lvl_target})
        update_user_coins(user_id, total_payout)
        
        await query.message.reply_text(f"🧹 Вы продали всю стопку *{name_target}* [Ур. {lvl_target}] в количестве {count} шт. Получено: +{total_payout} 🪙!")
        return

    # ==================== ПРОМОКОДЫ ====================
    elif data == "menu_promo_hub":
        text = "🎟️ *АКТИВАЦИЯ БОНУСНЫХ КОДОВ*"
        kb = [[InlineKeyboardButton("🔥 Промокод: cosmo", callback_data="promo_click_cosmo")]]
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data == "promo_click_cosmo":
        promo = promo_col.find_one({"code": "cosmo"})
        if not promo or user_id in promo.get("users_activated", []) or promo.get("uses", 0) >= promo.get("max_uses", 25):
            await query.message.reply_text("⚠️ Ошибка активации: лимит исчерпан или уже активирован.")
            return
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": 150}, "$addToSet": {"owned_titles": "CosmoMan"}})
        promo_col.update_one({"code": "cosmo"}, {"$inc": {"uses": 1}, "$push": {"users_activated": user_id}})
        await query.message.reply_text("🚀 Промокод успешно активирован! +150 монет и титул CosmoMan!")
        return

    # ==================== ГАРДЕРОБНАЯ ТИТУЛОВ ====================
    elif data == "menu_wardrobe":
        owned_titles = ud.get("owned_titles", ["Нет титула"])
        active_title = ud.get("active_title", "Нет титула")
        kb = []
        for title in owned_titles:
            mark = " ✅" if title == active_title else ""
            kb.append([InlineKeyboardButton(f"{title}{mark}", callback_data=f"equip_title_{title}")])
        await query.message.reply_text("👤 *ГАРДЕРОБНАЯ ТИТУЛОВ*:", reply_markup=InlineKeyboardMarkup(kb))
        return

    elif data.startswith("equip_title_"):
        target_title = data.replace("equip_title_", "")
        if target_title not in ud.get("owned_titles", ["Нет титула"]): return
        users_col.update_one({"user_id": user_id}, {"$set": {"active_title": target_title}})
        await query.message.reply_text(f"👑 Надет титул: *{target_title}*!")
        return

    # ==================== ПРОКАЧКА КАРТ ====================
    elif data == "menu_card_upgrade_list":
        cards = get_user_cards(user_id)
        if not cards: return
        text = "📈 *ВЫБЕРИТЕ КАРТУ ДЛЯ УЛУЧШЕНИЯ (+20%):*"
        kb = []
        for c in cards:
            rarity = c.get("rarity", "⚪ Обычная")
            cost = UPGRADE_CARD_COSTS.get(rarity, 50)
            kb.append([InlineKeyboardButton(f"{c['card_name']} [Ур.{c.get('level', 1)}] — {cost} 🪙", callback_data=f"upcard_{c['_id']}")])
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
        return

    elif data.startswith("upcard_"):
        card_id = data.replace("upcard_", "")
        card = collections_col.find_one({"_id": ObjectId(card_id), "user_id": user_id})
        if not card: return
        cost = UPGRADE_CARD_COSTS.get(card.get("rarity", "⚪ Обычная"), 50)
        if ud.get("coins", 0) < cost: return
        
        collections_col.update_one({"_id": ObjectId(card_id)}, {"$set": {
            "hp": int(card.get("hp", 50) * 1.2), "atk": int(card.get("atk", 10) * 1.2),
            "def": int(card.get("def", 5) * 1.2), "level": card.get("level", 1) + 1
        }})
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -cost}})
        await query.message.reply_text("🔥 Характеристики насекомого повышены на 20%!")
        return

    # ==================== КОЛЕСО И АРЕНА ====================
    elif data == "menu_wheel":
        if now - ud.get("last_wheel_time", 0) < 120 or ud.get("coins", 0) < 30: return
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -30}, "$set": {"last_wheel_time": now}})
        win = random.choices([0, 10, 25, 60, 150], weights=[40, 30, 15, 10, 5])[0]
        update_user_coins(user_id, win)
        await query.message.reply_text(f"🎡 Выигрыш: {win} 🪙")
        return

    elif data == "menu_card_arena":
        if now - ud.get("last_arena_time", 0) < 120 or ud.get("coins", 0) < 20: return
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -20}, "$set": {"last_arena_time": now}})
        
        user_cards = get_user_cards(user_id)
        p_name, p_hp, p_atk, p_def = (user_cards[0]["card_name"], user_cards[0].get("hp", 65), user_cards[0].get("atk", 13), user_cards[0].get("def", 5)) if user_cards else ("🐜 Рядовой", 65, 13, 5)
        b_name, b_hp, b_atk, b_def = random.choice(["🦟 Комар", "🐝 Шершень"]), 65, 35, 30
        
        battle_sessions[user_id] = {"p_name": p_name, "p_hp": p_hp, "p_atk": p_atk, "p_def": p_def, "b_name": b_name, "b_hp": b_hp, "b_atk": b_atk, "b_def": b_def, "round": 1}
        kb = [[InlineKeyboardButton("⚔️ Сделать Ход", callback_data="arena_action_hit")]]
        await query.message.reply_text(f"🏟️ *БОЙ:* {p_name} VS {b_name}", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data.startswith("arena_action_"):
        if user_id not in battle_sessions: return
        session = battle_sessions[user_id]
        if data.replace("arena_action_", "") == "hit":
            session["b_hp"] -= max(1, session["p_atk"] - session["b_def"])
            if session["b_hp"] <= 0:
                reward = random.randint(25, 50) + (ud.get("colony_level", 1) * 5)
                update_user_coins(user_id, reward)
                await query.message.reply_text(f"🎉 Победа! Награда: +{reward} 🪙")
                del battle_sessions[user_id]
                return
            session["p_hp"] -= max(1, session["b_atk"] - session["p_def"])
            if session["p_hp"] <= 0:
                await query.message.reply_text("💀 Поражение!")
                del battle_sessions[user_id]
                return
            kb = [[InlineKeyboardButton("⚔️ Ход", callback_data="arena_action_hit")]]
            await query.message.reply_text(f"❤️ Твоё HP: {session['p_hp']} | ❤️ Враг: {session['b_hp']}", reply_markup=InlineKeyboardMarkup(kb))
        return

    # ==================== ОСТАЛЬНЫЕ ФУНКЦИИ МАГАЗИНА / БАНКА ====================
    elif data == "shop_sell_duplicates":
        cards = get_user_cards(user_id)
        counts = {}
        for c in cards: counts[c['card_name']] = counts.get(c['card_name'], []) + [c]
        earnings, sold = 0, 0
        for name, clist in counts.items():
            if len(clist) > 1:
                for d in clist[1:]:
                    collections_col.delete_one({"_id": d["_id"]})
                    earnings += d.get("price", 2)
                    sold += 1
        if sold > 0: update_user_coins(user_id, earnings)
        await query.message.reply_text(f"🧹 Удалено дубликатов: {sold} шт. Банк: +{earnings} 🪙")
        return

    elif data == "shop_titles_menu":
        kb = []
        for tid, tinfo in SHOP_TITLES.items():
            status = " (Куплен)" if tinfo["name"] in ud.get("owned_titles", []) else f" — {tinfo['price']} 🪙"
            kb.append([InlineKeyboardButton(f"{tinfo['name']}{status}", callback_data=f"buy_title_{tid}")])
        await query.message.reply_text("🎖️ Магазин титулов:", reply_markup=InlineKeyboardMarkup(kb))
        return

    elif data.startswith("buy_title_"):
        title_info = SHOP_TITLES[data.replace("buy_title_", "")]
        if title_info["name"] in ud.get("owned_titles", []): return
        if ud.get("coins", 0) < title_info["price"]: return
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -title_info["price"]}, "$addToSet": {"owned_titles": title_info["name"]}})
        await query.message.reply_text("🎉 Успешно куплено!")
        return

    elif data == "buy_colony_upgrade":
        cost = get_upgrade_cost(ud.get("colony_level", 1))
        if ud.get("coins", 0) < cost: return
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -cost, "colony_level": 1}})
        await query.message.reply_text("🧬 Уровень колонии повышен!")
        return

    elif data == "menu_craft":
        cards = get_user_cards(user_id)
        if len(cards) < 3: return
        for bc in cards[:3]: collections_col.delete_one({"_id": bc["_id"]})
        cr = random.choice(list(REAL_CARDS_POOL.keys()))
        new_c = {**random.choice(REAL_CARDS_POOL[cr]), "rarity": cr, "level": 1}
        add_card_to_db(user_id, new_c)
        await query.message.reply_text(f"🔮 Создан боец: {new_c['name']}")
        return

    elif data == "menu_bank":
        kb = []
        if ud.get("coins", 0) >= 20: kb.append([InlineKeyboardButton("💰 Положить 20", callback_data="bank_deposit_100")])
        if ud.get("bank_deposit", 0) >= 20: kb.append([InlineKeyboardButton("💸 Снять 20", callback_data="bank_withdraw_100")])
        await query.message.reply_text(f"🏦 Банк: {ud.get('bank_deposit', 0)} 🪙", reply_markup=InlineKeyboardMarkup(kb))
        return

    elif data == "bank_deposit_100":
        if ud.get("coins", 0) < 20: return
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -20, "bank_deposit": 20}})
        await query.message.reply_text("✅ Внесено.")
        return

    elif data == "bank_withdraw_100":
        if ud.get("bank_deposit", 0) < 20: return
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": 20, "bank_deposit": -20}})
        await query.message.reply_text("✅ Снято.")
        return

    elif data == "menu_themes_list":
        kb = [[InlineKeyboardButton(f"{info['name']}", callback_data=f"theme_act_{k}")] for k, info in PROFILE_THEMES.items()]
        await query.message.reply_text("🎨 Локации:", reply_markup=InlineKeyboardMarkup(kb))
        return

    elif data.startswith("theme_act_"):
        th_key = data.replace("theme_act_", "")
        users_col.update_one({"user_id": user_id}, {"$set": {"profile_theme": th_key}})
        await query.message.reply_text("✨ Тема обновлена!")
        return

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Используйте меню кнопок.")

# ==================== ЗАПУСК ====================
def main():
    init_promo_db()
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
