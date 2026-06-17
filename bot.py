import telebot
from telebot import types
import uuid
import random

# 🔑 Актуальный токен
TOKEN = "8930026163:AAGXKa6jYNtPVZ2kTYTpuN2UtlY8ZKxJKWQ"
bot = telebot.TeleBot(TOKEN)

# 👑 ID Администратора
ADMIN_ID = 7501899378

# ==================== БАЗА ДАННЫХ ====================
players = {}
market_lots = {}       
breeding_sessions = {}
LOCKED_INVENTORIES = set() 

# Настройки
PACK_PRICE = 50            
RARE_PACK_PRICE = 150      

REAL_CARDS = [
    {"name": "Муравей-Воин 🐜", "rarity": "⚔️ Военная", "price": 15},
    {"name": "Пчела-Рабочий 🐝", "rarity": "📦 Сборщик", "price": 10},
    {"name": "Элитный Трутень 🍯", "rarity": "⭐ Редкая", "price": 40},
    {"name": "Муравей-Листорез 🍃", "rarity": "⭐ Обычная", "price": 12},
    {"name": "Королевская Нянька 👑", "rarity": "🔮 Эпическая", "price": 100},
    {"name": "Гвардеец Королевы 🛡️", "rarity": "🔮 Эпическая", "price": 120},
]

def init_player(uid, name="Особь"):
    if uid not in players:
        players[uid] = {
            "balance": 500, 
            "inventory": [], 
            "titles": ["🐜 Начинающий Энтомолог"], 
            "username": name
        }

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📦 Открыть пак", "👤 Профиль")
    markup.row("📁 Коллекция", "🛍️ Магазин")
    return markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    bot.send_message(
        message.chat.id, 
        f"🐜 **Добро пожаловать в Улей!**\nВаш ID: `{uid}`", 
        parse_mode="Markdown", 
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda msg: msg.text == "👤 Профиль")
def profile_cmd(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    p = players[uid]
    bot.send_message(
        message.chat.id, 
        f"👤 **Профиль {p['username']}:**\n💰 Баланс: `{p['balance']}`\n🎒 Карт: {len(p['inventory'])}", 
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.text == "📦 Открыть пак")
def open_pack(message):
    uid = message.from_user.id
    if players[uid]["balance"] < PACK_PRICE:
        bot.send_message(message.chat.id, "❌ Недостаточно монет.")
        return
    players[uid]["balance"] -= PACK_PRICE
    chosen = random.choice(REAL_CARDS)
    card = {"id": str(uuid.uuid4())[:8], "name": chosen["name"], "price": chosen["price"]}
    players[uid]["inventory"].append(card)
    bot.send_message(message.chat.id, f"🥚 Вы получили: {card['name']}")

if __name__ == '__main__':
    bot.infinity_polling()
