import telebot
from telebot import types
import uuid
import random
import time

# 🔑 Данные доступа
TOKEN = "8930026163:AAGXKa6jYNtPVZ2kTYTpuN2UtlY8ZKxJKWQ"
bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 7501899378

# ==================== БАЗА ДАННЫХ И ПЕРЕМЕННЫЕ ====================
players = {}
breeding_sessions = {}  
pvp_lobby = {}         # Очередь на PvP: {uid: unit_id}
COCON_PRICE = 50  
EXPEDITION_COOLDOWN = 600  

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
            "username": name,
            "last_expedition": 0  
        }

def main_keyboard(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🥚 Инкубатор коконов", "🏰 Мой Муравейник")
    markup.row("📁 Список особи", "🛍️ Магазин Улья")
    markup.row("⚔️ Экспедиции (Походы)", "🧬 Лаборатория Генов")
    markup.row("🏟️ PvP Битвы Арены")
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
        f"🐜 **Приветствуем в Симуляторе Колонии!**\n\nВыращивайте рой, скрещивайте гены и сражайтесь с другими игроками на PvP Арене улья!", 
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

# ==================== ЭКСПЕДИЦИИ (ПОХОДЫ) ====================
@bot.message_handler(func=lambda msg: msg.text == "⚔️ Экспедиции (Походы)")
def expedition_cmd(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    
    if not players[uid]["colony"]:
        bot.send_message(message.chat.id, "❌ У вас нет насекомых для боевого роя!")
        return
        
    current_time = time.time()
    time_passed = current_time - players[uid]["last_expedition"]
    
    if time_passed < EXPEDITION_COOLDOWN:
        time_left = int(EXPEDITION_COOLDOWN - time_passed)
        bot.send_message(message.chat.id, f"⏳ **Ваши насекомые устали!** До нового похода осталось: `{time_left // 60} мин. {time_left % 60} сек.`", parse_mode="Markdown")
        return

    players[uid]["last_expedition"] = current_time
    bot.send_message(message.chat.id, "⚔️ **Отряд собирает маршевые феромоны...**")
    
    if random.choice([True, False]):
        loot = random.randint(60, 130)
        players[uid]["biomass"] += loot
        bot.send_message(message.chat.id, f"🎉 **Успех!** Рой разгромил гнездо диких термитов. Получено: `+{loot}` биомассы!", parse_mode="Markdown")
    else:
        lost_unit = random.choice(players[uid]["colony"])
        players[uid]["colony"].remove(lost_unit)
        bot.send_message(message.chat.id, f"💔 **Засада!** Из похода не вернулся: **{lost_unit['name']}**")

# ==================== ЛАБОРАТОРИЯ ГЕНОВ ====================
@bot.message_handler(func=lambda msg: msg.text == "🧬 Лаборатория Генов")
def lab_cmd(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    if len(players[uid]["colony"]) < 2:
        bot.send_message(message.chat.id, "❌ Нужны хотя бы 2 особи в списке!")
        return
    
    breeding_sessions[uid] = {"parent1": None}
    markup = types.InlineKeyboardMarkup()
    for u in players[uid]["colony"]:
        markup.add(types.InlineKeyboardButton(f"🧬 {u['name']}", callback_data=f"lab1_{u['id']}"))
    bot.send_message(message.chat.id, "🧬 **Выберите первого родителя для скрещивания ДНК:**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lab1_"))
def lab1_callback(call):
    uid = call.from_user.id
    p1_id = call.data.replace("lab1_", "")
    breeding_sessions[uid]["parent1"] = p1_id
    
    markup = types.InlineKeyboardMarkup()
    for u in players[uid]["colony"]:
        if u["id"] != p1_id:
            markup.add(types.InlineKeyboardButton(f"🧬 {u['name']}", callback_data=f"lab2_{u['id']}"))
    bot.edit_message_text("🧬 **Выберите второго родителя:**", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lab2_"))
def lab2_callback(call):
    uid = call.from_user.id
    p2_id = call.data.replace("lab2_", "")
    p1_id = breeding_sessions[uid]["parent1"]
    
    u1 = next((u for u in players[uid]["colony"] if u["id"] == p1_id), None)
    u2 = next((u for u in players[uid]["colony"] if u["id"] == p2_id), None)
    if not u1 or not u2: return
    
    new_stats = {}
    all_keys = set(u1["stats"].keys()).union(u2["stats"].keys())
    for k in all_keys:
        v1 = u1["stats"].get(k, 20)
        v2 = u2["stats"].get(k, 20)
        new_stats[k] = int((v1 + v2) * 0.6) + random.randint(5, 15)
        
    mutant = {"id": str(uuid.uuid4())[:8], "name": f"🧪 Мутант-{u1['name'].split('-')[-1]}", "desc": "Результат генной инженерии.", "stats": new_stats}
    players[uid]["colony"].remove(u1)
    players[uid]["colony"].remove(u2)
    players[uid]["colony"].append(mutant)
    
    bot.edit_message_text(f"🎉 **Синтез завершен!** Выведен супер-организм:\n\n**{mutant['name']}**\n📊 Характеристики:\n`{format_stats(mutant['stats'])}`", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# ==================== НОВАЯ СИСТЕМА: PvP БИТВЫ ====================
@bot.message_handler(func=lambda msg: msg.text == "🏟️ PvP Битвы Арены")
def pvp_menu(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    
    if uid in pvp_lobby:
        bot.send_message(message.chat.id, "🏟️ Ваша особь уже ожидает противника на Арене!")
        return
        
    if not players[uid]["colony"]:
        bot.send_message(message.chat.id, "❌ У вас нет насекомых, чтобы отправить бойца на Арену!")
        return
        
    if players[uid]["biomass"] < 50:
        bot.send_message(message.chat.id, "❌ Для участия в PvP нужно иметь минимум 50 биомассы (входная ставка).")
        return

    markup = types.InlineKeyboardMarkup()
    for unit in players[uid]["colony"]:
        markup.add(types.InlineKeyboardButton(f"🤺 {unit['name']} (Сила: {unit['stats'].get('⚔️ Сила', 15)})", callback_data=f"pvp_select_{unit['id']}"))
    
    bot.send_message(message.chat.id, "🏟️ **Добро пожаловать на Гладиаторскую Арену Улья!**\n\nВыберите насекомое, которое представит вашу колонию. Ставка: `50` биомассы.\n⚠️ *Внимание:* Проигравший теряет своего бойца навсегда!", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pvp_select_"))
def pvp_select_callback(call):
    uid = call.from_user.id
    unit_id = call.data.replace("pvp_select_", "")
    
    unit = next((u for u in players[uid]["colony"] if u["id"] == unit_id), None)
    if not unit: return
    
    # Если в лобби уже кто-то есть и это не сам игрок
    if pvp_lobby and list(pvp_lobby.keys())[0] != uid:
        opponent_id = list(pvp_lobby.keys())[0]
        opp_unit_id = pvp_lobby[opponent_id]
        
        opp_unit = next((u for u in players[opponent_id]["colony"] if u["id"] == opp_unit_id), None)
        
        if not opp_unit:
            # Если боец оппонента пропал/был удален
            del pvp_lobby[opponent_id]
            pvp_lobby[uid] = unit_id
            bot.edit_message_text("🏟️ Вы встали в очередь. Ожидайте противника...", call.message.chat.id, call.message.message_id)
            return

        # Проведение битвы!
        del pvp_lobby[opponent_id]
        bot.edit_message_text("⚔️ **Противник найден! Битва началась...**", call.message.chat.id, call.message.message_id)
        
        # Расчет боевой мощи (Сила + Защита)
        power1 = unit["stats"].get("⚔️ Сила", 10) + unit["stats"].get("🛡️ Защита", 10)
        power2 = opp_unit["stats"].get("⚔️ Сила", 10) + opp_unit["stats"].get("🛡️ Защита", 10)
        
        total_power = power1 + power2
        chance1 = (power1 / total_power) * 100
        
        # Определение победителя
        if random.randint(1, 100) <= chance1:
            winner_id, winner_name, winner_unit = uid, players[uid]["username"], unit
            loser_id, loser_name, loser_unit = opponent_id, players[opponent_id]["username"], opp_unit
        else:
            winner_id, winner_name, winner_unit = opponent_id, players[opponent_id]["username"], opp_unit
            loser_id, loser_name, loser_unit = uid, players[uid]["username"], unit

        # Применение результатов
        players[winner_id]["biomass"] += 50
        players[loser_id]["biomass"] = max(0, players[loser_id]["biomass"] - 50)
        players[loser_id]["colony"].remove(loser_unit)
        
        # Отправка сообщений обоим
        result_text = (
            f"🏟️ **РЕЗУЛЬТАТЫ БИТВЫ НА АРЕНЕ**\n━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 **Победитель:** {winner_name} со своим боевым *{winner_unit['name']}*!\n"
            f"💰 Выигрыш: `+50` биомассы.\n\n"
            f"💀 **Проигравший:** {loser_name}.\n"
            f"❌ Потери: `-50` биомассы и боец *{loser_unit['name']}* погиб в бою."
        )
        
        bot.send_message(winner_id, f"🎉 **Вы победили в PvP!**\n\n{result_text}", parse_mode="Markdown")
        try: bot.send_message(loser_id, f"💔 **Вы проиграли в PvP!**\n\n{result_text}", parse_mode="Markdown")
        except Exception: pass
        
    else:
        # Встаем в очередь
        pvp_lobby[uid] = unit_id
        bot.edit_message_text("🏟️ Ваш боец отправлен на Арену. Ожидаем вызова от другой колонии...", call.message.chat.id, call.message.message_id)

# ==================== МАГАЗИН И УПРАВЛЕНИЕ (АДМИН) ====================
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

@bot.message_handler(func=lambda msg: msg.text == "👑 Управление Ульем" and msg.from_user.id == ADMIN_ID)
def admin_cmd(message):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("📋 Все участники и ID", callback_data="adm_list_users"))
    markup.row(types.InlineKeyboardButton("🔋 Начислить биомассу игроку", callback_data="adm_give_other"))
    bot.send_message(message.chat.id, "👑 **Центральный Пульт Королевы Улья**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_") and call.from_user.id == ADMIN_ID)
def admin_callbacks(call):
    action = call.data.replace("adm_", "")
    if action == "list_users":
        if not players:
            bot.send_message(call.message.chat.id, "🐜 В улье пока нет зарегистрированных особей.")
            return
        user_list = "📋 **Список всех колоний в улье:**\n━━━━━━━━━━━━━━━━━━━━\n"
        for uid, data in players.items():
            user_list += f"👤 Имя: *{data['username']}*\n🆔 Telegram ID: `{uid}`\n🔋 Биомасса: `{data['biomass']}` ед.\n🐜 Особей: {len(data['colony'])} шт.\n━━━━━━━━━━━━━━━━━━━━\n"
        bot.send_message(call.message.chat.id, user_list, parse_mode="Markdown")
    elif action == "give_other":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        msg = bot.send_message(call.message.chat.id, "🆔 Введите **Telegram ID** игрока для начисления ресурсов:")
        bot.register_next_step_handler(msg, process_admin_target_id)

def process_admin_target_id(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        target_id = int(message.text.strip())
        if target_id not in players:
            bot.send_message(message.chat.id, "❌ Данный ID не зарегистрирован.")
            return
        msg = bot.send_message(message.chat.id, f"Укажите количество биомассы для *{players[target_id]['username']}*:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_admin_gift_amount, target_id)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Некорректный ID.")

def process_admin_gift_amount(message, target_id):
    if message.from_user.id != ADMIN_ID: return
    try:
        amount = int(message.text.strip())
        players[target_id]["biomass"] += amount
        bot.send_message(message.chat.id, f"✅ Начислено `+{amount}` биомассы игроку *{players[target_id]['username']}*!", parse_mode="Markdown")
        try: bot.send_message(target_id, f"👑 **Милость Королевы!** Получено `+{amount}` биомассы!", parse_mode="Markdown")
        except Exception: pass
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверное число.")

if __name__ == '__main__':
    bot.infinity_polling()
