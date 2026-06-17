import telebot
from telebot import types
import uuid
import random
import time
from pymongo import MongoClient

# 🔑 Обновленный токен доступа
TOKEN = "8930026163:AAHEFZZUK85IxLkZIVlRqZHQa59wBLcS1iM"
bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 7501899378

# 🍃 ПОДКЛЮЧЕНИЕ К MONGODB (Вставьте вашу строку подключения сюда!)
MONGO_URI = "ВАША_СТРОКА_ПОДКЛЮЧЕНИЯ_MONGODB" 
try:
    client = MongoClient(MONGO_URI)
    db = client["colony_game_db"]
    players_col = db["players"]
    print("✅ Успешное подключение к MongoDB Atlas!")
except Exception as e:
    print(f"❌ Ошибка подключения к MongoDB: {e}")
    players_col = None

# Временные сессии для боев и крафта
breeding_sessions = {}  
pvp_lobby = {}         # Очередь: {uid: {"unit_id": id, "time": timestamp}}
active_battles = {}    # PvP бои в процессе
pve_battles = {}       # Походы в процессе

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

ENEMIES = [
    {"name": "Азиатский Шершень 🐝☠️", "hp": 150, "dmg": 25},
    {"name": "Паук-Волк 🕷️", "hp": 120, "dmg": 30},
    {"name": "Жук-Олень 🪲", "hp": 200, "dmg": 15}
]

# ==================== РАБОТА С БД ====================
def get_player(uid, name="Особь"):
    if players_col is None:
        return {"biomass": 500, "colony": [], "username": name, "last_expedition": 0}
    
    player = players_col.find_one({"_id": str(uid)})
    if not player:
        player = {
            "_id": str(uid),
            "biomass": 500,           
            "colony": [],             
            "username": name,
            "last_expedition": 0  
        }
        players_col.insert_one(player)
    return player

def save_player(uid, data):
    if players_col is not None:
        players_col.update_one({"_id": str(uid)}, {"$set": data}, upsert=True)

def main_keyboard(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🥚 Инкубатор коконов", "🏰 Мой Муравейник")
    markup.row("📁 Отряд", "🛍️ Магазин Улья")
    markup.row("⚔️ Экспедиции (Походы)", "🧬 Лаборатория Генов")
    markup.row("🏟️ PvP Битвы Арены")
    if uid == ADMIN_ID:
        markup.row("👑 Управление Ульем")
    return markup

def format_stats(stats_dict):
    return " | ".join([f"{k}: {v}" for k, v in stats_dict.items()])

# ==================== ЛОГИКА КОМАНД ====================

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    get_player(uid, message.from_user.first_name)
    bot.send_message(
        message.chat.id, 
        f"🐜 **Приветствуем в обновленном Симуляторе Колонии!**\n\nНовый токен применен, данные сохраняются в MongoDB Atlas. Наш рой готов к труду и обороне!", 
        reply_markup=main_keyboard(uid)
    )

@bot.message_handler(func=lambda msg: msg.text == "🏰 Мой Муравейник")
def profile_cmd(message):
    uid = message.from_user.id
    p = get_player(uid, message.from_user.first_name)
    bot.send_message(
        message.chat.id, 
        f"🏰 **Муравейник особи {p['username']}:**\n\n"
        f"🔋 **Запас биомассы:** `{p['biomass']}` единиц\n"
        f"🐝 **Численность отряда:** {len(p['colony'])} насекомых",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.text == "🥚 Инкубатор коконов")
def open_pack(message):
    uid = message.from_user.id
    p = get_player(uid, message.from_user.first_name)
    if p["biomass"] < COCON_PRICE:
        bot.send_message(message.chat.id, f"❌ Недостаточно биомассы (нужно {COCON_PRICE} ед.)")
        return
    p["biomass"] -= COCON_PRICE
    chosen = random.choice(COLONY_UNITS)
    unit = {"id": str(uuid.uuid4())[:8], "name": chosen["name"], "desc": chosen["desc"], "stats": chosen["stats"].copy()}
    p["colony"].append(unit)
    save_player(uid, p)
    bot.send_message(message.chat.id, f"🥚 **Кокон лопнул!** Вылупился: **{unit['name']}**\n`{format_stats(unit['stats'])}`", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "📁 Отряд")
def collection_cmd(message):
    uid = message.from_user.id
    p = get_player(uid, message.from_user.first_name)
    
    current_time = time.time()
    if uid in pvp_lobby and (current_time - pvp_lobby[uid]["time"] > 120):
        del pvp_lobby[uid]
        bot.send_message(message.chat.id, "⏱️ **Время ожидания боя вышло (2 мин).** Ваш боец вернулся обратно в отряд.")

    if not p["colony"]:
        bot.send_message(message.chat.id, "🐜 Ваш отряд пуст. Используйте инкубатор!")
        return
    bot.send_message(message.chat.id, "🗂️ **Состав вашего отряда:**")
    for unit in p["colony"]:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🍂 Выпустить на волю (+биомасса)", callback_data=f"release_{unit['id']}"))
        bot.send_message(message.chat.id, f"🐜 **{unit['name']}**\n📊 Характеристики:\n`{format_stats(unit['stats'])}`", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("release_"))
def release_callback(call):
    uid = call.from_user.id
    unit_id = call.data.split("_")[1]
    p = get_player(uid)
    unit = next((u for u in p["colony"] if u["id"] == unit_id), None)
    if unit:
        reward = random.randint(25, 45)
        p["biomass"] += reward
        p["colony"].remove(unit)
        save_player(uid, p)
        bot.answer_callback_query(call.id, f"Успешно! Получено +{reward} биомассы.")
        bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== ЭКСПЕДИЦИИ С СИСТЕМОЙ БОЯ ====================
@bot.message_handler(func=lambda msg: msg.text == "⚔️ Экспедиции (Походы)")
def expedition_cmd(message):
    uid = message.from_user.id
    p = get_player(uid, message.from_user.first_name)
    
    if not p["colony"]:
        bot.send_message(message.chat.id, "❌ Нужны бойцы для экспедиции!")
        return
        
    current_time = time.time()
    if current_time - p["last_expedition"] < EXPEDITION_COOLDOWN:
        bot.send_message(message.chat.id, "⏳ Ваши насекомые еще не восстановили силы.")
        return

    p["last_expedition"] = current_time
    save_player(uid, p)

    enemy = random.choice(ENEMIES).copy()
    pve_battles[uid] = {
        "enemy": enemy,
        "squad_hp": sum(u["stats"].get("🛡️ Защита", 50) for u in p["colony"]),
        "squad_dmg": sum(u["stats"].get("⚔️ Сила", 50) for u in p["colony"])
    }
    
    show_pve_turn(message.chat.id, uid)

def show_pve_turn(chat_id, uid):
    battle = pve_battles[uid]
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("⚔️ Удар", callback_data="pve_hit"), types.InlineKeyboardButton("🛡️ Защита", callback_data="pve_block"))
    markup.row(types.InlineKeyboardButton("🏃 Отступить", callback_data="pve_run"))
    
    bot.send_message(
        chat_id, 
        f"🚨 **В походе обнаружен затаившийся враг!**\n\n👹 **Противник:** {battle['enemy']['name']} (HP: {battle['enemy']['hp']})\n🛡️ **Защита вашего отряда:** {battle['squad_hp']}\n\nВыберите действие:", 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("pve_"))
def pve_callback(call):
    uid = call.from_user.id
    action = call.data.replace("pve_", "")
    p = get_player(uid)
    
    if uid not in pve_battles: 
        bot.answer_callback_query(call.id, "Бой уже завершен.")
        return
        
    battle = pve_battles[uid]
    
    if action == "run":
        if random.randint(1, 100) <= 40:
            bot.edit_message_text("🏃‍♂️ Рой успешно применил защитные феромоны и скрылся без потерь!", call.message.chat.id, call.message.message_id)
            del pve_battles[uid]
        else:
            loss_count = random.randint(1, len(p["colony"]))
            lost_names = []
            for _ in range(loss_count):
                if p["colony"]:
                    u = random.choice(p["colony"])
                    lost_names.append(u["name"])
                    p["colony"].remove(u)
            save_player(uid, p)
            bot.edit_message_text(f"💀 **Враг догнал отряд при побеге!**\nУничтожено особей ({loss_count} шт.):\n" + "\n".join(lost_names), call.message.chat.id, call.message.message_id)
            del pve_battles[uid]
        return

    enemy_dmg = battle["enemy"]["dmg"]
    if action == "block":
        enemy_dmg = int(enemy_dmg * 0.3)

    battle["enemy"]["hp"] -= random.randint(int(battle["squad_dmg"]*0.3), int(battle["squad_dmg"]*0.5))
    battle["squad_hp"] -= enemy_dmg

    if battle["enemy"]["hp"] <= 0:
        loot = random.randint(80, 200)
        p["biomass"] += loot
        save_player(uid, p)
        bot.edit_message_text(f"🎉 **Победа!** {battle['enemy']['name']} повержен. Получено +`{loot}` биомассы!", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        del pve_battles[uid]
    elif battle["squad_hp"] <= 0:
        lost_unit = random.choice(p["colony"])
        p["colony"].remove(lost_unit)
        save_player(uid, p)
        bot.edit_message_text(f"💔 **Ваш отряд разбит!** Вы потеряли бойца: **{lost_unit['name']}**", call.message.chat.id, call.message.message_id)
        del pve_battles[uid]
    else:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_pve_turn(call.message.chat.id, uid)

# ==================== ПОШАГОВАЯ PVP АРЕНА ====================
@bot.message_handler(func=lambda msg: msg.text == "🏟️ PvP Битвы Арены")
def pvp_menu(message):
    uid = message.from_user.id
    p = get_player(uid, message.from_user.first_name)
    
    if uid in pvp_lobby:
        bot.send_message(message.chat.id, "🏟️ Вы уже ожидаете противника.")
        return
    if not p["colony"]:
        bot.send_message(message.chat.id, "❌ Отряд пуст!")
        return
    if p["biomass"] < 50:
        bot.send_message(message.chat.id, "❌ Нужно минимум 50 биомассы.")
        return

    markup = types.InlineKeyboardMarkup()
    for unit in p["colony"]:
        markup.add(types.InlineKeyboardButton(f"🤺 {unit['name']}", callback_data=f"pvp_sel_{unit['id']}"))
    bot.send_message(message.chat.id, "🏟️ **Выберите гладиатора для Арены:**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pvp_sel_"))
def pvp_select_callback(call):
    uid = call.from_user.id
    unit_id = call.data.replace("pvp_sel_", "")
    p = get_player(uid)
    
    unit = next((u for u in p["colony"] if u["id"] == unit_id), None)
    if not unit: return
    
    if pvp_lobby and list(pvp_lobby.keys())[0] != uid:
        opp_id = list(pvp_lobby.keys())[0]
        opp_unit_id = pvp_lobby[opp_id]["unit_id"]
        opp_p = get_player(opp_id)
        opp_unit = next((u for u in opp_p["colony"] if u["id"] == opp_unit_id), None)
        
        if not opp_unit:
            del pvp_lobby[opp_id]
            pvp_lobby[uid] = {"unit_id": unit_id, "time": time.time()}
            bot.edit_message_text("🏟️ Ожидание оппонента...", call.message.chat.id, call.message.message_id)
            return
            
        del pvp_lobby[opp_id]
        
        b_id = str(uuid.uuid4())[:8]
        active_battles[b_id] = {
            "p1": uid, "p1_name": p["username"], "p1_unit": unit, "p1_hp": unit["stats"].get("🛡️ Защита", 100), "p1_act": None,
            "p2": opp_id, "p2_name": opp_p["username"], "p2_unit": opp_unit, "p2_hp": opp_unit["stats"].get("🛡️ Защита", 100), "p2_act": None
        }
        
        bot.send_message(uid, f"⚔️ Противник найден! Начинается поединок против *{opp_p['username']}*", parse_mode="Markdown")
        bot.send_message(opp_id, f"⚔️ Противник найден! Начинается поединок против *{p['username']}*", parse_mode="Markdown")
        
        send_pvp_controls(b_id)
    else:
        pvp_lobby[uid] = {"unit_id": unit_id, "time": time.time()}
        bot.edit_message_text("🏟️ Боец отправлен на Арену. Ожидаем вызова (таймаут возврата 2 минуты)...", call.message.chat.id, call.message.message_id)

def send_pvp_controls(b_id):
    battle = active_battles[b_id]
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("⚔️ Удар", callback_data=f"pvp_turn_hit_{b_id}"), types.InlineKeyboardButton("🛡️ Защита", callback_data=f"pvp_turn_block_{b_id}"))
    
    for user_id, hp, uname in [(battle["p1"], battle["p1_hp"], battle["p2_name"]), (battle["p2"], battle["p2_hp"], battle["p1_name"])]:
        bot.send_message(user_id, f"🏟️ **Ваше здоровье:** `{hp}`\nПротивник: *{uname}*\nСделайте ваш ход в раунде:", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pvp_turn_"))
def pvp_turn_callback(call):
    data = call.data.replace("pvp_turn_", "").split("_")
    action = data[0]
    b_id = data[1]
    uid = call.from_user.id
    
    if b_id not in active_battles: return
    battle = active_battles[b_id]
    
    if uid == battle["p1"]: battle["p1_act"] = action
    elif uid == battle["p2"]: battle["p2_act"] = action
    
    bot.edit_message_text("⏳ Действие выбрано. Ожидание выбора соперника...", call.message.chat.id, call.message.message_id)
    
    if battle["p1_act"] and battle["p2_act"]:
        dmg1 = int(battle["p1_unit"]["stats"].get("⚔️ Сила", 20) * (0.3 if battle["p2_act"] == "block" else 1))
        dmg2 = int(battle["p2_unit"]["stats"].get("⚔️ Сила", 20) * (0.3 if battle["p1_act"] == "block" else 1))
        
        battle["p2_hp"] -= dmg1
        battle["p1_hp"] -= dmg2
        
        battle["p1_act"], battle["p2_act"] = None, None
        
        if battle["p1_hp"] <= 0 or battle["p2_hp"] <= 0:
            winner, loser = (battle["p1"], battle["p2"]) if battle["p1_hp"] > battle["p2_hp"] else (battle["p2"], battle["p1"])
            w_p, l_p = get_player(winner), get_player(loser)
            
            l_unit = battle["p1_unit"] if loser == battle["p1"] else battle["p2_unit"]
            
            w_p["biomass"] += 50
            l_p["biomass"] = max(0, l_p["biomass"] - 50)
            
            l_p["colony"] = [u for u in l_p["colony"] if u["id"] != l_unit["id"]]
            
            save_player(winner, w_p)
            save_player(loser, l_p)
            
            bot.send_message(winner, f"🎉 **Вы победили на Арене!** Получено +50 биомассы.")
            bot.send_message(loser, f"💔 **Ваш гладиатор повержен!** Вы потеряли бойца {l_unit['name']} и 50 биомассы.")
            del active_battles[b_id]
        else:
            send_pvp_controls(b_id)

# ==================== СИСТЕМА КРАФТА И МАГАЗИН ====================
@bot.message_handler(func=lambda msg: msg.text == "🧬 Лаборатория Генов")
def lab_cmd(message):
    uid = message.from_user.id
    p = get_player(uid)
    if len(p["colony"]) < 2:
        bot.send_message(message.chat.id, "❌ Нужны 2 особи!")
        return
    breeding_sessions[uid] = {"parent1": None}
    markup = types.InlineKeyboardMarkup()
    for u in p["colony"]:
        markup.add(types.InlineKeyboardButton(f"🧬 {u['name']}", callback_data=f"l1_{u['id']}"))
    bot.send_message(message.chat.id, "🧬 Выберите первого родителя:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("l1_"))
def l1_callback(call):
    uid = call.from_user.id
    p1_id = call.data.replace("l1_", "")
    breeding_sessions[uid]["parent1"] = p1_id
    p = get_player(uid)
    markup = types.InlineKeyboardMarkup()
    for u in p["colony"]:
        if u["id"] != p1_id:
            markup.add(types.InlineKeyboardButton(f"🧬 {u['name']}", callback_data=f"l2_{u['id']}"))
    bot.edit_message_text("🧬 Выберите второго родителя:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("l2_"))
def l2_callback(call):
    uid = call.from_user.id
    p2_id = call.data.replace("l2_", "")
    p1_id = breeding_sessions[uid]["parent1"]
    p = get_player(uid)
    
    u1 = next((u for u in p["colony"] if u["id"] == p1_id), None)
    u2 = next((u for u in p["colony"] if u["id"] == p2_id), None)
    if not u1 or not u2: return
    
    new_stats = {}
    for k in set(u1["stats"].keys()).union(u2["stats"].keys()):
        new_stats[k] = int((u1["stats"].get(k, 20) + u2["stats"].get(k, 20)) * 0.6) + random.randint(5, 15)
        
    mutant = {"id": str(uuid.uuid4())[:8], "name": f"🧪 Мутант-{u1['name'].split('-')[-1]}", "desc": "Результат инженерии.", "stats": new_stats}
    p["colony"] = [u for u in p["colony"] if u["id"] not in [p1_id, p2_id]]
    p["colony"].append(mutant)
    save_player(uid, p)
    bot.edit_message_text(f"🎉 Выведен супер-организм **{mutant['name']}**!", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda msg: msg.text == "🛍️ Магазин Улья")
def store_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(f"🥚 Кокон ({COCON_PRICE} 🔋)", callback_data="buy_normal"))
    bot.send_message(message.chat.id, "🛍️ **Магазин Матки Улья**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "buy_normal")
def buy_callback(call):
    uid = call.from_user.id
    p = get_player(uid)
    if p["biomass"] < COCON_PRICE:
        bot.answer_callback_query(call.id, "❌ Нет биомассы!", show_alert=True)
        return
    p["biomass"] -= COCON_PRICE
    chosen = random.choice(COLONY_UNITS)
    unit = {"id": str(uuid.uuid4())[:8], "name": chosen["name"], "desc": chosen["desc"], "stats": chosen["stats"].copy()}
    p["colony"].append(unit)
    save_player(uid, p)
    bot.send_message(call.message.chat.id, f"🛒 Вывелась особь: **{unit['name']}**")

# ==================== АДМИН ПАНЕЛЬ ====================
@bot.message_handler(func=lambda msg: msg.text == "👑 Управление Ульем" and msg.from_user.id == ADMIN_ID)
def admin_cmd(message):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("📋 Все участники и ID", callback_data="adm_list_users"))
    markup.row(types.InlineKeyboardButton("🔋 Начислить биомассу игроку", callback_data="adm_give_other"))
    bot.send_message(message.chat.id, "👑 **Панель Королевы**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_") and call.from_user.id == ADMIN_ID)
def admin_callbacks(call):
    action = call.data.replace("adm_", "")
    if action == "list_users":
        if players_col is None: return
        all_players = players_col.find()
        user_list = "📋 **Список всех колоний в MongoDB:**\n━━━━━━━━━━━━━━━━━━━━\n"
        for data in all_players:
            user_list += f"👤 Имя: *{data.get('username','Особь')}*\n🆔 ID: `{data['_id']}`\n🔋 Биомасса: `{data.get('biomass',0)}` ед.\n━━━━━━━━━━━━━━━━━━━━\n"
        bot.send_message(call.message.chat.id, user_list, parse_mode="Markdown")
    elif action == "give_other":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        msg = bot.send_message(call.message.chat.id, "🆔 Введите Telegram ID игрока:")
        bot.register_next_step_handler(msg, process_admin_target_id)

def process_admin_target_id(message):
    if message.from_user.id != ADMIN_ID: return
    target_id = message.text.strip()
    p = get_player(target_id)
    msg = bot.send_message(message.chat.id, f"Укажите количество биомассы для *{p['username']}*:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_admin_gift_amount, target_id)

def process_admin_gift_amount(message, target_id):
    if message.from_user.id != ADMIN_ID: return
    try:
        amount = int(message.text.strip())
        p = get_player(target_id)
        p["biomass"] += amount
        save_player(target_id, p)
        bot.send_message(message.chat.id, f"✅ Добавлено `+{amount}` биомассы игроку!")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Ошибка.")

if __name__ == '__main__':
    bot.infinity_polling()
