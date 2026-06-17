import os
import threading
import telebot
from telebot import types
import random
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

# 🔑 Автоматический токен из Render или твой актуальный
TOKEN = os.environ.get("BOT_TOKEN", "8701989939:AAFVTHvkObrmq6EsQClsTByOEL7tJNqg4_Q")
bot = telebot.TeleBot(TOKEN)

# 👑 ID Главного Администратора (Творца)
ADMIN_ID = 7501899378

# ==================== БАЗА ДАННЫХ (В ПАМЯТИ) ====================
players = {}

# Настройки фракций и рас
FACTIONS = {
    "Муравьи 🐜": ["Рыжие лесные", "Муравьи-Листорезы", "Черные садовые"],
    "Пчёлы 🐝": ["Медоносные пчёлы", "Земляные шмели", "Лесные осы-одиночки"]
}

# Враги насекомые
ENEMIES = [
    {"name": "Жук-Олень 🪲", "power": 3, "loot": 40},
    {"name": "Паук-Волк 🕷️", "power": 7, "loot": 90},
    {"name": "Дикая Оса 🐝", "power": 5, "loot": 60},
    {"name": "Хищная Многоножка 🐛", "power": 12, "loot": 180}
]

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def init_player(uid, first_name="Неизвестный муравей"):
    if uid not in players:
        players[uid] = {
            "username": first_name, 
            "faction": None,
            "race": None,
            "biomass": 10,       
            "eggs": 1,           
            "workers": 0,        
            "soldiers": 0,       
            "titles": [],         # Список титулов игрока
            "last_collect": 0    
        }
    if players[uid]["username"] != first_name and first_name != "Неизвестный муравей":
        players[uid]["username"] = first_name

def get_main_keyboard(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if players[uid]["faction"] is None:
        return None
    markup.row("🏰 Моё Гнездо", "🥚 Инкубатор (Яйца)")
    markup.row("🌾 Сбор ресурсов", "⚔️ Поход на врагов")
    return markup

# ==================== КОМАНДЫ И ЛОГИКА ИГРЫ ====================

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    
    msg_text = ""
    if uid == ADMIN_ID:
        msg_text += "👑 **С возвращением, Творец!** Вам доступны админ-команды:\n/admin_players — инлайн-панель\n/users_list — список всех игроков\n\n"

    if players[uid]["faction"] is None:
        markup = types.InlineKeyboardMarkup()
        for faction in FACTIONS.keys():
            markup.add(types.InlineKeyboardButton(faction, callback_data=f"fac_{faction}"))
        
        bot.send_message(
            message.chat.id, 
            msg_text + "👑 **Приветствуем тебя, Матка!**\n\nТы ищешь место для основания новой великой колонии. "
            "Для начала выбери свой вид насекомых:", 
            parse_mode="Markdown", 
            reply_markup=markup
        )
    else:
        bot.send_message(
            message.chat.id, 
            msg_text + "🐜 Вы уже управляете своим гнездом!", 
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(uid)
        )

# Выбор Фракции и Расы
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
            f"Вы выбрали вид: **{faction}**.\nТеперь выберите подвид (расу) вашей Королевы:", 
            call.message.chat.id, call.message.message_id, 
            parse_mode="Markdown", reply_markup=markup
        )
        
    elif call.data.startswith("race_"):
        race = call.data.replace("race_", "")
        players[uid]["race"] = race
        
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
        welcome_txt = (
            f"✨ **Колония основана!** ✨\n\n"
            f"Вы — Королева расы **{race}** ({players[uid]['faction']}).\n"
            f"Плутая по диким землям, вы наткнулись на ветхое, заброшенное чужое гнездо. "
            f"Внутри среди пыли вы обнаружили **1 уцелевшее яйцо** 🥚.\n\n"
            f"Пора возродить былую мощь этого места! Используйте меню ниже."
        )
        bot.send_message(call.message.chat.id, welcome_txt, parse_mode="Markdown", reply_markup=get_main_keyboard(uid))

# Меню Гнезда
@bot.message_handler(func=lambda msg: msg.text == "🏰 Моё Гнездо")
def nest_menu(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    if players[uid]["faction"] is None: return

    p = players[uid]
    
    # Формируем строку титулов, если они есть
    titles_str = f"\n🎖️ **Титулы:** {', '.join(p['titles'])}" if p.get("titles") else ""

    text = (
        f"🏰 **Статус гнезда колонии [{p['race']}]**\n"
        f"👤 Ваш TG ID: `{uid}`{titles_str}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 **Биомасса (ресурсы):** `{p['biomass']}` ед.\n"
        f"🥚 **Невылупившиеся яйца:** {p['eggs']} шт.\n\n"
        f"📋 **Ваша популяция:**\n"
        f"📦 **Грузчики (Рабочие):** {p['workers']} особей\n"
        f"⚔️ **Солдаты (Защитники):** {p['soldiers']} особей\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💡 _Грузчики увеличивают добычу биомассы. Солдаты нужны для победы над врагами._"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# Инкубатор (Вылупление)
@bot.message_handler(func=lambda msg: msg.text == "🥚 Инкубатор (Яйца)")
def incubator_menu(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    if players[uid]["faction"] is None: return

    p = players[uid]
    markup = types.InlineKeyboardMarkup()
    
    if p["eggs"] > 0:
        markup.row(
            types.InlineKeyboardButton("📦 Вырастить Грузчика", callback_data="hatch_worker"),
            types.InlineKeyboardButton("⚔️ Вырастить Солдата", callback_data="hatch_soldier")
        )
    markup.row(types.InlineKeyboardButton("➕ Купить яйцо (15 биомассы)", callback_data="buy_egg"))

    bot.send_message(
        message.chat.id, 
        f"🥚 **Инкубационный отсек**\n\nУ вас в наличии: {p['eggs']} яиц.\n"
        f"Вы можете превратить яйцо в нужную вам особь.", 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("hatch_") or call.data == "buy_egg")
def incubator_callback(call):
    uid = call.from_user.id
    init_player(uid, call.from_user.first_name)
    p = players[uid]
    
    if call.data == "buy_egg":
        if p["biomass"] < 15:
            bot.answer_callback_query(call.id, "❌ Недостаточно биомассы!", show_alert=True)
            return
        p["biomass"] -= 15
        p["eggs"] += 1
        bot.answer_callback_query(call.id, "🥚 Яйцо отложено в инкубатор!")
        bot.edit_message_text(f"🥚 **Инкубационный отсек**\n\nУ вас в наличии: {p['eggs']} яиц.", call.message.chat.id, call.message.message_id, reply_markup=call.message.reply_markup)
        
    elif call.data.startswith("hatch_"):
        if p["eggs"] < 1:
            bot.answer_callback_query(call.id, "❌ Нет яиц для вылупления!", show_alert=True)
            return
        
        p["eggs"] -= 1
        role = call.data.replace("hatch_", "")
        
        if role == "worker":
            p["workers"] += 1
            msg = "🐣 Из яйца успешно вылупился **Грузчик**! Он сразу приступил к очистке заброшенных камер."
        else:
            p["soldiers"] += 1
            msg = "⚔️ Из кокона прогрызся мощный **Солдат**! Он встал на охрану периметра гнезда."
            
        bot.answer_callback_query(call.id, "Вылупление завершено!")
        bot.edit_message_text(f"🎉 {msg}\n\nОсталось яиц: {p['eggs']} шт.", call.message.chat.id, call.message.message_id)

# Сбор биомассы
@bot.message_handler(func=lambda msg: msg.text == "🌾 Сбор ресурсов")
def collect_resources(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    if players[uid]["faction"] is None: return

    p = players[uid]
    now = time.time()
    
    if now - p["last_collect"] < 15:
        remains = int(15 - (now - p["last_collect"]))
        bot.send_message(message.chat.id, f"⏳ Ваши рабочие ещё не вернулись с прошлых плантаций. Подождите {remains} сек.")
        return

    base_loot = 5
    worker_bonus = p["workers"] * 3
    total_loot = base_loot + worker_bonus
    
    p["biomass"] += total_loot
    p["last_collect"] = now
    
    bot.send_message(
        message.chat.id, 
        f"🌾 **Экспедиция за кормом**\n\n"
        f"Вы отправили рабочих на поиски.\n"
        f"📈 Собрано биомассы: `+{total_loot}` ед. (Из них бонус от грузчиков: `+{worker_bonus}`)"
    )

# Походы и Битвы с насекомыми
@bot.message_handler(func=lambda msg: msg.text == "⚔️ Поход на врагов")
def battle_system(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    if players[uid]["faction"] is None: return

    p = players[uid]
    if p["soldiers"] == 0:
        bot.send_message(message.chat.id, "❌ У вас нет **Солдат**. Отправлять в дикие земли некого, матка не может воевать одна!")
        return

    enemy = random.choice(ENEMIES)
    bot.send_message(message.chat.id, f"🧭 Ваш боевой отряд наткнулся на угроzen: **{enemy['name']}** (Сила: {enemy['power']})!")
    
    player_power = p["soldiers"] + random.randint(0, 2)
    time.sleep(1.5) 
    
    if player_power >= enemy["power"]:
        p["biomass"] += enemy["loot"]
        lost = 0
        if random.choice([True, False]) and p["soldiers"] > 0:
            p["soldiers"] -= 1
            lost = 1
        
        loss_text = "\n💀 К сожалению, 1 солдат погиб в бою." if lost else ""
        bot.send_message(
            message.chat.id, 
            f"🏆 **Победа улья!**\nВраг разбит. Вы утащили его тушку на биомассу: `+{enemy['loot']}` монет.{loss_text}", 
            parse_mode="Markdown"
        )
    else:
        lost_soldiers = min(p["soldiers"], random.randint(1, 2))
        p["soldiers"] -= lost_soldiers
        bot.send_message(
            message.chat.id, 
            f"💔 **Поражение...**\n{enemy['name']} оказался сильнее ваших тактических феромонов. "
            f"Вы отступили, потеряв `-{lost_soldiers}` солдат.", 
            parse_mode="Markdown"
        )

# ==================== ОБНОВЛЕННАЯ АДМИН ПАНЕЛЬ ====================

# Текстовый список игроков под новое имя /users_list
@bot.message_handler(commands=['users_list'])
def users_list_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    
    if not players:
        bot.send_message(message.chat.id, "📭 База игроков пуста. Никто еще не заходил.")
        return
        
    list_txt = "📋 **СПИСОК ВСЕХ ИГРОКОВ УЛЬЯ:**\n━━━━━━━━━━━━━━━━━━━━\n"
    for num, (uid, data) in enumerate(players.items(), 1):
        race_info = data['race'] if data['race'] else "Ещё на старте"
        titles_info = ", ".join(data['titles']) if data['titles'] else "Нет титулов"
        list_txt += f"{num}. 👤 **{data['username']}**\n   🆔 ID: `{uid}`\n   🧬 Раса: _{race_info}_\n   💰 Баланс: `{data['biomass']}` биомассы\n   🏅 Титулы: _{titles_info}_\n━━━━━━━━━━━━━━━━━━━━\n"
        
    bot.send_message(message.chat.id, list_txt, parse_mode="Markdown")

# Инлайн панель под новое имя /admin_players
@bot.message_handler(commands=['admin_players'])
def admin_players_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("📊 Статистика серверов", callback_data="adm_stats"),
               types.InlineKeyboardButton("👥 Краткий список", callback_data="adm_list"))
    markup.row(types.InlineKeyboardButton("🎁 Глобальный бонус (+биомасса)", callback_data="adm_bonus"))
    
    bot.send_message(
        message.chat.id, 
        "🎛 **Панель Творца (Администратор)**\n\n"
        "Доступные команды прямо в чате:\n"
        "`/givecoins [ID] [Количество]` — выдать монеты биомассы\n"
        "`/givetitle [ID] [Название титула]` — выдать красивый титул\n"
        "`/users_list` — выгрузить полный текстовый список",
        parse_mode="Markdown", reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_callbacks(call):
    if call.from_user.id != ADMIN_ID: return
    action = call.data.replace("adm_", "")

    if action == "stats":
        total_players = len(players)
        total_bio = sum(p["biomass"] for p in players.values())
        total_eggs = sum(p["eggs"] for p in players.values())
        total_workers = sum(p["workers"] for p in players.values())
        total_soldiers = sum(p["soldiers"] for p in players.values())
        
        txt = (
            f"📊 **Глобальная статистика:**\n\n"
            f"👥 Активных колоний (игроков): **{total_players}**\n"
            f"💰 Всего биомассы в мире: **{total_bio}**\n"
            f"🥚 Всего яиц в инкубаторах: **{total_eggs}**\n"
            f"📦 Общая армия грузчиков: **{total_workers}**\n"
            f"⚔️ Общая армия солдат: **{total_soldiers}**"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Назад", callback_data="adm_back"))
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    elif action == "list":
        if not players:
            txt = "📭 База игроков улья пуста."
        else:
            txt = "📋 **Краткий список ID:**\n\n"
            for uid, data in players.items():
                txt += f"• {data['username']} — `{uid}`\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Назад", callback_data="adm_back"))
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    elif action == "bonus":
        msg = bot.send_message(call.message.chat.id, "Введи количество биомассы для глобальной раздачи (число):")
        bot.register_next_step_handler(msg, process_global_bonus)
        
    elif action == "back":
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("📊 Статистика серверов", callback_data="adm_stats"),
                   types.InlineKeyboardButton("👥 Краткий список", callback_data="adm_list"))
        markup.row(types.InlineKeyboardButton("🎁 Глобальный бонус (+биомасса)", callback_data="adm_bonus"))
        bot.edit_message_text("🎛 **Панель Творца (Администратор)**", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

def process_global_bonus(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        amount = int(message.text)
        for uid in players:
            players[uid]["biomass"] += amount
        bot.send_message(message.chat.id, f"✅ Всем игрокам ({len(players)} чел.) успешно выдано по `{amount}` биомассы!", parse_mode="Markdown")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Ошибка. Нужно ввести число.")

# Текстовые команды выдачи монет и титулов
@bot.message_handler(func=lambda msg: (msg.text.startswith('/givecoins') or msg.text.startswith('/givetitle')) and msg.from_user.id == ADMIN_ID)
def execute_admin_commands(message):
    parts = message.text.split(maxsplit=2)
    cmd = parts[0].replace('/', '')
    
    if len(parts) < 3:
        if cmd == "givecoins":
            bot.send_message(message.chat.id, "❌ Формат: `/givecoins [ID пользователя] [количество]`", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ Формат: `/givetitle [ID пользователя] [название титула]`", parse_mode="Markdown")
        return
        
    try:
        target_id = int(parts[1])
        value_arg = parts[2] # Это либо число монет, либо строка титула
    except ValueError:
        bot.send_message(message.chat.id, "❌ ID пользователя должен быть числом!")
        return

    if target_id not in players:
        bot.send_message(message.chat.id, "❌ Игрок с таким ID не найден в базе данных!")
        return

    if cmd == "givecoins":
        try:
            amount = int(value_arg)
        except ValueError:
            bot.send_message(message.chat.id, "❌ Количество монет должно быть числом!")
            return
            
        players[target_id]["biomass"] += amount
        bot.send_message(message.chat.id, f"✅ Игроку {target_id} успешно начислено `{amount}` монет.", parse_mode="Markdown")
        try: bot.send_message(target_id, f"🎁 Творец даровал вашей колонии `{amount}` монет биомассы!", parse_mode="Markdown")
        except: pass
        
    elif cmd == "givetitle":
        title_name = value_arg.strip()
        if title_name not in players[target_id]["titles"]:
            players[target_id]["titles"].append(title_name)
            bot.send_message(message.chat.id, f"✅ Игроку {target_id} выдан титул: `[{title_name}]`", parse_mode="Markdown")
            try: bot.send_message(target_id, f"👑 Творец удостоил вас великого титула: **{title_name}**!", parse_mode="Markdown")
            except: pass
        else:
            bot.send_message(message.chat.id, "❌ У этого игрока уже есть такой титул.")

# ==================== СЕРВЕР HEALTH CHECK ДЛЯ RENDER ====================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Hive Engine 2.2 is alive!")

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

if __name__ == '__main__':
    if os.environ.get("RENDER") or os.environ.get("PORT"):
        threading.Thread(target=run_health_server, daemon=True).start()
    
    print("Бот с новыми админ-командами запущен!")
    bot.infinity_polling()
