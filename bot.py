import os
import threading
import telebot
from telebot import types
import random
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

# 🔑 Токен бота (автоматически берется из Render или используется твой)
TOKEN = os.environ.get("BOT_TOKEN", "8701989939:AAFVTHvkObrmq6EsQClsTByOEL7tJNqg4_Q")
bot = telebot.TeleBot(TOKEN)

# 👑 ID Главного Администратора (Творца)
ADMIN_ID = 7501899378

# ==================== ГЛОБАЛЬНЫЕ ОБЩИЕ КОЛОНИИ ====================
# Реализм: на старте улья 50 биомассы (стартовый запас), 0 рабочих и 3 яйца.
GLOBAL_HIVES = {
    "Рыжие лесные": {"biomass": 50.0, "eggs": 3, "workers": 0, "soldiers": 0, "status": "Стабильно"},
    "Муравьи-Листорезы": {"biomass": 50.0, "eggs": 3, "workers": 0, "soldiers": 0, "status": "Стабильно"},
    "Черные садовые": {"biomass": 50.0, "eggs": 3, "workers": 0, "soldiers": 0, "status": "Стабильно"},
    "Медоносные пчёлы": {"biomass": 50.0, "eggs": 3, "workers": 0, "soldiers": 0, "status": "Стабильно"},
    "Земляные шмели": {"biomass": 50.0, "eggs": 3, "workers": 0, "soldiers": 0, "status": "Стабильно"},
    "Лесные osы-одиночки": {"biomass": 50.0, "eggs": 3, "workers": 0, "soldiers": 0, "status": "Стабильно"}
}

# Личная статистика участников
players = {}

FACTIONS = {
    "Муравьи 🐜": ["Рыжие лесные", "Муравьи-Листорезы", "Черные садовые"],
    "Пчёлы 🐝": ["Медоносные пчёлы", "Земляные шмели", "Лесные osы-одиночки"]
}

ENEMIES = [
    {"name": "Жук-Олень 🪲", "power": 8, "loot": 60},
    {"name": "Паук-Волк 🕷️", "power": 20, "loot": 200},
    {"name": "Дикая Оса 🐝", "power": 14, "loot": 110},
    {"name": "Хищная Многоножка 🐛", "power": 35, "loot": 450}
]

# ==================== СИСТЕМА ЖИЗНЕДЕЯТЕЛЬНОСТИ И ГОЛОДА ====================
def hive_life_cycle_loop():
    """Фоновый поток: симуляция метаболизма, голода и смерти раз в 5 минут"""
    while True:
        time.sleep(300) # ⏳ Трата ресурсов происходит ровно раз в 5 минут (300 секунд)
        for race, hive in GLOBAL_HIVES.items():
            # Если в расе еще нет активного населения, не обсчитываем расход
            if hive["workers"] == 0 and hive["soldiers"] == 0 and hive["biomass"] == 50.0:
                continue
                
            # 🍽️ Расчет потребления (Матка ест 3.5, рабочий 0.5, солдат 1.0)
            consumption = 3.5 + (hive["workers"] * 0.5) + (hive["soldiers"] * 1.0)
            consumption = round(consumption, 1)
            
            if hive["biomass"] >= consumption:
                hive["biomass"] = round(hive["biomass"] - consumption, 1)
                hive["status"] = f"Сыты (Потребление: -{consumption} ед/5мин)"
            else:
                # 🚨 НАЧАЛСЯ ГОЛОД
                hive["biomass"] = 0.0
                hive["status"] = "⚠️ ГОЛОД! Население умирает!"
                
                # Естественный отбор косит касты по очереди
                if hive["eggs"] > 0:
                    hive["eggs"] -= 1
                elif hive["workers"] > 0:
                    hive["workers"] -= 1
                elif hive["soldiers"] > 0:
                    hive["soldiers"] -= 1

# Запуск фонового потока жизнедеятельности
threading.Thread(target=hive_life_cycle_loop, daemon=True).start()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def init_player(uid, first_name="Неизвестный"):
    if uid not in players:
        players[uid] = {
            "username": first_name,
            "faction": None,
            "race": None,
            "personal_contribution": 0.0,
            "titles": [],
            "last_collect": 0
        }
    if players[uid]["username"] != first_name and first_name != "Неизвестный":
        players[uid]["username"] = first_name

def get_main_keyboard(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if players[uid]["faction"] is None: return None
    markup.row("🏰 Общее Гнездо", "🥚 Инкубатор Расы")
    markup.row("🌾 Добыча для Улья", "⚔️ Военный Поход")
    return markup

# ==================== ЛОГИКА ИГРЫ ====================

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    
    msg_text = ""
    if uid == ADMIN_ID:
        msg_text += "👑 **С возвращением, Творец!**\n/admin_players — управление\n/users_list — список игроков\n\n"

    if players[uid]["faction"] is None:
        markup = types.InlineKeyboardMarkup()
        for faction in FACTIONS.keys():
            markup.add(types.InlineKeyboardButton(faction, callback_data=f"fac_{faction}"))
        
        bot.send_message(
            message.chat.id, 
            msg_text + "🐜 **Добро пожаловать в Глобальный Рой!**\n\nВы становитесь частью огромного общего организма. Без еды колония погибнет от голода. Выберите вид насекомых:", 
            parse_mode="Markdown", reply_markup=markup
        )
    else:
        bot.send_message(
            message.chat.id, 
            msg_text + f"🐜 Вы уже состоите в касте расы **{players[uid]['race']}**!", 
            parse_mode="Markdown", reply_markup=get_main_keyboard(uid)
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("fac_") or call.data.startswith("race_"))
def faction_callback(call):
    uid = call.from_user.id
    init_player(uid, call.from_user.first_name)
    
    if call.data.startswith("fac_"):
        faction = call.data.replace("fac_", "")
        players[uid]["faction"] = faction
        
        markup = types.InlineKeyboardMarkup()
        for race in FACTIONS[faction]:
            markup.add(types.InlineKeyboardButton(race, callback_data=f"race_{race}"))
            
        bot.edit_message_text(
            f"Вы выбрали вид: **{faction}**.\nК какому глобальному улью вы хотите присоединиться?", 
            call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup
        )
        
    elif call.data.startswith("race_"):
        race = call.data.replace("race_", "")
        players[uid]["race"] = race
        
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
        welcome_txt = (
            f"✨ **Вы внутри улья!** ✨\n\n"
            f"Отныне вы — часть расы **{race}**!\n"
            f"🔴 **ВНИМАНИЕ:** Сейчас в гнезде **0 рабочих**. "
            f"Матка огромна, опасна, но слишком медлительна. Она не может собирать ресурсы на поверхности самостоятельно.\n\n"
            f"Срочно зайдите в **🥚 Инкубатор Расы** и вырастите первых рабочих из стартовых яиц, чтобы запустить жизнь колонии!"
        )
        bot.send_message(call.message.chat.id, welcome_txt, parse_mode="Markdown", reply_markup=get_main_keyboard(uid))

# Меню «Общее Гнездо»
@bot.message_handler(func=lambda msg: msg.text == "🏰 Общее Гнездо")
def nest_menu(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    if players[uid]["faction"] is None: return

    race = players[uid]["race"]
    hive = GLOBAL_HIVES[race]
    p = players[uid]
    
    titles_str = f"\n🎖️ **Ваши титулы:** {', '.join(p['titles'])}" if p.get("titles") else ""

    text = (
        f"🏰 **Глобальное Гнездо расы [{race}]**\n"
        f"Статус питания: `{hive['status']}`\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 **ОБЩАЯ БИОМАССА (ЕДА):** `{hive['biomass']}` ед.\n"
        f"🥚 **Яиц в инкубаторе:** {hive['eggs']} шт.\n\n"
        f"📋 **Касты общего гнезда:**\n"
        f"📦 **Грузчики (Рабочие):** {hive['workers']} особей " + ("⚠️ (НЕТ РАБОЧИХ!)" if hive['workers'] == 0 else "✅") + "\n"
        f"⚔️ **Солдаты (Защитники):** {hive['soldiers']} особей\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f" Lydia **Личные данные:**\n"
        f"🆔 Ваш ID: `{uid}`{titles_str}\n"
        f"📊 Ваш личный вклад в сбор: `+{p['personal_contribution']}` ед.\n\n"
        f"💡 _Внимание! Каждые 5 минут улей потребляет биомассу. Не оставляйте склад пустым!_"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# Меню «Инкубатор Расы»
@bot.message_handler(func=lambda msg: msg.text == "🥚 Инкубатор Расы")
def incubator_menu(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    if players[uid]["faction"] is None: return

    race = players[uid]["race"]
    hive = GLOBAL_HIVES[race]
    
    markup = types.InlineKeyboardMarkup()
    if hive["eggs"] > 0:
        markup.row(
            types.InlineKeyboardButton("📦 Вырастить Рабочего", callback_data="hatch_worker"),
            types.InlineKeyboardButton("⚔️ Вырастить Солдата", callback_data="hatch_soldier")
        )
    markup.row(types.InlineKeyboardButton("➕ Купить яйцо (30 биомассы)", callback_data="buy_egg"))

    bot.send_message(
        message.chat.id, 
        f"🥚 **Глобальный Инкубатор [{race}]**\n\n"
        f"В наличии улья: {hive['eggs']} яиц.\n"
        f"Выращивание из имеющихся яиц бесплатное. Новые касты будут требовать еду!", 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("hatch_") or call.data == "buy_egg")
def incubator_callback(call):
    uid = call.from_user.id
    init_player(uid, call.from_user.first_name)
    race = players[uid]["race"]
    hive = GLOBAL_HIVES[race]
    
    if call.data == "buy_egg":
        if hive["workers"] == 0:
            bot.answer_callback_query(call.id, "❌ Некому принести биомассу! Вырастите рабочего из стартовых яиц.", show_alert=True)
            return
        if hive["biomass"] < 30:
            bot.answer_callback_query(call.id, "❌ В общем улье недостаточно биомассы!", show_alert=True)
            return
        hive["biomass"] -= 30
        hive["eggs"] += 1
        bot.answer_callback_query(call.id, "🥚 Новое яйцо добавлено в инкубатор!")
        bot.edit_message_text(f"🥚 **Глобальный Инкубатор [{race}]**\n\nВ наличии улья: {hive['eggs']} яиц.", call.message.chat.id, call.message.message_id, reply_markup=call.message.reply_markup)
        
    elif call.data.startswith("hatch_"):
        if hive["eggs"] < 1:
            bot.answer_callback_query(call.id, "❌ В инкубаторе закончились яйца!", show_alert=True)
            return
        
        hive["eggs"] -= 1
        role = call.data.replace("hatch_", "")
        
        if role == "worker":
            hive["workers"] += 1
            msg = f"🐣 Игрок {call.from_user.first_name} вывел **Рабочего**! Теперь колония может добывать ресурсы."
        else:
            hive["soldiers"] += 1
            msg = f"⚔️ Игрок {call.from_user.first_name} вывел **Солдата** для охраны улья."
            
        bot.answer_callback_query(call.id, "Вылупление завершено!")
        bot.edit_message_text(f"🎉 {msg}\n\nОсталось яиц в инкубаторе: {hive['eggs']} шт.", call.message.chat.id, call.message.message_id)

# Сбор ресурсов с ФИЗИКОЙ ВЕСА и БЛОКИРОВКОЙ
@bot.message_handler(func=lambda msg: msg.text == "🌾 Добыча для Unья" or msg.text == "🌾 Добыча для Улья")
def collect_resources(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    if players[uid]["faction"] is None: return

    p = players[uid]
    race = p["race"]
    hive = GLOBAL_HIVES[race]
    
    # ❌ СТРОГАЯ БЛОКИРОВКА БЕЗ РАБОЧИХ
    if hive["workers"] == 0:
        error_txt = (
            "⚠️ **Сбор невозможен!**\n\n"
            "В вашей колонии ещё **нет вылупившихся рабочих**!\n"
            "Матка — самое крупное насекомое, она невероятно медлительна "
            "и не способна выйти на поверхность самостоятельно.\n\n"
            "👉 Срочно откройте вкладку **🥚 Инкубатор Расы** и выведите хотя бы 1 рабочего!"
        )
        bot.send_message(message.chat.id, error_txt, parse_mode="Markdown")
        return

    now = time.time()
    if now - p["last_collect"] < 15:
        remains = int(15 - (now - p["last_collect"]))
        bot.send_message(message.chat.id, f"⏳ Ваши рабочие ещё тащат прошлый груз. Подождите {remains} сек.")
        return

    # ⚖️ ФИЗИКА ВЕСА ДОБЫЧИ
    loot_objects = [
        {"name": "дохлую гусеницу 🐛", "weight": 80},
        {"name": "крупную каплю нектара 💧", "weight": 40},
        {"name": "сочную травинку 🌱", "weight": 25},
        {"name": "кусок спелого яблока 🍏", "weight": 150}
    ]
    found = random.choice(loot_objects)
    
    # Максимальная подъемная сила (1 рабочий поднимает ~15 единиц веса)
    max_carry_power = hive["workers"] * 15
    
    if max_carry_power >= found["weight"]:
        # Силы рабочих хватило поднять груз целиком
        gained_biomass = round(found["weight"] / 4, 1)
        hive["biomass"] = round(hive["biomass"] + gained_biomass, 1)
        p["personal_contribution"] += gained_biomass
        msg = f"💪 **Сила физики!** Ваши рабочие нашли {found['name']} весом `{found['weight']} мг` и успешно дотащили её до склада! Общая казна улья пополнена на `+{gained_biomass}` ед. биомассы."
    else:
        # Груз оказался неподъемным
        partial_loot = round(max_carry_power / 5, 1)
        hive["biomass"] = round(hive["biomass"] + partial_loot, 1)
        p["personal_contribution"] += partial_loot
        msg = f"😰 **Слишком тяжело!** Ваши рабочие нашли {found['name']} весом `{found['weight']} мг`. Из-за законов физики и нехватки сил они смогли отгрызть лишь кусочек на `+{partial_loot}` биомассы. Нужно больше рабочих!"

    p["last_collect"] = now
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

# Военные походы (Матка защищается, если нет солдат)
@bot.message_handler(func=lambda msg: msg.text == "⚔️ Военный Поход")
def battle_system(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    if players[uid]["faction"] is None: return

    race = players[uid]["race"]
    hive = GLOBAL_HIVES[race]
    enemy = random.choice(ENEMIES)
    
    bot.send_message(message.chat.id, f"🧭 Боевой отряд столкнулся с хищником: **{enemy['name']}** (Сила: {enemy['power']})")
    time.sleep(1.5)

    using_queen = False
    if hive["soldiers"] == 0:
        using_queen = True
        # Матка ОЧЕНЬ опасна в защите кладки. Её базовая боевая сила равна 25!
        player_power = 25 + random.randint(-5, 5)
        bot.send_message(message.chat.id, "⚠️ **Солдат нет!** В бой вступает сама Матка-Королева. Она невероятно сильна и яростно защищает кладку!")
    else:
        player_power = hive["soldiers"] * 5 + random.randint(0, 5)

    if player_power >= enemy["power"]:
        hive["biomass"] = round(hive["biomass"] + enemy["loot"], 1)
        
        loss_text = ""
        if not using_queen:
            if hive["soldiers"] > 0:
                hive["soldiers"] -= 1
                loss_text = "\n💀 1 отважный солдат погиб, сдерживая натиск."
        else:
            loss_text = "\n👑 Матка победила, но из-за своей медлительности сильно устала."
            
        bot.send_message(
            message.chat.id, 
            f"🏆 **Победа!**\nВраг повержен. Улей забирает ресурсы: `+{enemy['loot']}` биомассы.{loss_text}", 
            parse_mode="Markdown"
        )
    else:
        if not using_queen:
            lost_soldiers = min(hive["soldiers"], random.randint(1, 3))
            hive["soldiers"] -= lost_soldiers
            bot.send_message(message.chat.id, f"💔 **Отряд разбит.** Мы потеряли `-{lost_soldiers}` солдат.")
        else:
            # Из-за медлительности Матки при поражении улей грабят сильнее!
            stolen = min(hive["biomass"], enemy["loot"] * 2)
            hive["biomass"] = round(hive["biomass"] - stolen, 1)
            bot.send_message(
                message.chat.id, 
                f"💥 **Тяжёлое поражение!**\nМатка слишком медлительна, чтобы защитить все углы. "
                f"Хищник прорвался в кладовые и утащил `-{stolen}` биомассы!", 
                parse_mode="Markdown"
            )

# ==================== АДМИН ПАНЕЛЬ ====================

@bot.message_handler(commands=['users_list'])
def users_list_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    if not players:
        bot.send_message(message.chat.id, "📭 В ульях пусто.")
        return
        
    list_txt = "📋 **УЧАСТНИКИ ВСЕХ ГЛОБАЛЬНЫХ РАС:**\n━━━━━━━━━━━━━━━━━━━━\n"
    for num, (uid, data) in enumerate(players.items(), 1):
        race_info = data['race'] if data['race'] else "Выбирает фракцию"
        list_txt += f"{num}. 👤 **{data['username']}**\n   🆔 ID: `{uid}`\n   🧬 Глобальная раса: _{race_info}_\n   📊 Личный вклад: `{data['personal_contribution']}`\n━━━━━━━━━━━━━━━━━━━━\n"
        
    bot.send_message(message.chat.id, list_txt, parse_mode="Markdown")

@bot.message_handler(commands=['admin_players'])
def admin_players_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("📊 Состояние Гнезд", callback_data="adm_stats"))
    
    bot.send_message(
        message.chat.id, 
        "🎛 **Панель Творца (Глобальные ульи)**\n\n"
        "Админ-команды в чате:\n"
        "`/givecoins [ID] [Количество]` — начислить монеты в ОБЩИЙ УЛЕЙ\n"
        "`/givetitle [ID] [Титул]` — выдать личный титул\n"
        "`/users_list` — список игроков",
        parse_mode="Markdown", reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_callbacks(call):
    if call.from_user.id != ADMIN_ID: return
    action = call.data.replace("adm_", "")

    if action == "stats":
        txt = "📊 **Биологический мониторинг видов:**\n━━━━━━━━━━━━━━━━━━━━\n"
        for name, data in GLOBAL_HIVES.items():
            txt += f"🐜 **{name}**:\n💰 Биомасса: `{data['biomass']}` | Статус: `{data['status']}`\n🥚 Яйца: `{data['eggs']}` | 📦 Рабочие: `{data['workers']}` | ⚔️ Солдаты: `{data['soldiers']}`\n━━━━━━━━━━━━━━━━━━━━\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Назад", callback_data="adm_back"))
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        
    elif action == "back":
        admin_players_cmd(call.message)

@bot.message_handler(func=lambda msg: (msg.text.startswith('/givecoins') or msg.text.startswith('/givetitle')) and msg.from_user.id == ADMIN_ID)
def execute_admin_commands(message):
    parts = message.text.split(maxsplit=2)
    cmd = parts[0].replace('/', '')
    
    if len(parts) < 3:
        bot.send_message(message.chat.id, "❌ Неверный формат.")
        return
        
    try:
        target_id = int(parts[1])
        value_arg = parts[2]
    except ValueError:
        bot.send_message(message.chat.id, "❌ ID должен быть числом.")
        return

    if target_id not in players: return
    race = players[target_id]["race"]

    if cmd == "givecoins":
        try: amount = int(value_arg)
        except ValueError: return
        if race:
            GLOBAL_HIVES[race]["biomass"] += amount
            bot.send_message(message.chat.id, f"✅ В улей **{race}** добавлено `{amount}` монет!")
        
    elif cmd == "givetitle":
        title_name = value_arg.strip()
        if title_name not in players[target_id]["titles"]:
            players[target_id]["titles"].append(title_name)
            bot.send_message(message.chat.id, f"✅ Титул выдан.")

# ==================== HEALTH CHECK СЕРВЕР ====================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"EcoSystem is Simulated!")

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

if __name__ == '__main__':
    if os.environ.get("RENDER") or os.environ.get("PORT"):
        threading.Thread(target=run_health_server, daemon=True).start()
    
    print("Глобальный реалистичный бот запущен!")
    bot.infinity_polling()
