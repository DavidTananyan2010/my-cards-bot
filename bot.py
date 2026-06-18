import telebot
from telebot import types
import uuid
import random
import time
import os
from flask import Flask, request
from pymongo import MongoClient

# 🔑 Токен вашего бота
TOKEN = "8930026163:AAE5iIQSzSUOIgaeddKb0WX4T2shG9JA_LE"
bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 7501899378

# 🌐 Инициализация веб-сервера Flask
app = Flask(__name__)

# Главная страница для прохождения проверок Render (Health Check)
@app.route('/')
def home():
    return "Бот колонии активен и подключен к MongoDB через Webhook!", 200

# Маршрут для обработки входящих сообщений от Telegram
@app.route(f'/{TOKEN}', methods=['POST'])
def receive_update():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Forbidden', 403

# 🔌 НАСТРОЙКА MONGODB
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    MONGO_URI = "YOUR_MONGODB_CONNECTION_STRING"

client = MongoClient(MONGO_URI)
db = client["colony_game"]       # Имя базы данных в кластере
users_col = db["users"]          # Коллекция пользователей

# Временные игровые сессии (в ОЗУ)
breeding_sessions = {}  
pvp_lobby = {}         
active_battles = {}    
pve_battles = {}       

COCON_PRICE = 50  
ELITE_COCON_PRICE = 150
EXPEDITION_COOLDOWN = 180  

# 🐜 Виды муравьев и пчел
COLONY_UNITS = [
    {"name": "Муравей-Воин 🐜", "desc": "Защищает входы в муравейник.", "stats": {"⚔️ Сила": 85, "🛡️ Защита": 60, "📦 Сбор": 10}, "elite": False},
    {"name": "Пчела-Рабочий 🐝", "desc": "Трудолюбиво собирает пыльцу.", "stats": {"🍯 Сбор нектара": 95, "⚡ Скорость": 80, "⚔️ Сила": 15}, "elite": False},
    {"name": "Муравей-Листорез 🍃", "desc": "Заготавливает зелень.", "stats": {"⛏️ Копка": 70, "📦 Сбор": 90, "🛡️ Защита": 30}, "elite": False},
    {"name": "Муравей-Пуля 🎯", "desc": "Обладает болезненным укусом.", "stats": {"⚔️ Сила": 120, "🛡️ Защита": 40, "⚡ Скорость": 75}, "elite": True},
    {"name": "Бродячий Муравей ⚔️", "desc": "Кочевой убийца.", "stats": {"⚔️ Сила": 140, "🛡️ Защита": 50, "⚡ Скорость": 65}, "elite": True},
    {"name": "Медовый Муравей 🍯", "desc": "Резервуар со сладким сиропом.", "stats": {"🍯 Сбор нектара": 150, "🛡️ Защита": 20, "📦 Сбор": 110}, "elite": False},
    {"name": "Муравей-Древоточец 🪵", "desc": "Мощные челюсти.", "stats": {"🛡️ Защита": 95, "⚔️ Сила": 75, "⛏️ Копка": 85}, "elite": False},
    {"name": "Гвардеец Королевы 🛡️", "desc": "Личная охрана Матки.", "stats": {"🛡️ Защита": 160, "⚔️ Сила": 110, "⚡ Скорость": 40}, "elite": True},
    {"name": "Муравей-Развиччик 🔭", "desc": "Ищет территории.", "stats": {"🔭 Обзор": 95, "⚡ Скорость": 120, "⚔️ Сила": 25}, "elite": False}
]

ENEMIES_STANDARD = [
    {"name": "Азиатский Шершень 🐝☠️", "hp": 160, "dmg": 28},
    {"name": "Паук-Волк 🕷️", "hp": 130, "dmg": 35},
    {"name": "Жук-Олень 🪲", "hp": 220, "dmg": 18}
]

ENEMIES_FOREST = [
    {"name": "Хищная Богомолиха 🪰⚔️", "hp": 180, "dmg": 32},
    {"name": "Лесной Скорпион 🦂", "hp": 145, "dmg": 40},
    {"name": "Гусеница-Шелкопряд (Босс) 🐛👑", "hp": 300, "dmg": 15},
    {"name": "Рыжий Лесной Муравей-Изгой 🐜❌", "hp": 110, "dmg": 25}
]

def get_player(uid, name="Особь"):
    uid_str = str(uid)
    player = users_col.find_one({"_id": uid_str})
    if not player:
        player = {"_id": uid_str, "biomass": 500, "colony": [], "username": name, "last_expedition": 0}
        users_col.insert_one(player)
    return player

def save_player(uid, data):
    uid_str = str(uid)
    users_col.replace_one({"_id": uid_str}, data, upsert=True)

def main_keyboard(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🥚 Инкубатор коконов", "🏰 Мой Муравейник")
    markup.row("📁 Отряд", "🛍️ Магазин Unья")
    markup.row("⚔️ Экспедиции (Походы)", "🧬 Лаборатория Генов")
    markup.row("🏟️ PvP Битвы Арены")
    if int(uid) == ADMIN_ID:
        markup.row("👑 Управление Ульем")
    return markup

def format_stats(stats_dict):
    return " | ".join([f"{k}: {v}" for k, v in stats_dict.items()])

# ==================== ХЕНДЛЕРЫ ИГРЫ ====================

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    get_player(uid, message.from_user.first_name)
    bot.send_message(
        message.chat.id, 
        f"🐜 **Приветствуем в Симуляторе Colony!**\nРазвивайте свой муравейник, выводите мутантов и штурмуйте Арену.", 
        reply_markup=main_keyboard(uid)
    )

@bot.message_handler(func=lambda msg: msg.text == "🏰 Мой Муравейник")
def profile_cmd(message):
    uid = message.from_user.id
    p = get_player(uid, message.from_user.first_name)
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Сбросить весь прогресс", callback_data="player_self_reset_confirm"))
    
    bot.send_message(
        message.chat.id, 
        f"🏰 **Муравейник особи {p['username']}:**\n\n"
        f"🔋 **Запас биомассы:** `{p['biomass']}` единиц\n"
        f"🐝 **Численность отряда:** {len(p['colony'])} насекомых",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "player_self_reset_confirm")
def self_reset_confirm(call):
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ ДА, удалить", callback_data="player_self_reset_execute"),
        types.InlineKeyboardButton("❌ НЕТ, отмена", callback_data="player_self_reset_cancel")
    )
    bot.edit_message_text(
        "⚠️ **Вы уверены, что хотите ПОЛНОСТЬЮ уничтожить свой муравейник?**\n"
        "Все ресурсы, муравьи и мутации удалятся из MongoDB навсегда!", 
        call.message.chat.id, 
        call.message.message_id, 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("player_self_reset_"))
def self_reset_action(call):
    uid = call.from_user.id
    action = call.data.replace("player_self_reset_", "")
    
    if action == "cancel":
        bot.edit_message_text("❌ Сброс отменен. Ваш улей в безопасности!", call.message.chat.id, call.message.message_id)
        return
        
    if action == "execute":
        uid_str = str(uid)
        new_data = {"_id": uid_str, "biomass": 500, "colony": [], "username": call.from_user.first_name, "last_expedition": 0}
        save_player(uid, new_data)
        bot.edit_message_text("🔄 **Прогресс успешно стерт в MongoDB.** Королева начинает всё заново!", call.message.chat.id, call.message.message_id)

# ==================== СИСТЕМА ЭКСПЕДИЦИЙ ====================
@bot.message_handler(func=lambda msg: msg.text == "⚔️ Экспедиции (Походы)")
def expedition_menu(message):
    uid = message.from_user.id
    p = get_player(uid, message.from_user.first_name)
    
    if not p["colony"]:
        bot.send_message(message.chat.id, "❌ Отправлять некого! Выведите сначала воинов из кокона.")
        return
        
    current_time = time.time()
    if current_time - p["last_expedition"] < EXPEDITION_COOLDOWN:
        remains = int(EXPEDITION_COOLDOWN - (current_time - p["last_expedition"]))
        bot.send_message(message.chat.id, f"⏳ Насекомые восстанавливают силы. Ждать: {remains} сек.")
        return

    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("🍂 Стандартная вылазка", callback_data="exp_zone_standard"))
    markup.row(types.InlineKeyboardButton("🌲 Дремучая Чаща", callback_data="exp_zone_forest"))
    markup.row(types.InlineKeyboardButton("🔙 Назад к гнезду", callback_data="exp_zone_back"))
    
    bot.send_message(message.chat.id, "🗺️ **Куда направим исследовательский отряд?**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("exp_zone_"))
def expedition_zone_callback(call):
    uid = call.from_user.id
    zone = call.data.replace("exp_zone_", "")
    
    if zone == "back":
        bot.edit_message_text("🔙 Отряд вернулся к охране туннелей.", call.message.chat.id, call.message.message_id)
        return
        
    p = get_player(uid, call.from_user.first_name)
    current_time = time.time()
    
    if current_time - p["last_expedition"] < EXPEDITION_COOLDOWN:
        bot.answer_callback_query(call.id, "⏳ Ваши муравьи еще не отдохнули!", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        return

    p["last_expedition"] = current_time
    save_player(uid, p)

    if zone == "forest":
        enemy = random.choice(ENEMIES_FOREST).copy()
        zone_title = "🌲 Дремучая Чаща 🌲"
    else:
        enemy = random.choice(ENEMIES_STANDARD).copy()
        zone_title = "🍂 Окрестности Гнезда 🍂"

    pve_battles[str(uid)] = {
        "enemy": enemy,
        "zone": zone_title,
        "squad_hp": sum(u["stats"].get("🛡️ Защита", 50) for u in p["colony"]),
        "squad_dmg": sum(u["stats"].get("⚔️ Сила", 50) for u in p["colony"])
    }
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_pve_turn(call.message.chat.id, uid)

def show_pve_turn(chat_id, uid):
    battle = pve_battles[str(uid)]
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("⚔️ Атака", callback_data="pve_hit"), types.InlineKeyboardButton("🛡️ Защита", callback_data="pve_block"))
    
    bot.send_message(
        chat_id, 
        f"📍 Локация: **{battle['zone']}**\n"
        f"👹 **Враг:** {battle['enemy']['name']} (HP: {battle['enemy']['hp']})\n"
        f"🛡️ **Защита отряда:** {battle['squad_hp']}\n\n"
        f"Ваш приказ:", reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("pve_"))
def pve_callback(call):
    uid = call.from_user.id
    action = call.data.replace("pve_", "")
    p = get_player(uid)
    
    if str(uid) not in pve_battles: return
    battle = pve_battles[str(uid)]

    enemy_dmg = battle["enemy"]["dmg"]
    if action == "block":
        enemy_dmg = int(enemy_dmg * 0.25)

    battle["enemy"]["hp"] -= random.randint(int(battle["squad_dmg"] * 0.3), int(battle["squad_dmg"] * 0.6))
    battle["squad_hp"] -= enemy_dmg

    if battle["enemy"]["hp"] <= 0:
        loot = random.randint(150, 300) if "Чаща" in battle["zone"] else random.randint(100, 250)
        p["biomass"] += loot
        save_player(uid, p)
        bot.edit_message_text(f"🎉 **Победа!** `{battle['enemy']['name']}` разбит. Получено +`{loot}` биомассы!", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        del pve_battles[str(uid)]
    elif battle["squad_hp"] <= 0:
        lost_unit = random.choice(p["colony"])
        p["colony"].remove(lost_unit)
        save_player(uid, p)
        bot.edit_message_text(f"💔 **Поражение...** Отряд разгромлен. Погиб боец: **{lost_unit['name']}**", call.message.chat.id, call.message.message_id)
        del pve_battles[str(uid)]
    else:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_pve_turn(call.message.chat.id, uid)

# ==================== ОСТАЛЬНЫЕ КНОПКИ (ИНКУБАТОР / ОТРЯД) ====================

@bot.message_handler(func=lambda msg: msg.text == "🥚 Инкубатор коконов")
def open_pack(message):
    uid = message.from_user.id
    p = get_player(uid, message.from_user.first_name)
    if p["biomass"] < COCON_PRICE:
        bot.send_message(message.chat.id, f"❌ Недостаточно биомассы (нужно {COCON_PRICE} ед.)")
        return
    p["biomass"] -= COCON_PRICE
    available = [u for u in COLONY_UNITS if not u["elite"]]
    chosen = random.choice(available)
    unit = {"id": str(uuid.uuid4())[:8], "name": chosen["name"], "desc": chosen["desc"], "stats": chosen["stats"].copy()}
    p["colony"].append(unit)
    save_player(uid, p)
    bot.send_message(message.chat.id, f"🥚 **Кокон созрел!** Из него вылез: **{unit['name']}**\n`{format_stats(unit['stats'])}`", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "📁 Отряд")
def collection_cmd(message):
    uid = message.from_user.id
    p = get_player(uid, message.from_user.first_name)
    if not p["colony"]:
        bot.send_message(message.chat.id, "Ваш отряд пуст. Загляните в инкубатор!")
        return
    bot.send_message(message.chat.id, f"🗂️ **Ваша армия насекомых ({len(p['colony'])}):**")
    for unit in p["colony"]:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🍂 Утилизировать (+биомасса)", callback_data=f"release_{unit['id']}"))
        bot.send_message(message.chat.id, f"🐜 **{unit['name']}**\n`{format_stats(unit['stats'])}`", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("release_"))
def release_callback(call):
    uid = call.from_user.id
    unit_id = call.data.split("_")[1]
    p = get_player(uid)
    unit = next((u for u in p["colony"] if u["id"] == unit_id), None)
    if unit:
        reward = random.randint(30, 55)
        p["biomass"] += reward
        p["colony"].remove(unit)
        save_player(uid, p)
        bot.answer_callback_query(call.id, f"Успешно. Получено +{reward} биомассы.")
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda msg: msg.text == "🛍️ Магазин Unья")
def store_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"🥚 Обычный кокон ({COCON_PRICE} 🔋)", callback_data="store_buy_normal"))
    markup.add(types.InlineKeyboardButton(f"🧪 Элитный кокон ({ELITE_COCON_PRICE} 🔋)", callback_data="store_buy_elite"))
    bot.send_message(message.chat.id, "🛍️ **Королевский магазин Улья**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("store_buy_"))
def store_buy_callback(call):
    uid = call.from_user.id
    type_cocon = call.data.replace("store_buy_", "")
    p = get_player(uid)
    price = COCON_PRICE if type_cocon == "normal" else ELITE_COCON_PRICE
    if p["biomass"] < price:
        bot.answer_callback_query(call.id, "❌ Маловато биомассы!", show_alert=True)
        return
    p["biomass"] -= price
    available = [u for u in COLONY_UNITS if u["elite"]] if type_cocon == "elite" else [u for u in COLONY_UNITS if not u["elite"]]
    chosen = random.choice(available)
    unit = {"id": str(uuid.uuid4())[:8], "name": chosen["name"], "desc": chosen["desc"], "stats": chosen["stats"].copy()}
    p["colony"].append(unit)
    save_player(uid, p)
    bot.send_message(call.message.chat.id, f"🛒 В инвентарь добавлен: **{unit['name']}**")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== СКРЕЩИВАНИЕ В ЛАБОРАТОРИИ ====================
@bot.message_handler(func=lambda msg: msg.text == "🧬 Лаборатория Генов")
def lab_cmd(message):
    uid = message.from_user.id
    p = get_player(uid)
    if len(p["colony"]) < 2:
        bot.send_message(message.chat.id, "❌ Для мутации нужно хотя бы 2 насекомых в отряде!")
        return
    breeding_sessions[str(uid)] = {"parent1": None}
    markup = types.InlineKeyboardMarkup()
    for u in p["colony"]:
        markup.add(types.InlineKeyboardButton(f"🧬 {u['name']}", callback_data=f"lab1_{u['id']}"))
    bot.send_message(message.chat.id, "🧬 **Генная лаборатория.** Выберите первого родителя:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lab1_"))
def lab1_callback(call):
    uid = call.from_user.id
    p1_id = call.data.replace("lab1_", "")
    if str(uid) not in breeding_sessions: return
    breeding_sessions[str(uid)]["parent1"] = p1_id
    p = get_player(uid)
    markup = types.InlineKeyboardMarkup()
    for u in p["colony"]:
        if u["id"] != p1_id:
            markup.add(types.InlineKeyboardButton(f"🧬 {u['name']}", callback_data=f"lab2_{u['id']}"))
    bot.edit_message_text("🧬 Выберите второго родителя для слияния генов:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lab2_"))
def lab2_callback(call):
    uid = call.from_user.id
    p2_id = call.data.replace("lab2_", "")
    if str(uid) not in breeding_sessions or not breeding_sessions[str(uid)]["parent1"]: return
    p1_id = breeding_sessions[str(uid)]["parent1"]
    p = get_player(uid)
    u1 = next((u for u in p["colony"] if u["id"] == p1_id), None)
    u2 = next((u for u in p["colony"] if u["id"] == p2_id), None)
    if not u1 or not u2: return
    
    new_stats = {}
    for k in set(u1["stats"].keys()).union(u2["stats"].keys()):
        new_stats[k] = int((u1["stats"].get(k, 20) + u2["stats"].get(k, 20)) * 0.6) + random.randint(10, 25)
        
    mutant = {"id": str(uuid.uuid4())[:8], "name": f"🧪 Мутант ({u1['name'].split()[0]})", "desc": "Результат генетических мутаций.", "stats": new_stats}
    p["colony"] = [u for u in p["colony"] if u["id"] not in [p1_id, p2_id]]
    p["colony"].append(mutant)
    save_player(uid, p)
    bot.edit_message_text(f"🎉 **Скрещивание успешно!** Выведен новый вид: **{mutant['name']}**!", call.message.chat.id, call.message.message_id)
    del breeding_sessions[str(uid)]

# ==================== СИСТЕМА PVP АРЕНЫ ====================
@bot.message_handler(func=lambda msg: msg.text == "🏟️ PvP Битвы Арены")
def pvp_menu(message):
    uid = message.from_user.id
    p = get_player(uid, message.from_user.first_name)
    if str(uid) in pvp_lobby: return
    if not p["colony"] or p["biomass"] < 50:
        bot.send_message(message.chat.id, "❌ Для участия нужен гладиатор и взнос 50 биомассы.")
        return
    markup = types.InlineKeyboardMarkup()
    for unit in p["colony"]:
        markup.add(types.InlineKeyboardButton(f"🤺 {unit['name']}", callback_data=f"arena_sel_{unit['id']}"))
    bot.send_message(message.chat.id, "🏟️ **Выберите насекомое для отправки на Арену:**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("arena_sel_"))
def pvp_select_callback(call):
    uid = call.from_user.id
    unit_id = call.data.replace("arena_sel_", "")
    p = get_player(uid)
    unit = next((u for u in p["colony"] if u["id"] == unit_id), None)
    if not unit: return
    uid_str = str(uid)
    if pvp_lobby and list(pvp_lobby.keys())[0] != uid_str:
        opp_id = list(pvp_lobby.keys())[0]
        opp_unit_id = pvp_lobby[opp_id]["unit_id"]
        opp_p = get_player(opp_id)
        opp_unit = next((u for u in opp_p["colony"] if u["id"] == opp_unit_id), None)
        if not opp_unit:
            del pvp_lobby[opp_id]
            return
        del pvp_lobby[opp_id]
        b_id = str(uuid.uuid4())[:8]
        active_battles[b_id] = {
            "p1": uid_str, "p1_name": p["username"], "p1_unit": unit, "p1_hp": unit["stats"].get("🛡️ Защита", 100), "p1_act": None,
            "p2": opp_id, "p2_name": opp_p["username"], "p2_unit": opp_unit, "p2_hp": opp_unit["stats"].get("🛡️ Защита", 100), "p2_act": None
        }
        bot.send_message(int(uid_str), f"⚔️ Соперник найден! Бой против колонии *{opp_p['username']}* начался!", parse_mode="Markdown")
        bot.send_message(int(opp_id), f"⚔️ Соперник найден! Бой против колонии *{p['username']}* начался!", parse_mode="Markdown")
        send_pvp_controls(b_id)
    else:
        pvp_lobby[uid_str] = {"unit_id": unit_id, "time": time.time()}
        bot.edit_message_text("🏟️ Вы заняли место в лобби. Ожидаем соперника...", call.message.chat.id, call.message.message_id)

def send_pvp_controls(b_id):
    battle = active_battles[b_id]
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("⚔️ Нанести удар", callback_data=f"pvp_trn_hit_{b_id}"), types.InlineKeyboardButton("🛡️ Уйти в защиту", callback_data=f"pvp_trn_block_{b_id}"))
    bot.send_message(int(battle["p1"]), f"🏟️ Здоровье бойца: `{battle['p1_hp']}`. Выберите действие:", parse_mode="Markdown", reply_markup=markup)
    bot.send_message(int(battle["p2"]), f"🏟️ Здоровье бойца: `{battle['p2_hp']}`. Выберите действие:", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pvp_trn_"))
def pvp_turn_callback(call):
    data = call.data.replace("pvp_trn_", "").split("_")
    action, b_id = data[0], data[1]
    uid_str = str(call.from_user.id)
    if b_id not in active_battles: return
    battle = active_battles[b_id]
    if uid_str == battle["p1"]: battle["p1_act"] = action
    elif uid_str == battle["p2"]: battle["p2_act"] = action
    bot.edit_message_text("⏳ Ожидание хода оппонента...", call.message.chat.id, call.message.message_id)
    if battle["p1_act"] and battle["p2_act"]:
        dmg1 = int(battle["p1_unit"]["stats"].get("⚔️ Сила", 25) * (0.25 if battle["p2_act"] == "block" else 1))
        dmg2 = int(battle["p2_unit"]["stats"].get("⚔️ Сила", 25) * (0.25 if battle["p1_act"] == "block" else 1))
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
            bot.send_message(int(winner), "🎉 Вы победили на Арене и забрали +50 биомассы со ставки!")
            bot.send_message(int(loser), f"💔 Ваш гладиатор {l_unit['name']} пал смертью храбрых и потерял 50 биомассы.")
            del active_battles[b_id]
        else:
            send_pvp_controls(b_id)

# ==================== ПАНЕЛЬ АДМИНИСТРАТОРА (MONGODB) ====================
@bot.message_handler(func=lambda msg: msg.text == "👑 Управление Ульем" and msg.from_user.id == ADMIN_ID)
def admin_cmd(message):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("📋 Все колонии из MongoDB", callback_data="adm_list_users"))
    markup.row(types.InlineKeyboardButton("🔋 Выдать биомассу", callback_data="adm_give_other"))
    markup.row(types.InlineKeyboardButton("🧹 Обнулить игрока", callback_data="adm_clear_user_start"))
    bot.send_message(message.chat.id, "👑 **Панель Управления Ульем**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_") and call.from_user.id == ADMIN_ID)
def admin_callbacks(call):
    action = call.data.replace("adm_", "")
    
    if action == "list_users":
        user_list = "📋 **Список колоний в MongoDB:**\n━━━━━━━━━━━━━━━━━━━━\n"
        for data in users_col.find():
            user_list += f"👤 Ник: *{data.get('username','Личинка')}*\n🆔 ID: `{data.get('_id')}`\n🔋 Биомасса: `{data.get('biomass',0)}` ед.\n🐜 Особей: {len(data.get('colony', []))}\n━━━━━━━━━━━━━━━━━━━━\n"
        bot.send_message(call.message.chat.id, user_list, parse_mode="Markdown")
        
    elif action == "give_other":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        msg = bot.send_message(call.message.chat.id, "🆔 Введите Telegram ID игрока для отправки ресурсов:")
        bot.register_next_step_handler(msg, process_admin_target_id)
        
    elif action == "clear_user_start":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        msg = bot.send_message(call.message.chat.id, "🧹 **ПРИНУДИТЕЛЬНОЕ ОБНУЛЕНИЕ**\nВведите Telegram ID игрока, чей прогресс нужно полностью удалить из MongoDB:")
        bot.register_next_step_handler(msg, process_admin_clear_id)

def process_admin_clear_id(message):
    if message.from_user.id != ADMIN_ID: return
    target_id = message.text.strip()
    
    p = users_col.find_one({"_id": target_id})
    if not p:
        bot.send_message(message.chat.id, f"❌ ID `{target_id}` отсутствует в базе MongoDB.", parse_mode="Markdown")
        return
        
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("💥 Стереть базу", callback_data=f"adm_force_clear_yes_{target_id}"),
        types.InlineKeyboardButton("❌ Отмена", callback_data="adm_force_clear_no")
    )
    
    bot.send_message(
        message.chat.id, 
        f"❓ Вы точно хотите полностью стереть данные игрока *{p.get('username', 'Игрок')}* (ID: `{target_id}`)?", 
        parse_mode="Markdown", 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_force_clear_") and call.from_user.id == ADMIN_ID)
def execute_admin_clear_callback(call):
    data = call.data.replace("adm_force_clear_", "").split("_")
    decision = data[0]
    
    if decision == "no":
        bot.edit_message_text("❌ Операция отменена.", call.message.chat.id, call.message.message_id)
        return
        
    if decision == "yes":
        target_id = data[1]
        p = users_col.find_one({"_id": target_id})
        if p:
            username = p.get('username', 'Игрок')
            new_data = {"_id": target_id, "biomass": 500, "colony": [], "username": username, "last_expedition": 0}
            save_player(target_id, new_data)
            
            bot.edit_message_text(f"💥 **Данные игрока {username} (ID: {target_id}) полностью сброшены в MongoDB!**", call.message.chat.id, call.message.message_id)
            try:
                bot.send_message(int(target_id), "⚠️ **Внимание!** Главный администратор сбросил ваш игровой прогресс до начального уровня.")
            except Exception:
                pass

def process_admin_target_id(message):
    if message.from_user.id != ADMIN_ID: return
    target_id = message.text.strip()
    p = get_player(target_id)
    msg = bot.send_message(message.chat.id, f"Какое количество биомассы начислить игроку *{p['username']}*?:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_admin_gift_amount, target_id)

def process_admin_gift_amount(message, target_id):
    if message.from_user.id != ADMIN_ID: return
    try:
        amount = int(message.text.strip())
        p = get_player(target_id)
        p["biomass"] += amount
        save_player(target_id, p)
        bot.send_message(message.chat.id, f"✅ Успешно начислено +`{amount}` биомассы.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Ошибка. Введите корректное число.")

# ==================== ЗАПУСК WEBHOOK И СЕРВЕРА ====================
if __name__ == '__main__':
    # 1. Снимаем старый режим получения данных (очистка)
    bot.remove_webhook()
    time.sleep(0.1)
    
    # 2. Устанавливаем новый Webhook, привязанный к URL твоего Render
    bot.set_webhook(url=f"https://my-cards-bot.onrender.com/{TOKEN}")
    
    # 3. Запускаем Flask на порту, который автоматически выдал хостинг Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
