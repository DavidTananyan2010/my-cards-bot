import telebot
from telebot import types
import uuid
import random

# 🔑 Токен и ID Администратора
TOKEN = "8930026163:AAGXKa6jYNtPVZ2kTYTpuN2UtlY8ZKxJKWQ"
bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 7501899378

# ==================== БАЗА ДАННЫХ И ХАРАКТЕРИСТИКИ ====================
players = {}
COCON_PRICE = 50  # Стоимость созревания кокона в инкубаторе

# Особи с их биологическими характеристиками
COLONY_UNITS = [
    {
        "name": "Муравей-Воин 🐜", 
        "desc": "Защищает входы в муравейник от набегов.",
        "stats": "⚔️ Сила: 85 | 🛡️ Защита: 60 | 📦 Сбор: 10"
    },
    {
        "name": "Пчела-Рабочий 🐝", 
        "desc": "Трудолюбивое насекомое, собирающее пыльцу.",
        "stats": "🍯 Сбор нектара: 95 | ⚡ Скорость: 80 | ⚔️ Сила: 15"
    },
    {
        "name": "Муравей-Листорез 🍃", 
        "desc": "Заготавливает зелень для грибных ферм.",
        "stats": "⛏️ Скорость копки: 70 | 📦 Сбор: 90 | 🛡️ Защита: 30"
    },
    {
        "name": "Элитный Трутень 🍯", 
        "desc": "Особь особого назначения для ухода за потомством.",
        "stats": "🧪 Инкубация: 90 | ⚡ Скорость: 50 | 🛡️ Защита: 20"
    },
    {
        "name": "Гвардеец Королевы 🛡️", 
        "desc": "Личная охрана царской особы.",
        "stats": "🛡️ Защита: 100 | ⚔️ Сила: 95 | ⚡ Скорость: 40"
    },
    {
        "name": "Муравей-Разведчик 🔭", 
        "desc": "Ищет новые источники пищи и территории.",
        "stats": "🔭 Дальность обзора: 95 | ⚡ Скорость: 90 | ⚔️ Сила: 20"
    }
]

def init_player(uid, name="Особь"):
    if uid not in players:
        players[uid] = {
            "biomass": 500,           # Основной ресурс вместо денег
            "colony": [],             # Список живых насекомых
            "username": name
        }

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🥚 Инкубатор коконов", "🏰 Мой Муравейник")
    markup.row("📁 Список особей", "🛍️ Магазин Улья")
    return markup

# ==================== ЛОГИКА БОТА ====================

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    bot.send_message(
        message.chat.id, 
        f"🐜 **Приветствуем в Симуляторе Колонии!**\n\nЗдесь вы выращиваете муравьёв и пчёл, улучшаете характеристики своего роя и управляете экосистемой.", 
        parse_mode="Markdown", 
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda msg: msg.text == "🏰 Мой Муравейник")
def profile_cmd(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    p = players[uid]
    bot.send_message(
        message.chat.id, 
        f"🏰 **Муравейник особи {p['username']}:**\n\n"
        f"🔋 **Запас биомассы:** `{p['biomass']}` единиц\n"
        f"🐝 **Численность популяции:** {len(p['colony'])} насекомых",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.text == "🥚 Инкубатор коконов")
def open_pack(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    
    if players[uid]["biomass"] < COCON_PRICE:
        bot.send_message(message.chat.id, f"❌ Недостаточно биомассы. Стимуляция кокона стоит {COCON_PRICE} ед.")
        return
        
    players[uid]["biomass"] -= COCON_PRICE
    chosen = random.choice(COLONY_UNITS)
    
    unit = {
        "id": str(uuid.uuid4())[:8], 
        "name": chosen["name"], 
        "desc": chosen["desc"],
        "stats": chosen["stats"]
    }
    players[uid]["colony"].append(unit)
    
    bot.send_message(
        message.chat.id, 
        f"🥚 **В инкубаторе созрел новый кокон!**\n\nВылупился: **{unit['name']}**\n📋 _Описание:_ {unit['desc']}\n📊 **Характеристики:**\n`{unit['stats']}`", 
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.text == "📁 Список особей")
def collection_cmd(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    
    if not players[uid]["colony"]:
        bot.send_message(message.chat.id, "🐜 Ваша колония пуста. Используйте инкубатор!")
        return
        
    bot.send_message(message.chat.id, "🗂️ **Популяция вашей колонии:**")
    for unit in players[uid]["colony"]:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🍂 Выпустить на волю (добыть биомассу)", callback_data=f"release_{unit['id']}"))
        
        bot.send_message(
            message.chat.id, 
            f"🐜 **{unit['name']}**\n📋 {unit['desc']}\n📊 Характеристики:\n`{unit['stats']}`", 
            parse_mode="Markdown", 
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("release_"))
def release_callback(call):
    uid = call.from_user.id
    unit_id = call.data.split("_")[1]
    
    if uid not in players: return
    
    unit = next((u for u in players[uid]["colony"] if u["id"] == unit_id), None)
    if unit:
        # При выпуске на волю особь приносит случайное количество биомассы обратно в улей
        reward = random.randint(20, 45)
        players[uid]["biomass"] += reward
        players[uid]["colony"].remove(unit)
        bot.answer_callback_query(call.id, f"Насекомое отправлено в дикую природу! Получено +{reward} биомассы.")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ Насекомое не найдено.", show_alert=True)

@bot.message_handler(func=lambda msg: msg.text == "🛍️ Магазин Улья")
def store_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(f"🥚 Заказать обычный кокон ({COCON_PRICE} 🔋)", callback_data="buy_unit_normal"))
    bot.send_message(message.chat.id, "🛍️ **Торговые каналы матки Улья**\n\nЗдесь можно обменять накопленную биомассу на новые личинки.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "buy_unit_normal")
def buy_callback(call):
    uid = call.from_user.id
    init_player(uid, call.from_user.first_name)
    
    if players[uid]["biomass"] < COCON_PRICE:
        bot.answer_callback_query(call.id, "❌ Не хватает биомассы улья!", show_alert=True)
        return
        
    players[uid]["biomass"] -= COCON_PRICE
    chosen = random.choice(COLONY_UNITS)
    unit = {"id": str(uuid.uuid4())[:8], "name": chosen["name"], "desc": chosen["desc"], "stats": chosen["stats"]}
    players[uid]["colony"].append(unit)
    
    bot.send_message(call.message.chat.id, f"🛒 Заказ выполнен! Из кокона появился: **{unit['name']}**\n`{unit['stats']}`", parse_mode="Markdown")

if __name__ == '__main__':
    bot.infinity_polling()
