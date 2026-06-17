import telebot
from telebot import types
import uuid
import random

# 🔑 Ваши проверенные данные доступа
TOKEN = "8930026163:AAGXKa6jYNtPVZ2kTYTpuN2UtlY8ZKxJKWQ"
bot = telebot.TeleBot(TOKEN)

# 👑 Королева улья (Администратор)
ADMIN_ID = 7501899378

# ==================== БАЗА ДАННЫХ И ЦЕНЫ ====================
players = {}

PACK_PRICE = 50            # Стоимость обычного кокона
RARE_PACK_PRICE = 150      # Стоимость элитного яйца

# Сеттинг колонии: муравьи и пчёлы
COLONY_UNITS = [
    {"name": "Муравей-Воин 🐜", "rarity": "⚔️ Военная особь", "price": 15},
    {"name": "Пчела-Рабочий 🐝", "rarity": "📦 Сборщик нектара", "price": 10},
    {"name": "Элитный Трутень 🍯", "rarity": "⭐ Редкая особь", "price": 40},
    {"name": "Муравей-Листорез 🍃", "rarity": "⭐ Обычная особь", "price": 12},
    {"name": "Королевская Нянька 👑", "rarity": "🔮 Эпическая особь", "price": 100},
    {"name": "Гвардеец Королевы 🛡️", "rarity": "🔮 Эпическая особь", "price": 120},
    {"name": "Муравей-Разведчик 🔭", "rarity": "⭐ Обычная особь", "price": 15},
    {"name": "Мистический Рой 🌌", "rarity": "🌌 Легендарный рой", "price": 300},
]

def init_player(uid, name="Особь"):
    if uid not in players:
        players[uid] = {
            "balance": 500,           # Стартовая биомасса
            "colony": [],             # Список выращенных насекомых
            "username": name
        }

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🥚 Инкубатор коконов", "🏰 Мой Муравейник")
    markup.row("📁 Список особей", "🛍️ Магазин Улья")
    return markup

# ==================== ЛОГИКА КОМАНД ====================

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    
    msg_text = f"🐜 **Добро пожаловать в симулятор Колонии!**\nВаш ID в улье: `{uid}`"
    if uid == ADMIN_ID:
        msg_text += "\n\n👑 Приветствуем, Королева улья! Доступ зафиксирован."
        
    bot.send_message(message.chat.id, msg_text, parse_mode="Markdown", reply_markup=main_keyboard())

@bot.message_handler(func=lambda msg: msg.text == "🏰 Мой Муравейник")
def profile_cmd(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    p = players[uid]
    
    bot.send_message(
        message.chat.id, 
        f"🏰 **Состояние муравейника {p['username']}:**\n\n"
        f"💰 **Запас биомассы:** `{p['balance']}` монет\n"
        f"🐜 **Всего особей в колонии:** {len(p['colony'])} шт.",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.text == "🥚 Инкубатор коконов")
def open_pack(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    
    if players[uid]["balance"] < PACK_PRICE:
        bot.send_message(message.chat.id, f"❌ Недостаточно биомассы. Инкубация стоит {PACK_PRICE} монет.")
        return
        
    players[uid]["balance"] -= PACK_PRICE
    chosen = random.choice(COLONY_UNITS)
    
    unit = {
        "id": str(uuid.uuid4())[:8], 
        "name": chosen["name"], 
        "rarity": chosen["rarity"], 
        "price": chosen["price"]
    }
    players[uid]["colony"].append(unit)
    
    bot.send_message(
        message.chat.id, 
        f"🥚 **В инкубаторе лопнул кокон!**\nВ вашу колонию добавлена новая особь: **{unit['name']}**\nКласс: _{unit['rarity']}_", 
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.text == "📁 Список особей")
def collection_cmd(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    
    if not players[uid]["colony"]:
        bot.send_message(message.chat.id, "🐜 Ваша колония пуста. Отправляйтесь в инкубатор, чтобы вырастить первых рабочих!")
        return
        
    bot.send_message(message.chat.id, "🗂️ **Особи вашей колонии:**")
    for unit in players[uid]["colony"]:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("♻️ Сдать в улей за биомассу", callback_data=f"sell_{unit['id']}"))
        
        bot.send_message(
            message.chat.id, 
            f"🐜 **{unit['name']}**\n🧬 Роль: {unit['rarity']}\n💰 Ценность биомассы: {unit['price']} монет\nID: `{unit['id']}`", 
            parse_mode="Markdown", 
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("sell_"))
def sell_callback(call):
    uid = call.from_user.id
    unit_id = call.data.split("_")[1]
    
    if uid not in players: return
    
    unit = next((u for u in players[uid]["colony"] if u["id"] == unit_id), None)
    if unit:
        players[uid]["balance"] += unit["price"]
        players[uid]["colony"].remove(unit)
        bot.answer_callback_query(call.id, f"Особь переработана в +{unit['price']} биомассы!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ Особь не найдена в муравейнике.", show_alert=True)

@bot.message_handler(func=lambda msg: msg.text == "🛍️ Магазин Улья")
def store_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(f"🥚 Обычный кокон ({PACK_PRICE} 💰)", callback_data="buy_colony_pack"))
    markup.row(types.InlineKeyboardButton(f"🍯 Элитное яйцо ({RARE_PACK_PRICE} 💰)", callback_data="buy_colony_rare"))
    bot.send_message(message.chat.id, "🛍️ **Добро пожаловать на торговую площадку Улья!**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_colony_"))
def buy_callback(call):
    uid = call.from_user.id
    init_player(uid, call.from_user.first_name)
    goods = call.data.replace("buy_colony_", "")
    
    if goods == "pack":
        if players[uid]["balance"] < PACK_PRICE:
            bot.answer_callback_query(call.id, "❌ Недостаточно биомассы!", show_alert=True)
            return
        players[uid]["balance"] -= PACK_PRICE
        chosen = random.choice(COLONY_UNITS)
        unit = {"id": str(uuid.uuid4())[:8], "name": chosen["name"], "rarity": chosen["rarity"], "price": chosen["price"]}
        players[uid]["colony"].append(unit)
        bot.send_message(call.message.chat.id, f"🛒 Куплен кокон! Вывелась особь: **{unit['name']}**")
        
    elif goods == "rare":
        if players[uid]["balance"] < RARE_PACK_PRICE:
            bot.answer_callback_query(call.id, "❌ Недостаточно биомассы!", show_alert=True)
            return
        players[uid]["balance"] -= RARE_PACK_PRICE
        rares = [u for u in COLONY_UNITS if "Эпическая" in u["rarity"] or "Легендарный" in u["rarity"]]
        chosen = random.choice(rares)
        unit = {"id": str(uuid.uuid4())[:8], "name": f"👑 Элитная {chosen['name']}", "rarity": chosen["rarity"], "price": chosen["price"] * 2}
        players[uid]["colony"].append(unit)
        bot.send_message(call.message.chat.id, f"🛒 Из элитного яйца появилась: **{unit['name']}**")

if __name__ == '__main__':
    bot.infinity_polling()
