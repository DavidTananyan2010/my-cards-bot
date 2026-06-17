import telebot
from telebot import types
import uuid
import random

# 🔑 Токен
TOKEN = "8930026163:AAGXKa6jYNtPVZ2kTYTpuN2UtlY8ZKxJKWQ"
bot = telebot.TeleBot(TOKEN)

# 👑 ID Администратора
ADMIN_ID = 7501899378

# База данных
players = {}
PACK_PRICE = 50            
REAL_CARDS = [
    {"name": "Муравей-Воин 🐜", "price": 15},
    {"name": "Пчела-Рабочий 🐝", "price": 10},
    {"name": "Элитный Трутень 🍯", "price": 40},
]

def init_player(uid, name):
    if uid not in players:
        players[uid] = {"balance": 500, "inventory": [], "username": name}

@bot.message_handler(commands=['start'])
def start_cmd(message):
    init_player(message.from_user.id, message.from_user.first_name)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📦 Открыть пак", "👤 Профиль")
    bot.send_message(message.chat.id, "🐜 Улей открыт. Используйте кнопки:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "📦 Открыть пак")
def open_pack(message):
    uid = message.from_user.id
    if players[uid]["balance"] < PACK_PRICE:
        bot.send_message(message.chat.id, "❌ Недостаточно монет.")
        return
    players[uid]["balance"] -= PACK_PRICE
    card = random.choice(REAL_CARDS)
    players[uid]["inventory"].append(card)
    bot.send_message(message.chat.id, f"🥚 Вы получили: {card['name']}")

@bot.message_handler(func=lambda msg: msg.text == "👤 Профиль")
def profile(message):
    uid = message.from_user.id
    p = players[uid]
    bot.send_message(message.chat.id, f"👤 {p['username']}\n💰 Баланс: {p['balance']}")

if __name__ == '__main__':
    bot.infinity_polling()
