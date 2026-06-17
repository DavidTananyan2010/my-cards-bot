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

# 👑 ID Главного Администратора (Творца) — ОБЯЗАТЕЛЬНО ПРОВЕРЬ ЕГО!
ADMIN_ID = 7501899378

# ==================== ГЛОБАЛЬНЫЕ ОБЩИЕ КОЛОНИИ ====================
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
                
                if hive["eggs"] > 0:
                    hive["eggs"] -= 1
                elif hive["workers"] > 0:
                    hive["workers"] -= 1
                elif hive["soldiers"] > 0:
                    hive["soldiers"] -= 1

# Запуск фонового метаболизма
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
        msg_text += "👑 **С возвращением, Творец! Ваша админка активна.**\n/admin_players — управление\n/users_list — список игроков\n\n"
    else:
        msg_text += f"ℹ️ _Ваш Telegram ID: `{uid}` (Передайте его создателю для получения прав)_\n\n"

    # 🔄 Если игрок уже выбрал фракцию, перезагружаем кнопки меню
    if players[uid]["faction"] is not None:
        bot.send_message(
            message.chat.id, 
            msg_text + f"🔄 **Игровые кнопки успешно перезагружены!**\nВы находитесь в строю расы: **{players[uid]['race']}**.", 
            parse_mode="Markdown", reply_markup=get_main_keyboard(uid)
        )
    else:
        # Для новых игроков запускаем стандартный диалог выбора фракции
        markup = types.InlineKeyboardMarkup()
        for faction in FACTIONS.keys():
            markup.add(types.InlineKeyboardButton(faction, callback_data=f"fac_{faction}"))
        
        bot.send_message(
            message.chat.id, 
            msg_text + "🐜 **Добро пожаловать в Глобальный Рой!**\n\nВы становитесь частью огромного общего организма. Без еды колония погибнет от голода. Выберите вид насекомых:", 
            parse_mode="Markdown", reply_markup=markup
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
    
    if players[uid]["faction"] is None or players[uid]["race"] is None:
        bot.send_message(message.chat.id, "⚠️ Ваши данные улья не найдены или были сброшены из-за перезапуска сервера. Пожалуйста, введите /start, чтобы обновить профиль.")
        return

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
        f"👤 **Личные данные:**\n"
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
    
    if players[uid]["faction"] is None or players[uid]["race"] is None:
        bot.send_message(message.chat.id, "⚠️ Данные не найдены. Пожалуйста, введите /start")
        return

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
    
    if players[uid]["race"] is None:
        bot.answer_callback_query(call.id, "⚠️ Данные устарели, введите /start", show_alert=True)
        return
        
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

# Сбор ресурсов с ФИЗИКОЙ ВЕСА и защитой от перезапусков
@bot.message_handler(func=lambda msg: msg.text == "🌾 Добыча для Улья")
def collect_resources(message):
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    
    p = players[uid]
    if p["faction"] is None or p["race"] is None:
        bot.send_message(message.chat.id, "⚠️ Сервер обновился, и ваш сеанс истек. Пожалуйста, нажмите /start, чтобы заново активировать игровое меню.")
        return

    race = p["race"]
    hive = GLOBAL_HIVES[race]
    
    if hive["workers"] == 0:
        error_txt = (
            "⚠️ **Сбор невозможен!**\n\n"
            "В вашей колонии ещё **нет вылупившихся рабочих**!\n"
            "Матка — самое крупное насекомое, она невероятно медлительна "
            "и не способна выйти на поверхность самостоятельно.\n\n"
            "👉 С
