import telebot
from telebot import types
import uuid
import os
import random

# Укажи здесь токен своего бота
TOKEN = "ТВОЙ_ТОКЕН_БОТА"
bot = telebot.TeleBot(TOKEN)

# ==================== БАЗА ДАННЫХ ИГРОКОВ И РЫНКА (В ОЗУ) ====================
# Структура игрока: {"balance": 500, "inventory": [...], "titles": [...], "spouse": ID/None, "username": str}
players = {}
market_lots = []
# Временное хранилище для селекции: {user_id: {"card1_id": str, "card2_id": str}}
breeding_sessions = {}

# ==================== ТАБЛИЦА ВСЕХ КАРТ ====================
REAL_CARDS = [
    {"file": "0.jpg", "name": "карта moon 🌙", "rarity": "🔮 Секретная", "price": 100},
    {"file": "1.jpg", "name": "金 sunny🌲 김지ха | DA 🐂", "rarity": "🔮 Секретная", "price": 100},
    {"file": "5.jpg", "name": "Солнечный Самурай ☀️", "rarity": "⭐ Обычная", "price": 10},
    {"file": "4.jpg", "name": "Меха-Бык 🐂", "rarity": "⭐ Редкая", "price": 30},
    {"file": "2.jpg", "name": "👻losnya🐂🌲", "rarity": "🔮 Секретная", "price": 100},
    {"file": "7.jpg", "name": "Призрак Леса 👻", "rarity": "⭐ Редкая", "price": 30},
    {"file": "6.jpg", "name": "Таинственный Лось 🦌", "rarity": "⭐ Обычная", "price": 10},
    {"file": "3.jpg", "name": "Дониёр 🌲", "rarity": "🔮 Секретная", "price": 100},
    {"file": "9.jpg", "name": "Страж Дубравы 🌲", "rarity": "⭐ Обычная", "price": 10},
    {"file": "8.jpg", "name": "Лесной Хакер 💻", "rarity": "⭐ Редкая", "price": 30}
]

EMPTY_CARDS = [{"file": None, "name": "Эта карта пуста, открой ещё 😔", "rarity": "⚪ Пустышка", "price": 0}] * 50
CARDS = REAL_CARDS + EMPTY_CARDS

START_TITLES = ["🌲 Лесной Житель", "⚔️ Самурай", "🔮 Мистик"]

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def init_player(user_id, username="Игрок"):
    """Автоматически регистрирует пользователя, если его нет в базе данных"""
    if user_id not in players:
        players[user_id] = {
            "balance": 500,
            "inventory": [],
            "titles": list(START_TITLES),
            "spouse": None,
            "username": username
        }
    else:
        # Обновляем юзернейм при активности
        players[user_id]["username"] = username

def get_card_by_id(user_id, card_id):
    for card in players[user_id]["inventory"]:
        if card["id"] == card_id:
            return card
    return None

def main_keyboard():
    """Красивая главная клавиатура"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🃏 Получить карту", "🎒 Инвентарь")
    markup.row("🏪 Рынок", "🧬 Селекция")
    markup.row("💍 ЗАГС / Брак", "💰 Баланс")
    return markup

# ==================== КОМАНДЫ И МЕНЮ ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    init_player(user_id, message.from_user.first_name)
    
    welcome_text = (
        f"🌲✨ **Добро пожаловать, {message.from_user.first_name}!** ✨🌲\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Вы попали в мистический мир коллекционных карт!\n\n"
        f"🪐 **Твои стартовые бонусы:**\n"
        f"💰 На баланс зачислено: `500` монет\n"
        f"👑 Разблокировано стартовых титулов: `{len(START_TITLES)}` шт.\n"
        f"🆔 Твой ID для брака: `{user_id}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f" Нажимай на кнопки меню ниже, чтобы испытать удачу, начать торговлю или провести селекцию!"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=main_keyboard())

@bot.message_handler(func=lambda msg: msg.text == "💰 Баланс")
def balance_cmd(message):
    user_id = message.from_user.id
    init_player(user_id, message.from_user.first_name)
    bot.send_message(message.chat.id, f"💵 **Твой текущий баланс:** `{players[user_id]['balance']}` монет.", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🃏 Получить карту")
def get_card_cmd(message):
    user_id = message.from_user.id
    init_player(user_id, message.from_user.first_name)
    
    chosen = random.choice(CARDS)
    
    if chosen["file"] is None:
        bot.send_message(message.chat.id, f"💨 {chosen['name']}")
    else:
        player_card = {
            "id": str(uuid.uuid4())[:8],
            "file": chosen["file"],
            "name": chosen["name"],
            "rarity": chosen["rarity"],
            "price": chosen["price"],
            "locked": False,
            "on_sale": False
        }
        players[user_id]["inventory"].append(player_card)
        
        status_text = (
            f"🎉 **Тебе выпала новая карта!**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"ℹ️ **Название:** {player_card['name']}\n"
            f"💎 **Редкость:** {player_card['rarity']}\n"
            f"💰 **Ценность:** `{player_card['price']}` монет\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f" Маркер безопасности: `[Разблокирована]`"
        )
        
        if os.path.exists(player_card["file"]):
            with open(player_card["file"], 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=status_text, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, status_text + "\n\n⚠️ *(Изображение карты временно отсутствует на сервере)*", parse_mode="Markdown")

# ==================== МОДУЛЬ ИНВЕНТАРЯ И БЛОКИРОВКИ ====================
@bot.message_handler(func=lambda msg: msg.text == "🎒 Инвентарь")
def inventory_cmd(message):
    user_id = message.from_user.id
    init_player(user_id, message.from_user.first_name)
    
    cards = players[user_id]["inventory"]
    visible_cards = [c for c in cards if not c.get("on_sale")]
    
    if not visible_cards:
        bot.send_message(message.chat.id, "🎒 **Твой инвентарь пуст.** Получи карты в меню или дождись завершения сделок на рынке!", parse_mode="Markdown")
        return
        
    bot.send_message(message.chat.id, "📋 **Твой личный инвентарь:\nУправляй замками для защиты от случайной продажи.")
    
    for card in visible_cards:
        lock_status = "🔒 [ЗАБЛОКИРОВАНА]" if card["locked"] else "🔓 [Свободна]"
        text = f"🃏 \n┗ Редкость: {card['rarity']} | Состояние: {lock_status} | Ценность: {card['price']} 💰"
        
        markup = types.InlineKeyboardMarkup()
        btn_lock = types.InlineKeyboardButton(
            text="🔓 Заблокировать" if not card["locked"] else "🔒 Разблокировать", 
            callback_data=f"inv_lock_{card['id']}"
        )
        btn_sell_sys = types.InlineKeyboardButton(
            text="💵 Продать системе", 
            callback_data=f"inv_sys_sell_{card['id']}"
        )
        markup.add(btn_lock, btn_sell_sys)
        
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("inv_"))
def inventory_callback(call):
    user_id = call.from_user.id
    init_player(user_id, call.from_user.first_name)
    
    action = call.data.split("_")[1]
    card_id = call.data.split("_")[2] if len(call.data.split("_")) > 2 else call.data.split("_")[-1]
    
    card = get_card_by_id(user_id, card_id)
    if not card:
        bot.answer_callback_query(call.id, "❌ Карта не найдена в текущей сессии!")
        return

    if action == "lock":
        card["locked"] = not card["locked"]
        lock_str = "заблокирована 🔒" if card["locked"] else "разблокирована 🔓"
        bot.answer_callback_query(call.id, f"Карта {lock_str}!")
        
        markup = types.InlineKeyboardMarkup()
        btn_lock = types.InlineKeyboardButton(
            text="🔓 Заблокировать" if not card["locked"] else "🔒 Разблокировать", 
            callback_data=f"inv_lock_{card['id']}"
        )
        btn_sell_sys = types.InlineKeyboardButton(
            text="💵 Продать системе", 
            callback_data=f"inv_sys_sell_{card['id']}"
        )
        markup.add(btn_lock, btn_sell_sys)
        
        lock_status = "🔒 [ЗАБЛОКИРОВАНА]" if card["locked"] else "🔓 [Свободна]"
        text = f"🃏 **\n┗ Редкость: {card['rarity']} | Состояние: {lock_status} | Ценность: {card['price']} 💰"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            text=text, 
            parse_mode="Markdown",
            reply_markup=markup
        )

    elif action == "sys": 
        if card["locked"]:
            bot.answer_callback_query(call.id, "❌ Эта карта заблокирована! Снимите блокировку в инвентаре.", show_alert=True)
            return
        
        # Бонус за брак: в браке система покупает на 10% дороже
        final_payout = card["price"]
        if players[user_id].get("spouse"):
            final_payout = int(final_payout * 1.1)
            
        players[user_id]["balance"] += final_payout
        players[user_id]["inventory"].remove(card)
        bot.answer_callback_query(call.id, f"Вы успешно продали карту за {final_payout} монет! (С учетом бонусов)")
        bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== МОДУЛЬ СЕЛЕКЦИИ (СКРЕЩИВАНИЯ КАРТ) ====================
@bot.message_handler(func=lambda msg: msg.text == "🧬 Селекция")
def breed_main(message):
    user_id = message.from_user.id
    init_player(user_id, message.from_user.first_name)
    
    # Очищаем старые сессии селекции
    breeding_sessions[user_id] = {"card1_id": None, "card2_id": None}
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🧬 Начать скрещивание (50 💰)", callback_data="breed_start"))
    
    info_text = (
        "🧬 **Лаборатория Селекции карт** 🧬\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Здесь вы можете скрестить две любые разблокированные карты, чтобы вывести абсолютно новый экземпляр!\n\n"
        "⚠️ **Правила генетики:**\n"
        "• Стоимость процедуры: `50` монет.\n"
        "• Исходные карты уничтожаются.\n"
        "• Новая карта унаследует имя случайной карты из пула, но её **базовая ценность будет равна сумме стоимостей родителей** + бонус мутации (до +50 монет)!"
    )
    bot.send_message(message.chat.id, info_text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("breed_"))
def breed_callback(call):
    user_id = call.from_user.id
    init_player(user_id, call.from_user.first_name)
    action = call.data.replace("breed_", "")
    
    if user_id not in breeding_sessions:
        breeding_sessions[user_id] = {"card1_id": None, "card2_id": None}

    if action == "start":
        if players[user_id]["balance"] < 50:
            bot.answer_callback_query(call.id, "❌ Недостаточно монет для проведения селекции! Нужно 50 💰", show_alert=True)
            return
            
        # Показываем карты для первого родителя
        cards = [c for c in players[user_id]["inventory"] if not c.get("locked") and not c.get("on_sale")]
        if len(cards) < 2:
            bot.answer_callback_query(call.id, "❌ У вас должно быть как минимум 2 свободных карты в инвентаре для скрещивания!", show_alert=True)
            return
            
        markup = types.InlineKeyboardMarkup()
        for card in cards:
            markup.add(types.InlineKeyboardButton(f"🧬 {card['name']} ({card['price']} 💰)", callback_data=f"breed_set1_{card['id']}"))
            
        bot.edit_message_text("🧬 Выберите **первую карту (Родитель №1)**:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action.startswith("set1_"):
        card1_id = action.replace("set1_", "")
        breeding_sessions[user_id]["card1_id"] = card1_id
        
        # Показываем карты для второго родителя (исключая первую выбранную карту)
        cards = [c for c in players[user_id]["inventory"] if not c.get("locked") and not c.get("on_sale") and c["id"] != card1_id]
        
        markup = types.InlineKeyboardMarkup()
        for card in cards:
            markup.add(types.InlineKeyboardButton(f"🧬 {card['name']} ({card['price']} 💰)", callback_data=f"breed_set2_{card['id']}"))
            
        bot.edit_message_text("🧬 Отлично. Теперь выберите **вторую карту (Родитель №2)**:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action.startswith("set2_"):
        card2_id = action.replace("set2_", "")
        card1_id = breeding_sessions[user_id]["card1_id"]
        
        card1 = get_card_by_id(user_id, card1_id)
        card2 = get_card_by_id(user_id, card2_id)
        
        if not card1 or not card2:
            bot.answer_callback_query(call.id, "❌ Ошибка селекции! Карты не найдены.", show_alert=True)
            return
            
        # Проводим операцию
        players[user_id]["balance"] -= 50
        
        # Считаем параметры новой карты
        new_price = card1["price"] + card2["price"] + random.randint(10, 50) # Мутация цены
        base_template = random.choice(REAL_CARDS) # Берем случайный внешний вид и имя из пула реальных карт
        
        new_card = {
            "id": str(uuid.uuid4())[:8],
            "file": base_template["file"],
            "name": f"🧬 {base_template['name']} (Гибрид)",
            "rarity": "🧬 Селекционная",
            "price": new_price,
            "locked": False,
            "on_sale": False
        }
        
        # Удаляем родителей, добавляем гибрид
        players[user_id]["inventory"].remove(card1)
        players[user_id]["inventory"].remove(card2)
        players[user_id]["inventory"].append(new_card)
        
        # Сброс сессии
        breeding_sessions[user_id] = {"card1_id": None, "card2_id": None}
        
        result_text = (
            f"🧬 **Успешный генетический эксперимент!** 🧬\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Вы скрестили:\n"
            f"1️⃣ {card1['name']}\n"
            f"2️⃣ {card2['name']}\n\n"
            f"🎉 **Результат селекции:**\n"
            f"ℹ️ **Название:** {new_card['name']}\n"
            f"💎 **Редкость:** {new_card['rarity']}\n"
            f"💰 **Итоговая ценность гибрида:** `{new_card['price']}` монет!"
        )
        
        bot.edit_message_text(result_text, call.message.chat.id, call.message.message_id)

# ==================== МОДУЛЬ ЗАГСА И БРАКОВ ====================
@bot.message_handler(func=lambda msg: msg.text == "💍 ЗАГС / Брак")
def marriage_menu(message):
    user_id = message.from_user.id
    init_player(user_id, message.from_user.first_name)
    
    spouse_id = players[user_id].get("spouse")
    
    if spouse_id:
        spouse_name = players.get(spouse_id, {}).get("username", "Неизвестный партнер")
        status_text = (
            f"❤️ **Ты состоишь в официальном браке!** ❤️\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👩‍❤️‍👨 Твоя половинка: **{spouse_name}** (ID: `{spouse_id}`)\n"
            f"💍 Брак дает вам пассивный бонус **+10%** к стоимости продажи карт системе!\n\n"
            f"Если чувства угасли, вы можете подать на развод написав команду: /divorce"
        )
    else:
        status_text = (
            f"🏛 **Добро пожаловать в ЗАГС игрового мира!** 🏛\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Вы сейчас одиноки. Брак дает обоим партнерам ценный экономический буст в размере +10% к золоту за сдачу карт системе!\n\n"
            f"🆔 Твой личный ID для ЗАГСа: `{user_id}` (Передай его своей половинке)\n\n"
            f"👉 Чтобы сделать предложение руки и сердца, отправь команду:\n `/marry ID_ПОЛЬЗОВАТЕЛЯ`"
        )
        
    bot.send_message(message.chat.id, status_text, parse_mode="Markdown")

@bot.message_handler(commands=['marry'])
def marry_proposal(message):
    user_id = message.from_user.id
    init_player(user_id, message.from_user.first_name)
    
    if players[user_id].get("spouse"):
        bot.send_message(message.chat.id, "❌ Вы уже состоите в браке! Сначала разведитесь с помощью /divorce.")
        return
        
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(message.chat.id, "⚠️ Укажи ID игрока, которому хочешь сделать предложение. Пример: `/marry 12345678`", parse_mode="Markdown")
        return
        
    try:
        target_id = int(args[1])
    except ValueError:
        bot.send_message(message.chat.id, "❌ Некорректный формат ID!")
        return
        
    if target_id == user_id:
        bot.send_message(message.chat.id, "❌ Нельзя жениться на самом себе!")
        return
        
    if target_id not in players:
        bot.send_message(message.chat.id, "❌ Этот пользователь еще ни разу не играл в бота или не зарегистрирован!")
        return
        
    if players[target_id].get("spouse"):
        bot.send_message(message.chat.id, "❌ Этот игрок уже состоит в браке с кем-то другим!")
        return

    # Создаем предложение кнопками
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("❤️ Да, я согласен(а)!", callback_data=f"wedding_accept_{user_id}"),
        types.InlineKeyboardButton("💔 Отказать", callback_data=f"wedding_decline_{user_id}")
    )
    
    try:
        bot.send_message(
            target_id, 
            f"💍 Игрок **{players[user_id]['username']}** (ID: `{user_id}`) делает тебе предложение руки и сердца! Ты принимаешь его?", 
            parse_mode="Markdown", 
            reply_markup=markup
        )
        bot.send_message(message.chat.id, f"💌 Предложение успешно отправлено игроку под ID `{target_id}`. Ждем ответа...", parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, "❌ Бот не может написать этому пользователю в ЛС. Пусть он сначала нажмет /start.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("wedding_"))
def wedding_callback(call):
    my_id = call.from_user.id
    init_player(my_id, call.from_user.first_name)
    
    parts = call.data.split("_")
    action = parts[1]
    proposer_id = int(parts[2])
    
    if action == "accept":
        if players[my_id].get("spouse") or players[proposer_id].get("spouse"):
            bot.edit_message_text("❌ Один из участников уже успел вступить в брак!", call.message.chat.id, call.message.message_id)
            return
            
        # Заключаем брак
        players[my_id]["spouse"] = proposer_id
        players[proposer_id]["spouse"] = my_id
        
        bot.edit_message_text(f"🎉 Поздравляем! Вы официально заключили брак с игроком **{players[proposer_id]['username']}**!", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        try:
            bot.send_message(proposer_id, f"🔔 ❤️ Твое предложение принято! Вы с **{players[my_id]['username']}** теперь официально в браке!", parse_mode="Markdown")
        except Exception: pass
        
    elif action == "decline":
        bot.edit_message_text("💔 Вы отклонили предложение руки и сердца.", call.message.chat.id, call.message.message_id)
        try:
            bot.send_message(proposer_id, f"🔔 Игрок **{players[my_id]['username']}** отклонил ваше предложение брака...", parse_mode="Markdown")
        except Exception: pass

@bot.message_handler(commands=['divorce'])
def divorce_cmd(message):
    user_id = message.from_user.id
    init_player(user_id, message.from_user.first_name)
    
    spouse_id = players[user_id].get("spouse")
    if not spouse_id:
        bot.send_message(message.chat.id, "❌ Ты и так не состоишь в браке.")
        return
        
    # Разводим
    players[user_id]["spouse"] = None
    if spouse_id in players:
        players[spouse_id]["spouse"] = None
        try:
            bot.send_message(spouse_id, "💔 Твой партнер расторг брак с тобой в одностороннем порядке. Теперь вы свободны.")
        except Exception: pass
        
    bot.send_message(message.chat.id, "💔 Вы официально оформили развод. Бонус к продажам аннулирован.")


# ==================== МОДУЛЬ ТОРГОВОЙ ПЛОЩАДКИ (РЫНОК) ====================
@bot.message_handler(func=lambda msg: msg.text == "🏪 Рынок")
def market_main_menu(message):
    init_player(message.from_user.id, message.from_user.first_name)
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("➕ Выставить товар", callback_data="market_sell_menu"),
        types.InlineKeyboardButton("🛒 Купить товар", callback_data="market_buy_menu")
    )
    bot.send_message(message.chat.id, "🏪 **Торговая Площадка (P2P)**\nЗдесь вы можете безопасно продавать или покупать предметы у других игроков.", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("market_"))
def market_callback(call):
    user_id = call.from_user.id
    init_player(user_id, call.from_user.first_name)
    action = call.data.replace("market_", "")
    
    if action == "sell_menu":
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("🃏 Выставить Карту", callback_data="market_choose_card"),
            types.InlineKeyboardButton("👑 Выставить Титул", callback_data="market_choose_title")
        )
        markup.row(types.InlineKeyboardButton("🔙 Назад", callback_data="market_back_main"))
        bot.edit_message_text("Какую категорию имущества вы хотите выставить на продажу?", call.message.chat.id, call.message.message_id, reply_markup=markup)
        
    elif action == "back_main":
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("➕ Выставить товар", callback_data="market_sell_menu"),
            types.InlineKeyboardButton("🛒 Купить товар", callback_data="market_buy_menu")
        )
        bot.edit_message_text("🏪 **Торговая Площадка (P2P)**\nЗдесь вы можете безопасно продавать или покупать предметы у других игроков.", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    elif action == "choose_card":
        cards = [c for c in players[user_id]["inventory"] if not c.get("locked") and not c.get("on_sale")]
        if not cards:
            bot.answer_callback_query(call.id, "❌ У вас нет доступных разблокированных карт для продажи!", show_alert=True)
            return
        
        markup = types.InlineKeyboardMarkup()
        for card in cards:
            markup.add(types.InlineKeyboardButton(f"{card['name']} (Номинал: {card['price']})", callback_data=f"market_pre_card_{card['id']}"))
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="market_sell_menu"))
        bot.edit_message_text("Выберите карту для отправки на витрину рынка:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action.startswith("pre_card_"):
        card_id = action.replace("pre_card_", "")
        card = get_card_by_id(user_id, card_id)
        if not card: return
        
        markup = types.InlineKeyboardMarkup()
        rec_p = card["price"]
        markup.row(
            types.InlineKeyboardButton(f"{int(rec_p*0.8)} 💰", callback_data=f"market_confirm_card_{card_id}_{int(rec_p*0.8)}"),
            types.InlineKeyboardButton(f"{rec_p} 💰", callback_data=f"market_confirm_card_{card_id}_{rec_p}")
        )
        markup.row(
            types.InlineKeyboardButton(f"{int(rec_p*1.5)} 💰", callback_data=f"market_confirm_card_{card_id}_{int(rec_p*1.5)}"),
            types.InlineKeyboardButton(f"{rec_p*2} 💰", callback_data=f"market_confirm_card_{card_id}_{rec_p*2}")
        )
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="market_sell_menu"))
        bot.edit_message_text(f"Укажите рыночную стоимость для карты *{card['name']}*:", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    elif action.startswith("confirm_card_"):
        parts = action.replace("confirm_card_", "").split("_")
        card_id = parts[0]
        final_price = int(parts[1])
        
        card = get_card_by_id(user_id, card_id)
        if not card or card["locked"] or card["on_sale"]: return
        
        card["on_sale"] = True
        lot_id = str(uuid.uuid4())[:8]
        
        market_lots.append({
            "lot_id": lot_id,
            "seller_id": user_id,
            "item_type": "card",
            "item_data": card,
            "price": final_price
        })
        bot.answer_callback_query(call.id, "🎉 Товар успешно опубликован на рынке!", show_alert=True)
        market_main_menu(call.message)

    elif action == "choose_title":
        titles = players[user_id]["titles"]
        if not titles:
            bot.answer_callback_query(call.id, "❌ У вас нет свободных титулов на продажу!", show_alert=True)
            return
        
        markup = types.InlineKeyboardMarkup()
        for title in titles:
            markup.add(types.InlineKeyboardButton(f"{title}", callback_data=f"market_pre_title_{title}"))
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="market_sell_menu"))
        bot.edit_message_text("Выберите титул для продажи:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action.startswith("pre_title_"):
        title_name = action.replace("pre_title_", "")
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("50 💰", callback_data=f"market_confirm_title_{title_name}_50"),
            types.InlineKeyboardButton("150 💰", callback_data=f"market_confirm_title_{title_name}_150"),
            types.InlineKeyboardButton("500 💰", callback_data=f"market_confirm_title_{title_name}_500")
        )
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="market_sell_menu"))
        bot.edit_message_text(f"Укажите стоимость для титула '{title_name}':", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action.startswith("confirm_title_"):
        parts = action.replace("confirm_title_", "").split("_")
        title_name = parts[0]
        final_price = int(parts[1])
        
        if title_name not in players[user_id]["titles"]: return
        
        players[user_id]["titles"].remove(title_name)
        lot_id = str(uuid.uuid4())[:8]
        
        market_lots.append({
            "lot_id": lot_id,
            "seller_id": user_id,
            "item_type": "title",
            "item_data": {"name": title_name},
            "price": final_price
        })
        bot.answer_callback_query(call.id, "🎉 Титул выставлен на продажу!", show_alert=True)
        market_main_menu(call.message)

    elif action == "buy_menu":
        available_lots = [lot for lot in market_lots if lot["seller_id"] != user_id]
        
        if not available_lots:
            bot.answer_callback_query(call.id, "🛒 Активных чужих предложений на рынке сейчас нет.", show_alert=True)
            return
            
        markup = types.InlineKeyboardMarkup()
        for lot in available_lots:
            if lot["item_type"] == "card":
                display_name = f"🃏 Карта: {lot['item_data']['name']} | 💵 {lot['price']}"
            else:
                display_name = f"👑 Титул: {lot['item_data']['name']} | 💵 {lot['price']}"
                
            markup.add(types.InlineKeyboardButton(display_name, callback_data=f"market_purchase_{lot['lot_id']}"))
            
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="market_back_main"))
        bot.edit_message_text("🛒 **Глобальный список лотов:**\nНажмите на любой товар, чтобы совершить покупку.", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    elif action.startswith("purchase_"):
        lot_id = action.replace("purchase_", "")
        
        target_lot = None
        for lot in market_lots:
            if lot["lot_id"] == lot_id:
                target_lot = lot
                break
                
        if not target_lot:
            bot.answer_callback_query(call.id, "❌ Данный лот уже выкуплен или удален продавцом!", show_alert=True)
            return
            
        seller_id = target_lot["seller_id"]
        price = target_lot["price"]
        
        if players[user_id]["balance"] < price:
            bot.answer_callback_query(call.id, f"❌ Недостаточно монет на балансе! Требуется: {price}", show_alert=True)
            return
            
        # Проведение транзакции
        players[user_id]["balance"] -= price
        init_player(seller_id, "Игрок")
        players[seller_id]["balance"] += price
        
        if target_lot["item_type"] == "card":
            card_data = target_lot["item_data"]
            card_data["on_sale"] = False
            
            original_card = get_card_by_id(seller_id, card_data["id"])
            if original_card:
                players[seller_id]["inventory"].remove(original_card)
                
            card_data["id"] = str(uuid.uuid4())[:8]
            players[user_id]["inventory"].append(card_data)
            
            try:
                bot.send_message(seller_id, f"🏪 Твой товар '{card_data['name']}' успешно куплен игроком! На счет зачислено: +`{price}` монет.", parse_mode="Markdown")
            except Exception: pass
            bot.answer_callback_query(call.id, f"🎉 Поздравляем! Карта '{card_data['name']}' перенесена в ваш инвентарь.", show_alert=True)
            
        elif target_lot["item_type"] == "title":
            title_name = target_lot["item_data"]["name"]
            players[user_id]["titles"].append(title_name)
            
            try:
                bot.send_message(seller_id, f"🏪 Твой титул '{title_name}' успешно выкуплен! На счет зачислено: +`{price}` монет.", parse_mode="Markdown")
            except Exception: pass
            bot.answer_callback_query(call.id, f"🎉 Вы успешно приобрели титул '{title_name}'!", show_alert=True)

        market_lots.remove(target_lot)
        market_main_menu(call.message)

# ==================== ЗАЩИТНЫЙ ОБРАБОТЧИК ДЛЯ НЕИЗВЕСТНОГО ТЕКСТА ====================
@bot.message_handler(func=lambda message: True)
def unknown_and_unregistered_messages(message):
    user_id = message.from_user.id
    
    if user_id not in players:
        init_player(user_id, message.from_user.first_name)
        alert_msg = (
            f"⚠️ **Внимание!** Похоже, вы не запустили игру должным образом.\n"
            f"Пожалуйста, нажмите на команду -> /start для полной инициализации профиля и получения стартовых 500 монет! 🎁"
        )
        bot.send_message(message.chat.id, alert_msg, parse_mode="Markdown", reply_markup=main_keyboard())
    else:
        bot.send_message(
            message.chat.id, 
            "❓ Я не понимаю этот текст. Пожалуйста, используйте встроенные кнопки меню или выполните команду /start для перезапуска.",
            reply_markup=main_keyboard()
        )

if __name__ == '__main__':
    print("Бот успешно запущен со всеми доработками, ЗАГСом и селекцией!")
    bot.infinity_polling()
