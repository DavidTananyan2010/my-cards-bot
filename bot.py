import os, threading, telebot, random, time
from telebot import types
from http.server import BaseHTTPRequestHandler, HTTPServer

# 🔑 Токен бота (Сгенерируй НОВЫЙ в BotFather, если вылезает старая подписка!)
TOKEN = os.environ.get("BOT_TOKEN", "8701989939:AAFVTHvkObrmq6EsQClsTByOEL7tJNqg4_Q")
bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 7501899378

GLOBAL_HIVES = {
    "Рыжие лесные": {"biomass": 50.0, "eggs": 3, "workers": 0, "soldiers": 0, "status": "Стабильно"},
    "Муравьи-Листорезы": {"biomass": 50.0, "eggs": 3, "workers": 0, "soldiers": 0, "status": "Стабильно"},
    "Черные садовые": {"biomass": 50.0, "eggs": 3, "workers": 0, "soldiers": 0, "status": "Стабильно"},
    "Медоносные пчёлы": {"biomass": 50.0, "eggs": 3, "workers": 0, "soldiers": 0, "status": "Стабильно"},
    "Земляные шмели": {"biomass": 50.0, "eggs": 3, "workers": 0, "soldiers": 0, "status": "Стабильно"},
    "Лесные осы-одиночки": {"biomass": 50.0, "eggs": 3, "workers": 0, "soldiers": 0, "status": "Стабильно"}
}
players = {}
FACTIONS = {
    "Муравьи 🐜": ["Рыжие лесные", "Муравьи-Листорезы", "Черные садовые"], 
    "Пчёлы 🐝": ["Медоносные пчёлы", "Земляные шмели", "Лесные осы-одиночки"]
}
ENEMIES = [{"name": "Жук-Олень 🪲", "p": 8, "l": 60}, {"name": "Паук-Волк 🕷️", "p": 20, "l": 200}, {"name": "Дикая Оса 🐝", "p": 14, "l": 110}, {"name": "Хищная Многоножка 🐛", "p": 35, "l": 450}]

def life_cycle():
    while True:
        time.sleep(300) # Жизненный цикл раз в 5 минут
        for h in GLOBAL_HIVES.values():
            if h["workers"] == h["soldiers"] == 0 and h["biomass"] == 50.0: continue
            cost = round(3.5 + h["workers"]*0.5 + h["soldiers"]*1.0, 1)
            if h["biomass"] >= cost:
                h["biomass"] = round(h["biomass"] - cost, 1)
                h["status"] = f"Сыты (-{cost} ед/5м)"
            else:
                h["biomass"], h["status"] = 0.0, "⚠️ ГОЛОД! Население вымирает!"
                for k in ["eggs", "workers", "soldiers"]:
                    if h[k] > 0: h[k] -= 1; break

threading.Thread(target=life_cycle, daemon=True).start()

def get_user(m):
    uid = m.from_user.id
    if uid not in players:
        players[uid] = {"name": m.from_user.first_name, "faction": None, "race": None, "contrib": 0.0, "titles": [], "cooldown": 0}
    return uid, players[uid]

def main_kb(p):
    if not p["faction"]: return None
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🏰 Общее Гнездо", "🥚 Инкубатор Расы")
    kb.row("🌾 Добыча для Улья", "⚔️ Военный Поход")
    return kb

@bot.message_handler(commands=['start'])
def start(m):
    uid, p = get_user(m)
    txt = f"👑 **Панель Творца активна.**\n/admin_players | /users_list\n\n" if uid == ADMIN_ID else f"ℹ️ Ваш ID: `{uid}`\n\n"
    if p["race"]:
        bot.send_message(m.chat.id, txt + f"🔄 Игровые кнопки обновлены! Раса: **{p['race']}**", parse_mode="Markdown", reply_markup=main_kb(p))
    else:
        kb = types.InlineKeyboardMarkup([[types.InlineKeyboardButton(f, callback_data=f"f_{f}")] for f in FACTIONS])
        bot.send_message(m.chat.id, txt + "🐜 **Добро пожаловать в Рой!** Выберите вид насекомых:", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def cb_handler(c):
    uid, p = get_user(c)
    d = c.data
    
    if d.startswith("f_"):
        p["faction"] = d[2:]
        kb = types.InlineKeyboardMarkup([[types.InlineKeyboardButton(r, callback_data=f"r_{r}")] for r in FACTIONS[p["faction"]]])
        bot.edit_message_text(f"Вид выбран: **{p['faction']}**. Выберите глобальный улей:", c.message.chat.id, c.message.message_id, parse_mode="Markdown", reply_markup=kb)
    
    elif d.startswith("r_"):
        p["race"] = d[2:]
        bot.delete_message(c.message.chat.id, c.message.message_id)
        bot.send_message(c.message.chat.id, f"✨ Вы вошли в улей **{p['race']}**!\n\nВ гнезде пока 0 рабочих. Зайдите в **🥚 Инкубатор Расы** и выведите первых помощников из яиц!", parse_mode="Markdown", reply_markup=main_kb(p))
        
    elif d.startswith("h_"):
        if not p["race"]: return bot.answer_callback_query(c.id, "⚠️ Сессия устарела, введите /start", show_alert=True)
        h = GLOBAL_HIVES[p["race"]]
        if h["eggs"] < 1: return bot.answer_callback_query(c.id, "❌ В инкубаторе нет яиц!", show_alert=True)
        h["eggs"] -= 1
        role = d[2:]
        h[role + "s"] += 1
        bot.edit_message_text(f"🎉 Вы вырастили {'Рабочего' if role=='worker' else 'Солдата'}!\nОсталось яиц в инкубаторе: {h['eggs']} шт.", c.message.chat.id, c.message.message_id)
        
    elif d == "buy_egg":
        if not p["race"]: return
        h = GLOBAL_HIVES[p["race"]]
        if h["workers"] == 0: return bot.answer_callback_query(c.id, "❌ Некому принести биомассу! Сначала выведите рабочего.", show_alert=True)
        if h["biomass"] < 30: return bot.answer_callback_query(c.id, "❌ Недостаточно биомассы в улье!", show_alert=True)
        h["biomass"] -= 30; h["eggs"] += 1
        bot.edit_message_text(f"🥚 **Глобальный Инкубатор [{p['race']}]**\n\nВ наличии улья: {h['eggs']} яиц.", c.message.chat.id, c.message.message_id, reply_markup=c.message.reply_markup)

    elif d.startswith("adm_"):
        if uid != ADMIN_ID: return
        if d == "adm_stats":
            txt = "📊 **Мониторинг всех видов:**\n━━━━━━━━━━━━━━━━━━━━\n" + "".join([f"🐜 *{k}*:\n💰 Биомасса: `{v['biomass']}` | {v['status']}\n🥚 Яйца: {v['eggs']} | 📦 Раб: {v['workers']} | ⚔️ Солд: {v['soldiers']}\n━━━━━━━━━━━━━━━━━━━━\n" for k,v in GLOBAL_HIVES.items()])
            bot.edit_message_text(txt, c.message.chat.id, c.message.message_id, parse_mode="Markdown", reply_markup=types.InlineKeyboardMarkup([[types.InlineKeyboardButton("↩️ Назад", callback_data="adm_back")]]))
        elif d == "adm_back":
            bot.edit_message_text("🎛 **Панель Творца**\n\n/givecoins ID КОЛИЧЕСТВО\n/givetitle ID ТИТУЛ\n/users_list", c.message.chat.id, c.message.message_id, reply_markup=types.InlineKeyboardMarkup([[types.InlineKeyboardButton("📊 Состояние Гнезд", callback_data="adm_stats")]]))

@bot.message_handler(func=lambda m: m.text in ["🏰 Общее Гнездо", "🥚 Инкубатор Расы", "🌾 Добыча для Улья", "⚔️ Военный Поход"])
def game_logic(m):
    uid, p = get_user(m)
    if not p["race"]: return bot.send_message(m.chat.id, "⚠️ Данные улья сброшены из-за перезапуска. Введите /start для восстановления.")
    h = GLOBAL_HIVES[p["race"]]
    
    if m.text == "🏰 Общее Гнездо":
        t = f"\n🎖 **Ваши титулы:** {', '.join(p['titles'])}" if p['titles'] else ""
        bot.send_message(m.chat.id, f"🏰 **Глобальное Гнездо [{p['race']}]**\nСтатус: `{h['status']}`\n━━━━━━━━━━━━━━━━━━\n💰 **БИОМАССА:** `{h['biomass']}` ед.\n🥚 **Яиц в инкубаторе:** {h['eggs']} шт.\n\n📋 **Касты:**\n📦 Рабочие: {h['workers']} {'⚠️ (НЕТ РАБОЧИХ!)' if h['workers']==0 else '✅'}\n⚔️ Солдаты: {h['soldiers']} особей\n━━━━━━━━━━━━━━━━━━\n👤 **Вклад:** `+{p['contrib']}` ед.{t}", parse_mode="Markdown")
        
    elif m.text == "🥚 Инкубатор Расы":
        kb = types.InlineKeyboardMarkup()
        if h["eggs"] > 0: kb.row(types.InlineKeyboardButton("📦 Рабочего", callback_data="h_worker"), types.InlineKeyboardButton("⚔️ Солдата", callback_data="h_soldier"))
        kb.add(types.InlineKeyboardButton("➕ Купить яйцо (30 биомассы)", callback_data="buy_egg"))
        bot.send_message(m.chat.id, f"🥚 **Глобальный Инкубатор [{p['race']}]**\nВ наличии улья: {h['eggs']} яиц.", reply_markup=kb)
        
    elif m.text == "🌾 Добыча для Улья":
        if h["workers"] == 0: return bot.send_message(m.chat.id, "⚠️ **Сбор невозможен!** В улье нет рабочих. Откройте Инкубатор.")
        if time.time() - p["cooldown"] < 15: return bot.send_message(m.chat.id, f"⏳ Ваши рабочие ещё в пути. Подождите {int(15 - (time.time() - p['cooldown']))} сек.")
        
        item = random.choice([("гусеницу 🐛", 80), ("каплю нектара 💧", 40), ("травинку 🌱", 25), ("кусок яблока 🍏", 150)])
        carry = h["workers"] * 15
        gain = round(item[1] / 4 if carry >= item[1] else carry / 5, 1)
        h["biomass"] = round(h["biomass"] + gain, 1)
        p["contrib"] += gain; p["cooldown"] = time.time()
        bot.send_message(m.chat.id, f"💪 **Успех!** Рабочие нашли {item[0]} ({item[1]} мг). На склад доставлено `+{gain}` биомассы!")
        
    elif m.text == "⚔️ Военный Поход":
        e = random.choice(ENEMIES)
        bot.send_message(m.chat.id, f"🧭 Боевой отряд встретил хищника: **{e['name']}** (Сила: {e['p']})")
        time.sleep(1)
        u_queen = h["soldiers"] == 0
        power = random.randint(20, 30) if u_queen else h["soldiers"] * 5 + random.randint(0, 5)
        
        if power >= e['p']:
            h["biomass"] = round(h["biomass"] + e['l'], 1)
            loss = "\n👑 Матка защитила гнездо, но устала." if u_queen else "\n💀 1 отважный солдат погиб."
            if not u_queen: h["soldiers"] -= 1
            bot.send_message(m.chat.id, f"🏆 **Победа!** Разведчики забрали `+{e['l']}` биомассы.{loss}")
        else:
            if u_queen:
                stolen = min(h["biomass"], e['l'] * 2)
                h["biomass"] = round(h["biomass"] - stolen, 1)
                bot.send_message(m.chat.id, f"💥 **Поражение!** Хищник ворвался на склад и утащил `-{stolen}` биомассы!")
            else:
                lost = min(h["soldiers"], random.randint(1, 3))
                h["soldiers"] -= lost
                bot.send_message(m.chat.id, f"💔 **Отряд разбит.** Мы потеряли `-{lost}` солдат.")

@bot.message_handler(commands=['users_list', 'admin_players', 'givecoins', 'givetitle'])
def admin_commands(m):
    if m.from_user.id != ADMIN_ID: return
    cmd = m.text.split()
    
    if cmd[0] == '/users_list':
        txt = "📋 **Список участников:**\n" + "".join([f"👤 {v['name']} | ID: `{k}` | Раса: {v['race']}\n" for k,v in players.items()]) if players else "📭 Ульи пока пусты."
        bot.send_message(m.chat.id, txt, parse_mode="Markdown")
    elif cmd[0] == '/admin_players':
        kb = types.InlineKeyboardMarkup([[types.InlineKeyboardButton("📊 Состояние Гнезд", callback_data="adm_stats")]])
        bot.send_message(m.chat.id, "🎛 **Панель Творца**\n\n/givecoins [ID] [КОЛИЧЕСТВО]\n/givetitle [ID] [ТИТУЛ]", reply_markup=kb)
    elif cmd[0] == '/givecoins' and len(cmd) >= 3:
        tid, am = int(cmd[1]), float(cmd[2])
        if tid in players and players[tid]["race"]:
            r = players[tid]["race"]
            GLOBAL_HIVES[r]["biomass"] = round(GLOBAL_HIVES[r]["biomass"] + am, 1)
            bot.send_message(m.chat.id, f"✅ Добавлено `+{am}` биомассы улью {r}")
    elif cmd[0] == '/givetitle' and len(cmd) >= 3:
        tid, title = int(cmd[1]), " ".join(cmd[2:])
        if tid in players:
            players[tid]["titles"].append(title)
            bot.send_message(m.chat.id, f"✅ Игроку `{tid}` выдан титул: **{title}**", parse_mode="Markdown")

# ==================== HEALTH CHECK СЕРВЕР ДЛЯ RENDER ====================
class HealthServer(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
def run_web(): HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), HealthServer).serve_forever()

if __name__ == '__main__':
    if os.environ.get("PORT"): threading.Thread(target=run_web, daemon=True).start()
    print("Чистый компактный бот запущен!")
    bot.infinity_polling()
