import os
import threading
import telebot
from telebot import types
import random
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

# 🔑 Токен
TOKEN = os.environ.get("BOT_TOKEN", "8701989939:AAFVTHvkObrmq6EsQClsTByOEL7tJNqg4_Q")
bot = telebot.TeleBot(TOKEN)

# 👑 ID Главного Администратора (Творца)
ADMIN_ID = 7501899378

# ==================== ГЛОБАЛЬНЫЕ ОБЩИЕ КОЛОНИИ ====================
GLOBAL_HIVES = {
    "Рыжие лесные": {"biomass": 50, "eggs": 3, "workers": 0, "soldiers": 0, "status": "Стабильно"},
    "Муравьи-Листорезы": {"biomass": 50, "eggs": 3, "workers": 0, "soldiers": 0, "status": "Стабильно"},
    "Черные садовые": {"biomass": 50, "eggs": 3, "workers": 0, "soldiers": 0, "status": "Стабильно"},
    "Медоносные пчёлы": {"biomass": 50, "eggs": 3, "workers": 0, "soldiers": 0, "status": "Стабильно"},
    "Земляные шмели": {"biomass": 50, "eggs": 3, "workers": 0, "soldiers": 0, "status": "Стабильно"},
    "Лесные osы-одиночки": {"biomass": 50, "eggs": 3, "workers": 0, "soldiers": 0, "status": "Стабильно"}
}

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
    """Фоновый поток, симулирующий постоянный голод, метаболизм и смерть насекомых"""
    while True:
        time.sleep(30) # Расчет происходит каждые 30 секунд
        for race, hive in GLOBAL_HIVES.items():
            # Если в расе еще нет игроков (население нулевое), не обсчитываем
            if hive["workers"] == 0 and hive["soldiers"] == 0 and hive["biomass"] == 50:
                continue
                
            # 🍽️ Расчет потребления (Матка ест 2, рабочий 0.5, солдат 1.0)
            consumption = 2 + (hive["workers"] * 0.5) + (hive["soldiers"] * 1.0)
            consumption = round(consumption, 1)
            
            if hive["biomass"] >= consumption:
                hive["biomass"] = round(hive["biomass"] - consumption, 1)
                hive["status"] = "Сыты (Потребление: -{} ед/30с)".format(consumption)
            else:
                # 🚨 НАЧАЛСЯ ГОЛОД
                hive["biomass"] = 0
                hive["status"] = "⚠️ ГОЛОД! Население умирает!"
                
                # Смерть косит касты по очереди (сначала яйца, потом рабочие, потом солдаты)
                if hive["eggs"] > 0:
                    hive["eggs"] -= 1
                elif hive["workers"] > 0:
                    hive["workers"] -= 1
                elif hive["soldiers"] > 0:
                    hive["soldiers"] -= 1

# Запуск фонового метаболизма колоний
threading.Thread(target=hive_life_cycle_loop, daemon=True).start()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def init_player(uid, first_name="Неизвестный"):
    if uid not in players:
        players[uid] = {
            "username": first_name,
            "faction": None,
            "race": None,
            "personal_contribution": 0,
            "titles": [],
            "last_collect": 0
        }

def get_main_keyboard(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if players[uid]["faction"] is None: return None
    markup.row("🏰 Общее Гнездо", "🥚 Инкубатор Расы")
    markup.row("🌾 Добыча для Улья", "⚔️ Военный Поход")
    return markup

# ==================== ИГРОВАЯ ЛОГИКА ====================

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    if players[uid]["faction"] is None:
        markup = types.InlineKeyboardMarkup()
        for faction in FACTIONS.keys():
            markup.add(types.InlineKeyboardButton(faction, callback_data=f"fac_{faction}"))
        bot.send_message(message.chat.id, "🐜 **Добро пожаловать в Глобальный Рой!**\n\nЗдесь бушует естественный отбор. Без еды колония погибнет от голода за считанные минуты. Выберите вид:", parse_mode="Markdown", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, f"🐜 Вы в строю расы **{players[uid]['race']}**!", reply_markup=get_main_keyboard(uid))

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
        bot.edit_message_text(f"Вы выбрали вид: **{faction}**.\nВыберите улей:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        
    elif call.data.startswith("race_"):
        race = call.data.replace("race_", "")
        players[uid]["race"] = race
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, f"✨ **Вы внутри улья [{race}]!**\n\n⚠️ Каждый рабочий и солдат хочет есть! Если общая биомасса упадет до 0, начнется мор и смерть населения. Бегом в инкубатор выращивать касты!", parse_mode="Markdown", reply_markup=get_main_keyboard(uid))

# Общее гнездо (Показывает статус голода)
@bot.message_handler(func=lambda msg: msg.text == "🏰 Общее Гнездо")
def nest_menu(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    if players[uid]["faction"] is None: return

    race = players[uid]["race"]
    hive = GLOBAL_HIVES[race]
    
    text = (
        f"🏰 **Глобальное Гнездо [{race}]**\n"
        f"Статус питания: `{hive['status']}`\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 **БИОМАССА (ЕДА НА СКЛАДЕ):** `{hive['biomass']}` ед.\n"
        f"🥚 **Яиц в инкубаторе:** {hive['eggs']} шт.\n\n"
        f"📋 **Популяция улья:**\n"
        f"📦 **Рабочие:** {hive['workers']} особей\n"
        f"⚔️ **Солдаты:** {hive['soldiers']} особей\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💡 _Внимание! Каждые 30 секунд улей потребляет биомассу. Не оставляйте склад пустым!_"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# Сбор ресурсов с ФИЗИКОЙ ВЕСА
@bot.message_handler(func=lambda msg: msg.text == "🌾 Добыча для Улья")
def collect_resources(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    if players[uid]["faction"] is None: return

    p = players[uid]
    race = p["race"]
    hive = GLOBAL_HIVES[race]
    
    if hive["workers"] == 0:
        bot.send_message(message.chat.id, "⚠️ Матка слишком тяжелая и медлительная, она не может собирать еду! Вырастите рабочих в инкубаторе.")
        return

    now = time.time()
    if now - p["last_collect"] < 15:
        bot.send_message(message.chat.id, f"⏳ Муравьи еще тащат прошлый груз. Подождите {int(15 - (now - p['last_collect']))} сек.")
        return

    # ⚖️ ФИЗИКА ВЕСА ДОБЫЧИ
    # Генерируем объект случайного веса (в мг/ед)
    loot_objects = [
        {"name": "дохлую гусеницу 🐛", "weight": 80},
        {"name": "крупную каплю нектара 💧", "weight": 40},
        {"name": "сочную травинку 🌱", "weight": 25},
        {"name": "кусок спелого яблока 🍏", "weight": 150}
    ]
    found = random.choice(loot_objects)
    
    # Максимальная подъемная сила зависит от количества рабочих (1 рабочий поднимает ~15 единиц веса)
    max_carry_power = hive["workers"] * 15
    
    if max_carry_power >= found["weight"]:
        # Рабочие успешно дотащили груз благодаря массе
        gained_biomass = round(found["weight"] / 4, 1)
        hive["biomass"] = round(hive["biomass"] + gained_biomass, 1)
        p["personal_contribution"] += gained_biomass
        msg = f"💪 **Сила физики!** Ваши рабочие нашли {found['name']} весом `{found['weight']} мг` и успешно дотащили её до склада благодаря численности! Общая казна улья пополнена на `+{gained_biomass}` ед. биомассы."
    else:
        # Груз оказался неподъемным для текущего числа рабочих!
        partial_loot = round(max_carry_power / 5, 1)
        hive["biomass"] = round(hive["biomass"] + partial_loot, 1)
        msg = f"😰 **Слишком тяжело!** Ваши рабочие нашли {found['name']} весом `{found['weight']} мг`. Но из-за законов физики и нехватки сил они не смогли поднять её целиком, отгрызли лишь кусочек на `+{partial_loot}` биомассы. Нужно больше рабочих!"

    p["last_collect"] = now
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

# Инкубатор
@bot.message_handler(func=lambda msg: msg.text == "🥚 Инкубатор Расы")
def incubator_menu(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    if players[uid]["faction"] is None: return
    race = players[uid]["race"]
    hive = GLOBAL_HIVES[race]
    
    markup = types.InlineKeyboardMarkup()
    if hive["eggs"] > 0:
        markup.row(types.InlineKeyboardButton("📦 Вырастить Рабочего", callback_data="hatch_worker"),
                   types.InlineKeyboardButton("⚔️ Вырастить Солдата", callback_data="hatch_soldier"))
    markup.row(types.InlineKeyboardButton("➕ Купить яйцо (30 биомассы)", callback_data="buy_egg"))
    bot.send_message(message.chat.id, f"🥚 **Инкубатор [{race}]**\nЯиц: {hive['eggs']} шт.\nЗдесь выводятся новые рты, которые нужно будет кормить!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("hatch_") or call.data == "buy_egg")
def incubator_callback(call):
    uid = call.from_user.id
    race = players[uid]["race"]
    hive = GLOBAL_HIVES[race]
    
    if call.data == "buy_egg":
        if hive["biomass"] < 30:
            bot.answer_callback_query(call.id, "❌ Нет биомассы для кладки яиц!", show_alert=True)
            return
        hive["biomass"] -= 30
        hive["eggs"] += 1
        bot.edit_message_text(f"🥚 **Инкубатор [{race}]**\nЯиц: {hive['eggs']} шт.", call.message.chat.id, call.message.message_id, reply_markup=call.message.reply_markup)
    elif call.data.startswith("hatch_"):
        if hive["eggs"] < 1: return
        hive["eggs"] -= 1
        role = call.data.replace("hatch_", "")
        if role == "worker": hive["workers"] += 1
        else: hive["soldiers"] += 1
        bot.edit_message_text(f"🎉 Вылупление завершено! Проверьте вкладку общего гнезда.", call.message.chat.id, call.message.message_id)

# Походы
@bot.message_handler(func=lambda msg: msg.text == "⚔️ Военный Поход")
def battle_system(message):
    uid = message.from_user.id
    race = players[uid]["race"]
    hive = GLOBAL_HIVES[race]
    enemy = random.choice(ENEMIES)
    
    bot.send_message(message.chat.id, f"🧭 Натиск природы: На улей движется **{enemy['name']}** (Сила: {enemy['power']})")
    time.sleep(1)
    
    power = (hive["soldiers"] * 5) if hive["soldiers"] > 0 else 25
    if power >= enemy["power"]:
        hive["biomass"] += enemy["loot"]
        if hive["soldiers"] > 0: hive["soldiers"] -= 1
        bot.send_message(message.chat.id, f"🏆 **Победа!** Хищник отступил, улей получил `+{enemy['loot']}` еды.")
    else:
        if hive["soldiers"] > 0:
            hive["soldiers"] = max(0, hive["soldiers"] - 2)
            bot.send_message(message.chat.id, "💔 Поражение. Солдаты разбиты.")
        else:
            stolen = min(hive["biomass"], 50)
            hive["biomass"] = round(hive["biomass"] - stolen, 1)
            bot.send_message(message.chat.id, f"💥 Королева ранена и отступила вглубь! Враги разграбили склад на `-{stolen}` биомассы.")

# ==================== АДМИНКА И КАНАЛ СВЯЗИ ====================
@bot.message_handler(commands=['admin_players'])
def admin_players_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📊 Мониторинг ульев", callback_data="adm_stats"))
    bot.send_message(message.chat.id, "🎛 Панель Творца экосистемы:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "adm_stats")
def admin_stats(call):
    txt = "📊 **Биологическое состояние видов:**\n\n"
    for name, data in GLOBAL_HIVES.items():
        txt += f"🐜 *{name}*: Биомасса: `{data['biomass']}` | Статус: `{data['status']}`\nНаселение: Рабочие ({data['workers']}), Солдаты ({data['soldiers']})\n\n"
    bot.send_message(call.message.chat.id, txt, parse_mode="Markdown")

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"EcoSystem is Simulated!")

if __name__ == '__main__':
    threading.Thread(target=lambda: HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), HealthCheckHandler).serve_forever(), daemon=True).start()
    bot.infinity_polling()
