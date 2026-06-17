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
breeding_sessions = {}  # Для хранения процесса скрещивания
COCON_PRICE = 50  

COLONY_UNITS = [
    {"name": "Муравей-Воин 🐜", "desc": "Защищает входы в муравейник.", "stats": {"⚔️ Сила": 85, "🛡️ Защита": 60, "📦 Сбор": 10}},
    {"name": "Пчела-Рабочий 🐝", "desc": "Трудолюбиво собирает пыльцу.", "stats": {"🍯 Сбор нектара": 95, "⚡ Скорость": 80, "⚔️ Сила": 15}},
    {"name": "Муравей-Листорез 🍃", "desc": "Заготавливает зелень для ферм.", "stats": {"⛏️ Копка": 70, "📦 Сбор": 90, "🛡️ Защита": 30}},
    {"name": "Элитный Трутень 🍯", "desc": "Ухаживает за будущим потомством.", "stats": {"🧪 Инкубация": 90, "⚡ Скорость": 50, "🛡️ Защита": 20}},
    {"name": "Гвардеец Королевы 🛡️", "desc": "Личная элитная охрана Матки.", "stats": {"🛡️ Защита": 100, "⚔️ Сила": 95, "⚡ Скорость": 40}},
    {"name": "Муравей-Разведчик 🔭", "desc": "Ищет новые богатые территории.", "stats": {"🔭 Обзор": 95, "⚡ Скорость": 90, "⚔️ Сила": 20}}
]

def init_player(uid, name="Особь"):
    if uid not in players:
        players[uid] = {
            "biomass": 500,           
            "colony": [],             
            "username": name
        }

def main_keyboard(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🥚 Инкубатор коконов", "🏰 Мой Муравейник")
    markup.row("📁 Список особи", "🛍️ Магазин Улья")
    markup.row("⚔️ Экспедиции (Походы)", "🧬 Лаборатория Генов")
    if uid == ADMIN_ID:
        markup.row("👑 Управление Ульем")
    return markup

def format_stats(stats_dict):
    return " | ".join([f"{k}: {v}" for k, v in stats_dict.items()])

# ==================== ЛОГИКА БОТА ====================

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    bot.send_message(
        message.chat.id, 
        f"🐜 **Приветствуем в обновленном Симуляторе Колонии!**\n\nРазвивайте свой рой, отправляйте отряды в походы и создавайте новые виды мутантов в лаборатории.", 
        parse_mode="Markdown", 
        reply_markup=main_keyboard(uid)
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
        bot.send_message(message.chat.id, f"❌ Недостаточно биомассы (нужно {COCON_PRICE} ед.)")
        return
    players[uid]["biomass"] -= COCON_PRICE
    chosen = random.choice(COLONY_UNITS)
    unit = {"id": str(uuid.uuid4())[:8], "name": chosen["name"], "desc": chosen["desc"], "stats": chosen["stats"].copy()}
    players[uid]["colony"].append(unit)
    bot.send_message(
        message.chat.id, 
        f"🥚 **В инкубаторе лопнул кокон!**\nВылупился: **{unit['name']}**\n📊 **Характеристики:**\n`{format_stats(unit['stats'])}`", 
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.text == "📁 Список особи")
def collection_cmd(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    if not players[uid]["colony"]:
        bot.send_message(message.chat.id, "🐜 Ваша колония пуста. Загляните в инкубатор!")
        return
    bot.send_message(message.chat.id, "🗂️ **Популяция вашей колонии:**")
    for unit in players[uid]["colony"]:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🍂 Выпустить на волю (+биомасса)", callback_data=f"release_{unit['id']}"))
        bot.send_message(
            message.chat.id, 
            f"🐜 **{unit['name']}**\n📋 {unit['desc']}\n📊 Характеристики:\n`{format_stats(unit['stats'])}`", 
            parse_mode="Markdown", reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("release_"))
def release_callback(call):
    uid = call.from_user.id
    unit_id = call.data.split("_")[1]
    if uid not in players: return
    unit = next((u for u in players[uid]["colony"] if u["id"] == unit_id), None)
    if unit:
        reward = random.randint(25, 45)
        players[uid]["biomass"] += reward
        players[uid]["colony"].remove(unit)
        bot.answer_callback_query(call.id, f"Насекомое улетело на волю. Получено +{reward} биомассы!")
        bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== НОВАЯ КНОПКА: ЭКСПЕДИЦИИ ====================
@bot.message_handler(func=lambda msg: msg.text == "⚔️ Экспедиции (Походы)")
def expedition_cmd(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    if not players[uid]["colony"]:
        bot.send_message(message.chat.id, "❌ У вас нет насекомых, чтобы собрать маршевый отряд!")
        return
    
    bot.send_message(message.chat.id, "⚔️ **Сбор боевого роя...**\nОтряд выдвигается на разведку диких территорий!")
    
    # Расчет успеха на основе случайности (в будущем можно привязать к силе)
    if random.choice([True, False]):
        loot = random.randint(60, 130)
        players[uid]["biomass"] += loot
        bot.send_message(message.chat.id, f"🎉 **Экспедиция успешна!**\nВаш рой захватил склад дикого меда термитов. Принесено в улей: `+{loot}` биомассы!", parse_mode="Markdown")
    else:
        lost_unit = random.choice(players[uid]["colony"])
        players[uid]["colony"].remove(lost_unit)
        bot.send_message(message.chat.id, f"💔 **Набег провалился!**\nОтряд попал в ловушку хищной птицы. Из похода не вернулся: **{lost_unit['name']}**")

# ==================== НОВАЯ КНОПКА: ЛАБОРАТОРИЯ ГЕНОВ ====================
@bot.message_handler(func=lambda msg: msg.text == "🧬 Лаборатория Генов")
def lab_cmd(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    if len(players[uid]["colony"]) < 2:
        bot.send_message(message.chat.id, "❌ Для скрещивания ДНК нужно иметь хотя бы 2 особи в списке!")
        return
    
    breeding_sessions[uid] = {"parent1": None}
    markup = types.InlineKeyboardMarkup()
    for u in players[uid]["colony"]:
        markup.add(types.InlineKeyboardButton(f"🧬 {u['name']}", callback_data=f"lab1_{u['id']}"))
    bot.send_message(message.chat.id, "🧬 **Выберите первую родительскую особь для скрещивания генов:**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lab1_"))
def lab1_callback(call):
    uid = call.from_user.id
    p1_id = call.data.replace("lab1_", "")
    breeding_sessions[uid]["parent1"] = p1_id
    
    markup = types.InlineKeyboardMarkup()
    for u in players[uid]["colony"]:
        if u["id"] != p1_id:
            markup.add(types.InlineKeyboardButton(f"🧬 {u['name']}", callback_data=f"lab2_{u['id']}"))
    bot.edit_message_text("🧬 **Выберите вторую особь для синтеза ДНК:**", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lab2_"))
def lab2_callback(call):
    uid = call.from_user.id
    p2_id = call.data.replace("lab2_", "")
    p1_id = breeding_sessions[uid]["parent1"]
    
    u1 = next((u for u in players[uid]["colony"] if u["id"] == p1_id), None)
    u2 = next((u for u in players[uid]["colony"] if u["id"] == p2_id), None)
    
    if not u1 or not u2: return
    
    # Создание мутанта
    new_stats = {}
    all_keys = set(u1["stats"].keys()).union(u2["stats"].keys())
    for k in all_keys:
        v1 = u1["stats"].get(k, 20)
        v2 = u2["stats"].get(k, 20)
        new_stats[k] = int((v1 + v2) * 0.6) + random.randint(5, 15) # Скрещивание + бонус мутации
        
    mutant = {
        "id": str(uuid.uuid4())[:8],
        "name": f"🧪 Мутант-{u1['name'].split('-')[-1]}",
        "desc": "Сверхживучий результат генной инженерии улья.",
        "stats": new_stats
    }
    
    players[uid]["colony"].remove(u1)
    players[uid]["colony"].remove(u2)
    players[uid]["colony"].append(mutant)
    
    bot.edit_message_text(
        f"🎉 **Генетический синтез завершен!**\nРодители исчезли в инкубаторе, но на свет появился супер-организм:\n\n"
        f"**{mutant['name']}**\n📊 Новые параметры:\n`{format_stats(mutant['stats'])}`",
        call.message.chat.id, call.message.message_id, parse_mode="Markdown"
    )

# ==================== ОСТАЛЬНЫЕ КНОПКИ ====================
@bot.message_handler(func=lambda msg: msg.text == "🛍️ Магазин Улья")
def store_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(f"🥚 Заказать обычный кокон ({COCON_PRICE} 🔋)", callback_data="buy_normal"))
    bot.send_message(message.chat.id, "🛍️ **Торговые каналы матки Улья**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "buy_normal")
def buy_callback(call):
    uid = call.from_user.id
    init_player(uid, call.from_user.first_name)
    if players[uid]["biomass"] < COCON_PRICE:
        bot.answer_callback_query(call.id, "❌ Не хватает биомассы!", show_alert=True)
        return
    players[uid]["biomass"] -= COCON_PRICE
    chosen = random.choice(COLONY_UNITS)
    unit = {"id": str(uuid.uuid4())[:8], "name": chosen["name"], "desc": chosen["desc"], "stats": chosen["stats"].copy()}
    players[uid]["colony"].append(unit)
    bot.send_message(call.message.chat.id, f"🛒 Новый кокон доставлен! Вывелась особь: **{unit['name']}**", parse_mode="Markdown")

# ==================== АДМИН-КНОПКА ====================
@bot.message_handler(func=lambda msg: msg.text == "👑 Управление Ульем" and msg.from_user.id == ADMIN_ID)
def admin_cmd(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔋 Дать себе +500 биомассы", callback_data="adm_give"))
    bot.send_message(message.chat.id, "👑 **Приветствуем, Королева роя!** Настройки экосистемы:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "adm_give" and call.from_user.id == ADMIN_ID)
def adm_give_callback(call):
    uid = call.from_user.id
    players[uid]["biomass"] += 500
    bot.answer_callback_query(call.id, "Ресурсы успешно синтезированы!", show_alert=True)

if __name__ == '__main__':
    bot.infinity_polling()
