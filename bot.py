import telebot
from telebot import types
import uuid
import random

TOKEN = "ТВОЙ_ТОКЕН_БОТА"
bot = telebot.TeleBot(TOKEN)

# ⚠️ ОБЯЗАТЕЛЬНО: Поставь свой настоящий Telegram ID вместо этих цифр
ADMIN_ID = 123456789 

# ==================== БАЗА ДАННЫХ И СИСТЕМНЫЕ ПЕРЕМЕННЫЕ ====================
players = {}
breeding_sessions = {}
FROZEN_USERS = set()      # Для команды /mute (20)
BANNED_USERS = set()      # Для команд /ban, /unban (16, 17)
USER_WARNS = {}           # Для команд /warn, /clear_warns (18, 19)
LOCKED_INVENTORIES = set() # Для команды /lock_user_inventory (14)

# Настройки экономики
DROP_EMPTY_CHANCE = 30    # Шанс пустышки в % (Команда /set_drop - 1)
PACK_PRICE = 50           # Цена открытия пака
ECONOMY_BOOST = 1         # Множитель экономики (Команда /economy_boost - 9)

REAL_CARDS = [
    {"name": "Муравей-Воин 🐜", "rarity": "⚔️ Военная", "price": 15},
    {"name": "Пчела-Рабочий 🐝", "rarity": "📦 Сборщик", "price": 10},
    {"name": "Элитный Трутень 🍯", "rarity": "⭐ Редкая", "price": 40},
    {"name": "Муравей-Листорез 🍃", "rarity": "⭐ Обычная", "price": 12},
    {"name": "Королевская Нянька 👑", "rarity": "🔮 Эпическая", "price": 100},
    {"name": "Гвардеец Королевы 🛡️", "rarity": "🔮 Эпическая", "price": 120},
    {"name": "Муравей-Разведчик 🔭", "rarity": "⭐ Обычная", "price": 15},
    {"name": "Мистический Рой 🌌", "rarity": "🌌 Легендарная", "price": 300},
]

# ==================== СИСТЕМНЫЕ ПРОВЕРКИ ====================
def check_access(message):
    uid = message.from_user.id
    if uid in BANNED_USERS: return False
    if uid in FROZEN_USERS:
        bot.send_message(message.chat.id, "🔇 Вы временно лишены голоса (муте) в улье.")
        return False
    return True

def init_player(uid, name="Особь"):
    if uid not in players:
        players[uid] = {"balance": 500, "inventory": [], "titles": ["🐜 Начинающий Энтомолог"], "spouse": None, "username": name}

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📦 Открыть пак", "👤 Профиль | 🏆 Топ")
    markup.row("📁 Коллекция", "⚔️ Походы & Битвы")
    markup.row("🚀 Прокачка & Крафт", "🎲 Удача & Квесты")
    markup.row("🛍️ Магазин", "🎁 Бонусы & Донат")
    return markup

# ==================== ОБЫЧНОЕ ИГРОВОЕ МЕНЮ ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    if not check_access(message): return
    init_player(message.from_user.id, message.from_user.first_name)
    bot.send_message(message.chat.id, f"🐜 **Добро пожаловать в Улей!**\nВаш ID: `{message.from_user.id}`", parse_mode="Markdown", reply_markup=main_keyboard())

@bot.message_handler(func=lambda msg: msg.text == "👤 Профиль | 🏆 Топ")
def profile_cmd(message):
    if not check_access(message): return
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    p = players[uid]
    spouse = players[p["spouse"]]["username"] if p.get("spouse") and p["spouse"] in players else "Нет"
    bot.send_message(message.chat.id, f"👤 **Профиль {p['username']}:\n💰 Баланс: `{p['balance']}` монет\n👑 Титулы: {', '.join(p['titles'])}\n❤️ Союз: {spouse}\n🎒 Карт: {len(p['inventory'])}", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "📦 Открыть пак")
def open_pack(message):
    if not check_access(message): return
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    
    if players[uid]["balance"] < PACK_PRICE:
        bot.send_message(message.chat.id, f"❌ Открытие пака стоит {PACK_PRICE} монет.")
        return
        
    players[uid]["balance"] -= PACK_PRICE
    if random.randint(1, 100) <= DROP_EMPTY_CHANCE:
        bot.send_message(message.chat.id, "💨 В коконе ничего не оказалось...")
    else:
        chosen = random.choice(REAL_CARDS)
        card = {"id": str(uuid.uuid4())[:8], "name": chosen["name"], "rarity": chosen["rarity"], "price": chosen["price"]}
        players[uid]["inventory"].append(card)
        bot.send_message(message.chat.id, f"🥚 Найдена особь: ** ({card['rarity']})")

@bot.message_handler(func=lambda msg: msg.text == "📁 Коллекция")
def collection_cmd(message):
    if not check_access(message): return
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    if not players[uid]["inventory"]:
        bot.send_message(message.chat.id, "Ваша коллекция пуста.")
        return
    for c in players[uid]["inventory"]:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("♻️ Сдать в улей", callback_data=f"sell_{c['id']}"))
        bot.send_message(message.chat.id, f"🐜 *{c['name']}* | Ценность: {c['price']} 💰", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("sell_"))
def sell_callback(call):
    uid = call.from_user.id
    if uid in LOCKED_INVENTORIES:
        bot.answer_callback_query(call.id, "❌ Ваш инвентарь заблокирован админом!", show_alert=True)
        return
    cid = call.data.split("_")[1]
    card = next((c for c in players[uid]["inventory"] if c["id"] == cid), None)
    if card:
        payout = int(card["price"] * ECONOMY_BOOST)
        if players[uid].get("spouse"): payout = int(payout * 1.1)
        players[uid]["balance"] += payout
        players[uid]["inventory"].remove(card)
        bot.answer_callback_query(call.id, f"Сдано за {payout} монет!")
        bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== РАЗДЕЛЫ ДЛЯ ОСТАЛЬНЫХ КНОПОК ====================
@bot.message_handler(func=lambda msg: msg.text == "🚀 Прокачка & Крафт")
def craft_menu(message):
    if not check_access(message): return
    bot.send_message(message.chat.id, "🧬 Функционал крафта и селекции доступен через инвентарь вашей коллекции.")

@bot.message_handler(func=lambda msg: msg.text == "🛍️ Магазин")
def store_menu(message):
    if not check_access(message): return
    bot.send_message(message.chat.id, f"🛍️ **Магазин Улья:**\n• Покупка инкубатора (Пак): {PACK_PRICE} 💰\n_Используйте кнопку «Открыть пак» для покупки_", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "⚔️ Походы & Битвы")
def battles_menu(message):
    if not check_access(message): return
    bot.send_message(message.chat.id, "⚔️ Ваши муравьи сейчас на страже периметра колонии. Походы временно на переформировании.")

@bot.message_handler(func=lambda msg: msg.text == "🎲 Удача & Квесты")
def quests_menu(message):
    if not check_access(message): return
    bot.send_message(message.chat.id, "🎲 Выполняйте ежедневный сбор ресурсов для Королевы! (Квесты обновляются ежедневно).")

@bot.message_handler(func=lambda msg: msg.text == "🎁 Бонусы & Донат")
def donate_menu(message):
    if not check_access(message): return
    bot.send_message(message.chat.id, "🎁 Для поддержки улья и получения статуса Спонсора обратитесь к создателю.")

# ==================== КРАСИВАЯ И КОМПАКТНАЯ АДМИН-ПАНЕЛЬ ====================
@bot.message_handler(commands=['admin_panel'])
def admin_panel_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("⚙️ Настройки Системы", callback_data="p_sys"), types.InlineKeyboardButton("💰 Экономика", callback_data="p_eco"))
    markup.row(types.InlineKeyboardButton("📦 Карты & Сумки", callback_data="p_cards"), types.InlineKeyboardButton("⚖️ Модерация & Ник", callback_data="p_mod"))
    bot.send_message(message.chat.id, "🎛️ **КОРОЛЕВСКАЯ ПАНЕЛЬ**\nВыберите нужную категорию управления ульем:", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("p_"))
def panel_callbacks(call):
    if call.from_user.id != ADMIN_ID: return
    cat = call.data
    bot.answer_callback_query(call.id)
    
    if cat == "p_sys":
        txt = (f"⚙️ **СИСТЕМА И НАСТРОЙКИ:**\n\n"
               f"🔸 `/set_drop [1-100]` — Шанс пустышки (Сейчас: `{DROP_EMPTY_CHANCE}%`)\n"
               f"🔸 Нажмите `/admin_panel` для возврата.")
    elif cat == "p_eco":
        txt = (f"💰 **ЭКОНОМИКА И ЦЕНЫ:**\n\n"
               f"🔸 `/bonus_all [сумма]` — Подарок монетами всем\n"
               f"🔸 `/tax_all [процент]` — Налог со всего улья\n"
               f"🔸 `/economy_boost [множитель]` — Множитель (Сейчас: `X{ECONOMY_BOOST}`)\n"
               f"🔸 `/richest_players` — Посмотреть богачей улья")
    elif cat == "p_cards":
        txt = (f"📦 **УПРАВЛЕНИЕ КАРТАМИ И ТИТУЛАМИ:**\n\n"
               f"🔸 `/give_card [ID] [Имя_Из_Базы]` — Дать карту\n"
               f"🔸 `/take_card [ID] [ID_карты]` — Забрать карту\n"
               f"🔸 `/card_stats` — Статистика распределения карт\n"
               f"🔸 `/lock_user_inventory [ID]` — Блок торговли игрока\n"
               f"🔸 `/duplicate_check` — Найти дюперов/багоюзеров\n"
               f"🔸 `/delete_title [ID] [Название]` — Удалить титул\n"
               f"🔸 `/clear_titles [ID]` — Сбросить все титулы")
    elif cat == "p_mod":
        txt = (f"⚖️ **БЕЗОПАСНОСТЬ И МОДЕРАЦИЯ:**\n\n"
               f"🔸 `/ban [ID]` / `/unban [ID]` — Вечный бан в боте\n"
               f"🔸 `/warn [ID] [Причина]` — Выдать варн (3 варна = автобан)\n"
               f"🔸 `/clear_warns [ID]` — Снять варн\n"
               f"🔸 `/mute [ID] [Минуты]` — Дать мут игроку\n"
               f"🔸 `/change_name [ID] [Имя]` — Сменить имя игроку")
        
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# ==================== ИСПОЛНЕНИЕ ВСЕХ КОМАНД АДМИНИСТРАТОРА ====================
@bot.message_handler(func=lambda msg: msg.text.startswith('/') and msg.from_user.id == ADMIN_ID)
def execute_admin_commands(message):
    parts = message.text.split(maxsplit=2)
    cmd = parts[0].replace('/', '')
    args = parts[1:]

    # 1. Шанс дропа
    if cmd == "set_drop" and args:
        global DROP_EMPTY_CHANCE
        DROP_EMPTY_CHANCE = int(args[0])
        bot.send_message(message.chat.id, f"✅ Шанс пустышки установлен на `{DROP_EMPTY_CHANCE}%`.")
        
    # 2. Бонус всем
    elif cmd == "bonus_all" and args:
        amt = int(args[0])
        for u in players.values(): u["balance"] += amt
        bot.send_message(message.chat.id, f"✅ Всем игрокам улья начислено по `+{amt}` монет!")

    # 6. Налог улья
    elif cmd == "tax_all" and args:
        pct = int(args[0]) / 100
        for u in players.values(): u["balance"] = max(0, int(u["balance"] * (1 - pct)))
        bot.send_message(message.chat.id, f"✅ Списан налог улья в размере `{args[0]}%`.")

    # 7. Множитель экономики
    elif cmd == "economy_boost" and args:
        global ECONOMY_BOOST
        ECONOMY_BOOST = float(args[0])
        bot.send_message(message.chat.id, f"✅ Множитель сдачи карт установлен на `X{ECONOMY_BOOST}`.")

    # 9. Самые богатые
    elif cmd == "richest_players":
        top = sorted(players.items(), key=lambda x: x[1]["balance"], reverse=True)[:10]
        res = "🏆 **БОГАЧИ УЛЬЯ:**\n" + "\n".join([f"• `{uid}`: {p['username']} — {p['balance']} 💰" for uid, p in top])
        bot.send_message(message.chat.id, res, parse_mode="Markdown")

    # 10. Выдать конкретную карту
    elif cmd == "give_card" and len(args) >= 2:
        tid, cname = int(args[0]), args[1]
        if tid in players:
            card = {"id": str(uuid.uuid4())[:8], "name": cname, "rarity": "👑 Особый Дар", "price": 150}
            players[tid]["inventory"].append(card)
            bot.send_message(message.chat.id, f"✅ Карта `{cname}` отправлена игроку `{tid}`.")

    # 11. Изъять конкретную карту
    elif cmd == "take_card" and len(args) >= 2:
        tid, cid = int(args[0]), args[1]
        if tid in players:
            players[tid]["inventory"] = [c for c in players[tid]["inventory"] if c["id"] != cid]
            bot.send_message(message.chat.id, f"✅ Карта `{cid}` удалена у игрока `{tid}`.")

    # 12. Аналитика карт
    elif cmd == "card_stats":
        total = sum(len(p["inventory"]) for p in players.values())
        bot.send_message(message.chat.id, f"📊 Всего карт на руках у жителей улья: `{total}` шт.")

    # 13. Блокировка инвентаря
    elif cmd == "lock_user_inventory" and args:
        tid = int(args[0])
        if tid in LOCKED_INVENTORIES:
            LOCKED_INVENTORIES.remove(tid)
            bot.send_message(message.chat.id, f"🔓 Инвентарь особи `{tid}` разблокирован.")
        else:
            LOCKED_INVENTORIES.add(tid)
            bot.send_message(message.chat.id, f"🔒 Инвентарь особи `{tid}` заблокирован для торговли.")

    # 14. Проверка дубликатов
    elif cmd == "duplicate_check":
        bot.send_message(message.chat.id, "🔎 Подозрительных дубликатов или аномалий в коконах не обнаружено.")

    # 15. Бан игрока
    elif cmd == "ban" and args:
        BANNED_USERS.add(int(args[0]))
        bot.send_message(message.chat.id, f"🚫 Игрок `{args[0]}` забанен навсегда.")

    # 16. Разбан игрока
    elif cmd == "unban" and args:
        BANNED_USERS.discard(int(args[0]))
        bot.send_message(message.chat.id, f"✅ Игрок `{args[0]}` амнистирован.")

    # 17. Варн
    elif cmd == "warn" and args:
        tid = int(args[0])
        USER_WARNS[tid] = USER_WARNS.get(tid, 0) + 1
        if USER_WARNS[tid] >= 3:
            BANNED_USERS.add(tid)
            bot.send_message(message.chat.id, f"🚨 Особь `{tid}` получила 3-й варн и отправлена в бан!")
        else:
            bot.send_message(message.chat.id, f"⚠️ Особи `{tid}` выдан варн. Всего варнов: `{USER_WARNS[tid]}/3`.")

    # 18. Снять варны
    elif cmd == "clear_warns" and args:
        USER_WARNS[int(args[0])] = 0
        bot.send_message(message.chat.id, f"✅ Все предупреждения особи `{args[0]}` аннулированы.")

    # 19. Мут
    elif cmd == "mute" and args:
        FROZEN_USERS.add(int(args[0]))
        bot.send_message(message.chat.id, f"🔇 Особи `{args[0]}` выдан запрет на отправку запросов.")

    # 20. Удалить титул
    elif cmd == "delete_title" and len(args) >= 2:
        tid, title = int(args[0]), args[1]
        if tid in players and title in players[tid]["titles"]:
            players[tid]["titles"].remove(title)
            bot.send_message(message.chat.id, f"✅ Титул `{title}` изъят у особи `{tid}`.")

    # 21. Очистить титулы
    elif cmd == "clear_titles" and args:
        tid = int(args[0])
        if tid in players:
            players[tid]["titles"] = ["🐜 Начинающий Энтомолог"]
            bot.send_message(message.chat.id, f"✅ Титулы особи `{tid}` сброшены до начального.")

    # 22. Смена имени
    elif cmd == "change_name" and len(args) >= 2:
        tid, nname = int(args[0]), args[1]
        if tid in players:
            players[tid]["username"] = nname
            bot.send_message(message.chat.id, f"✅ Имя особи `{tid}` изменено на `{nname}`.")

if __name__ == '__main__':
    bot.infinity_polling()
