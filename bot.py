import logging
import random
import os
import asyncio
import time  # Для отслеживания времени кулдауна
import threading  # Для фонового веб-сервера
from datetime import datetime, date  # Для работы с датой, временем и квестами
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

COOLDOWNS = {}
COOLDOWN_TIME = 1.5 

# Вспомогательная функция для безопасного вывода юзернеймов в Markdown
def escape_markdown(text):
    if not text:
        return ""
    for c in ['_', '*', '`', '[']:
        text = text.replace(c, f"\\{c}")
    return text

# ==================== ОБНОВЛЕННАЯ СТИЛЬНАЯ КЛАВИАТУРА ====================
def get_main_keyboard():
    buttons = [
        ["📦 Открыть пак", "👤 Мой профиль"],      
        ["🗂️ Моя коллекция", "🏆 ТОП игроков"],    
        ["🛍️ Магазин", "🎲 Зона Удачи & Квесты"], # Наша новая мега-кнопка
        ["⚠️ Сброс прогресса"]       
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
def register_user(user_id, first_name, username=None):
    update_data = {"first_name": first_name}
    if username:
        update_data["username"] = username

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
                # Поля для ежедневной статистики (квестов)
                "daily_date": "",
                "daily_packs": 0,
                "daily_games": 0,
                "daily_reward_packs_claimed": False,
                "daily_reward_games_claimed": False
            }
        },
        upsert=True
    )

def get_user_stats(user_id):
    user = users_col.find_one({"user_id": user_id})
    if user:
        return user.get("coins", 0), user.get("packs_opened", 0), user.get("active_title", "Нет титула"), user.get("owned_titles", ["Нет титула"])
    return 0, 0, "Нет титула", ["Нет титула"]

def increment_packs(user_id):
    # Общий счетчик
    users_col.update_one({"user_id": user_id}, {"$inc": {"packs_opened": 1}})
    # Ежедневный счетчик квестов
    check_and_reset_daily(user_id)
    users_col.update_one({"user_id": user_id}, {"$inc": {"daily_packs": 1}})

def increment_daily_games(user_id):
    check_and_reset_daily(user_id)
    users_col.update_one({"user_id": user_id}, {"$inc": {"daily_games": 1}})

def check_and_reset_daily(user_id):
    """Сверяет текущую дату. Если день изменился — сбрасывает дневной прогресс квестов."""
    today_str = date.today().isoformat()
    user = users_col.find_one({"user_id": user_id})
    if user and user.get("daily_date") != today_str:
        users_col.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "daily_date": today_str,
                    "daily_packs": 0,
                    "daily_games": 0,
                    "daily_reward_packs_claimed": False,
                    "daily_reward_games_claimed": False
                }
            }
        )

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
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    await update.message.reply_text("Добро пожаловать в DAcards! Выберите действие в меню ниже:", reply_markup=get_main_keyboard())

async def open_pack_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    
    current_time = time.time()
    if user_id in COOLDOWNS:
        time_passed = current_time - COOLDOWNS[user_id]
        if time_passed < COOLDOWN_TIME:
            time_left = COOLDOWN_TIME - time_passed
            await update.message.reply_text(
                f"⏳ *Подождите еще {time_left:.1f} сек.* перед следующим открытием пака!", 
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
            
    COOLDOWNS[user_id] = current_time
    
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
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    coins, packs, title, _ = get_user_stats(user_id)
    
    profile_text = f"👤 *Профиль игрока {update.effective_user.first_name}*\nID: `{user_id}`\n🎖️ Титул: *{title}*\n🪙 Баланс: {coins} монеток\n📦 Открыто паков: {packs}\n"
    await update.message.reply_text(profile_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

# ==================== УВЕЛИЧЕННЫЙ ТОП ДО 20 МЕСТ ====================
async def top_players_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = users_col.find().sort("coins", -1).limit(20) # Лимит до 20 мест
    text = "🏆 *ТОП-20 БОГАТЕЙШИХ ИГРОКОВ DAcards* 🏆\n\n"
    for index, user in enumerate(top_users, start=1):
        if index == 1: emoji = "🥇"
        elif index == 2: emoji = "🥈"
        elif index == 3: emoji = "🥉"
        elif index <= 10: emoji = "✨"
        else: emoji = "▪️"
        
        text += f"{emoji} *{user.get('first_name', 'Игрок')}* — {user.get('coins', 0)} 🪙 ({user.get('active_title', 'Нет титула')})\n"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard())

# ==================== МЕНЮ НОВОЙ КНОПКИ: УДАЧА И КВЕСТЫ ====================
async def lucky_and_quests_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    
    text = (
        "🎲 *ИГРОВАЯ ЗОНА DAcards* 📋\n\n"
        "Рады приветствовать тебя в развлекательном секторе!\n"
        "Выбирай, чем хочешь заняться:\n\n"
        "🎲 *Испытать удачу* — делай ставки монетами и выигрывай джекпоты!\n"
        "📋 *Ежедневные задания* — выполняй регулярные квесты и получай стабильный доход!"
    )
    kb = [
        [InlineKeyboardButton("🎲 Испытать удачу", callback_data="open_lucky_dice_menu")],
        [InlineKeyboardButton("📋 Ежедневные задания", callback_data="open_daily_quests_menu")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# ==================== ЛОГИКА СТИЛЬНОЙ КОЛЛЕКЦИИ (УДАЛЕНИЕ НА ВЫБОР) ====================
async def collection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
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
        keyboard.append([InlineKeyboardButton(f"❌ Удалить 1 шт: {name}", callback_data=f"delete_card_{name}")])
        
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==================== ИНТЕРАКТИВНЫЙ СБРОС ПРОГРЕССА (БЕЗОПАСНОСТЬ) ====================
async def request_reset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    
    kb = [
        [InlineKeyboardButton("✅ Да, сбросить всё", callback_data="confirm_full_reset"),
         InlineKeyboardButton("❌ Отмена", callback_data="cancel_reset")]
    ]
    await update.message.reply_text(
        "⚠️ *ВНИМАНИЕ! ПОЛНОЕ ОБНУЛЕНИЕ ПРОФИЛЯ!*\n\n"
        "Вы действительно хотите навсегда стереть ваш прогресс, обнулить баланс монет и полностью очистить коллекцию карт? Это действие нельзя отменить!",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

# ==================== СТРУКТУРИРОВАННЫЙ МАГАЗИН ====================
async def open_shop_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id, update.effective_user.first_name, update.effective_user.username)
    
    keyboard = [
        [InlineKeyboardButton("🎫 Магазин титулов", callback_data="menu_titles"),
         InlineKeyboardButton("💰 Продажа карт", callback_data="menu_cards")]
    ]
    await update.message.reply_text("🛍️ *Главное меню Торгового Центра DAcards.*\nВыберите необходимый отдел:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==================== АДМИНИСТРАТИВНЫЕ КОМАНДЫ ====================
async def users_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    all_users = list(users_col.find())
    if not all_users:
        await update.message.reply_text("База данных пользователей пуста.")
        return
        
    text = f"👥 *СПИСОК ВСЕХ ИГРОКОВ БОТА ({len(all_users)}):*\n\n"
    
    for user in all_users:
        username_val = user.get("username")
        if username_val:
            username_text = f"@{escape_markdown(username_val)}"
        else:
            username_text = "_нет юзернейма_"
        
        joined_at_str = user.get("joined_at")
        time_spent_text = "Неизвестно"
        
        if joined_at_str:
            try:
                joined_at_dt = datetime.fromisoformat(joined_at_str)
                delta = datetime.utcnow() - joined_at_dt
                days = delta.days
                hours = delta.seconds // 3600
                minutes = (delta.seconds % 3600) // 60
                
                time_parts = []
                if days > 0: time_parts.append(f"{days} дн.")
                if hours > 0: time_parts.append(f"{hours} ч.")
                time_parts.append(f"{minutes} мин.")
                time_spent_text = " ".join(time_parts)
            except:
                pass

        text += (
            f"• *{escape_markdown(user.get('first_name', 'Игрок'))}* | {username_text}\n"
            f"  ID: `{user.get('user_id')}`\n"
            f"  🪙 Монеты: {user.get('coins', 0)} | 🎖️ Титул: {user.get('active_title', 'Нет')}\n"
            f"  ⏱️ В боте: `{time_spent_text}`\n\n"
        )
        
    await update.message.reply_text(text, parse_mode="Markdown")

async def admin_players_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
        
    all_users = list(users_col.find())
    if not all_users:
        await update.message.reply_text("Нет игроков для управления.")
        return
        
    kb = []
    for user in all_users:
        kb.append([InlineKeyboardButton(f"⚙️ Управлять: {user.get('first_name', 'Игрок')}", callback_data=f"adm_manage_{user.get('user_id')}")])
        
    await update.message.reply_text("🛠️ *Панель управления игроками.*\nВыберите пользователя:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


# ==================== CALLBACK-ОБРАБОТЧИК КНОПОК ====================
async def shop_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    # Сразу проверяем и подгружаем актуальные данные по квестам, чтобы не было багов с датой
    check_and_reset_daily(user_id)
    user_data = users_col.find_one({"user_id": user_id})

    # --- МЕНЮ «ИСПЫТАТЬ УДАЧУ» ---
    if data == "open_lucky_dice_menu":
        coins = user_data.get("coins", 0)
        text = (
            "🎲 *ИСПЫТАЙ СВОЮ УДАЧУ!* 🎲\n\n"
            "Каждая попытка бросить кубики стоит *50 монет*.\n\n"
            "Возможные исходы:\n"
            "🔴 Проигрыш (0 монет) [Шанс 50%]\n"
            "🟡 Возврат ставки (50 монет) [Шанс 30%]\n"
            "🟢 Небольшой выигрыш (100 монет) [Шанс 15%]\n"
            "🔥 ДЖЕКПОТ (300 монет)! [Шанс 5%]\n\n"
            f"💰 Твой баланс: {coins} 🪙"
        )
        kb = [
            [InlineKeyboardButton("🎲 Бросить кубики (50 🪙)", callback_data="play_lucky_dice")],
            [InlineKeyboardButton("⬅️ Назад в Игровую Зону", callback_data="back_to_games_zone")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    elif data == "play_lucky_dice":
        coins = user_data.get("coins", 0)
        if coins < 50:
            await query.message.reply_text("❌ У вас недостаточно монет для игры! Требуется минимум 50 🪙.")
            return
            
        # Засчитываем игру для ежедневного квеста
        increment_daily_games(user_id)
        update_user_coins(user_id, -50)
        
        roll = random.randint(1, 100)
        if roll <= 50:
            result_text = "🔴 Увы! Ваши кубики легли неудачно. Вы потеряли 50 🪙."
            reward = 0
        elif roll <= 80:
            result_text = "🟡 Почти! Кубики вернули вашу ставку. Начислено: +50 🪙."
            reward = 50
        elif roll <= 95:
            result_text = "🟢 Отлично! Удача улыбнулась вам. Начислено: +100 🪙."
            reward = 100
        else:
            result_text = "🔥 ОГО! ВЫ ВЫБИЛИ ДЖЕКПОТ! Начислено: +300 🪙."
            reward = 300
            
        update_user_coins(user_id, reward)
        new_coins = coins - 50 + reward
        
        text = (
            f"🎲 *Результат игры:*\n\n{result_text}\n\n"
            f"💰 Ваш обновленный баланс: {new_coins} 🪙"
        )
        kb = [
            [InlineKeyboardButton("🎲 Сыграть еще раз (50 🪙)", callback_data="play_lucky_dice")],
            [InlineKeyboardButton("⬅️ Назад в Игровую Зону", callback_data="back_to_games_zone")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    # --- МЕНЮ «ЕЖЕДНЕВНЫЕ ЗАДАНИЯ» ---
    elif data == "open_daily_quests_menu":
        dp = user_data.get("daily_packs", 0)
        dg = user_data.get("daily_games", 0)
        rc_packs = user_data.get("daily_reward_packs_claimed", False)
        rc_games = user_data.get("daily_reward_games_claimed", False)
        
        # Формируем текст первого задания
        status_packs = "✅ Выполнено" if dp >= 5 else f"⏳ Прогресс: `{dp}/5`"
        btn_text_packs = "🎁 Забрать 80 🪙" if dp >= 5 and not rc_packs else ("🎉 Забрано" if rc_packs else "❌ Не выполнено")
        
        # Формируем текст второго задания
        status_games = "✅ Выполнено" if dg >= 3 else f"⏳ Прогресс: `{dg}/3`"
        btn_text_games = "🎁 Забрать 60 🪙" if dg >= 3 and not rc_games else ("🎉 Забрано" if rc_games else "❌ Не выполнено")

        text = (
            "📋 *ЕЖЕДНЕВНЫЕ ЗАДАНИЯ DAcards* 📋\n\n"
            "Выполняй задания каждый день. Прогресс обновляется в полночь!\n\n"
            f"📦 *Задание 1: Начинающий кладоискатель*\nОткрыть 5 любых паков за сегодня.\n{status_packs}\n\n"
            f"🎲 *Задание 2: Азартный игрок*\nСыграть в мини-игру «Испытать удачу» 3 раза.\n{status_games}\n"
        )
        
        kb = [
            [InlineKeyboardButton(f"Задание 1: {btn_text_packs}", callback_data="claim_reward_packs")],
            [InlineKeyboardButton(f"Задание 2: {btn_text_games}", callback_data="claim_reward_games")],
            [InlineKeyboardButton("⬅️ Назад в Игровую Зону", callback_data="back_to_games_zone")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    # Выдача наград за паки
    elif data == "claim_reward_packs":
        dp = user_data.get("daily_packs", 0)
        rc_packs = user_data.get("daily_reward_packs_claimed", False)
        
        if dp < 5:
            await query.message.reply_text("🛑 Вы еще не открыли 5 паков сегодня!")
            return
        if rc_packs:
            await query.message.reply_text("🛑 Вы уже забрали эту награду сегодня!")
            return
            
        users_col.update_one({"user_id": user_id}, {"$set": {"daily_reward_packs_claimed": True}})
        update_user_coins(user_id, 80)
        await query.message.reply_text("🎉 Отлично! Вам начислено +80 🪙 за выполнение ежедневного квеста!")
        return

    # Выдача наград за игры
    elif data == "claim_reward_games":
        dg = user_data.get("daily_games", 0)
        rc_games = user_data.get("daily_reward_games_claimed", False)
        
        if dg < 3:
            await query.message.reply_text("🛑 Вы еще не сыграли 3 раза в мини-игру сегодня!")
            return
        if rc_games:
            await query.message.reply_text("🛑 Вы уже забрали эту награду сегодня!")
            return
            
        users_col.update_one({"user_id": user_id}, {"$set": {"daily_reward_games_claimed": True}})
        update_user_coins(user_id, 60)
        await query.message.reply_text("🎉 Отлично! Вам начислено +60 🪙 за выполнение ежедневного квеста!")
        return

    elif data == "back_to_games_zone":
        text = (
            "🎲 *ИГРОВАЯ ЗОНА DAcards* 📋\n\n"
            "Рады приветствовать тебя в развлекательном секторе!\n"
            "Выбирай, чем хочешь заняться:\n\n"
            "🎲 *Испытать удачу* — делай ставки монетами и выигрывай джекпоты!\n"
            "📋 *Ежедневные задания* — выполняй регулярные квесты и получай стабильный доход!"
        )
        kb = [
            [InlineKeyboardButton("🎲 Испытать удачу", callback_data="open_lucky_dice_menu")],
            [InlineKeyboardButton("📋 Ежедневные задания", callback_data="open_daily_quests_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    # --- ЛОГИКА АДМИН-ПАНЕЛИ (ADMIN_PLAYERS) ---
    elif data.startswith("adm_manage_"):
        if user_id != ADMIN_ID: return
        target_uid = int(data.replace("adm_manage_", ""))
        target_user = users_col.find_one({"user_id": target_uid})
        
        if not target_user:
            await query.edit_message_text("Пользователь не найден.")
            return
            
        text = f"👤 *Управление игроком:* {target_user.get('first_name')}\nID: `{target_uid}`\nБаланс: {target_user.get('coins', 0)} 🪙"
        kb = [
            [InlineKeyboardButton("➕ Дать 500 монет", callback_data=f"adm_give_500_{target_uid}"),
             InlineKeyboardButton("➖ Забрать 500 монет", callback_data=f"adm_take_500_{target_uid}")],
            [InlineKeyboardButton("❌ Обнулить игрока", callback_data=f"adm_reset_player_{target_uid}")],
            [InlineKeyboardButton("⬅️ К списку игроков", callback_data="adm_back_to_list")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return
        
    elif data.startswith("adm_give_500_"):
        if user_id != ADMIN_ID: return
        target_uid = int(data.replace("adm_give_500_", ""))
        update_user_coins(target_uid, 500)
        await query.edit_message_text(f"✅ Успешно выдано +500 монет игроку `{target_uid}`!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data=f"adm_manage_{target_uid}")]]) )
        return

    elif data.startswith("adm_take_500_"):
        if user_id != ADMIN_ID: return
        target_uid = int(data.replace("adm_take_500_", ""))
        update_user_coins(target_uid, -500)
        await query.edit_message_text(f"✅ Успешно изъято -500 монет у игрока `{target_uid}`!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data=f"adm_manage_{target_uid}")]]) )
        return

    elif data.startswith("adm_reset_player_"):
        if user_id != ADMIN_ID: return
        target_uid = int(data.replace("adm_reset_player_", ""))
        users_col.update_one({"user_id": target_uid}, {"$set": {"coins": 500, "packs_opened": 0, "active_title": "Нет титула", "owned_titles": ["Нет титула"], "joined_at": datetime.utcnow().isoformat()}})
        collections_col.delete_many({"user_id": target_uid})
        await query.edit_message_text(f"💥 Полный сброс игрока `{target_uid}` выполнен!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="adm_back_to_list")]]) )
        return

    elif data == "adm_back_to_list":
        if user_id != ADMIN_ID: return
        all_users = list(users_col.find())
        kb = [[InlineKeyboardButton(f"⚙️ Управлять: {u.get('first_name')}", callback_data=f"adm_manage_{u.get('user_id')}")] for u in all_users]
        await query.edit_message_text("🛠️ *Панель управления игроками.*\nВыберите пользователя:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    # --- БЕЗОПАСНЫЙ СБРОС ДАННЫХ ПОЛЬЗОВАТЕЛЯ ---
    elif data == "confirm_full_reset":
        users_col.update_one(
            {"user_id": user_id},
            {"$set": {"coins": 500, "packs_opened": 0, "active_title": "Нет титула", "owned_titles": ["Нет титула"], "joined_at": datetime.utcnow().isoformat()}}
        )
        collections_col.delete_many({"user_id": user_id})
        await query.edit_message_text("♻️ *Ваш прогресс успешно аннулирован!*\nБаланс сброшен до 500 монет, коллекция полностью очищена.", parse_mode="Markdown")
        return
        
    elif data == "cancel_reset":
        await query.edit_message_text("❌ *Сброс отменен.* Ваши карты и монеты остались в полной сохранности!", parse_mode="Markdown")
        return

    # --- НАВИГАЦИЯ МЕНЮ МАГАЗИНА ---
    elif data == "menu_titles":
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
            await query.message.reply_text("🛑 У вас нет карт для продажи.", reply_markup=get_main_keyboard())
            return
        income = sum(c.get("price", 0) for c in cards)
        update_user_coins(user_id, income)
        collections_col.delete_many({"user_id": user_id})
        await query.edit_message_text(f"💵 Сделка совершена! Вы продали все свои карты ({len(cards)} шт.) и получили +*{income}* 🪙", parse_mode="Markdown")

    # --- ЛОГИКА КАРТ: ПРОДАТЬ ДУБЛИКАТЫ ---
    elif data == "sell_duplicates":
        cards = get_user_cards(user_id)
        if not cards:
            await query.message.reply_text("🛑 Ваш инвентарь пуст.", reply_markup=get_main_keyboard())
            return
        
        seen = set()
        duplicates_ids = []
        income = 0
        
        for c in cards:
            name = c["card_name"]
            if name in seen:
                duplicates_ids.append(c["_id"])
                income += c.get("price", 0)
            else:
                seen.add(name)
                
        if not duplicates_ids:
            await query.edit_message_text("♻️ У вас нет повторяющихся карт. Все карты в коллекции уникальны! ✨")
            return
            
        collections_col.delete_many({"_id": {"$in": duplicates_ids}})
        update_user_coins(user_id, income)
        await query.edit_message_text(f"♻️ Дубликаты успешно проданы! Очищено карт: *{len(duplicates_ids)} шт.* Выручка: +*{income}* 🪙. По одному экземпляру каждой карты сохранено!", parse_mode="Markdown")

    # --- ТИТУЛЫ: СПИСОК ПОКУПКИ ---
    elif data == "buy_title_list":
        coins, _, active_title, owned_titles = get_user_stats(user_id)
        text = f"🛍️ *Витрина титулов*\nВаш баланс: {coins} 🪙\n\nВыберите титул:"
        kb = []
        for key, info in SHOP_TITLES.items():
            if info['name'] in owned_titles:
                status = " (Куплен)"
            else:
                status = f" — {info['price']} 🪙"
            kb.append([InlineKeyboardButton(f"{info['name']}{status}", callback_data=f"proc_buy_{key}")])
        kb.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_titles")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data.startswith("proc_buy_"):
        title_key = data.replace("proc_buy_", "")
        if title_key in SHOP_TITLES:
            info = SHOP_TITLES[title_key]
            coins, _, _, owned_titles = get_user_stats(user_id)
            
            if info['name'] in owned_titles:
                await query.message.reply_text("🛑 Этот титул уже приобретен. Наденьте его через Гардеробную!", reply_markup=get_main_keyboard())
                return
            if coins < info['price']:
                await query.message.reply_text("❌ Недостаточно монет для покупки данного статуса.", reply_markup=get_main_keyboard())
            else:
                update_user_coins(user_id, -info['price'])
                add_title_to_owned(user_id, info['name'])
                set_user_title(user_id, info['name'])
                await query.edit_message_text(f"🎉 Роскошное приобретение! Вы разблокировали и надели титул *{info['name']}*.", parse_mode="Markdown")

    # --- ТИТУЛЫ: ГАРДЕРОБНАЯ / НАДЕТЬ ---
    elif data == "wardrobe_list":
        _, _, active_title, owned_titles = get_user_stats(user_id)
        text = f"👗 *Ваша персональная гардеробная*\nТекущий активный титул: *{active_title}*\n\nНажмите на титул, чтобы активировать его:"
        kb = []
        for t_name in owned_titles:
            tag = " ✅" if t_name == active_title else ""
            kb.append([InlineKeyboardButton(f"{t_name}{tag}", callback_data=f"wear_{t_name}")])
        kb.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_titles")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data.startswith("wear_"):
        title_to_wear = data.replace("wear_", "")
        set_user_title(user_id, title_to_wear)
        await query.edit_message_text(f"👑 Изменение стиля! Вы успешно надели титул: *{title_to_wear}*", parse_mode="Markdown")

# ==================== СТАРЫЕ АДМИН-КОМАНДЫ (ЧЕРЕЗ АРГУМЕНТЫ) ====================
async def admin_give_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        target_id, amount = int(context.args[0]), int(context.args[1])
        update_user_coins(target_id, amount)
        await update.message.reply_text(f"✅ Баланс игрока `{target_id}` изменен на {amount} 🪙.")
    except: pass

async def admin_give_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        target_id = int(context.args[0])
        title_name = " ".join(context.args[1:])
        add_title_to_owned(target_id, title_name)
        set_user_title(target_id, title_name)
        await update.message.reply_text(f"✅ Игроку `{target_id}` выдан титул: {title_name}")
    except: pass

# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================
def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(MessageHandler(filters.Text("📦 Открыть пак"), open_pack_handler))
    application.add_handler(MessageHandler(filters.Text("🛍️ Магазин"), open_shop_main))
    application.add_handler(MessageHandler(filters.Text("🗂️ Моя коллекция"), collection_handler))
    application.add_handler(MessageHandler(filters.Text("👤 Мой профиль"), profile_handler))
    application.add_handler(MessageHandler(filters.Text("🏆 ТОП игроков"), top_players_handler))
    application.add_handler(MessageHandler(filters.Text("⚠️ Сброс прогресса"), request_reset_handler))
    
    # Регистрация новой объединенной кнопки
    application.add_handler(MessageHandler(filters.Text("🎲 Зона Удачи & Квесты"), lucky_and_quests_main_handler))
    
    # Регистрация админских команд
    application.add_handler(CommandHandler("users_list", users_list_command))
    application.add_handler(CommandHandler("admin_players", admin_players_command))
    
    application.add_handler(CommandHandler("givecoins", admin_give_coins))
    application.add_handler(CommandHandler("givetitle", admin_give_title))
    application.add_handler(CallbackQueryHandler(shop_callback_handler))

    application.run_polling()

if __name__ == '__main__':
    main()
