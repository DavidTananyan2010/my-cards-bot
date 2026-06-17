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

# ==================== БАЗА ДАННЫХ (В ПАМЯТИ) ====================
# Структура игрока: 
# { uid: { "faction": str, "race": str, "biomass": int, "eggs": int, "workers": int, "soldiers": int, "state": str } }
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
def init_player(uid):
    if uid not in players:
        players[uid] = {
            "faction": None,
            "race": None,
            "biomass": 10,       # Стартовая биомасса
            "eggs": 1,           # То самое 1 первое яйцо по задумке
            "workers": 0,        # Грузчики / Рабочие
            "soldiers": 0,       # Воины / Защитники
            "last_collect": 0    # Время последнего сбора ресурсов
        }

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
    init_player(uid)
    
    if players[uid]["faction"] is None:
        markup = types.InlineKeyboardMarkup()
        for faction in FACTIONS.keys():
            markup.add(types.InlineKeyboardButton(faction, callback_data=f"fac_{faction}"))
        
        bot.send_message(
            message.chat.id, 
            "👑 **Приветствуем тебя, Матка!**\n\nТы ищешь место для основания новой великой колонии. "
            "Для начала выбери свой вид насекомых:", 
            parse_mode="Markdown", 
            reply_markup=markup
        )
    else:
        bot.send_message(
            message.chat.id, 
            "🐜 Вы уже управляете своим гнездом!", 
            reply_markup=get_main_keyboard(uid)
        )

# Выбор Фракции и Расы
@bot.callback_query_handler(func=lambda call: call.data.startswith("fac_") or call.data.startswith("race_"))
def faction_callback(call):
    uid = call.from_user.id
    init_player(uid)
    
    if call.data.startswith("fac_"):
        faction = call.data.replace("fac_", "")
        players[uid]["faction"] = faction
        
        # Даем выбор расы внутри фракции
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
    init_player(uid)
    if players[uid]["faction"] is None: return

    p = players[uid]
    text = (
        f"🏰 **Статус гнезда колонии [{p['race']}]**\n"
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
    init_player(uid)
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
    init_player(uid)
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
    init_player(uid)
    if players[uid]["faction"] is None: return

    p = players[uid]
    now = time.time()
    
    # Кулдаун 15 секунд на сбор
    if now - p["last_collect"] < 15:
        remains = int(15 - (now - p["last_collect"]))
        bot.send_message(message.chat.id, f"⏳ Ваши рабочие ещё не вернулись с прошлых плантаций. Подождите {remains} сек.")
        return

    # Базовый сбор 5 ед + по 3 ед за каждого грузчика
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
    init_player(uid)
    if players[uid]["faction"] is None: return

    p = players[uid]
    if p["soldiers"] == 0:
        bot.send_message(message.chat.id, "❌ У вас нет **Солдат**. Отправлять в дикие земли некого, матка не может воевать одна!")
        return

    enemy = random.choice(ENEMIES)
    bot.send_message(message.chat.id, f"🧭 Ваш боевой отряд наткнулся на угрозу: **{enemy['name']}** (Сила: {enemy['power']})!")
    
    # Сила игрока = количество солдат + случайный кубик везения (0-2)
    player_power = p["soldiers"] + random.randint(0, 2)
    
    time.sleep(1.5) # Эффект ожидания битвы
    
    if player_power >= enemy["power"]:
        # Победа
        p["biomass"] += enemy["loot"]
        # Шанс потерять солдата в тяжелом бою
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
        # Поражение
        lost_soldiers = min(p["soldiers"], random.randint(1, 2))
        p["soldiers"] -= lost_soldiers
        bot.send_message(
            message.chat.id, 
            f"💔 **Поражение...**\n{enemy['name']} оказался сильнее ваших тактических феромонов. "
            f"Вы отступили, потеряв `-{lost_soldiers}` солдат.", 
            parse_mode="Markdown"
        )

# ==================== СЕРВЕР HEALTH CHECK ДЛЯ RENDER ====================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Hive Engine 2.0 is alive!")

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

if __name__ == '__main__':
    if os.environ.get("RENDER") or os.environ.get("PORT"):
        threading.Thread(target=run_health_server, daemon=True).start()
    
    print("Бот новой игры успешно запущен!")
    bot.infinity_polling()
