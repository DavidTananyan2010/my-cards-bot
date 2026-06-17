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
            parse
