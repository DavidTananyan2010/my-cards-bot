import telebot
from telebot import types
import uuid
import random

TOKEN = "8701989939:AAG2z5cJ-kSkTe1k3OizAeTKHFc-OJ97Bfg"
bot = telebot.TeleBot(TOKEN)

# 👑 ID Главного Администратора (Королевы улья)
ADMIN_ID = 7501899378

# ==================== БАЗА ДАННЫХ И СИСТЕМНЫЕ ПЕРЕМЕННЫЕ ====================
players = {}
market_lots = {}           # Рынок: {lot_id: {"seller_id": uid, "card": card, "price": price}}
breeding_sessions = {}
FROZEN_USERS = set()       
BANNED_USERS = set()       
USER_WARNS = {}            
LOCKED_INVENTORIES = set() 

# Настройки экономики
DROP_EMPTY_CHANCE = 30     
PACK_PRICE = 50            
RARE_PACK_PRICE = 150      
ECONOMY_BOOST = 1.0        

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
        players[uid] = {
            "balance": 500, 
            "inventory": [], 
            "titles": ["🐜 Начинающий Энтомолог"], 
            "spouse": None, 
            "username": name
        }
    # Защита на случай, если имя сменилось в ТГ
    if players[uid]["username"] == "Особь" and name != "Особь":
        players[uid]["username"] = name

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📦 Открыть пак", "👤 Профиль | 🏆 Топ")
    markup.row("📁 Коллекция", "🚀 Прокачка & Крафт")
    markup.row("🛍️ Магазин", "🏪 Рынок Улья")
    markup.row("🎲 ЗАГС & Квесты", "🎁 Бонусы & Донат")
    return markup

# ==================== ОБЫЧНОЕ ИГРОВОЕ МЕНЮ ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    if not check_access(message): return
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    
    msg_text = f"🐜 **Добро пожаловать в Улей!**\nВаш ID: `{uid}`"
    if uid == ADMIN_ID:
        msg_text += "\n\n👑 **Приветствуем, Королева улья!** Вам доступна скрытая команда чата `/admin_panel`"
        
    bot.send_message(message.chat.id, msg_text, parse_mode="Markdown", reply_markup=main_keyboard())

@bot.message_handler(func=lambda msg: msg.text == "👤 Профиль | 🏆 Топ")
def profile_cmd(message):
    if not check_access(message): return
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    p = players[uid]
    spouse = players[p["spouse"]]["username"] if p.get("spouse") and p["spouse"] in players else "Нет"
    
    bot.send_message(
        message.chat.id, 
        f"👤 **Профиль {p['username']}:**\n\n"
        f"💰 **Баланс биомассы:** `{p['balance']}` монет\n"
        f"👑 **Титулы:** {', '.join(p['titles'])}\n"
        f"❤️ **Союз:** {spouse}\n"
        f"🎒 **Карт в коллекции: {len(p['inventory'])} шт.", 
        parse_mode="Markdown"
    )

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
        bot.send_message(message.chat.id, f"🥚 Из кокона вылупилась особь: ** ({card['rarity']})", parse_mode="Markdown")

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
        markup.row(
            types.InlineKeyboardButton("♻️ Сдать в улей", callback_data=f"sell_{c['id']}"),
            types.InlineKeyboardButton("🏪 На Рынок", callback_data=f"mkt_pre_{c['id']}")
        )
        bot.send_message(message.chat.id, f"🐜 *{c['name']}* | Ценность: {c['price']} 💰\nID: `{c['id']}`", parse_mode="Markdown", reply_markup=markup)

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
        if players[uid].get("spouse"): payout = int(payout * 1.1) # Бонус за брак +10%
        players[uid]["balance"] += payout
        players[uid]["inventory"].remove(card)
        bot.answer_callback_query(call.id, f"Сдано за {payout} монет!")
        bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== СИСТЕМА СЕЛЕКЦИИ (СКРЕЩИВАНИЕ) ====================
@bot.message_handler(func=lambda msg: msg.text == "🚀 Прокачка & Крафт")
def craft_menu(message):
    if not check_access(message): return
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    
    breeding_sessions[uid] = {"card1_id": None, "card2_id": None}
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🧬 Начать селекцию особей (50 💰)", callback_data="breed_start"))
    
    bot.send_message(
        message.chat.id, 
        "🧬 **Лаборатория скрещивания особей**\n\nОбъедините гены двух насекомых, чтобы получить улучшенного селекционного мутанта.\n"
        "Ценность мутанта равна стоимости обоих родителей + бонус мутации!", 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("breed_"))
def breed_callback(call):
    uid = call.from_user.id
    action = call.data.replace("breed_", "")
    
    if action == "start":
        if players[uid]["balance"] < 50:
            bot.answer_callback_query(call.id, "❌ Недостаточно биомассы (нужно 50 💰)", show_alert=True)
            return
        cards = players[uid]["inventory"]
        if len(cards) < 2:
            bot.answer_callback_query(call.id, "❌ У вас должно быть минимум 2 особи в коллекции!", show_alert=True)
            return
        markup = types.InlineKeyboardMarkup()
        for c in cards:
            markup.add(types.InlineKeyboardButton(f"🐜 {c['name']} ({c['price']} 💰)", callback_data=f"breed_set1_{c['id']}"))
        bot.edit_message_text("🧬 Выберите **первую** родительскую особь:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action.startswith("set1_"):
        c1 = action.replace("set1_", "")
        breeding_sessions[uid]["card1_id"] = c1
        cards = [c for c in players[uid]["inventory"] if c["id"] != c1]
        markup = types.InlineKeyboardMarkup()
        for c in cards:
            markup.add(types.InlineKeyboardButton(f"🐝 {c['name']} ({c['price']} 💰)", callback_data=f"breed_set2_{c['id']}"))
        bot.edit_message_text("🧬 Выберите **вторую** родительскую особь для скрещивания:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action.startswith("set2_"):
        c2 = action.replace("set2_", "")
        c1 = breeding_sessions[uid]["card1_id"]
        
        card1 = next((c for c in players[uid]["inventory"] if c["id"] == c1), None)
        card2 = next((c for c in players[uid]["inventory"] if c["id"] == c2), None)
        if not card1 or not card2: return
            
        players[uid]["balance"] -= 50
        new_price = card1["price"] + card2["price"] + random.randint(15, 50)
        template = random.choice(REAL_CARDS)
        
        hybrid = {"id": str(uuid.uuid4())[:8], "name": f"🧬 {template['name']} (Мутант)", "rarity": "🧬 Селекционный Вид", "price": new_price}
        players[uid]["inventory"].remove(card1)
        players[uid]["inventory"].remove(card2)
        players[uid]["inventory"].append(hybrid)
        
        bot.edit_message_text(f"🎉 **Скрещивание успешно!**\nВывели новый вид: *{hybrid['name']}*\n💰 Ценность новой особи: `{hybrid['price']}` монет!", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# ==================== СИСТЕМА РЫНКА УЛЬЯ (P2P МАРКЕТ) ====================
@bot.message_handler(func=lambda msg: msg.text == "🏪 Рынок Улья")
def market_menu(message):
    if not check_access(message): return
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    
    if not market_lots:
        bot.send_message(message.chat.id, "🏪 **Рынок Улья**\n\nСейчас никто ничего не продает. Вы можете выставить карту на продажу через меню `📁 Коллекция`.")
        return
        
    bot.send_message(message.chat.id, "🏪 **Актуальные лоты на Рынке Улья:**\nПокупайте редких особей у других игроков напрямую:")
    for lid, lot in list(market_lots.items()):
        seller = players.get(lot["seller_id"], {}).get("username", "Неизвестный")
        markup = types.InlineKeyboardMarkup()
        if lot["seller_id"] == uid:
            markup.add(types.InlineKeyboardButton("❌ Снять с продажи", callback_data=f"mkt_cancel_{lid}"))
        else:
            markup.add(types.InlineKeyboardButton(f"💳 Купить за {lot['price']} 💰", callback_data=f"mkt_buy_{lid}"))
            
        bot.send_message(
            message.chat.id, 
            f"📦 **Лот: {lot['card']['name']}\n"
            f"💎 Редкость: {lot['card']['rarity']}\n"
            f"👤 Продавец: {seller}\n"
            f"💰 Цена сделки: `{lot['price']}` монет", 
            parse_mode="Markdown", reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("mkt_"))
def market_callback(call):
    uid = call.from_user.id
    init_player(uid, call.from_user.first_name)
    data = call.data.replace("mkt_", "")
    
    # Подготовка продажи (выставление цены через команду)
    if data.startswith("pre_"):
        cid = data.replace("pre_", "")
        card = next((c for c in players[uid]["inventory"] if c["id"] == cid), None)
        if not card: return
        bot.send_message(call.message.chat.id, f"💡 Чтобы установить цену и выставить ** на рынок, введите команду:\n`/sell_market {cid} [Цена]`")
        bot.answer_callback_query(call.id)
        
    # Покупка лота
    elif data.startswith("buy_"):
        lid = data.replace("buy_", "")
        lot = market_lots.get(lid)
        if not lot:
            bot.answer_callback_query(call.id, "❌ Лот уже продан или снят с рынка!", show_alert=True)
            return
        if players[uid]["balance"] < lot["price"]:
            bot.answer_callback_query(call.id, "❌ У вас недостаточно монет для покупки!", show_alert=True)
            return
            
        # Процесс сделки
        players[uid]["balance"] -= lot["price"]
        players[lot["seller_id"]]["balance"] += lot["price"]
        players[uid]["inventory"].append(lot["card"])
        
        # Уведомление продавцу
        try: bot.send_message(lot["seller_id"], f"💰 Вашу карту **{lot['card']['name']} купили на рынке за {lot['price']} монет!")
        except Exception: pass
        
        del market_lots[lid]
        bot.edit_message_text("🎉 Вы успешно приобрели особь с рынка улья!", call.message.chat.id, call.message.message_id)

    # Отмена лота
    elif data.startswith("cancel_"):
        lid = data.replace("cancel_", "")
        lot = market_lots.get(lid)
        if lot and lot["seller_id"] == uid:
            players[uid]["inventory"].append(lot["card"])
            del market_lots[lid]
            bot.edit_message_text("❌ Вы сняли особь с продажи. Карта вернулась в вашу коллекцию.", call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=['sell_market'])
def sell_market_cmd(message):
    if not check_access(message): return
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    args = message.text.split()
    if len(args) < 3:
        bot.send_message(message.chat.id, "⚠️ Использование: `/sell_market [ID_карты] [Цена]`")
        return
    cid, price = args[1], int(args[2])
    if price <= 0: return
    
    card = next((c for c in players[uid]["inventory"] if c["id"] == cid), None)
    if not card:
        bot.send_message(message.chat.id, "❌ Данная особь не найдена в вашей коллекции.")
        return
        
    lid = str(uuid.uuid4())[:6]
    market_lots[lid] = {"seller_id": uid, "card": card, "price": price}
    players[uid]["inventory"].remove(card)
    bot.send_message(message.chat.id, f"✅ Карта ** выставлена на общий рынок за `{price}` монет!")

# ==================== ИНТЕРАКТИВНЫЙ ЗАГС И КВЕСТЫ ====================
@bot.message_handler(func=lambda msg: msg.text == "🎲 ЗАГС & Квесты")
def quests_menu(message):
    if not check_access(message): return
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("💍 Заключить Союз", callback_data="mar_list"), types.InlineKeyboardButton("💔 Расторгнуть Союз", callback_data="mar_divorce"))
    
    bot.send_message(
        message.chat.id, 
        f"🎲 **Муравьиный ЗАГС и Отношения**\n\n"
        f"Семейный союз связывает феромоны двух игроков, давая постоянный бонус **+10% к стоимости сдачи карт** в улей!\n\n"
        f"Выберите действие на кнопках ниже:", 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("mar_"))
def marry_callback(call):
    uid = call.from_user.id
    init_player(uid, call.from_user.first_name)
    data = call.data.replace("mar_", "")
    
    if data == "list":
        if players[uid].get("spouse"):
            bot.answer_callback_query(call.id, "❌ Вы уже состоите в союзе!", show_alert=True)
            return
        # Список свободных особей
        free_players = [pid for pid, p in players.items() if pid != uid and not p.get("spouse")]
        if not free_players:
            bot.answer_callback_query(call.id, "🐜 В улье пока нет других свободных особей.", show_alert=True)
            return
        markup = types.InlineKeyboardMarkup()
        for pid in free_players[:8]:
            markup.add(types.InlineKeyboardButton(f"🐝 {players[pid]['username']}", callback_data=f"mar_req_{pid}"))
        bot.edit_message_text("💍 Выберите свободную особь для отправки предложения:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        
    elif data.startswith("req_"):
        target_id = int(data.replace("req_", ""))
        if players[uid].get("spouse") or players[target_id].get("spouse"): return
        
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("✅ Принять", callback_data=f"mar_accept_{uid}"), types.InlineKeyboardButton("❌ Отклонить", callback_data=f"mar_deny_{uid}"))
        try:
            bot.send_message(target_id, f"💍 Особь **{players[uid]['username']}** предлагает вам заключить брачный союз! Вы согласны?", reply_markup=markup)
            bot.edit_message_text("💌 Свадебные феромоны улетели к избраннику. Ожидайте ответа.", call.message.chat.id, call.message.message_id)
        except Exception:
            bot.answer_callback_query(call.id, "❌ Ошибка отправки запроса.", show_alert=True)

    elif data.startswith("accept_"):
        prop_id = int(data.replace("accept_", ""))
        players[uid]["spouse"] = prop_id
        players[prop_id]["spouse"] = uid
        bot.edit_message_text("❤️ Брачный союз успешно заключен! Бонус +10% к сдаче карт активирован.", call.message.chat.id, call.message.message_id)
        try: bot.send_message(prop_id, f"🎉 Особь **{players[uid]['username']}** приняла ваше предложение! Союз заключен.")
        except Exception: pass

    elif data == "divorce":
        spouse_id = players[uid].get("spouse")
        if not spouse_id:
            bot.answer_callback_query(call.id, "❌ Вы не состоите в союзе.", show_alert=True)
            return
        players[uid]["spouse"] = None
        if spouse_id in players: players[spouse_id]["spouse"] = None
        bot.edit_message_text("💔 Брачный союз расторгнут. Бонус сдачи аннулирован.", call.message.chat.id, call.message.message_id)
        try: bot.send_message(spouse_id, f"💔 Особь **{players[uid]['username']}** расторгла брачный союз с вами.")
        except Exception: pass
        
    elif data.startswith("deny_"):
        prop_id = int(data.replace("deny_", ""))
        bot.edit_message_text("❌ Предложение отклонено.", call.message.chat.id, call.message.message_id)
        try: bot.send_message(prop_id, f"💔 Особь отклонила ваше брачное предложение.")
        except Exception: pass

# ==================== ОСТАЛЬНЫЕ СИСТЕМНЫЕ КНОПКИ ====================
@bot.message_handler(func=lambda msg: msg.text == "🛍️ Магазин")
def store_menu(message):
    if not check_access(message): return
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(f"📦 Инкубатор ({PACK_PRICE} 💰)", callback_data="buy_pack"))
    markup.row(types.InlineKeyboardButton(f"💎 Элитный кокон ({RARE_PACK_PRICE} 💰)", callback_data="buy_rare"))
    markup.row(types.InlineKeyboardButton("👑 Купить Титул [⭐️ VIP] (300 💰)", callback_data="buy_title_vip"))
    bot.send_message(message.chat.id, "🛍️ **Добро пожаловать в Магазин улья!\nВыберите товар:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_callback(call):
    uid = call.from_user.id
    init_player(uid, call.from_user.first_name)
    goods = call.data.replace("buy_", "")
    
    if goods == "pack":
        if players[uid]["balance"] < PACK_PRICE:
            bot.answer_callback_query(call.id, "❌ Недостаточно монет!", show_alert=True)
            return
        players[uid]["balance"] -= PACK_PRICE
        chosen = random.choice(REAL_CARDS)
        card = {"id": str(uuid.uuid4())[:8], "name": chosen["name"], "rarity": chosen["rarity"], "price": chosen["price"]}
        players[uid]["inventory"].append(card)
        bot.send_message(message.chat.id, f"🛒 Куплен обычный пак! Вылупился: **")
    elif goods == "rare":
        if players[uid]["balance"] < RARE_PACK_PRICE:
            bot.answer_callback_query(call.id, "❌ Недостаточно монет!", show_alert=True)
            return
        players[uid]["balance"] -= RARE_PACK_PRICE
        rares = [c for c in REAL_CARDS if "Эпическая" in c["rarity"] or "Легендарная" in c["rarity"]]
        chosen = random.choice(rares)
        card = {"id": str(uuid.uuid4())[:8], "name": f"🔥 {chosen['name']}", "rarity": chosen["rarity"], "price": chosen["price"] * 2}
        players[uid]["inventory"].append(card)
        bot.send_message(message.chat.id, f"🛒 Вылупилась Элитная особь: **{card['name']}**")
    elif goods == "title_vip":
        if players[uid]["balance"] < 300:
            bot.answer_callback_query(call.id, "❌ Недостаточно монет!", show_alert=True)
            return
        if "⭐️ VIP" in players[uid]["titles"]:
            bot.answer_callback_query(call.id, "❌ У вас уже есть этот титул!", show_alert=True)
            return
        players[uid]["balance"] -= 300
        players[uid]["titles"].append("⭐️ VIP")
        bot.send_message(message.chat.id, "🎉 Вы успешно купили титул `[⭐️ VIP]`!")

@bot.message_handler(func=lambda msg: msg.text == "🎁 Бонусы & Донат")
def donate_menu(message):
    if not check_access(message): return
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    bot.send_message(
        message.chat.id, 
        f"🏦 **Центральный Муравьиный Банк**\n━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 Счет аккаунта: `{players[uid]['balance']}` монет биомассы.\n\n"
        f"🎭 **Кастомизация профиля:**\n"
        f"Смена вашего имени внутри улья:\n"
        f"👉 Напишите в чат: `/myname [Новое_Имя]`",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['myname'])
def change_my_name_cmd(message):
    if not check_access(message): return
    uid = message.from_user.id
    init_player(uid, message.from_user.first_name)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Использование: `/myname [Ваше новое имя]`")
        return
    players[uid]["username"] = parts[1]
    bot.send_message(message.chat.id, f"🎉 Кастомизация успешна! Теперь вас зовут: **{parts[1]}**", parse_mode="Markdown")

# ==================== АДМИН-ПАНЕЛЬ И СИСТЕМНЫЕ КОМАНДЫ ====================
@bot.message_handler(commands=['admin_panel'])
def admin_panel_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("⚙️ Настройки Системы", callback_data="p_sys"), types.InlineKeyboardButton("💰 Экономика", callback_data="p_eco"))
    markup.row(types.InlineKeyboardButton("📦 Карты & Сумки", callback_data="p_cards"), types.InlineKeyboardButton("⚖️ Модерация & Ник", callback_data="p_mod"))
    bot.send_message(message.chat.id, "🎛️ **КОРОЛЕВСКАЯ ПАНЕЛЬ**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("p_"))
def panel_callbacks(call):
    if call.from_user.id != ADMIN_ID: return
    cat = call.data
    bot.answer_callback_query(call.id)
    if cat == "p_sys":
        txt = f"⚙️ Шанс пустышки: `/set_drop [1-100]` ({DROP_EMPTY_CHANCE}%)"
    elif cat == "p_eco":
        txt = f"💰 Бонус всем: `/bonus_all [монеты]`, Буст экономики: `/economy_boost [X]`"
    elif cat == "p_cards":
        txt = f"📦 Выдать карту: `/give_card [ID] [Имя]`, Бан инвентаря: `/lock_user_inventory [ID]`"
    elif cat == "p_mod":
        txt = f"⚖️ Бан: `/ban [ID]`, Мут: `/mute [ID]`, Изменить имя: `/change_name [ID] [Имя]`"
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda msg: msg.text.startswith('/') and msg.from_user.id == ADMIN_ID)
def execute_admin_commands(message):
    parts = message.text.split(maxsplit=2)
    cmd = parts[0].replace('/', '')
    args = parts[1:]
    
    if cmd == "set_drop" and args:
        global DROP_EMPTY_CHANCE
        DROP_EMPTY_CHANCE = int(args[0])
        bot.send_message(message.chat.id, f"✅ Шанс пустышки: {DROP_EMPTY_CHANCE}%")
    elif cmd == "bonus_all" and args:
        for u in players.values(): u["balance"] += int(args[0])
        bot.send_message(message.chat.id, "✅ Начислен бонус улью!")
    elif cmd == "ban" and args:
        BANNED_USERS.add(int(args[0]))
        bot.send_message(message.chat.id, "🚫 Забанен.")

if __name__ == '__main__':
    bot.infinity_polling()
