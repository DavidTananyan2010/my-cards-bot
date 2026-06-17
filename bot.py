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
    ],
    "🔵 Редкая": [
        {"file": "9.jpg", "name": "Страж Дубравы 🌲", "price": 6, "hp": 90, "atk": 18, "def": 12}
    ],
    "🟣 Эпическая": [
        {"file": "4.jpg", "name": "Меха-Бык 🐂", "price": 12, "hp": 110, "atk": 24, "def": 15}
    ],
    "🟠 Легендарная": [
        {"file": "7.jpg", "name": "Призрак Леса 👻", "price": 18, "hp": 125, "atk": 28, "def": 16}
    ],
    "🔴 Мифическая": [
        {"file": "8.jpg", "name": "Лесной Хакер 💻", "price": 30, "hp": 155, "atk": 35, "def": 22}
    ],
    "✨ Древняя": [
        {"file": "2.jpg", "name": "👻losnya🐂🌲", "price": 50, "hp": 210, "atk": 45, "def": 28}
    ],
    "💎 Секретная": [
        {"file": "3.jpg", "name": "Дониёр 🌲", "price": 85, "hp": 290, "atk": 58, "def": 38}
    ],
    "🌟 Божественная": [
        {"file": "10.jpg", "name": "𝒎𝒐𝒐𝒏🌳", "price": 250, "hp": 550, "atk": 100, "def": 52}
    ],
    "👑 Эксклюзивная": [
        {"file": "1.jpg", "name": "金 sunny🌲 김지ха | DA 🐂", "price": 140, "hp": 410, "atk": 75, "def": 70}
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
        ["📦 Открыть пак", "👤 Профиль | 🏆 Топ"],
        ["🗂️ Коллекция", "⚔️ Походы & Битвы"],
        ["🚀 Прокачка & Крафт", "🎲 Удача & Квесты"],
        ["🛍️ Магазин", "🎁 Бонусы & Донат"]
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
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

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
        left_time = int(COOLDOWN_TIME - (current_time - COOLDOWNS[user_id]))
        await update.message.reply_text(f"⏳ Пакеты охлаждаются! Подождите {left_time} сек.")
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

# ==================== ПРОФИЛЬ И ТОП ИГРОКОВ ====================
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    await update.message.reply_text("🐜 Симулятор Карточных Колоний запущен!", reply_markup=get_main_keyboard())

async def profile_and_top_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    
    kb = [
        [InlineKeyboardButton("👤 Показать мой профиль", callback_data="view_my_profile")],
        [InlineKeyboardButton("🏆 Глобальный ТОП-10 Игроков", callback_data="view_global_leaders")]
    ]
    await update.message.reply_text("📋 Выберите интересующий раздел:", reply_markup=InlineKeyboardMarkup(kb))

# ==================== ХАБЫ ДЛЯ ФУНКЦИЙ НАЗАД ====================
def get_expedition_hub_markup():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🗺️ Отправиться в Экспедицию", callback_data="start_expedition_run")]])

def get_upgrade_hub_markup(lvl, cost):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🧬 Повысить уровень ({cost} 🪙)", callback_data="buy_colony_upgrade")],
        [InlineKeyboardButton("📈 Улучшить характеристики карт", callback_data="menu_card_upgrade_list")],
        [InlineKeyboardButton("🔮 Войти в Крафт-Машину", callback_data="menu_craft")]
    ])

def get_lucky_hub_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎡 Колесо Фортуны (30 🪙)", callback_data="menu_wheel"),
         InlineKeyboardButton("🏟️ Арена Карт (20 🪙)", callback_data="menu_card_arena")]
    ])

# ==================== МЕНЮ МАГАЗИНА (ОБНОВЛЕННОЕ) ====================
def get_shop_hub_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Продажа карт", callback_data="shop_sell_cards_menu")],
        [InlineKeyboardButton("🎖️ Магазин Титулов", callback_data="shop_titles_menu")],
        [InlineKeyboardButton("👤 Гардеробная титулов / Надеть", callback_data="menu_wardrobe")]
    ])

def get_bonuses_hub_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏦 Муравьиный Банк", callback_data="menu_bank"),
         InlineKeyboardButton("🎨 Кастомизация", callback_data="menu_themes_list")],
        [InlineKeyboardButton("🎟️ Активировать промокод", callback_data="menu_promo_hub")],
        [InlineKeyboardButton("💎 донат тут", url="https://t.me/davit2010yt")]
    ])

# ==================== ОБРАБОТЧИКИ КНОПОК МЕНЮ ====================
async def collection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cards = get_user_cards(user_id)
    kb = [[InlineKeyboardButton("📋 Справочник редкостей карт", callback_data="show_rarities_manual")]]
    
    if not cards:
        await update.message.reply_text("🗂️ Твоя коллекция пока пуста. Открой свой первый пак!", reply_markup=InlineKeyboardMarkup(kb))
        return
        
    grouped_cards = {}
    for c in cards:
        key = (c['card_name'], c.get('level', 1))
        grouped_cards.setdefault(key, []).append(c)

    text = "🗂️ *ТВОЯ КОМПАКТНАЯ КОЛЛЕКЦИЯ:*\nДубликаты сгруппированы. Выберите карту для просмотра или продажи."
    for (name, level), list_of_copies in grouped_cards.items():
        count = len(list_of_copies)
        display_count = f" (x{count})" if count > 1 else ""
        kb.append([InlineKeyboardButton(f"{name} [Ур. {level}]{display_count}", callback_data=f"inspect_card_{list_of_copies[0]['_id']}")])
        
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def pvp_and_expeditions_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚔️ *ВОЕННЫЙ ШТАБ КОЛОНИИ* 🗺️\n\n🗺️ *Экспедиция* длится **2 минуты**.", reply_markup=get_expedition_hub_markup(), parse_mode="Markdown")

async def upgrade_and_craft_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ud = get_user_all_data(user_id)
    lvl = ud.get("colony_level", 1)
    cost = get_upgrade_cost(lvl)
    await update.message.reply_text(f"🚀 *ЛАБОРАТОРИЯ ЭВОЛЮЦИИ*\n\n🧬 Уровень колонии: *{lvl}* (Мутация: {cost} 🪙)", reply_markup=get_upgrade_hub_markup(lvl, cost), parse_mode="Markdown")

async def lucky_and_quests_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎲 *ИГРОВАЯ ЗОНА И ИСПЫТАНИЯ* 📜\n\nКулдаун на Колесо и Арену — **2 минуты**!", reply_markup=get_lucky_hub_markup(), parse_mode="Markdown")

async def shop_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛍️ *ТОРГОВАЯ ЛАВКА И ГАРДЕРОБ КОЛОНИИ*", reply_markup=get_shop_hub_markup(), parse_mode="Markdown")

async def bonuses_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎁 *ЦЕНТР РАЗВИТИЯ КОЛОНИИ И БОНУСЫ* 💎", reply_markup=get_bonuses_hub_markup(), parse_mode="Markdown")

# ==================== ЦЕНТРАЛЬНЫЙ CALLBACK-ОБРАБОТЧИК ====================
async def main_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    ud = get_user_all_data(user_id)
    if not ud: 
        await query.answer("Сначала напишите /start")
        return
    now = time.time()

    # КНОПКИ НАЗАД К СВОИМ ХАБАМ
    if data == "back_to_shop":
        await query.answer()
        await query.message.edit_text("🛍️ *ТОРГОВАЯ ЛАВКА И ГАРДЕРОБ КОЛОНИИ*", reply_markup=get_shop_hub_markup(), parse_mode="Markdown")
        return
    elif data == "back_to_bonuses":
        await query.answer()
        await query.message.edit_text("🎁 *ЦЕНТР РАЗВИТИЯ КОЛОНИИ И БОНУСЫ* 💎", reply_markup=get_bonuses_hub_markup(), parse_mode="Markdown")
        return
    elif data == "back_to_upgrade":
        await query.answer()
        lvl = ud.get("colony_level", 1)
        cost = get_upgrade_cost(lvl)
        await query.message.edit_text(f"🚀 *ЛАБОРАТОРИЯ ЭВОЛЮЦИИ*\n\n🧬 Уровень колонии: *{lvl}* (Мутация: {cost} 🪙)", reply_markup=get_upgrade_hub_markup(lvl, cost), parse_mode="Markdown")
        return
    elif data == "back_to_collection":
        await query.answer()
        cards = get_user_cards(user_id)
        kb = [[InlineKeyboardButton("📋 Справочник редкостей карт", callback_data="show_rarities_manual")]]
        grouped_cards = {}
        for c in cards:
            key = (c['card_name'], c.get('level', 1))
            grouped_cards.setdefault(key, []).append(c)
        for (name, level), list_of_copies in grouped_cards.items():
            count = len(list_of_copies)
            display_count = f" (x{count})" if count > 1 else ""
            kb.append([InlineKeyboardButton(f"{name} [Ур. {level}]{display_count}", callback_data=f"inspect_card_{list_of_copies[0]['_id']}")])
        await query.message.edit_text("🗂️ *ТВОЯ КОМПАКТНАЯ КОЛЛЕКЦИЯ:*\nДубликаты сгруппированы.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return
    elif data == "back_to_profile_menu":
        await query.answer()
        kb = [
            [InlineKeyboardButton("👤 Показать мой профиль", callback_data="view_my_profile")],
            [InlineKeyboardButton("🏆 Глобальный ТОП-10 Игроков", callback_data="view_global_leaders")]
        ]
        await query.message.edit_text("📋 Выберите интересующий раздел:", reply_markup=InlineKeyboardMarkup(kb))
        return

    # ==================== ЛОГИКА ПРОФИЛЯ И ТОПА ИГРОКОВ ====================
    elif data == "view_my_profile":
        await query.answer()
        theme_name = PROFILE_THEMES.get(ud.get("profile_theme", "default"), PROFILE_THEMES["default"])["name"]
        profile_text = (
            f"👤 *Профиль: {query.from_user.first_name}*\n"
            f"🌐 Локация: *{theme_name}*\n"
            f"🎖️ Титул: *{ud.get('active_title', 'Нет титула')}*\n"
            f"🚀 Уровень Эволюции: *{ud.get('colony_level', 1)}*\n"
            f"🪙 Баланс: {ud.get('coins')} 🪙\n"
            f"🏦 В Сбережениях: {ud.get('bank_deposit', 0)} 🪙\n"
            f"⚔️ Побед на Арене: {ud.get('pvp_wins', 0)}\n"
            f"📦 Всего открыто паков: {ud.get('packs_opened')}\n"
        )
        kb = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile_menu")]]
        await query.message.edit_text(profile_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data == "view_global_leaders":
        await query.answer()
        top_users = list(users_col.find().sort([("colony_level", -1), ("coins", -1)]).limit(10))
        
        leaderboard_text = "🏆 *ГЛОБАЛЬНЫЙ ТОП КОЛОНИЙ DAcards* 🏆\n\n"
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        for index, u in enumerate(top_users):
            medal = medals[index] if index < len(medals) else "🐜"
            name = u.get("first_name", "Инкогнито")
            title = u.get("active_title", "Нет титула")
            title_str = f" [{title}]" if title != "Нет титула" else ""
            
            leaderboard_text += (
                f"{medal} *{name}*{title_str}\n"
                f" └ 🧬 Ур. Эволюции: `{u.get('colony_level', 1)}` | 🪙 Монеты: `{u.get('coins', 0)}`\n"
            )
            
        kb = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile_menu")]]
        await query.message.edit_text(leaderboard_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    # ==================== РАБОЧАЯ ЭКСПЕДИЦИЯ ====================
    elif data == "start_expedition_run":
        await query.answer()
        is_active = ud.get("expedition_active", False)
        start_time = ud.get("expedition_start_time", 0)
        
        if is_active:
            passed = now - start_time
            if passed < 120:
                left = int(120 - passed)
                await query.message.reply_text(f"⏳ Ваши рабочие муравьи еще в походе! Оставшееся время: {left} сек.")
                return
            else:
                coins_reward = random.randint(40, 100)
                update_user_coins(user_id, coins_reward)
                
                card_loot_text = ""
                if random.random() < 0.4:
                    all_rarities = list(REAL_CARDS_POOL.keys())
                    r_rarity = random.choices(all_rarities, weights=[40, 25, 15, 10, 5, 3, 1, 0.7, 0.2, 0.1])[0]
                    card_data = random.choice(REAL_CARDS_POOL[r_rarity])
                    loot_card = {**card_data, "rarity": r_rarity, "level": 1}
                    add_card_to_db(user_id, loot_card)
                    card_loot_text = f"\n📦 По пути они раскопали карту: *{loot_card['name']}* ({r_rarity})!"
                
                users_col.update_one({"user_id": user_id}, {"$set": {"expedition_active": False, "expedition_start_time": 0}})
                await query.message.reply_text(f"🍁 *Экспедиция успешно завершилась!*\n\n🐜 Муравьи вернулись и принесли: +{coins_reward} 🪙.{card_loot_text}", parse_mode="Markdown")
                return
        else:
            users_col.update_one({"user_id": user_id}, {"$set": {"expedition_active": True, "expedition_start_time": now}})
            await query.message.reply_text("🎒 Вы собрали отряд и отправили муравьев в далекие земли за ресурсами на **2 минуты**! Ждите.")
            return

    # ==================== СПРАВОЧНИК РЕДКОСТЕЙ ====================
    elif data == "show_rarities_manual":
        await query.answer()
        manual_text = "📋 *СПРАВОЧНИК ВСЕХ РЕДКОСТЕЙ И КАРТ:*\n\n"
        for rarity, card_list in REAL_CARDS_POOL.items():
            manual_text += f"🔹 *Ранг: {rarity}*\n"
            for card in card_list:
                manual_text += f" ├ 👤 *{card['name']}*\n ├ 🪙 Цена: `{card['price']} 🪙`\n └ ❤️ HP: `{card['hp']}` | ⚔️ ATK: `{card['atk']}` | 🛡️ DEF: `{card['def']}`\n"
            manual_text += "\n"
        kb = [[InlineKeyboardButton("🔙 Назад в коллекцию", callback_data="back_to_collection")]]
        await query.message.edit_text(manual_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    # ==================== ПРОСМОТР И УМНАЯ ПРОДАЖА ====================
    elif data.startswith("inspect_card_"):
        await query.answer()
        card_id = data.replace("inspect_card_", "")
        card = collections_col.find_one({"_id": ObjectId(card_id), "user_id": user_id})
        if not card: return
        
        lvl = card.get('level', 1)
        name = card['card_name']
        same_copies = list(collections_col.find({"user_id": user_id, "card_name": name, "level": lvl}))
        total_count = len(same_copies)
        sell_price = card.get('price', 2)
        
        text = (
            f"🔍 *ИНФОРМАЦИЯ О КАРТЕ:*\n\n🃏 Название: *{name}*\n✨ Редкость: *{card.get('rarity', '⚪ Обычная')}*\n"
            f"⭐ Уровень: `{lvl}`\n📦 В наличии: **{total_count} шт.**\n\nHP: `{card.get('hp', 60)}` | ATK: `{card.get('atk', 15)}` | DEF: `{card.get('def', 5)}`"
        )
        kb = [[InlineKeyboardButton(f"💰 Продать 1 шт. (+{sell_price} 🪙)", callback_data=f"sell_one_{card_id}")]]
        if total_count > 1:
            kb.append([InlineKeyboardButton(f"💥 Продать ВСЕ {total_count} шт. (+{sell_price * total_count} 🪙)", callback_data=f"sell_bulk_{name}_{lvl}")])
        kb.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_collection")])
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data.startswith("sell_one_") or data.startswith("sell_bulk_"):
        await query.answer()
        if data.startswith("sell_one_"):
            card_id = data.replace("sell_one_", "")
            card = collections_col.find_one({"_id": ObjectId(card_id), "user_id": user_id})
            if card:
                collections_col.delete_one({"_id": ObjectId(card_id)})
                update_user_coins(user_id, card.get('price', 2))
                await query.message.reply_text(f"✅ Продана 1 копия {card['card_name']}!")
        else:
            parts = data.replace("sell_bulk_", "").rsplit("_", 1)
            all_matches = list(collections_col.find({"user_id": user_id, "card_name": parts[0], "level": int(parts[1])}))
            if all_matches:
                payout = all_matches[0].get("price", 2) * len(all_matches)
                collections_col.delete_many({"user_id": user_id, "card_name": parts[0], "level": int(parts[1])})
                update_user_coins(user_id, payout)
                await query.message.reply_text(f"🧹 Продана стопка {parts[0]} ({len(all_matches)} шт.) за +{payout} 🪙!")
        return

    # ==================== ПРОМОКОДЫ ====================
    elif data == "menu_promo_hub":
        await query.answer()
        kb = [[InlineKeyboardButton("🔥 Промокод: cosmo", callback_data="promo_click_cosmo")],
              [InlineKeyboardButton("🔙 Назад", callback_data="back_to_bonuses")]]
        await query.message.edit_text("🎟️ *АКТИВАЦИЯ БОНУСНЫХ КОДОВ*", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data == "promo_click_cosmo":
        promo = promo_col.find_one({"code": "cosmo"})
        if not promo or user_id in promo.get("users_activated", []) or promo.get("uses", 0) >= promo.get("max_uses", 25):
            await query.answer("⚠️ Ошибка активации", show_alert=True)
            await query.message.reply_text("⚠️ Лимит исчерпан или уже активирован.")
            return
        await query.answer("🎉 Успешно!", show_alert=True)
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": 150}, "$addToSet": {"owned_titles": "CosmoMan"}})
        promo_col.update_one({"code": "cosmo"}, {"$inc": {"uses": 1}, "$push": {"users_activated": user_id}})
        await query.message.reply_text("🚀 Активировано! +150 монет и титул CosmoMan!")
        return

    # ==================== ГАРДЕРОБНАЯ ТИТУЛОВ ====================
    elif data == "menu_wardrobe":
        await query.answer()
        kb = []
        for title in ud.get("owned_titles", ["Нет титула"]):
            mark = " ✅" if title == ud.get("active_title", "Нет титула") else ""
            kb.append([InlineKeyboardButton(f"{title}{mark}", callback_data=f"equip_title_{title}")])
        kb.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_shop")])
        await query.message.edit_text("👤 *ГАРДЕРОБНАЯ ТИТУЛОВ*:", reply_markup=InlineKeyboardMarkup(kb))
        return

    elif data.startswith("equip_title_"):
        target_title = data.replace("equip_title_", "")
        if target_title in ud.get("owned_titles", []):
            users_col.update_one({"user_id": user_id}, {"$set": {"active_title": target_title}})
            await query.answer(f"👑 Надет титул: {target_title}!", show_alert=True)
            kb = []
            updated_ud = get_user_all_data(user_id)
            for title in updated_ud.get("owned_titles", ["Нет титула"]):
                mark = " ✅" if title == updated_ud.get("active_title", "Нет титула") else ""
                kb.append([InlineKeyboardButton(f"{title}{mark}", callback_data=f"equip_title_{title}")])
            kb.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_shop")])
            await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
        else:
            await query.answer("Вы не владеете этим титулом", show_alert=True)
        return

    # ==================== ПРОКАЧКА КАРТ ====================
    elif data == "menu_card_upgrade_list":
        await query.answer()
        cards = get_user_cards(user_id)
        if not cards: 
            await query.message.reply_text("У вас нет карт для улучшения!")
            return
        kb = []
        for c in cards:
            cost = UPGRADE_CARD_COSTS.get(c.get("rarity", "⚪ Обычная"), 50)
            kb.append([InlineKeyboardButton(f"{c['card_name']} [Ур.{c.get('level', 1)}] — {cost} 🪙", callback_data=f"upcard_{c['_id']}")])
        kb.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_upgrade")])
        await query.message.edit_text("📈 *ВЫБЕРИТЕ КАРТУ ДЛЯ УЛУЧШЕНИЯ (+20%):*", reply_markup=InlineKeyboardMarkup(kb))
        return

    elif data.startswith("upcard_"):
        card_id = data.replace("upcard_", "")
        card = collections_col.find_one({"_id": ObjectId(card_id), "user_id": user_id})
        if not card: 
            await query.answer("Карта не найдена")
            return
        cost = UPGRADE_CARD_COSTS.get(card.get("rarity", "⚪ Обычная"), 50)
        if ud.get("coins", 0) < cost:
            await query.answer("❌ Недостаточно монет!", show_alert=True)
            return
        await query.answer("🔥 Эволюция!")
        collections_col.update_one({"_id": ObjectId(card_id)}, {"$set": {
            "hp": int(card.get("hp", 50) * 1.2), "atk": int(card.get("atk", 10) * 1.2),
            "def": int(card.get("def", 5) * 1.2), "level": card.get("level", 1) + 1
        }})
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -cost}})
        await query.message.reply_text(f"🔥 Карточка {card['card_name']} успешно эволюционировала!")
        return

    # ==================== КОЛЕСО И АРЕНА ====================
    elif data == "menu_wheel":
        passed = now - ud.get("last_wheel_time", 0)
        if passed < 120:
            await query.answer(f"⏳ Подождите {int(120 - passed)} сек.", show_alert=True)
            return
        if ud.get("coins", 0) < 30: 
            await query.answer("❌ Недостаточно монет (30 🪙)", show_alert=True)
            return
        await query.answer("🎰 Крутим!")
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -30}, "$set": {"last_wheel_time": now}})
        win = random.choices([0, 10, 25, 60, 150], weights=[40, 30, 15, 10, 5])[0]
        update_user_coins(user_id, win)
        await query.message.reply_text(f"🎡 Выигрыш: {win} 🪙")
        return

    elif data == "menu_card_arena":
        passed = now - ud.get("last_arena_time", 0)
        if passed < 120:
            await query.answer(f"⏳ Подождите {int(120 - passed)} сек.", show_alert=True)
            return
        if ud.get("coins", 0) < 20: 
            await query.answer("❌ Недостаточно монет (20 🪙)", show_alert=True)
            return
        await query.answer("⚔️ Вход на Арену!")
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -20}, "$set": {"last_arena_time": now}})
        
        user_cards = get_user_cards(user_id)
        p_name, p_hp, p_atk, p_def = (user_cards[0]["card_name"], user_cards[0].get("hp", 65), user_cards[0].get("atk", 13), user_cards[0].get("def", 5)) if user_cards else ("🐜 Муравей-Рядовой", 65, 13, 5)
        b_name, b_hp, b_atk, b_def = random.choice(["🦟 Малярийный Комар", "🐝 Разъяренный Шершень"]), 65, 35, 30
        
        battle_sessions[user_id] = {"p_name": p_name, "p_hp": p_hp, "p_atk": p_atk, "p_def": p_def, "b_name": b_name, "b_hp": b_hp, "b_atk": b_atk, "b_def": b_def}
        kb = [[InlineKeyboardButton("⚔️ Нанести удар", callback_data="arena_action_hit")]]
        await query.message.reply_text(f"🏟️ *БОЙ:* {p_name} VS {b_name}", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data == "arena_action_hit":
        await query.answer()
        if user_id not in battle_sessions: return
        session = battle_sessions[user_id]
        session["b_hp"] -= max(1, session["p_atk"] - session["b_def"])
        if session["b_hp"] <= 0:
            reward = random.randint(25, 50) + (ud.get("colony_level", 1) * 5)
            update_user_coins(user_id, reward)
            users_col.update_one({"user_id": user_id}, {"$inc": {"pvp_wins": 1}})
            await query.message.reply_text(f"🎉 Победа над вредителем! Награда: +{reward} 🪙")
            del battle_sessions[user_id]
            return
        session["p_hp"] -= max(1, session["b_atk"] - session["p_def"])
        if session["p_hp"] <= 0:
            await query.message.reply_text("💀 Поражение!")
            del battle_sessions[user_id]
            return
        kb = [[InlineKeyboardButton("⚔️ Сделать следующий ход", callback_data="arena_action_hit")]]
        await query.message.reply_text(f"❤️ Твоё HP: {session['p_hp']} | ❤️ Враг: {session['b_hp']}", reply_markup=InlineKeyboardMarkup(kb))
        return

    # ==================== ЕДИНАЯ СТРУКТУРА ПРОДАЖИ КАРТ И ТИТУЛОВ ====================
    elif data == "shop_sell_cards_menu":
        await query.answer()
        kb = [
            [InlineKeyboardButton("🧹 Продать вообще ВСЕ карты", callback_data="shop_sell_absolutely_all")],
            [InlineKeyboardButton("👥 Продать только дубликаты", callback_data="shop_sell_duplicates_action")],
            [InlineKeyboardButton("🔙 Назад в магазин", callback_data="back_to_shop")]
        ]
        await query.message.edit_text("💰 *ЦЕНТРАЛЬНЫЙ ПУНКТ ПРИЕМКИ КАРТ*\n\nВыберите тип продажи колонии:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data == "shop_sell_absolutely_all":
        cards = get_user_cards(user_id)
        if not cards:
            await query.answer("❌ Ваша коллекция пуста!", show_alert=True)
            return
        await query.answer("💰 Полная распродажа!")
        
        earnings = sum(c.get("price", 2) for c in cards)
        collections_col.delete_many({"user_id": user_id})
        update_user_coins(user_id, earnings)
        
        await query.message.reply_text(f"🧹 Вы очистили весь свой инвентарь! Продано карт: {len(cards)} шт. Баланс пополнен на: +{earnings} 🪙")
        return

    elif data == "shop_sell_duplicates_action":
        cards = get_user_cards(user_id)
        counts = {}
        for c in cards: counts.setdefault(c['card_name'], []).append(c)
        earnings, sold = 0, 0
        for clist in counts.values():
            if len(clist) > 1:
                for d in clist[1:]:
                    collections_col.delete_one({"_id": d["_id"]})
                    earnings += d.get("price", 2)
                    sold += 1
                    
        if sold > 0: 
            update_user_coins(user_id, earnings)
            await query.answer("🧹 Дубликаты утилизированы!")
            await query.message.reply_text(f"🧹 Удалено лишних дубликатов: {sold} шт. Баланс пополнен на: +{earnings} 🪙")
        else:
            await query.answer("📋 У вас нет повторяющихся дубликатов!", show_alert=True)
        return

    elif data == "shop_titles_menu":
        await query.answer()
        kb = []
        for tid, tinfo in SHOP_TITLES.items():
            status = " (Куплен)" if tinfo["name"] in ud.get("owned_titles", []) else f" — {tinfo['price']} 🪙"
            kb.append([InlineKeyboardButton(f"{tinfo['name']}{status}", callback_data=f"buy_title_{tid}")])
        kb.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_shop")])
        await query.message.edit_text("🎖️ Магазин титулов колоний:", reply_markup=InlineKeyboardMarkup(kb))
        return

    elif data.startswith("buy_title_"):
        title_id = data.replace("buy_title_", "")
        if title_id not in SHOP_TITLES:
            await query.answer("❌ Ошибка: Титул не найден!", show_alert=True)
            return
            
        title_info = SHOP_TITLES[title_id]
        title_real_name = title_info["name"]
        
        if title_real_name in ud.get("owned_titles", []):
            await query.answer("📋 Вы уже купили данный титул!", show_alert=True)
            return
            
        if ud.get("coins", 0) < title_info["price"]:
            await query.answer(f"❌ Недостаточно монет! Требуется: {title_info['price']} 🪙", show_alert=True)
            return
            
        users_col.update_one(
            {"user_id": user_id}, 
            {
                "$inc": {"coins": -title_info["price"]}, 
                "$addToSet": {"owned_titles": title_real_name}
            }
        )
        
        await query.answer(f"🎉 Вы успешно купили титул: {title_real_name}!", show_alert=True)
        
        updated_ud = get_user_all_data(user_id)
        kb = []
        for tid, tinfo in SHOP_TITLES.items():
            status = " (Куплен)" if tinfo["name"] in updated_ud.get("owned_titles", []) else f" — {tinfo['price']} 🪙"
            kb.append([InlineKeyboardButton(f"{tinfo['name']}{status}", callback_data=f"buy_title_{tid}")])
        kb.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_shop")])
        await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
        return

    elif data == "buy_colony_upgrade":
        cost = get_upgrade_cost(ud.get("colony_level", 1))
        if ud.get("coins", 0) >= cost:
            users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -cost, "colony_level": 1}})
            await query.answer("🧬 Мутация успешна!")
            await query.message.reply_text("🧬 Мутация завершена! Уровень муравейника повышен.")
        else:
            await query.answer("❌ Не хватает монет!", show_alert=True)
        return

    elif data == "menu_craft":
        await query.answer()
        cards = get_user_cards(user_id)
        if len(cards) >= 3:
            for bc in cards[:3]: collections_col.delete_one({"_id": bc["_id"]})
            cr = random.choice(list(REAL_CARDS_POOL.keys()))
            new_c = {**random.choice(REAL_CARDS_POOL[cr]), "rarity": cr, "level": 1}
            add_card_to_db(user_id, new_c)
            await query.message.reply_text(f"🔮 Из биомассы создан: {new_c['name']}")
        else:
            await query.message.reply_text("❌ Для крафта нужно минимум 3 карты в инвентаре!")
        return

    elif data == "menu_bank":
        await query.answer()
        kb = []
        if ud.get("coins", 0) >= 20: 
            kb.append([InlineKeyboardButton("💰 Внести 20 🪙", callback_data="bank_deposit_20")])
        if ud.get("bank_deposit", 0) >= 20: 
            kb.append([InlineKeyboardButton("🏧 Снять 20 🪙", callback_data="bank_withdraw_20")])
        kb.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_bonuses")])
        await query.message.edit_text(f"🏦 *МУРАВЬИНЫЙ БАНК СБЕРЕЖЕНИЙ*\n\nНа руках: {ud.get('coins')} 🪙\nВ сейфе банка: {ud.get('bank_deposit', 0)} 🪙", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data == "bank_deposit_20":
        if ud.get("coins", 0) >= 20:
            users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -20, "bank_deposit": 20}})
            await query.answer("🪙 Вклад пополнен!")
            updated_ud = get_user_all_data(user_id)
            kb = []
            if updated_ud.get("coins", 0) >= 20: kb.append([InlineKeyboardButton("💰 Внести 20 🪙", callback_data="bank_deposit_20")])
            if updated_ud.get("bank_deposit", 0) >= 20: kb.append([InlineKeyboardButton("🏧 Снять 20 🪙", callback_data="bank_withdraw_20")])
            kb.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_bonuses")])
            await query.message.edit_text(f"🏦 *МУРАВЬИНЫЙ БАНК СБЕРЕЖЕНИЙ*\n\nНа руках: {updated_ud.get('coins')} 🪙\nВ сейфе банка: {updated_ud.get('bank_deposit', 0)} 🪙", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data == "bank_withdraw_20":
        if ud.get("bank_deposit", 0) >= 20:
            users_col.update_one({"user_id": user_id}, {"$inc": {"coins": 20, "bank_deposit": -20}})
            await query.answer("🪙 Монеты сняты со счета!")
            updated_ud = get_user_all_data(user_id)
            kb = []
            if updated_ud.get("coins", 0) >= 20: kb.append([InlineKeyboardButton("💰 Внести 20 🪙", callback_data="bank_deposit_20")])
            if updated_ud.get("bank_deposit", 0) >= 20: kb.append([InlineKeyboardButton("🏧 Снять 20 🪙", callback_data="bank_withdraw_20")])
            kb.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_bonuses")])
            await query.message.edit_text(f"🏦 *МУРАВЬИНЫЙ БАНК СБЕРЕЖЕНИЙ*\n\nНа руках: {updated_ud.get('coins')} 🪙\nВ сейфе банка: {updated_ud.get('bank_deposit', 0)} 🪙", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data == "menu_themes_list":
        await query.answer("В разработке", show_alert=True)
        return

# ТЕКСТОВЫЕ МАРШРУТЫ И ГЛАВНОЕ МЕНЮ РЕПЛИ
async def text_message_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_text = update.message.text
    if msg_text == "📦 Открыть пак":
        await open_pack_handler(update, context)
    elif msg_text == "👤 Профиль | 🏆 Топ":
        await profile_and_top_handler(update, context)
    elif msg_text == "🗂️ Коллекция":
        await collection_handler(update, context)
    elif msg_text == "⚔️ Походы & Битвы":
        await pvp_and_expeditions_main_handler(update, context)
    elif msg_text == "🚀 Прокачка & Крафт":
        await upgrade_and_craft_main_handler(update, context)
    elif msg_text == "🎲 Удача & Квесты":
        await lucky_and_quests_main_handler(update, context)
    elif msg_text == "🛍️ Магазин":
        await shop_main_handler(update, context)
    elif msg_text == "🎁 Бонусы & Донат":
        await bonuses_main_handler(update, context)

def main():
    init_promo_db()
    run_health_server()
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(main_callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_dispatcher))
    
    logging.info("🤖 Бот Успешно запущен на MongoDB!")
    app.run_polling()

if __name__ == '__main__':
    main()
