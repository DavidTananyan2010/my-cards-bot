import telebot
from telebot import types
import uuid
import os

# Укажи здесь токен своего бота
TOKEN = "ТВОЙ_ТОКЕН_БОТА"
bot = telebot.TeleBot(TOKEN)

# ==================== БАЗА ДАННЫХ ИГРОКОВ И РЫНКА (В ОЗУ) ====================
players = {}
market_lots = []

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
def init_player(user_id):
    if user_id not in players:
        players[user_id] = {
            "balance": 500,
            "inventory": [],
            "titles": list(START_TITLES)
        }

def get_card_by_id(user_id, card_id):
    for card in players[user_id]["inventory"]:
        if card["id"] == card_id:
            return card
    return None

# ==================== КОМАНДЫ И МЕНЮ ====================
@bot.message_handler(commands=['start']) # ИСПРАВЛЕНО: убрана опечатка message_message_handler
def start_cmd(message):
    user_id = message.from_user.id
    init_player(user_id)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🃏 Получить карту", "🎒 Инвентарь")
    markup.row("🏪 Рынок", "💰 Баланс")
    
    bot.send_message(
        message.chat.id, 
        f"Привет, {message.from_user.first_name}! Добро пожаловать в карточную игру.\n"
        f"Используй меню для навигации. Тебе начислено 500 монет для тестов!", 
        reply_markup=markup
    )

@bot.message_handler(func=lambda msg: msg.text == "💰 Баланс")
def balance_cmd(message):
    user_id = message.from_user.id
    init_player(user_id)
    bot.send_message(message.chat.id, f"💵 Твой баланс: {players[user_id]['balance']} монет.")

@bot.message_handler(func=lambda msg: msg.text == "🃏 Получить карту")
def get_card_cmd(message):
    import random
    user_id = message.from_user.id
    init_player(user_id)
    
    chosen = random.choice(CARDS)
    
    if chosen["file"] is None:
        bot.send_message(message.chat.id, chosen["name"])
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
            f"🎉 Тебе выпала карта:\n"
            f"ℹ️ Название: {player_card['name']}\n"
            f"💎 Редкость: {player_card['rarity']}\n"
            f"💰 Стоимость: {player_card['price']} монет"
        )
        
        # Доработка: отправка реального фото, если файл существует в папке скрипта
        if os.path.exists(player_card["file"]):
            with open(player_card["file"], 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=status_text)
        else:
            bot.send_message(message.chat.id, status_text + "\n\n*(Картинка файла не найдена на сервере)*")

# ==================== МОДУЛЬ ИНВЕНТАРЯ И БЛОКИРОВКИ ====================
@bot.message_handler(func=lambda msg: msg.text == "🎒 Инвентарь")
def inventory_cmd(message):
    user_id = message.from_user.id
    init_player(user_id)
    
    cards = players[user_id]["inventory"]
    # Фильтруем те, что не на продаже
    visible_cards = [c for c in cards if not c.get("on_sale")]
    
    if not visible_cards:
        bot.send_message(message.chat.id, "🎒 Твой инвентарь пуст (или все карты выставлены на рынок).")
        return
        
    bot.send_message(message.chat.id, "📋 Твои карты (управляй блокировкой или продажей):")
    
    for card in visible_cards:
        lock_status = "🔒 [ЗАБЛОКИРОВАНА]" if card["locked"] else "🔓 [Свободна]"
        text = f"{card['name']} ({card['rarity']}) — {lock_status}"
        
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
        
        bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("inv_"))
def inventory_callback(call):
    user_id = call.from_user.id
    action = call.data.split("_")[1]
    card_id = call.data.split("_")[2] if len(call.data.split("_")) > 2 else call.data.split("_")[-1]
    
    card = get_card_by_id(user_id, card_id)
    if not card:
        bot.answer_callback_query(call.id, "Карта не найдена!")
        return

    if action == "lock":
        card["locked"] = not card["locked"]
        lock_str = "заблокирована" if card["locked"] else "разблокирована"
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
        bot.edit_message_text(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            text=f"{card['name']} ({card['rarity']}) — {lock_status}", 
            reply_markup=markup
        )

    elif action == "sys": 
        if card["locked"]:
            bot.answer_callback_query(call.id, "❌ Нельзя продать заблокированную карту!", show_alert=True)
            return
        
        players[user_id]["balance"] += card["price"]
        players[user_id]["inventory"].remove(card)
        bot.answer_callback_query(call.id, f"Вы успешно продали карту за {card['price']} монет!")
        bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== МОДУЛЬ ТОРГОВОЙ ПЛОЩАДКИ (РЫНОК) ====================
@bot.message_handler(func=lambda msg: msg.text == "🏪 Рынок")
def market_main_menu(message):
    init_player(message.from_user.id)
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("➕ Выставить товар", callback_data="market_sell_menu"),
        types.InlineKeyboardButton("🛒 Купить товар", callback_data="market_buy_menu")
    )
    bot.send_message(message.chat.id, "🏪 Торговая Площадка игроков!\nЧто вы хотите сделать?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("market_"))
def market_callback(call):
    user_id = call.from_user.id
    action = call.data.replace("market_", "")
    
    if action == "sell_menu":
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("🃏 Выставить Карту", callback_data="market_choose_card"),
            types.InlineKeyboardButton("👑 Выставить Титул", callback_data="market_choose_title")
        )
        markup.row(types.InlineKeyboardButton("🔙 Назад", callback_data="market_back_main"))
        bot.edit_message_text("Что именно вы хотите продать на рынке?", call.message.chat.id, call.message.message_id, reply_markup=markup)
        
    elif action == "back_main":
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("➕ Выставить товар", callback_data="market_sell_menu"),
            types.InlineKeyboardButton("🛒 Купить товар", callback_data="market_buy_menu")
        )
        bot.edit_message_text("🏪 Торговая Площадка игроков!\nЧто вы хотите сделать?", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action == "choose_card":
        cards = [c for c in players[user_id]["inventory"] if not c.get("locked") and not c.get("on_sale")]
        if not cards:
            bot.answer_callback_query(call.id, "У вас нет доступных разблокированных карт!", show_alert=True)
            return
        
        markup = types.InlineKeyboardMarkup()
        for card in cards:
            markup.add(types.InlineKeyboardButton(f"{card['name']} (Номинал: {card['price']})", callback_data=f"market_pre_card_{card['id']}"))
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="market_sell_menu"))
        bot.edit_message_text("Выберите карту из инвентаря:", call.message.chat.id, call.message.message_id, reply_markup=markup)

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
        bot.edit_message_text(f"Укажите цену для карты *{card['name']}*:", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

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
            "item_data": card, # Ссылка сохраняется
            "price": final_price
        })
        bot.answer_callback_query(call.id, "🎉 Карта выставлена на рынок!", show_alert=True)
        market_main_menu(call.message)

    elif action == "choose_title":
        titles = players[user_id]["titles"]
        if not titles:
            bot.answer_callback_query(call.id, "У вас нет титулов на продажу!", show_alert=True)
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
            bot.answer_callback_query(call.id, "🛒 На рынке сейчас нет чужих товаров.", show_alert=True)
            return
            
        markup = types.InlineKeyboardMarkup()
        for lot in available_lots:
            if lot["item_type"] == "card":
                display_name = f"🃏 Карта: {lot['item_data']['name']} | 💵 {lot['price']}"
            else:
                display_name = f"👑 Титул: {lot['item_data']['name']} | 💵 {lot['price']}"
                
            markup.add(types.InlineKeyboardButton(display_name, callback_data=f"market_purchase_{lot['lot_id']}"))
            
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="market_back_main"))
        bot.edit_message_text("🛒 Доступные товары на рынке:\nНажмите на товар, чтобы купить его.", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action.startswith("purchase_"):
        lot_id = action.replace("purchase_", "")
        
        target_lot = None
        for lot in market_lots:
            if lot["lot_id"] == lot_id:
                target_lot = lot
                break
                
        if not target_lot:
            bot.answer_callback_query(call.id, "Лот уже продан или снят с продажи!", show_alert=True)
            return
            
        seller_id = target_lot["seller_id"]
        price = target_lot["price"]
        
        if players[user_id]["balance"] < price:
            bot.answer_callback_query(call.id, f"❌ Недостаточно монет! Требуется: {price}", show_alert=True)
            return
            
        # Проведение транзакции
        players[user_id]["balance"] -= price
        init_player(seller_id)
        players[seller_id]["balance"] += price
        
        if target_lot["item_type"] == "card":
            card_data = target_lot["item_data"]
            card_data["on_sale"] = False
            
            # ИСПРАВЛЕНО: Безопасное удаление оригинального объекта из инвентаря продавца по совпадению ID структуры
            original_card = get_card_by_id(seller_id, card_data["id"])
            if original_card:
                players[seller_id]["inventory"].remove(original_card)
                
            # Передаем новый ID карты покупателю
            card_data["id"] = str(uuid.uuid4())[:8]
            players[user_id]["inventory"].append(card_data)
            
            try:
                bot.send_message(seller_id, f"🏪 Твой товар '{card_data['name']}' успешно куплен! Получено +{price} монет.")
            except Exception: pass
            bot.answer_callback_query(call.id, f"🎉 Вы успешно купили карту '{card_data['name']}'!", show_alert=True)
            
        elif target_lot["item_type"] == "title":
            title_name = target_lot["item_data"]["name"]
            players[user_id]["titles"].append(title_name)
            
            try:
                bot.send_message(seller_id, f"🏪 Твой титул '{title_name}' успешно куплен! Получено +{price} монет.")
            except Exception: pass
            bot.answer_callback_query(call.id, f"🎉 Вы успешно купили титул '{title_name}'!", show_alert=True)

        market_lots.remove(target_lot)
        market_main_menu(call.message)

if __name__ == '__main__':
    print("Бот успешно запущен и готов к работе!")
    bot.infinity_polling()
