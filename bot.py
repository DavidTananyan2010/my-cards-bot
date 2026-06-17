import telebot
from telebot import types
import uuid
import random

# 🔑 Актуальный токен
TOKEN = "8930026163:AAGXKa6jYNtPVZ2kTYTpuN2UtlY8ZKxJKWQ"
bot = telebot.TeleBot(TOKEN)

# 👑 ID Администратора
ADMIN_ID = 7501899378

# ==================== БАЗА ДАННЫХ И СИСТЕМНЫЕ ПЕРЕМЕННЫЕ ====================
players = {}
market_lots = {}       
breeding_sessions = {}
FROZEN_USERS = set()       
BANNED_USERS = set()       
USER_WARNS = {}            
LOCKED_INVENTORIES = set() 

# Настройки экономики
DROP_EMPTY_CHANCE = 30     
PACK_PRICE = 50            
RARE_PACK_PRICE = 150      
ECONOMY_BOOST = 1.0        

REAL_CARDS = [
    {"name": "Муравей-Воин 🐜", "rarity": "⚔️ Военная", "price": 15},
    {"name": "Пчела-Рабочий 🐝", "rarity": "📦 Сборщик", "price": 10},
    {"name": "Элитный Трутень 🍯", "rarity": "⭐ Редкая", "price": 40},
    {"name": "Муравей-Листорез 🍃", "rarity": "⭐ Обычная", "price": 12},
    {"name": "Королевская Нянька 👑", "rarity": "🔮 Эпическая", "price": 100},
    {"name": "Гвардеец Королевы 🛡️", "rarity": "🔮 Эпическая", "price": 120},
    {"name": "Муравей-Разведчик 🔭", "rarity": "⭐ Обычная", "price": 15},
    {"name": "Мистический Рой 🌌", "rarity": "🌌 Легендарная", "price": 300},
]

# (Остальная логика функций остается такой же, как в предыдущем сообщении)
def check_access(message):
    uid = message.from_user.id
    if uid in BANNED_USERS: return False
    if uid in FROZEN_USERS:
        bot.send_message(message.chat.id, "🔇 Вы временно лишены голоса (муте) в улье.")
        return False
    return True

def init_player(uid, name="Особь"):
    if uid not in players:
        players[uid] = {
            "balance": 500, 
            "inventory": [], 
            "titles": ["🐜 Начинающий Энтомолог"], 
            "spouse": None, 
            "username": name
        }
    if players[uid]["username"] == "Особь" and name != "Особь":
        players[uid]["username"] = name

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📦 Открыть пак", "👤 Профиль | 🏆 Топ")
    markup.row("📁 Коллекция", "🚀 Прокачка & Крафт")
    markup.row("🛍️ Магазин", "🏪 Рынок Улья")
    markup.row("🎁 Бонусы & Донат", "⚔️ Походы & Битвы")
    return markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    if not check_access(message): return
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    msg_text = f"🐜 **Добро пожаловать в Улей!**\nВаш ID: `{uid}`"
    if uid == ADMIN_ID:
        msg_text += "\n\n👑 **Приветствуем, Королева улья!** Вам доступна скрытая команда чата `/admin_panel`"
    bot.send_message(message.chat.id, msg_text, parse_mode="Markdown", reply_markup=main_keyboard())

# ... (все остальные функции: profile_cmd, open_pack, collection_cmd и т.д. остаются прежними)

@bot.message_handler(commands=['admin_panel'])
def admin_panel_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    # ... (код панели администратора)

if __name__ == '__main__':
    bot.infinity_polling()
