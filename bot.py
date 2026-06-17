import logging
import random
import os
import asyncio
import time
import threading
from datetime import datetime, date, timedelta
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pymongo import MongoClient
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, PreCheckoutQueryHandler

# ==================== ТАБЛИЦА РЕДКОСТЕЙ С КАРТАМИ И ХАРАКТЕРИСТИКАМИ ====================
# Список реальных карт, распределенный по новым 11 редкостям
REAL_CARDS_POOL = {
    "⚪ Обычная": [
        {"file": "5.jpg", "name": "Солнечный Самурай ☀️", "price": 10, "hp": 65, "atk": 13, "def": 5},
        {"file": "6.jpg", "name": "Таинственный Лось 🦌", "price": 12, "hp": 75, "atk": 14, "def": 6}
    ],
    "🟢 Необычная": [
        {"file": "9.jpg", "name": "Страж Дубравы 🌲", "price": 20, "hp": 90, "atk": 18, "def": 8}
    ],
    "🔵 Редкая": [
        {"file": "4.jpg", "name": "Меха-Бык 🐂", "price": 35, "hp": 110, "atk": 24, "def": 12},
        {"file": "7.jpg", "name": "Призрак Леса 👻", "price": 40, "hp": 105, "atk": 26, "def": 11}
    ],
    "🟣 Эпическая": [
        {"file": "8.jpg", "name": "Лесной Хакер 💻", "price": 60, "hp": 145, "atk": 32, "def": 15}
    ],
    "🟠 Легендарная": [
        {"file": "2.jpg", "name": "👻losnya🐂🌲", "price": 100, "hp": 200, "atk": 42, "def": 20}
    ],
    "🔴 Мифическая": [
        {"file": "3.jpg", "name": "Дониёр 🌲", "price": 180, "hp": 270, "atk": 55, "def": 26}
    ],
    "✨ Древняя": [
        {"file": "1.jpg", "name": "金 sunny🌲 김지ха | DA 🐂", "price": 300, "hp": 390, "atk": 72, "def": 36}
    ],
    "💎 Секретная": [
        {"file": "10.jpg", "name": "𝒎𝒐𝒐𝒏🌳", "price": 500, "hp": 500, "atk": 92, "def": 48}
    ],
    "🌟 Божественная": [
        {"file": "10.jpg", "name": "Божественный Аспект Муравья 👑", "price": 1000, "hp": 720, "atk": 135, "def": 62}
    ],
    "👑 Эксклюзивная": [
        {"file": "1.jpg", "name": "👑 Абсолютный Оверлорд Колонии", "price": 5000, "hp": 1150, "atk": 200, "def": 95}
    ]
}

EMPTY_RESPONSES = [
    "Эта карта оказалась пустой... Открой ещё разок! 😔",
    "Эх, тут ничего не оказалось. Повезет в следующий раз! 💨",
    "Увы, пак пуст. Фортуна сегодня отдыхает 🃏"
]

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

# ==================== ГЛАВНАЯ КЛАВИАТУРА ====================
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
        "user_id": user_id, 
        "card_name": card['name'], 
        "rarity": card['rarity'],
        "file_name": card['file'], 
        "price": card['price'],
        "hp": card['hp'],
        "atk": card['atk'],
        "def": card['def']
    })

def get_user_cards(user_id):
    return list(collections_col.find({"user_id": user_id}))

# ==================== ИСПРАВЛЕННОЕ МЕНЮ ОТКРЫТИЯ ПАКОВ (ПО ЗАДАННЫМ ШАНСАМ) ====================
async def open_pack_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    
    current_time = time.time()
    if user_id in COOLDOWNS and (current_time - COOLDOWNS[user_id] < COOLDOWN_TIME):
        await update.message.reply_text(f"⏳ Пакеты охлаждаются! Подождите немного.")
        return
    COOLDOWNS[user_id] = current_time
    
    # Списки редкостей и их точные шансы из ТЗ
    rarities = [
        "🗑️ Пустышка", "⚪ Обычная", "🟢 Необычная", "🔵 Редкая", "🟣 Эпическая", 
        "🟠 Легендарная", "🔴 Мифическая", "✨ Древняя", "💎 Секретная", "🌟 Божественная", "👑 Эксклюзивная"
    ]
    weights = [55.0, 35.0, 25.0, 15.0, 10.0, 5.0, 3.0, 1.0, 0.8, 0.5, 0.01]
    
    # Рандомный выбор редкости на основе весов
    chosen_rarity = random.choices(rarities, weights=weights, k=1)[0]
    
    users_col.update_one({"user_id": user_id}, {"$inc": {"packs_opened": 1, "daily_packs": 1}})
    
    if chosen_rarity == "🗑️ Пустышка":
        await update.message.reply_text(random.choice(EMPTY_RESPONSES))
    else:
        # Получаем карту из пула выбранной редкости
        card_data = random.choice(REAL_CARDS_POOL[chosen_rarity])
        
        # Собираем итоговый объект карты
        dropped_card = {
            "file": card_data["file"],
            "name": card_data["name"],
            "rarity": chosen_rarity,
            "price": card_data["price"],
            "hp": card_data["hp"],
            "atk": card_data["atk"],
            "def": card_data["def"]
        }
        
        add_card_to_db(user_id, dropped_card)
        update_user_coins(user_id, dropped_card['price'])
        
        path_to_image = f"cards/{dropped_card['file']}"
        caption_text = (
            f"🎉 **ВЫПАЛА КАРТА!** 🎉\n\n"
            f"👤 Название: *{dropped_card['name']}*\n"
            f"✨ Редкость: *{dropped_card['rarity']}*\n"
            f"❤️ HP: `{dropped_card['hp']}` | ⚔️ ATK: `{dropped_card['atk']}` | 🛡️ DEF: `{dropped_card['def']}`\n\n"
            f"🪙 Награда за раскрытие: +*{dropped_card['price']}* монет!"
        )
        if os.path.exists(path_to_image):
            await update.message.reply_photo(photo=open(path_to_image, 'rb'), caption=caption_text, parse_mode="Markdown")
        else:
            await update.message.reply_text(caption_text, parse_mode="Markdown")

# ==================== ОСТАЛЬНЫЕ ИГРОВЫЕ МЕНЮ ====================
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    await update.message.reply_text("🐜 Симулятор Карточных Колоний запущен! Управляй своей колонией с помощью меню ниже:", reply_markup=get_main_keyboard())

async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    ud = get_user_all_data(user_id)
    
    theme_name = PROFILE_THEMES.get(ud.get("profile_theme", "default"), PROFILE_THEMES["default"])["name"]
    
    profile_text = (
        f"👤 *Профиль: {update.effective_user.first_name}*\n"
        f"🌐 Локация: *{theme_name}*\n"
        f"🎖️ Титул: *{ud.get('active_title')}*\n"
        f"🚀 Уровень Эволюции: *{ud.get('colony_level', 1)}*\n"
        f"🪙 Баланс: {ud.get('coins')} монеток\n"
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
        text += f"• *{c['card_name']}* ({c.get('rarity', '⚪ Обычная')}) — [⚔️{c.get('atk', 15)} 🛡️{c.get('def', 5)} ❤️{c.get('hp', 60)}]\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def pvp_and_expeditions_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "⚔️ *ВОЕННЫЙ ШТАБ КОЛОНИИ* 🗺️\n\n"
        "Сражайся на арене или отправляй отряды в экспедиции за ресурсами!\n\n"
        "⚔️ *Битва Колоний (PvP)* — Бой с дикими насекомыми. Сила зависит от карт и эволюции.\n"
        "🗺️ *Экспедиции* — Поиск сладкого нектара (пассивный доход времени)."
    )
    kb = [
        [InlineKeyboardButton("⚔️ Начать Битву (PvP)", callback_data="play_pvp_battle")],
        [InlineKeyboardButton("🗺️ Отправиться в Экспедицию", callback_data="menu_expeditions")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def upgrade_and_craft_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ud = get_user_all_data(user_id)
    lvl = ud.get("colony_level", 1)
    cost = lvl * 300
    
    text = (
        "🚀 *ЛАБОРАТОРИЯ ЭВОЛЮЦИИ И КРАФТА* 🔮\n\n"
        f"🧬 Твой уровень колонии: *{lvl}*\n"
        f"Стоимость следующей мутации: *{cost} 🪙*\n\n"
        "🔮 *Синтез Карт (Крафт)*: Объедини 3 любые карты, чтобы гарантированно получить одну случайную карту из реального списка."
    )
    kb = [
        [InlineKeyboardButton(f"🧬 Повысить уровень ({cost} 🪙)", callback_data="buy_colony_upgrade")],
        [InlineKeyboardButton("🔮 Войти в Крафт-Машину", callback_data="menu_craft")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def lucky_and_quests_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎲 *ИГРОВАЯ ЗОНА И ЗАЗАНИЯ КОРОЛЕВЫ* 📜\n\n"
        "Испытай удачу на Колесе Фортуны, отправь своих бойцов на смертельную Арену Карт или выполняй квесты!"
    )
    kb = [
        [InlineKeyboardButton("🎡 Колесо Фортуны", callback_data="menu_wheel"),
         InlineKeyboardButton("🏟️ Арена Карт", callback_data="menu_card_arena")],
        [InlineKeyboardButton("📜 Ежедневные Квесты", callback_data="menu_quests")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def shop_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛍️ *ТОРГОВАЯ ЛАВКА КОЛОНИИ* 🛍️\n\n"
        "💰 *Сдача дубликатов* — Автоматически продает повторяющиеся карты за полную стоимость.\n"
        "🎖️ *Титулы* — Косметические префиксы для твоего профиля."
    )
    kb = [
        [InlineKeyboardButton("💰 Сдача дубликатов", callback_data="shop_sell_duplicates")],
        [InlineKeyboardButton("🎖️ Магазин Титулов", callback_data="shop_titles_menu")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def bonuses_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎁 *ЦЕНТР РАЗВИТИЯ КОЛОНИИ И ПОДДЕРЖКИ* 💎\n\n"
        "Забирай ежедневные награды, используй коды, настраивай внешний вид гнезда или приобретай монеты за **Telegram Stars**!"
    )
    kb = [
        [InlineKeyboardButton("🎁 Ежедневный Бонус (24ч)", callback_data="claim_24h_bonus"),
         InlineKeyboardButton("🎟️ Ввести Промокод", callback_data="enter_promo")],
        [InlineKeyboardButton("🏦 Муравьиный Банк", callback_data="menu_bank"),
         InlineKeyboardButton("🎨 Кастомизация", callback_data="menu_themes_list")],
        [InlineKeyboardButton("💎 КУПИТЬ МОНЕТЫ (ДОНАТ)", callback_data="menu_donate_stars")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


# ==================== CALLBACK-ОБРАБОТЧИК ДЛЯ АРЕНЫ И ОСТАЛЬНЫХ ФУНКЦИЙ ====================
async def main_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    ud = get_user_all_data(user_id)
    if not ud: return

    # --- КАРТОЧНАЯ АРЕНА (ДИНАМИЧЕСКИЕ ХАРАКТЕРИСТИКИ) ---
    if data == "menu_card_arena":
        if ud.get("coins", 0) < 50:
            await query.message.reply_text("❌ Вход на Арену стоит 50 🪙.")
            return

        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -50}})
        user_cards = get_user_cards(user_id)
        lvl = ud.get("colony_level", 1)
        
        if user_cards:
            my_card = random.choice(user_cards)
            my_name = my_card["card_name"]
            my_rarity = my_card.get("rarity", "⚪ Обычная")
            my_hp = my_card.get("hp", 65)
            my_atk = my_card.get("atk", 13)
            my_def = my_card.get("def", 5)
        else:
            my_name = "🐜 Муравей-Рядовой"
            my_rarity = "⚪ Обычная (Базовая)"
            my_hp = 65
            my_atk = 13
            my_def = 5

        # Сила босса подстраивается под уровень колонии
        boss_names = ["🦟 Дикий Комар-Убийца", "🐝 Разъяренный Шершень", "🕷️ Лесной Паук-Волк", "🦂 Бронированный Скорпион"]
        boss_name = random.choice(boss_names)
        boss_hp = random.randint(60, 110) + (lvl * 12)
        boss_atk = random.randint(14, 25) + (lvl * 3)
        boss_def = random.randint(3, 10) + (lvl * 2)

        battle_log = (
            f"🏟️ *ДОБРО ПОЖАЛОВАТЬ НА КАРТОЧНУЮ АРЕНУ!* 🏟️\n\n"
            f"🟢 *Твой боец:* {my_name} ({my_rarity})\n[❤️ HP: {my_hp} | ⚔️ ATK: {my_atk} | 🛡️ DEF: {my_def}]\n\n"
            f"🔴 *Вражеский Босс:* {boss_name}\n[❤️ HP: {boss_hp} | ⚔️ ATK: {boss_atk} | 🛡️ DEF: {boss_def}]\n\n"
            f"⚔️ *ХОД СРАЖЕНИЯ:*\n"
        )

        round_num = 1
        while my_hp > 0 and boss_hp > 0 and round_num <= 8:
            damage_to_boss = max(1, my_atk - boss_def)
            boss_hp -= damage_to_boss
            battle_log += f"• *Раунд {round_num}:* Твой боец наносит `{damage_to_boss}` урона.\n"
            if boss_hp <= 0: break
            
            damage_to_me = max(1, boss_atk - my_def)
            my_hp -= damage_to_me
            battle_log += f"• Босс отвечает на `{damage_to_me}` урона.\n"
            round_num += 1

        battle_log += "\n🏁 *ИТОГ БОЯ:* "
        if my_hp > boss_hp:
            reward = random.randint(100, 180) + (lvl * 25)
            update_user_coins(user_id, reward)
            users_col.update_one({"user_id": user_id}, {"$inc": {"pvp_wins": 1}})
            battle_log += f"🎉 *ПОБЕДА!* Вы сокрушили противника!\nНаграда: +*{reward}* 🪙!"
        else:
            battle_log += f"💀 *ПОРАЖЕНИЕ!* Твоя карта была повержена. Качай уровень колонии или выбивай эпические/легендарные карты!"

        await query.message.reply_text(battle_log, parse_mode="Markdown")
        return

    # --- ОСТАЛЬНЫЕ ОБРАБОТЧИКИ (МАГАЗИН, СИНТЕЗ, ТЕМЫ) ---
    elif data == "shop_sell_duplicates":
        cards = get_user_cards(user_id)
        counts = {}
        for c in cards: counts[c['card_name']] = counts.get(c['card_name'], []) + [c]
        total_earnings, sold_count = 0, 0
        for name, card_list in counts.items():
            if len(card_list) > 1:
                for duplicate in card_list[1:]:
                    collections_col.delete_one({"_id": duplicate["_id"]})
                    total_earnings += duplicate.get("price", 10)
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
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
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

    elif data == "menu_wheel":
        if ud.get("coins", 0) < 100:
            await query.message.reply_text("❌ Не хватает монет.")
            return
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -100}})
        win = random.choices([0, 50, 100, 200, 500], weights=[40, 30, 15, 10, 5])[0]
        update_user_coins(user_id, win)
        await query.message.reply_text(f"🎡 Выигрыш: *{win}* 🪙!", parse_mode="Markdown")
        return

    elif data == "menu_quests":
        await query.message.reply_text("📜 Квесты: 1. Открыть 5 паков сегодня. 2. Одержать победу на Арене.")
        return

    elif data == "menu_donate_stars":
        text = "💎 *ПОПОЛНЕНИЕ БАЛАНСА ЗВЁЗДАМИ TELEGRAM*"
        kb = [[InlineKeyboardButton("🛒 Купить 1,000 🪙 (15 ⭐)", callback_data="buy_stars_1000")], [InlineKeyboardButton("🛒 Купить 5,000 🪙 (50 ⭐)", callback_data="buy_stars_5000")], [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_bonuses_menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data == "back_to_bonuses_menu":
        text = "🎁 *ЦЕНТР РАЗВИТИЯ КОЛОНИИ И ПОДДЕРЖКИ* 💎"
        kb = [[InlineKeyboardButton("🎁 Ежедневный Бонус (24ч)", callback_data="claim_24h_bonus"), InlineKeyboardButton("🎟️ Ввести Промокод", callback_data="enter_promo")], [InlineKeyboardButton("🏦 Муравьиный Банк", callback_data="menu_bank"), InlineKeyboardButton("🎨 Кастомизация", callback_data="menu_themes_list")], [InlineKeyboardButton("💎 КУПИТЬ МОНЕТЫ (ДОНАТ)", callback_data="menu_donate_stars")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data == "buy_stars_1000":
        await context.bot.send_invoice(chat_id=user_id, title="Пакет «Малый запас» 🪙", description="Покупка 1,000 игровых монет", payload="donate_1000_coins", provider_token="", currency="XTR", prices=[LabeledPrice("1,000 Монет", 15)])
        return

    elif data == "buy_stars_5000":
        await context.bot.send_invoice(chat_id=user_id, title="Пакет «Сундук Королевы» 🪙", description="Покупка 5,000 игровых монет", payload="donate_5000_coins", provider_token="", currency="XTR", prices=[LabeledPrice("5,000 Монет", 50)])
        return

    elif data == "buy_colony_upgrade":
        lvl = ud.get("colony_level", 1)
        cost = lvl * 300
        if ud.get("coins", 0) < cost: return
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -cost, "colony_level": 1}})
        await query.message.reply_text(f"🧬 Эволюция! Твой уровень повышен до *{lvl + 1}*!")
        return

    elif data == "menu_craft":
        cards = get_user_cards(user_id)
        if len(cards) < 3: return
        for bc in cards[:3]: collections_col.delete_one({"_id": bc["_id"]})
        # При крафте случайно выбираем любую непустую редкость
        available_rarities = list(REAL_CARDS_POOL.keys())
        chosen_r = random.choice(available_rarities)
        new_card = random.choice(REAL_CARDS_POOL[chosen_r])
        
        final_card = {**new_card, "rarity": chosen_r}
        add_card_to_db(user_id, final_card)
        await query.message.reply_text(f"🔥 Синтез выполнен! Получен боец: *{final_card['name']}* ({final_card['rarity']})!")
        return

    elif data == "menu_bank":
        dep = ud.get("bank_deposit", 0)
        text = f"🏦 *БАНК ГНЕЗДА*\nВклад: *{dep} 🪙*"
        kb = []
        if ud.get("coins", 0) >= 100: kb.append([InlineKeyboardButton("💰 Положить 100 🪙", callback_data="bank_deposit_100")])
        if dep >= 100: kb.append([InlineKeyboardButton("💸 Снять 100 🪙", callback_data="bank_withdraw_100")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data == "bank_deposit_100":
        if ud.get("coins", 0) < 100: return
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -100, "bank_deposit": 100}})
        await query.message.reply_text("✅ 100 монет отправлены на вклад!")
        return

    elif data == "bank_withdraw_100":
        if ud.get("bank_deposit", 0) < 100: return
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": 100, "bank_deposit": -100}})
        await query.message.reply_text("✅ 100 монет сняты.")
        return

    elif data == "menu_themes_list":
        owned = ud.get("owned_themes", ["default"])
        kb = []
        for key, info in PROFILE_THEMES.items():
            status = " (Куплено)" if key in owned else f" — {info['price']} 🪙"
            kb.append([InlineKeyboardButton(f"{info['name']}{status}", callback_data=f"theme_act_{key}")])
        await query.edit_message_text("🎨 Выберите стиль:", reply_markup=InlineKeyboardMarkup(kb))
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
            await query.message.reply_text("🎉 Локация куплена!")
        return

# ==================== ОБРАБОТЧИКИ ПЛАТЕЖЕЙ TELEGRAM STARS ====================
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    if query.invoice_payload in ["donate_1000_coins", "donate_5000_coins"]: await query.answer(ok=True)
    else: await query.answer(ok=False, error_message="Ошибка платежной системы.")

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    payload = update.message.successful_payment.invoice_payload
    add_coins = 1000 if payload == "donate_1000_coins" else (5000 if payload == "donate_5000_coins" else 0)
    if add_coins > 0:
        register_user(user_id, update.effective_user.first_name, update.effective_user.username)
        update_user_coins(user_id, add_coins)
        await update.message.reply_text(f"💎 На ваш аккаунт зачислено +*{add_coins}* 🪙!", parse_mode="Markdown")

# ==================== ТЕКСТОВЫЙ ОБРАБОТЧИК (ПРОМОКОДЫ) ====================
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    user_text = update.message.text.strip()
    if user_text.upper() == "СТАРТ2026":
        ud = get_user_all_data(user_id)
        if ud.get("promo_claimed_start2026", False): await update.message.reply_text("❌ Промокод уже использован!")
        else:
            users_col.update_one({"user_id": user_id}, {"$set": {"promo_claimed_start2026": True}, "$inc": {"coins": 1000}})
            await update.message.reply_text("🎟️ Активировано! +1000 🪙!")
        return
    await update.message.reply_text("❓ Используйте кнопки меню.")

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
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    application.run_polling()

if __name__ == '__main__':
    main()
