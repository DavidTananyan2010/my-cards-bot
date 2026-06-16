import logging
import random
import os
import asyncio
import sqlite3
import threading  # Для фонового веб-сервера
from http.server import SimpleHTTPRequestHandler, HTTPServer # Для сервера
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ==================== СПИСОК КАРТ И ЦЕН ====================
REAL_CARDS = [
    {"file": "2.jpg", "name": "金 sunny🌲 김지ха | DA 🐂", "rarity": "🔮 Секретная", "price": 100},
    {"file": "5.jpg", "name": "Солнечный Самурай ☀️", "rarity": "⭐ Обычная", "price": 10},
    {"file": "4.jpg", "name": "Меха-Бык 🐂", "rarity": "⭐ Редкая", "price": 30},

    {"file": "1.jpg", "name": "👻losnya🐂🌲", "rarity": "🔮 Секретная", "price": 100},
    {"file": "7.jpg", "name": "Призрак Леса 👻", "rarity": "⭐ Редкая", "price": 30},
    {"file": "6.jpg", "name": "Таинственный Лось 🦌", "rarity": "⭐ Обычная", "price": 10},

    {"file": "3.jpg", "name": "Дониёр 🌲", "rarity": "🔮 Секретная", "price": 100},
    {"file": "9.jpg", "name": "Страж Дубравы 🌲", "rarity": "⭐ Обычная", "price": 10},
    {"file": "8.jpg", "name": "Лесной Хакер 💻", "rarity": "⭐ Редкая", "price": 30}
]

EMPTY_RESPONSES = [
    "Эта карта оказалась пустой... Открой ещё разок! 😔",
    "Эх, тут ничего не оказалось. Повезет в следующий раз! 💨",
    "Увы, пак пуст. Фортуна сегодня отдыхает 🃏",
    "Пустышка! Но не унывай, монеты целы — крути еще! 🪙"
]

# ==================== АССОРТИМЕНТ МАГАЗИНА ТИТУЛОВ ====================
SHOP_TITLES = {
    "title_collector": {"name": "🕶️ Коллекционер", "price": 150, "desc": "Выдается истинным ценителям прекрасного."},
    "title_rich": {"name": "💵 Магнат DAcards", "price": 500, "desc": "Для тех, кто сорит монетами направо и налево."},
    "title_lucky": {"name": "🍀 Любимчик Фортуны", "price": 1000, "desc": "Титул, притягивающий удачу (но это неточно)."},
    "title_legend": {"name": "🦅 Легенда Леса", "price": 2500, "desc": "Лимитированный статус величайшего лесного хакера."},
    "title_overlord": {"name": "🌌 Повелитель Рандома", "price": 5000, "desc": "Абсолютный статус. Все паки трепещут перед вами."}
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

# Токен берется из переменных окружения Render, либо используется твой дефолтный
TOKEN = os.environ.get("BOT_TOKEN", "8701989939:AAG2z5cJ-kSkTe1k3OizAeTKHFc-OJ97Bfg")
ADMIN_ID = 7501899378
LOG_CHAT_ID = ADMIN_ID  # ID чата для логов (по умолчанию равен ADMIN_ID)
DB_FILE = "bot_database.db"


# ==================== ВЕБ-СЕРВЕР ДЛЯ RENDER ====================
def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server_address = ("", port)
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass
    
    httpd = HTTPServer(server_address, QuietHandler)
    print(f"Встроенный веб-сервер запущен на порту {port}")
    httpd.serve_forever()


# ==================== РАБОТА С БАЗОЙ ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS users
                   (
                       user_id INTEGER PRIMARY KEY,
                       first_name TEXT,
                       coins INTEGER DEFAULT 0,
                       packs_opened INTEGER DEFAULT 0,
                       active_title TEXT DEFAULT 'Нет титула'
                   )
                   ''')
    
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN packs_opened INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN active_title TEXT DEFAULT 'Нет титула'")
    except sqlite3.OperationalError:
        pass

    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS collections
                   (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       user_id INTEGER,
                       card_name TEXT,
                       rarity TEXT,
                       file_name TEXT,
                       price INTEGER
                   )
                   ''')
    
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS titles
                   (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       user_id INTEGER,
                       title_id TEXT,
                       title_name TEXT,
                       UNIQUE(user_id, title_id)
                   )
                   ''')
    conn.commit()
    conn.close()


def register_user(user_id, first_name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
                   INSERT INTO users (user_id, first_name, coins)
                   VALUES (?, ?, 0) ON CONFLICT(user_id) DO
                   UPDATE SET first_name=excluded.first_name
                   ''', (user_id, first_name))
    conn.commit()
    conn.close()


def get_user_stats(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT coins, packs_opened, active_title FROM users WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res if res else (0, 0, "Нет титула")


def increment_packs(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET packs_opened = packs_opened + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()


def add_card_to_db(user_id, card):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
                   INSERT INTO collections (user_id, card_name, rarity, file_name, price)
                   VALUES (?, ?, ?, ?, ?)
                   ''', (user_id, card['name'], card['rarity'], card['file'], card['price']))
    conn.commit()
    conn.close()


def get_user_cards(user_id):
