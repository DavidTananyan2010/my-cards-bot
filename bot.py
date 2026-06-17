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

async def pvp_and_expeditions_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    
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
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    ud = get_user_all_data(user_id)
    
    lvl = ud.get("colony_level", 1)
    cost = lvl * 300
    
    text = (
        "🚀 *ЛАБОРАТОРИЯ ЭВОЛЮЦИИ И КРАФТА* 🔮\n\n"
        f"🧬 Твой уровень колонии: *{lvl}*\n"
        f"Бонус к открытию паков: +{lvl * 5}%\n"
        f"Стоимость следующей мутации: *{cost} 🪙*\n\n"
        "🔮 *Синтез Карт (Крафт)*: Объедини 3 любые карты, чтобы гарантированно получить одну случайную карту из реального списка (без пустышек!)."
    )
    kb = [
        [InlineKeyboardButton(f"🧬 Повысить уровень ({cost} 🪙)", callback_data="buy_colony_upgrade")],
        [InlineKeyboardButton("🔮 Войти в Крафт-Машину", callback_data="menu_craft")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# ==================== ОБНОВЛЕННАЯ КНОПКА: БОНУСЫ & ДОНАТ (Убраны новости) ====================
async def bonuses_and_news_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    
    text = (
        "🎁 *ЦЕНТР РАЗВИТИЯ КОЛОНИИ И ПОДДЕРЖКИ* 💎\n\n"
        "Забирай ежедневные награды, используй коды, настраивай внешний вид гнезда или приобретай монеты за **Telegram Stars (Звёзды)**!"
    )
    kb = [
        [InlineKeyboardButton("🎁 Ежедневный Бонус (24ч)", callback_data="claim_24h_bonus"),
         InlineKeyboardButton("🎟️ Ввести Промокод", callback_data="enter_promo")],
        [InlineKeyboardButton("🏦 Муравьиный Банк", callback_data="menu_bank"),
         InlineKeyboardButton("🎨 Кастомизация", callback_data="menu_themes_list")],
        [InlineKeyboardButton("💎 КУПИТЬ МОНЕТЫ (ДОНАТ)", callback_data="menu_donate_stars")] # Вместо новостей
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


# ==================== CALLBACK-ОБРАБОТЧИК КНОПОК ====================
async def shop_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    ud = get_user_all_data(user_id)
    if not ud: return

    # --- ДОНАТ МЕНЮ (TELEGRAM STARS) ---
    if data == "menu_donate_stars":
        text = (
            "💎 *ПОПОЛНЕНИЕ БАЛАНСА ЗВЁЗДАМИ TELEGRAM* 💎\n\n"
            "Поддержи проект и моментально прокачай свою колонию!\n"
            "Выбери желаемый пакет монет:\n\n"
            "📦 *Пакет «Малый запас»* — 1,000 монет за 15 ⭐️\n"
            "💼 *Пакет «Сундук Королевы»* — 5,000 монет за 50 ⭐️"
        )
        kb = [
            [InlineKeyboardButton("🛒 Купить 1,000 🪙 (15 ⭐)", callback_data="buy_stars_1000")],
            [InlineKeyboardButton("🛒 Купить 5,000 🪙 (50 ⭐)", callback_data="buy_stars_5000")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_bonuses_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data == "back_to_bonuses_menu":
        text = "🎁 *ЦЕНТР РАЗВИТИЯ КОЛОНИИ И ПОДДЕРЖКИ* 💎\n\nЗабирай ежедневные награды, используй коды, настраивай внешний вид гнезда или приобретай монеты за **Telegram Stars**!"
        kb = [
            [InlineKeyboardButton("🎁 Ежедневный Бонус (24ч)", callback_data="claim_24h_bonus"), InlineKeyboardButton("🎟️ Ввести Промокод", callback_data="enter_promo")],
            [InlineKeyboardButton("🏦 Муравьиный Банк", callback_data="menu_bank"), InlineKeyboardButton("🎨 Кастомизация", callback_data="menu_themes_list")],
            [InlineKeyboardButton("💎 КУПИТЬ МОНЕТЫ (ДОНАТ)", callback_data="menu_donate_stars")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    # Запуск процесса оплаты 1,000 монет
    elif data == "buy_stars_1000":
        await context.bot.send_invoice(
            chat_id=user_id,
            title="Пакет «Малый запас» 🪙",
            description="Покупка 1,000 игровых монет в DAcards",
            payload="donate_1000_coins",
            provider_token="", # Для Telegram Stars всегда оставляется ПУСТЫМ
            currency="XTR",   # Код валюты Telegram Stars
            prices=[LabeledPrice("1,000 Монет", 15)]
        )
        return

    # Запуск процесса оплаты 5,000 монет
    elif data == "buy_stars_5000":
        await context.bot.send_invoice(
            chat_id=user_id,
            title="Пакет «Сундук Королевы» 🪙",
            description="Покупка 5,000 игровых монет в DAcards",
            payload="donate_5000_coins",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice("5,000 Монет", 50)]
        )
        return

    # --- ОСТАЛЬНЫЕ МЕХАНИКИ ---
    elif data == "buy_colony_upgrade":
        lvl = ud.get("colony_level", 1)
        cost = lvl * 300
        if ud.get("coins", 0) < cost:
            await query.message.reply_text("❌ Недостаточно монет для эволюции колонии!")
            return
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -cost, "colony_level": 1}})
        await query.message.reply_text(f"🧬 Эволюция прошла успешно! Твой уровень колонии повышен до *{lvl + 1}*!", parse_mode="Markdown")
        return

    elif data == "menu_craft":
        cards = get_user_cards(user_id)
        if len(cards) < 3:
            await query.message.reply_text(f"🔮 Для синтеза нужно иметь хотя бы 3 карты в инвентаре. У тебя сейчас: {len(cards)} шт.")
            return
        burnt_cards = cards[:3]
        for bc in burnt_cards:
            collections_col.delete_one({"_id": bc["_id"]})
        new_card = random.choice(REAL_CARDS)
        add_card_to_db(user_id, new_card)
        await query.message.reply_text(f"🔥 *Реактор запущен!* Синтез выполнен:\n🧬 Результат: *{new_card['name']}* ({new_card['rarity']}) добавлен в твою коллекцию!", parse_mode="Markdown")
        return

    elif data == "play_pvp_battle":
        cards = get_user_cards(user_id)
        power = len(cards) * 10 + (ud.get("colony_level", 1) * 15)
        enemy_power = random.randint(10, 150)
        if power > enemy_power:
            win_coins = random.randint(40, 100)
            users_col.update_one({"user_id": user_id}, {"$inc": {"coins": win_coins, "pvp_wins": 1}})
            msg = f"⚔️ *Победа!*\nТвоя Сила: `{power}` vs Сила Врага: `{enemy_power}`\nНаграда: +*{win_coins}* 🪙"
        else:
            loss_coins = min(ud.get("coins", 0), 30)
            update_user_coins(user_id, -loss_coins)
            msg = f"💀 *Поражение!*\nТвоя Сила: `{power}` vs Сила Врага: `{enemy_power}`\nПотери: -*{loss_coins}* 🪙"
        await query.message.reply_text(msg, parse_mode="Markdown")
        return

    elif data == "menu_expeditions":
        now_str = ud.get("expedition_end", "")
        if now_str:
            end_time = datetime.fromisoformat(now_str)
            if datetime.utcnow() < end_time:
                rem = end_time - datetime.utcnow()
                await query.message.reply_text(f"🗺️ Твои муравьи всё еще в походе! Возвращение через {rem.seconds // 60} мин.")
                return
            else:
                users_col.update_one({"user_id": user_id}, {"$set": {"expedition_end": ""}})
                reward = random.randint(150, 300)
                update_user_coins(user_id, reward)
                await query.message.reply_text(f"🎉 Экспедиция вернулась! Принесено ресурсов на сумму: +*{reward}* 🪙", parse_mode="Markdown")
                return
        finish_time = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        users_col.update_one({"user_id": user_id}, {"$set": {"expedition_end": finish_time}})
        await query.message.reply_text("🗺️ Отряд отправлен в Экспедицию за сладкой росой на 5 минут!")
        return

    elif data == "claim_24h_bonus":
        today_str = date.today().isoformat()
        if ud.get("last_daily_bonus") == today_str:
            await query.message.reply_text("🎁 Твой ежедневный паёк уже получен!")
            return
        bonus = random.randint(50, 150)
        users_col.update_one({"user_id": user_id}, {"$set": {"last_daily_bonus": today_str}, "$inc": {"coins": bonus}})
        await query.message.reply_text(f"🎁 Ресурсы получены! Баланс пополнен на +*{bonus}* 🪙", parse_mode="Markdown")
        return

    elif data == "enter_promo":
        await query.message.reply_text("🎟️ Отправь промокод текстовым сообщением в чат бота! Например: `СТАРТ2026`")
        return

    elif data == "menu_bank":
        dep = ud.get("bank_deposit", 0)
        text = f"🏦 *БАНК ГНЕЗДА*\nВклад: *{dep} 🪙*\n\nПри входе начисляются проценты (+10%)."
        kb = []
        if ud.get("coins", 0) >= 100: kb.append([InlineKeyboardButton("💰 Положить 100 🪙", callback_data="bank_deposit_100")])
        if dep >= 100: kb.append([InlineKeyboardButton("💸 Снять 100 🪙", callback_data="bank_withdraw_100")])
        if dep > 0: users_col.update_one({"user_id": user_id}, {"$inc": {"bank_deposit": int(dep * 0.1)}})
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data == "bank_deposit_100":
        if ud.get("coins", 0) < 100: return
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -100, "bank_deposit": 100}})
        await query.message.reply_text("✅ 100 монет переведены в хранилище банка!")
        return

    elif data == "bank_withdraw_100":
        if ud.get("bank_deposit", 0) < 100: return
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": 100, "bank_deposit": -100}})
        await query.message.reply_text("✅ 100 монет успешно изъяты из банка!")
        return

    elif data == "menu_themes_list":
        owned = ud.get("owned_themes", ["default"])
        text = "🎨 *ЦЕНТР КАСТОМИЗАЦИИ ДИЗАЙНА*\nВыберите стиль:"
        kb = []
        for key, info in PROFILE_THEMES.items():
            status = " (Куплено)" if key in owned else f" — {info['price']} 🪙"
            kb.append([InlineKeyboardButton(f"{info['name']}{status}", callback_data=f"theme_act_{key}")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data.startswith("theme_act_"):
        th_key = data.replace("theme_act_", "")
        owned = ud.get("owned_themes", ["default"])
        if th_key in owned:
            users_col.update_one({"user_id": user_id}, {"$set": {"profile_theme": th_key}})
            await query.message.reply_text("✨ Стиль профиля обновлен!")
        else:
            price = PROFILE_THEMES[th_key]["price"]
            if ud.get("coins", 0) < price:
                await query.message.reply_text("❌ Недостаточно средств.")
            else:
                users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -price}, "$addToSet": {"owned_themes": th_key}, "$set": {"profile_theme": th_key}})
                await query.message.reply_text(f"🎉 Стиль {PROFILE_THEMES[th_key]['name']} куплен!")
        return

    # Заглушки старых систем (Удача и Квесты)
    elif data == "open_lucky_dice_menu":
        await query.message.reply_text(f"🎲 Баланс: {ud.get('coins')} 🪙. Ставка 50 монет.")
        users_col.update_one({"user_id": user_id}, {"$inc": {"coins": -50}})
        reward = random.choice([0, 50, 100, 300])
        update_user_coins(user_id, reward)
        await query.message.reply_text(f"🎲 Выпало: {reward} 🪙")
        return

# ==================== СИСТЕМА ОБРАБОТКИ ПЛАТЕЖЕЙ (TG STARS) ====================
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ответ на предварительный запрос подтверждения покупки"""
    query = update.pre_checkout_query
    # Проверяем, наш ли это payload покупки
    if query.invoice_payload in ["donate_1000_coins", "donate_5000_coins"]:
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Произошла ошибка во время обработки платежа.")

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Действие при успешном списании звёзд"""
    user_id = update.effective_user.id
    payment_info = update.message.successful_payment
    payload = payment_info.invoice_payload
    
    if payload == "donate_1000_coins":
        add_coins = 1000
    elif payload == "donate_5000_coins":
        add_coins = 5000
    else:
        add_coins = 0
        
    if add_coins > 0:
        register_user(user_id, update.effective_user.first_name, update.effective_user.username)
        update_user_coins(user_id, add_coins)
        await update.message.reply_text(
            f"💎 *Спасибо за поддержку проекта!*\n\n"
            f"Платеж прошел успешно. На ваш аккаунт зачислено +*{add_coins}* 🪙!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

# ==================== ТЕКСТОВЫЕ МЕССЕДЖИ ====================
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    user_text = update.message.text.strip()
    
    if user_text.upper() == "СТАРТ2026":
        ud = get_user_all_data(user_id)
        if ud.get("promo_claimed_start2026", False):
            await update.message.reply_text("❌ Ты уже активировал этот код!")
        else:
            users_col.update_one({"user_id": user_id}, {"$set": {"promo_claimed_start2026": True}, "$inc": {"coins": 1000}})
            await update.message.reply_text("🎟️ Промокод активирован! +1000 🪙!")
        return

    await update.message.reply_text("❓ Неизвестная команда. Пожалуйста, используйте кнопки.")

# ==================== ОЧИЩЕННЫЙ СПИСОК /users_list ====================
async def users_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    all_users = list(users_col.find())
    if not all_users:
        await update.message.reply_text("База данных пуста.")
        return
    text = f"👥 *СПИСОК ИГРОКОВ БОТА ({len(all_users)}):*\n\n"
    for user in all_users:
        text += (
            f"• *{escape_markdown(user.get('first_name', 'Игрок'))}*\n"
            f"  ID: `{user.get('user_id')}`\n"
            f"  🪙 Монеты: {user.get('coins', 0)} | 🎖️ Титул: {user.get('active_title', 'Нет')}\n\n"
        )
    await update.message.reply_text(text, parse_mode="Markdown")

# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================
def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(MessageHandler(filters.Text("📦 Открыть пак"), open_pack_handler))
    application.add_handler(MessageHandler(filters.Text("👤 Профиль"), profile_handler))
    
    application.add_handler(MessageHandler(filters.Text("⚔️ Походы & Битвы"), pvp_and_expeditions_main_handler))
    application.add_handler(MessageHandler(filters.Text("🚀 Прокачка & Крафт"), upgrade_and_craft_main_handler))
    application.add_handler(MessageHandler(filters.Text("🎁 Бонусы & Донат"), bonuses_and_news_main_handler))
    
    application.add_handler(CommandHandler("users_list", users_list_command))
    application.add_handler(CallbackQueryHandler(shop_callback_handler))
    
    # Хэндлеры для работы платежной системы (Донат)
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    application.run_polling()

if __name__ == '__main__':
    main()
