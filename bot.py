import logging
import random
import os
import asyncio
import time  # Добавлено для отслеживания времени кулдауна
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

# Словарь для хранения кулдаунов в оперативной памяти: {user_id: timestamp_последнего_открытия}
COOLDOWNS = {}
COOLDOWN_TIME = 1.5  # Время задержки в секунда

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
    
    # --- ПРОВЕРКА КУЛДАУНА (1.5 СЕКУНДЫ) ---
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
            
    # Обновляем время последнего успешного открытия
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

# ==================== АДМИН-КОМАНДЫ ====================
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
    
    application.add_handler(CommandHandler("givecoins", admin_give_coins))
    application.add_handler(CommandHandler("givetitle", admin_give_title))
    application.add_handler(CallbackQueryHandler(shop_callback_handler))

    application.run_polling()

if __name__ == '__main__':
    main()
