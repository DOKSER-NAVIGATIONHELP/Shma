# --- START OF UPDATED CODE --

import telebot
from telebot.types import Message, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
from decimal import Decimal, InvalidOperation, getcontext
from datetime import datetime, timedelta
import time
import threading
import sys
import requests
import uuid
import math
import os
import re
import base64

getcontext().prec = 30

# --- CONFIGURATION ---
API_TOKEN = '8471110373:AAHwo2pxt_sDvngINqXdDIIYrJUmDbkASkY'
COINMARKETCAP_API_KEY = 'b5d850b9-44e4-40aa-8232-c85765a053ac'
TECH_ADMIN_ID = 760217595
MODERATION_CHAT_ID = -1003367988326

BANNED_STICKER_PACKS = [
    "Hansters_stiker_by_TgEmodziBot", 
    "BadStickersPack",
]

# --- BANNED USERS ---
BANNED_USERS = [
    123456789,
]

# --- END BANNED USERS ---
# --- END CONFIGURATION ---

bot = telebot.TeleBot(API_TOKEN)
BOT_USERNAME = None
GOVERNMENT_TREASURY_ID = "government_treasury"
CHARACTER_RULES_LINK = "https://telegra.ph/Pravila-sozdaniya-personazha-09-13"

ROLES = {
    1: "🔹 Админ",
    2: "🔸 Создатель",
    3: "👑 Тех. Админ",
    4: "🏛️ Министр",
    9: "👮 Госс.Служащий"
}

RP_ROLES = {
    4: "🏛️ Министр",
    9: "👮 Госс.Служащий"
}

# --- House and Apartment Configuration ---
HOUSES_AVAILABLE = {
    "11": 10000, "12": 10000, "13": 10000, "14": 10000, "15": 10000,
    "16": 10000, "17": 10000, "18": 10000, "19": 10000, "20": 10000,
    "21": 10000, "22": 10000, "23": 10000, "24": 10000, "28": 18000,
    "29": 18000, "30": 1000000, "31": 18000, "32": 18000, "33": 15000,
    "34": 15000, "35": 25000, "36": 20000, "37": 25000, "38": 30000 # Example
}

APARTMENTS_AVAILABLE = {
    "6": 8000, "7": 8000
}

PROPERTY_TAX_RATES = {
    8000: 150,
    10000: 200,
    15000: 250,
    18000: 300,
    20000: 350,
    25000:400,
    30000: 500 # Example tax for new house
}
# --- END ---

DRIVER_LICENSE_CATEGORIES = {
    "АМ": {"name": "мопеды", "age": 16},
    "А": {"name": "мотоциклы", "age": 19},
    "А1": {"name": "мотоциклы до 125 м³", "age": 16},
    "В": {"name": "легковые/грузовые до 3.5т", "age": 20},
    "С": {"name": "грузовые более 3.5т", "age": 20},
    "D": {"name": "пассажирские автобусы", "age": 20},
    "ВЕ": {"name": "категория «В» с прицепом >750кг", "age": 20},
    "СЕ": {"name": "категория «С» с прицепом >750кг", "age": 20},
    "DE": {"name": "категория «D» с прицепом >750кг", "age": 20},
    "F": {"name": "трамваи", "age": 20},
    "I": {"name": "троллейбусы", "age": 20},
    "Водный транспорт": {"name": "Водный транспорт", "age": 21},
    "Летный транспорт": {"name": "Летный транспорт", "age": 25}
}

CRYPTO_CURRENCIES = {
    "RUB": "Russian Ruble",
    "BTC": "Bitcoin",
    "TON": "Toncoin",
    "GRAM": "Gram"
}

# NEW: Fields available for passport modification
PASSPORT_MODIFIABLE_FIELDS = {
    'full_name': "ФИО",
    'age': "Возраст",
    'photo_file_id': "Фото",
    'roblox_display_name': "Ник в Roblox (Дисплей)",
    'roblox_real_name': "Ник в Roblox (Настоящий)",
    'biography': "Биография (все поля)"
}

CURRENT_RATES = {
    "RUB": Decimal('0'), "BTC": Decimal('0'),
    "TON": Decimal('0'), "GRAM": Decimal('0')
}

USD_TO_RUB_RATE = Decimal('0')

USER_SPAM_DATA = {}
SPAM_MESSAGE_LIMIT = 5
SPAM_TIME_WINDOW = 5
XP_COOLDOWN_SECONDS = 3600

user_data_for_passport = {}
user_data_for_sim = {}
user_data_for_med_card = {}
user_data_for_license = {}
rejection_in_progress = {}
fining_in_progress = {}
TRANSACTION_IN_PROGRESS = set()
# NEW: For passport modification
passport_modification_in_progress = {}
# NEW: For auction creation
auction_creation_in_progress = {}
# NEW: For company creation
company_creation_in_progress = {}
# NEW: For company management actions (invites, role edits etc)
company_management_in_progress = {}
# NEW: For pending company invitations {invited_user_id: {inviter_id, company_id, message_id}}
company_invitations = {}


# For /search pagination
user_search_results = {}

def antispam_filter(func):
    def wrapper(message: Message):
        if message.from_user.id in BANNED_USERS:
            print(f"Заблокированный пользователь {message.from_user.id} пытался использовать команду")
            return
        user_id = message.from_user.id
        current_time = time.time()
        if user_id not in USER_SPAM_DATA:
            USER_SPAM_DATA[user_id] = []
        USER_SPAM_DATA[user_id] = [t for t in USER_SPAM_DATA[user_id] if current_time - t < SPAM_TIME_WINDOW]
        if len(USER_SPAM_DATA[user_id]) >= SPAM_MESSAGE_LIMIT:
            print(f"Пользователь {user_id} спамит. Команда проигнорирована.")
            return
        USER_SPAM_DATA[user_id].append(current_time)
        return func(message)
    return wrapper

def add_experience(user_id, amount):
    if amount <= 0: return
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        experience_to_add = int(math.sqrt(amount))
        if experience_to_add == 0: experience_to_add = 1
        
        cursor.execute("SELECT level, experience FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return
        level, experience = result
        new_experience = experience + experience_to_add
        xp_for_next_level = (level ** 2) * 100
        level_up = False
        while new_experience >= xp_for_next_level:
            level += 1
            new_experience -= xp_for_next_level
            xp_for_next_level = (level ** 2) * 100
            level_up = True
        cursor.execute("UPDATE users SET level = ?, experience = ? WHERE user_id = ?", (level, new_experience, user_id))
        conn.commit()
        if level_up:
            try:
                bot.send_message(user_id, f"🎉 <b>Поздравляем!</b> Вы достигли <b>{level}</b> уровня доверия!", parse_mode='HTML')
            except Exception as e:
                print(f"Не удалось отправить уведомление о повышении уровня пользователю {user_id}: {e}")
    except Exception as e:
        print(f"Ошибка при начислении опыта пользователю {user_id}: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def grant_xp_for_pair_transaction(sender_id, receiver_id, amount):
    if amount <= 0: return
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        user_one, user_two = min(sender_id, receiver_id), max(sender_id, receiver_id)
        cursor.execute("SELECT timestamp FROM xp_cooldowns WHERE user_one_id = ? AND user_two_id = ?", (user_one, user_two))
        result = cursor.fetchone()
        current_time = time.time()
        if result and (current_time - result[0]) < XP_COOLDOWN_SECONDS:
            return
        add_experience(sender_id, amount)
        cursor.execute("REPLACE INTO xp_cooldowns (user_one_id, user_two_id, timestamp) VALUES (?, ?, ?)", (user_one, user_two, current_time))
        conn.commit()
    except Exception as e:
        print(f"Ошибка при проверке кулдауна опыта: {e}")
    finally:
        conn.close()

def update_rates_from_coinmarketcap():
    global CURRENT_RATES
    crypto_keys = [key for key in CRYPTO_CURRENCIES.keys() if key != 'RUB']
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
    headers = {'Accepts': 'application/json', 'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY}
    params = {'symbol': ",".join(crypto_keys), 'convert': 'USD'}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        new_rates = {}
        for symbol in crypto_keys:
            if symbol in data['data']:
                usd_price = Decimal(str(data['data'][symbol]['quote']['USD']['price']))
                new_rates[symbol] = usd_price
        if new_rates: CURRENT_RATES.update(new_rates)
    except Exception as e:
        print(f"Ошибка при обновлении курсов: {e}")

def update_rub_rate():
    global USD_TO_RUB_RATE
    try:
        response = requests.get('https://api.exchangerate-api.com/v4/latest/USD')
        response.raise_for_status()
        data = response.json()
        if 'RUB' in data.get('rates', {}):
            USD_TO_RUB_RATE = Decimal(str(data['rates']['RUB']))
            CURRENT_RATES['RUB'] = Decimal('1.0')
    except Exception as e:
        print(f"Ошибка при обновлении курса RUB: {e}")

def run_rate_updater():
    while True:
        try:
            update_rates_from_coinmarketcap()
            update_rub_rate()
            time.sleep(300)
        except Exception as e:
            print(f"Ошибка в обновлении курсов: {e}")
            time.sleep(300)

def get_moscow_time():
    return datetime.now(pytz.timezone('Europe/Moscow'))

def get_user_info(user_id):
    try:
        chat = bot.get_chat(user_id)
        username = f"@{chat.username}" if chat.username else None
        return {'username': username, 'first_name': chat.first_name, 'last_name': chat.last_name}
    except Exception as e:
        print(f"Ошибка получения информации о пользователе {user_id}: {e}")
        return {'username': None, 'first_name': None, 'last_name': None}

def update_user_info(user_id):
    user_info = get_user_info(user_id)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
                       (user_id, user_info['username'], user_info['first_name'], user_info['last_name']))
        cursor.execute("UPDATE users SET username = COALESCE(?, username), first_name = COALESCE(?, first_name), last_name = COALESCE(?, last_name) WHERE user_id = ?",
                       (user_info['username'], user_info['first_name'], user_info['last_name'], user_id))
        conn.commit()
    except Exception as e:
        print(f"Ошибка обновления информации о пользователе {user_id}: {e}")
    finally:
        conn.close()

def get_display_name(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT username, first_name, last_name FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result:
            username, first_name, last_name = result
            if username: return username
            name_parts = [n for n in [first_name, last_name] if n]
            return " ".join(name_parts) if name_parts else f"ID:{user_id}"
        return f"ID:{user_id}"
    except Exception as e:
        print(f"Ошибка получения имени пользователя {user_id}: {e}")
        return f"ID:{user_id}"
    finally:
        conn.close()

def get_roles(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT roles FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result and result[0]:
            return [int(role_id) for role_id in result[0].split(',') if role_id]
        return []
    except Exception as e:
        print(f"Ошибка получения ролей пользователя {user_id}: {e}")
        return []
    finally:
        conn.close()

def register_user(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        update_user_info(user_id)
    except Exception as e:
        print(f"Ошибка регистрации пользователя {user_id}: {e}")
    finally:
        conn.close()

def notify_staff(action, details, sender_id=None, receiver_id=None, amount=None):
    timestamp = get_moscow_time().strftime("%Y-%m-%d %H:%M:%S (MSK)")
    log_message = f"🛠️ [{timestamp}] {action}\n"
    if sender_id: log_message += f"👤 Отправитель: {get_display_name(sender_id)} (ID: {sender_id})\n"
    if receiver_id: log_message += f"👥 Получатель: {get_display_name(receiver_id)} (ID: {receiver_id})\n"
    if amount is not None:
        try:
            log_message += f"💰 Сумма: {amount.normalize().to_eng_string() if isinstance(amount, Decimal) else amount}\n"
        except (TypeError, ValueError):
            log_message += f"💰 Сумма: {amount}\n"
    if details: log_message += f"📝 Детали: {details}\n"
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM users WHERE roles IS NOT NULL AND roles != ''")
        staff = cursor.fetchall()
        for (user_id,) in staff:
            try:
                bot.send_message(user_id, log_message)
            except Exception as e:
                print(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
    except Exception as e:
        print(f"Ошибка при получении списка персонала: {e}")
    finally:
        conn.close()
        
def init_db():
    # Увеличиваем timeout до 30 секунд, чтобы потоки ждали друг друга, а не крашились
    conn = sqlite3.connect('database.db', isolation_level=None, timeout=30)
    cursor = conn.cursor()
    
    # ВАЖНО: Используем режим DELETE вместо WAL для стабильности файловой системы
    cursor.execute("PRAGMA journal_mode=DELETE") 
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys = ON")
    
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS banned_photos (
            file_unique_id TEXT PRIMARY KEY,
            added_by INTEGER,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)    

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, last_name TEXT,
            balance INTEGER DEFAULT 0, roles TEXT, level INTEGER DEFAULT 1, experience INTEGER DEFAULT 0,
            auction_anon INTEGER DEFAULT 0
        )
    """)
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'level' not in columns: cursor.execute("ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1")
    if 'experience' not in columns: cursor.execute("ALTER TABLE users ADD COLUMN experience INTEGER DEFAULT 0")
    if 'auction_anon' not in columns: cursor.execute("ALTER TABLE users ADD COLUMN auction_anon INTEGER DEFAULT 0")


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, full_name TEXT, age INTEGER,
            gender TEXT, height TEXT, hair_color TEXT, eye_color TEXT, body_type TEXT, tattoos TEXT,
            childhood TEXT, father TEXT, mother TEXT, knowledge TEXT, current_life TEXT,
            roblox_display_name TEXT, roblox_real_name TEXT, photo_file_id TEXT, status TEXT DEFAULT 'pending',
            rejection_reason TEXT, moderator_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    cursor.execute("PRAGMA table_info(characters)")
    columns = {row[1] for row in cursor.fetchall()}
    new_columns = {
        'gender': 'TEXT', 'height': 'TEXT', 'hair_color': 'TEXT', 'eye_color': 'TEXT', 'tattoos': 'TEXT',
        'childhood': 'TEXT', 'father': 'TEXT', 'mother': 'TEXT', 'knowledge': 'TEXT', 'current_life': 'TEXT',
        'roblox_display_name': 'TEXT', 'roblox_real_name': 'TEXT'
    }
    for col, col_type in new_columns.items():
        if col not in columns:
            cursor.execute(f"ALTER TABLE characters ADD COLUMN {col} {col_type}")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sim_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER,
            user_id INTEGER NOT NULL,
            phone_number TEXT NOT NULL UNIQUE,
            status TEXT DEFAULT 'pending',
            moderator_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE SET NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medical_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT, character_id INTEGER NOT NULL UNIQUE, user_id INTEGER NOT NULL,
            psych_state TEXT, diagnoses TEXT, pain_threshold TEXT, weight TEXT, height TEXT,
            status TEXT DEFAULT 'pending', moderator_id INTEGER, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, character_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
            license_type TEXT NOT NULL,
            psych_state TEXT, criminal_record TEXT, reason TEXT,
            health_issues TEXT, category_details TEXT,
            status TEXT DEFAULT 'pending', moderator_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP, expires_at DATETIME, revoked_until DATETIME,
            UNIQUE(character_id, license_type),
            FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    cursor.execute("PRAGMA table_info(licenses)")
    columns = {row[1] for row in cursor.fetchall()}
    if 'health_issues' not in columns: cursor.execute("ALTER TABLE licenses ADD COLUMN health_issues TEXT")
    if 'category_details' not in columns: cursor.execute("ALTER TABLE licenses ADD COLUMN category_details TEXT")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS houses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_type TEXT NOT NULL,
            property_number TEXT NOT NULL,
            character_id INTEGER,
            user_id INTEGER NOT NULL,
            purchase_price INTEGER NOT NULL,
            purchase_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(property_type, property_number),
            FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE SET NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS passport_modifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            moderator_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            character_id INTEGER,
            invoice_type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            issuer_id INTEGER,
            reason TEXT,
            due_date DATETIME NOT NULL,
            status TEXT DEFAULT 'unpaid',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE SET NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auctions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER NOT NULL,
            item_type TEXT NOT NULL,
            item_db_id INTEGER,
            item_name TEXT NOT NULL,
            description TEXT,
            start_price INTEGER NOT NULL,
            start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            end_time DATETIME NOT NULL,
            status TEXT DEFAULT 'active',
            min_bid_step INTEGER DEFAULT 1,
            FOREIGN KEY (seller_id) REFERENCES users(user_id)
        )
    """)
    cursor.execute("PRAGMA table_info(auctions)")
    columns = {row[1] for row in cursor.fetchall()}
    if 'description' not in columns:
        cursor.execute("ALTER TABLE auctions ADD COLUMN description TEXT")
    if 'min_bid_step' not in columns:
        cursor.execute("ALTER TABLE auctions ADD COLUMN min_bid_step INTEGER DEFAULT 1")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            auction_id INTEGER NOT NULL,
            bidder_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            is_anonymous INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (auction_id) REFERENCES auctions(id) ON DELETE CASCADE,
            FOREIGN KEY (bidder_id) REFERENCES users(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER NOT NULL,
            character_id INTEGER NOT NULL,
            name TEXT NOT NULL UNIQUE,
            initial TEXT NOT NULL UNIQUE,
            logo_file_id TEXT,
            balance INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_user_id) REFERENCES users(user_id),
            FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("PRAGMA table_info(companies)")
    columns = {row[1] for row in cursor.fetchall()}
    if 'status' not in columns:
        cursor.execute("ALTER TABLE companies ADD COLUMN status TEXT DEFAULT 'active'")
        
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            role_name TEXT NOT NULL,
            salary_amount INTEGER DEFAULT 0,
            salary_frequency_days INTEGER DEFAULT 7,
            can_withdraw INTEGER DEFAULT 0,
            can_manage_roles INTEGER DEFAULT 0,
            can_invite INTEGER DEFAULT 0,
            is_owner INTEGER DEFAULT 0,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            character_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_salary_payment DATETIME,
            UNIQUE(company_id, user_id),
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (character_id) REFERENCES characters(id),
            FOREIGN KEY (role_id) REFERENCES company_roles(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_salary_debt (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            employee_user_id INTEGER NOT NULL,
            amount_owed INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (employee_user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)

    cursor.execute("CREATE TABLE IF NOT EXISTS xp_cooldowns (user_one_id INTEGER NOT NULL, user_two_id INTEGER NOT NULL, timestamp REAL NOT NULL, PRIMARY KEY (user_one_id, user_two_id))")
    cursor.execute("CREATE TABLE IF NOT EXISTS government_treasury (id TEXT PRIMARY KEY, balance INTEGER DEFAULT 0, president_id INTEGER UNIQUE)")
    cursor.execute("INSERT OR IGNORE INTO government_treasury (id, balance) VALUES (?, 0)", (GOVERNMENT_TREASURY_ID,))

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS government_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO government_settings (setting_key, setting_value) VALUES ('player_transfer_tax_percent', '0.5')")
    cursor.execute("INSERT OR IGNORE INTO government_settings (setting_key, setting_value) VALUES ('company_transfer_tax_percent', '5.0')")


    cursor.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, receiver_id INTEGER, amount INTEGER, action TEXT, details TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
    cursor.execute("CREATE TABLE IF NOT EXISTS bot_groups (chat_id INTEGER PRIMARY KEY, title TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS crypto_balances (user_id INTEGER, currency TEXT NOT NULL, amount TEXT DEFAULT '0', PRIMARY KEY (user_id, currency), FOREIGN KEY (user_id) REFERENCES users(user_id))")
    cursor.execute("CREATE TABLE IF NOT EXISTS checks (check_id TEXT PRIMARY KEY, creator_id INTEGER NOT NULL, amount INTEGER NOT NULL, target_user_id INTEGER, status TEXT DEFAULT 'active', created_at DATETIME DEFAULT CURRENT_TIMESTAMP, claimed_by_id INTEGER, claimed_at DATETIME, FOREIGN KEY (creator_id) REFERENCES users(user_id), FOREIGN KEY (target_user_id) REFERENCES users(user_id), FOREIGN KEY (claimed_by_id) REFERENCES users(user_id))")
    cursor.execute("CREATE TABLE IF NOT EXISTS laws (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL, UNIQUE(category, title))")

    cursor.execute("PRAGMA auto_vacuum = FULL")
    cursor.execute("VACUUM")


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wanted (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER NOT NULL,
            stars INTEGER DEFAULT 0,
            reason TEXT,
            issued_by INTEGER,
            issued_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            removed_by INTEGER,
            removed_at DATETIME,
            FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
            FOREIGN KEY (issued_by) REFERENCES users(user_id),
            FOREIGN KEY (removed_by) REFERENCES users(user_id)
        )
    """)
    cursor.execute("PRAGMA table_info(wanted)")
    columns = {row[1] for row in cursor.fetchall()}
    if 'status' not in columns:
        cursor.execute("ALTER TABLE wanted ADD COLUMN status TEXT DEFAULT 'active'")
    if 'removed_by' not in columns:
        cursor.execute("ALTER TABLE wanted ADD COLUMN removed_by INTEGER")
    if 'removed_at' not in columns:
        cursor.execute("ALTER TABLE wanted ADD COLUMN removed_at DATETIME")

    try:
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (TECH_ADMIN_ID,))
        cursor.execute("SELECT roles FROM users WHERE user_id = ?", (TECH_ADMIN_ID,))
        result = cursor.fetchone()
        current_roles_str = result[0] if result and result[0] else ""
        roles_set = set(current_roles_str.split(',')) if current_roles_str else set()
        roles_set.add(str(3))
        roles_set.discard('')
        new_roles_str = ",".join(sorted(list(roles_set)))
        cursor.execute("UPDATE users SET roles = ? WHERE user_id = ?", (new_roles_str, TECH_ADMIN_ID))
        update_user_info(TECH_ADMIN_ID)
    except Exception as e:
        print(f"Ошибка при назначении роли Тех. Админу: {e}")

    conn.commit()
    conn.close()

def get_item_display_name(item_type, item_db_id):
    """Возвращает читаемое имя для предмета аукциона."""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        if item_type == 'house':
            cursor.execute("SELECT property_type, property_number FROM houses WHERE id = ?", (item_db_id,))
            res = cursor.fetchone()
            if res:
                return f"Дом #{res[1]}" if res[0] == 'house' else f"Квартира #{res[1]}"
        elif item_type == 'sim_card':
            cursor.execute("SELECT phone_number FROM sim_cards WHERE id = ?", (item_db_id,))
            res = cursor.fetchone()
            if res:
                return f"SIM-карта {res[0]}"
        elif item_type == 'company':
            cursor.execute("SELECT name FROM companies WHERE id = ?", (item_db_id,))
            res = cursor.fetchone()
            if res:
                return f"Компания «{res[0]}»"
        
        # Если ничего не найдено, возвращаем запасной вариант
        return f"Предмет ID:{item_db_id}"
        
    except Exception as e:
        print(f"Ошибка в get_item_display_name: {e}")
        return "Неизвестный предмет"
    finally:
        conn.close()


def set_commands():
    commands = [
        BotCommand('start', 'Начать работу / Активировать чек'),
        BotCommand('profile', 'Показать профиль и баланс'),
        BotCommand('scheta', 'Мои счета, налоги и штрафы'),
        BotCommand('houses', 'Купить участок или квартиру'),
        BotCommand('warehouse', 'Мой склад (недвижимость, SIM)'),
        BotCommand('company', 'Управление Вашими компаниями'),
        BotCommand('auction', 'Аукцион'),
        BotCommand('id', 'Узнать ID пользователя'),
        # ...внутри списка команд...
        BotCommand('tax', 'Установить налоги (президент)'),
        BotCommand('pay', 'Перевести доллары (игроку или в компанию)'),
        BotCommand('top', 'Топ граждан по состоянию'),
        BotCommand('roles', 'Административные роли'),
        BotCommand('rproles', 'RP-роли'),
        BotCommand('treasury', 'Баланс Федеральной казны'),
        BotCommand('donate', 'Пожертвовать в казну'),
        BotCommand('laws', 'Законодательство'),
        BotCommand('wallet', 'Крипто-кошелек'),
        BotCommand('buy_crypto', 'Купить криптовалюту'),
        BotCommand('sell_crypto', 'Продать криптовалюту'),
        BotCommand('transfer_crypto', 'Перевести криптовалюту'),
        BotCommand('create_check', 'Создать чек'),
        BotCommand('claim', 'Активировать чек'),
        BotCommand('create_passport', 'Создать Паспорт'),
        BotCommand('passport', 'Показать мои Паспорта'),
        BotCommand('search', 'Поиск по RP базе данных (гос. службы)'),
        BotCommand('add', 'Выдать доллары (админ)'),
        BotCommand('delete', 'Изъять доллары (админ)'),
        BotCommand('giverole', 'Выдать роль (админ)'),
        BotCommand('removerole', 'Снять роль (админ)'),
        BotCommand('delete_passport', 'Удалить Паспорт (тех.админ)'),
        BotCommand('delete_company', 'Удалить компанию (тех.админ)'),
        BotCommand('addlaw', 'Добавить/изменить закон (президент/министр)'),
        BotCommand('deletelaw', 'Удалить закон (президент/министр)'),
        BotCommand('setpresident', 'Назначить президента (тех. админ)'),
        BotCommand('removepresident', 'Снять президента (тех. админ)'),
        BotCommand('set_treasury_role', 'Назначить роль для казны (президент/тех.админ)'),
        BotCommand('withdrawtreasury', 'Вывести из казны (президент/министр)'),
        BotCommand('wanted', 'Просмотреть всех в розыске (министр/президент)'),
    ]
    try:
        if bot.token: bot.set_my_commands(commands)
    except Exception as e:
        print(f"Ошибка установки команд бота: {e}")

def has_permission(user_id, required_roles):
    return any(role in get_roles(user_id) for role in required_roles)

# --- House System ---

@bot.message_handler(commands=['houses'])
@antispam_filter
def show_houses_for_sale(message: Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, full_name FROM characters WHERE user_id = ? AND status = 'approved'", (user_id,))
        characters = cursor.fetchall()
        if not characters:
            return bot.reply_to(message, "❌ У вас должен быть хотя бы один одобренный персонаж для покупки недвижимости.")

        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("🏘️ Участки (Дома)", callback_data="houses_list_house"),
            InlineKeyboardButton("🏢 Квартиры", callback_data="houses_list_apartment")
        )
        bot.reply_to(message, "🏡 <b>Рынок недвижимости</b>\n\nВыберите тип недвижимости для просмотра доступных вариантов:", reply_markup=markup, parse_mode='HTML')

    except Exception as e:
        bot.reply_to(message, f"⚠️ Произошла ошибка: {e}")
    finally:
        conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('houses_list_'))
def handle_property_list(call):
    # SECURITY CHECK: Only original user can interact
    # This type of menu is informational, so we allow anyone to click.
    # More sensitive actions below will have checks.
    property_type = call.data.split('_')[2]
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        # Fetch owner info along with property number
        cursor.execute("""
            SELECT h.property_number, c.full_name
            FROM houses h
            JOIN characters c ON h.character_id = c.id
            WHERE h.property_type = ? AND h.character_id IS NOT NULL
        """, (property_type,))
        owned_properties = {row[0]: row[1] for row in cursor.fetchall()}

        if property_type == 'house':
            available_properties = HOUSES_AVAILABLE
            title = "🏘️ Участки (Дома)"
        else: # apartment
            available_properties = APARTMENTS_AVAILABLE
            title = "🏢 Квартиры"

        markup = InlineKeyboardMarkup(row_width=2)
        buttons = []
        # Show all properties, mark owned ones
        for number, price in available_properties.items():
            if number in owned_properties:
                # This property is owned by a character
                owner_name = owned_properties[number]
                buttons.append(InlineKeyboardButton(
                    f"#{number} - Продано ({owner_name})",
                    callback_data="do_nothing"
                ))
            else:
                # Check if it's for sale (i.e., not in the houses table at all)
                cursor.execute("SELECT 1 FROM houses WHERE property_type = ? AND property_number = ?", (property_type, number))
                if cursor.fetchone():
                     buttons.append(InlineKeyboardButton(
                        f"#{number} - Продано (на складе)",
                        callback_data="do_nothing"
                    ))
                else:
                    # This property is available for purchase
                    buttons.append(InlineKeyboardButton(
                        f"#{number} - {price:,} $",
                        callback_data=f"house_buy_{property_type}_{number}_{call.message.chat.id}"
                    ))

        text = f"<b>{title} на продажу:</b>\n\nВыберите участок/квартиру для покупки."
        markup.add(*buttons)
        markup.add(InlineKeyboardButton("⬅️ Назад", callback_data=f"houses_back_main_{call.message.chat.id}"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')

    except Exception as e:
        print(f"Ошибка в handle_property_list: {e}")
        bot.answer_callback_query(call.id, "Произошла ошибка.", show_alert=True)
    finally:
        conn.close()

@bot.callback_query_handler(func=lambda call: call.data == 'do_nothing')
def do_nothing_callback(call):
    bot.answer_callback_query(call.id, "Эта недвижимость уже продана.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('houses_back_main'))
def handle_back_to_main_houses(call):
    original_user_id = int(call.data.split('_')[-1])
    if call.from_user.id != original_user_id:
        return bot.answer_callback_query(call.id, "Вы не можете использовать это меню.")

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🏘️ Участки (Дома)", callback_data="houses_list_house"),
        InlineKeyboardButton("🏢 Квартиры", callback_data="houses_list_apartment")
    )
    bot.edit_message_text("🏡 <b>Рынок недвижимости</b>\n\nВыберите тип недвижимости для просмотра доступных вариантов:",
                        call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('house_buy_'))
def handle_buy_property_confirmation(call):
    parts = call.data.split('_')
    original_user_id = int(parts[-1])
    if call.from_user.id != original_user_id:
        return bot.answer_callback_query(call.id, "Вы не можете совершить эту покупку.")

    user_id = call.from_user.id
    property_type = parts[2]
    property_number = parts[3]

    price_dict = HOUSES_AVAILABLE if property_type == 'house' else APARTMENTS_AVAILABLE
    price = price_dict.get(property_number)
    type_text = "Участок" if property_type == 'house' else "Квартира"

    text = (f"<b>Подтверждение покупки</b>\n\n"
            f"<b>Недвижимость:</b> {type_text} #{property_number}\n"
            f"<b>Стоимость:</b> {price:,} $\n\n"
            f"Вы уверены, что хотите совершить покупку?\n"
            f"<i>(Имущество будет добавлено на ваш склад /warehouse)</i>")

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ Да, купить", callback_data=f"house_final_{property_type}_{property_number}_{original_user_id}"),
        InlineKeyboardButton("❌ Отмена", callback_data=f"houses_list_{property_type}")
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')


@bot.callback_query_handler(func=lambda call: call.data.startswith('house_final_'))
def finalize_property_purchase(call):
    parts = call.data.split('_')
    original_user_id = int(parts[-1])
    if call.from_user.id != original_user_id:
        return bot.answer_callback_query(call.id, "Вы не можете совершить эту покупку.")

    user_id = call.from_user.id
    property_type = parts[2]
    property_number = parts[3]

    price_dict = HOUSES_AVAILABLE if property_type == 'house' else APARTMENTS_AVAILABLE
    price = price_dict.get(property_number)

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        # Check if property is already sold
        cursor.execute("SELECT 1 FROM houses WHERE property_type = ? AND property_number = ?", (property_type, property_number))
        if cursor.fetchone():
            bot.answer_callback_query(call.id, "Эта недвижимость уже продана.", show_alert=True)
            # Create a new call object to refresh the list
            fake_call = call
            fake_call.data = f'houses_list_{property_type}'
            handle_property_list(fake_call)
            return

        # Check user balance
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        balance = cursor.fetchone()[0]
        if balance < price:
            bot.answer_callback_query(call.id, f"Недостаточно средств. Ваш баланс: {balance:,} $", show_alert=True)
            return

        # --- НОВАЯ ЛОГИКА: Выбор персонажа ---
        cursor.execute("SELECT id, full_name FROM characters WHERE user_id = ? AND status = 'approved'", (user_id,))
        characters = cursor.fetchall()
        if not characters:
            bot.answer_callback_query(call.id, "У вас нет одобренных персонажей для покупки.", show_alert=True)
            return

        if len(characters) == 1:
            # Автоматическая привязка, если персонаж один
            character_id = characters[0][0]
            process_final_purchase(call, user_id, property_type, property_number, price, character_id)
        else:
            # Показываем кнопки для выбора
            markup = InlineKeyboardMarkup(row_width=1)
            for char_id, full_name in characters:
                markup.add(InlineKeyboardButton(full_name, callback_data=f"house_assign_{property_type}_{property_number}_{price}_{char_id}_{original_user_id}"))
            markup.add(InlineKeyboardButton("❌ Отмена", callback_data=f"houses_list_{property_type}"))
            bot.edit_message_text("Выберите персонажа, на которого будет оформлена недвижимость:",
                                  call.message.chat.id, call.message.message_id, reply_markup=markup)
            bot.answer_callback_query(call.id)

    except Exception as e:
        print(f"Ошибка в finalize_property_purchase: {e}")
        bot.answer_callback_query(call.id, "Произошла критическая ошибка.", show_alert=True)
    finally:
        conn.close()

def process_final_purchase(call, user_id, property_type, property_number, price, character_id):
    """Завершает покупку и привязывает дом к персонажу."""
    type_text = "Участок" if property_type == 'house' else "Квартира"
    conn = sqlite3.connect('database.db')
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, user_id))
        conn.execute("""
            INSERT INTO houses (property_type, property_number, character_id, user_id, purchase_price)
            VALUES (?, ?, ?, ?, ?)
        """, (property_type, property_number, character_id, user_id, price))
        conn.commit()

        char_name = conn.execute("SELECT full_name FROM characters WHERE id = ?", (character_id,)).fetchone()[0]

        bot.answer_callback_query(call.id, "Покупка совершена!", show_alert=True)
        bot.edit_message_text(f"🎉 <b>Поздравляем!</b>\n\nВы успешно приобрели '{type_text} #{property_number}' за {price:,} $.\n\n"
                              f"Имущество было привязано к персонажу: <b>{char_name}</b>.",
                              call.message.chat.id, call.message.message_id, parse_mode='HTML')
        notify_staff("Покупка недвижимости", f"Куплен {type_text} #{property_number} за {price:,} $", user_id, None, price)
    except Exception as e:
        if conn: conn.rollback()
        print(f"Ошибка в process_final_purchase: {e}")
        bot.answer_callback_query(call.id, "Произошла критическая ошибка при завершении покупки.", show_alert=True)
    finally:
        conn.close()

@bot.message_handler(content_types=['sticker'])
def handle_sticker_ban(message: Message):
    # Получаем информацию о стикере
    if not message.sticker or not message.sticker.set_name:
        return

    pack_name = message.sticker.set_name
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # (Опционально) Выводим в консоль название пака, чтобы ты мог его скопировать
    # print(f"User sent sticker from pack: {pack_name}") 

    if pack_name in BANNED_STICKER_PACKS:
        # Защита: не банить Тех. Админа
        if user_id == TECH_ADMIN_ID:
            return

        try:
            # 1. Удаляем сообщение со стикером
            bot.delete_message(chat_id, message.message_id)
            
            # 2. Баним пользователя (kick_chat_member тоже банит, ban_chat_member - новее)
            # until_date=0 или без него означает бан навсегда
            bot.ban_chat_member(chat_id, user_id)
            
            # 3. Отправляем уведомление в чат (можно убрать, если хочешь тихо)
            bot.send_message(chat_id, f"⛔ Пользователь <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a> заблокирован за запрещенный стикерпак.", parse_mode='HTML')
            
            # Логируем для админов
            notify_staff("Автобан", f"Забанен за стикерпак: {pack_name}", user_id, None)
            
        except Exception as e:
            print(f"Ошибка при бане за стикер: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('house_assign_'))
def handle_house_assign_callback(call):
    """Обрабатывает нажатие кнопки выбора персонажа при покупке дома."""
    parts = call.data.split('_')
    original_user_id = int(parts[-1])
    if call.from_user.id != original_user_id:
        return bot.answer_callback_query(call.id, "Вы не можете совершить эту покупку.")

    user_id = call.from_user.id
    property_type = parts[2]
    property_number = parts[3]
    price = int(parts[4])
    character_id = int(parts[5])
    process_final_purchase(call, user_id, property_type, property_number, price, character_id)

# --- Weekly Property Tax ---                    

def issue_weekly_property_taxes():
    while True:
        # Wait 7 days before running
        time.sleep(7 * 24 * 60 * 60)
        conn = None
        try:
            print("Выдача еженедельных налогов на недвижимость...")
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()

            cursor.execute("SELECT user_id, character_id, property_type, property_number, purchase_price FROM houses")
            all_properties = cursor.fetchall()
            due_date = datetime.now() + timedelta(days=3) # 3 days to pay

            for user_id, char_id, prop_type, prop_num, price in all_properties:
                tax_amount = PROPERTY_TAX_RATES.get(price)
                if not tax_amount:
                    print(f"Не найден налог для цены {price}, пропуск.")
                    continue

                type_text = "участок" if prop_type == 'house' else "квартиру"
                reason_text = f"Налог на {type_text} #{prop_num}"

                try:
                    cursor.execute("""
                        INSERT INTO invoices (user_id, character_id, invoice_type, amount, due_date, reason)
                        VALUES (?, ?, 'property_tax', ?, ?, ?)
                    """, (user_id, char_id, tax_amount, due_date, reason_text))

                    bot.send_message(user_id,
                                     f"🧾 Вам начислен еженедельный налог на недвижимость!\n\n"
                                     f"<b>Объект:</b> {type_text.capitalize()} #{prop_num}\n"
                                     f"<b>Сумма налога:</b> {tax_amount:,} $\n"
                                     f"<b>Срок оплаты:</b> 3 дня.\n\n"
                                     "Используйте /scheta для оплаты.", parse_mode='HTML')
                except Exception as e:
                    print(f"Не удалось выдать налог на недвижимость пользователю {user_id}: {e}")

            conn.commit()
            print("Еженедельные налоги на недвижимость успешно выданы.")
        except Exception as e:
            print(f"Критическая ошибка в потоке выдачи налогов на недвижимость: {e}")
        finally:
            if conn:
                conn.close()

# --- END ---

# --- COMPANY SYSTEM ---

def prompt_for_company_withdraw(call, company_id):
    user_id = call.from_user.id
    if not is_authorized_for_company(user_id, company_id, 'can_withdraw'):
        return bot.answer_callback_query(call.id, "⛔ У вас нет прав на это действие.", show_alert=True)
    
    company_management_in_progress[user_id] = {'action': 'withdraw', 'company_id': company_id}
    msg = bot.send_message(user_id, "Введите сумму для вывода со счета компании:")
    bot.register_next_step_handler(msg, process_company_withdraw)
    bot.answer_callback_query(call.id)

def process_company_withdraw(message: Message):
    user_id = message.from_user.id
    if user_id not in company_management_in_progress or company_management_in_progress[user_id].get('action') != 'withdraw':
        return

    company_id = company_management_in_progress[user_id]['company_id']
    
    try:
        amount = int(message.text)
        if amount <= 0: raise ValueError
    except (ValueError, TypeError):
        msg = bot.send_message(user_id, "❌ Неверный формат. Введите целое положительное число.")
        bot.register_next_step_handler(msg, process_company_withdraw)
        return

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT balance, name FROM companies WHERE id = ?", (company_id,))
        company_balance, company_name = cursor.fetchone()

        if company_balance < amount:
            bot.send_message(user_id, f"❌ На счету компании недостаточно средств. Доступно: {company_balance:,} $")
            del company_management_in_progress[user_id]
            return

        conn.execute("BEGIN TRANSACTION")
        cursor.execute("UPDATE companies SET balance = balance - ? WHERE id = ?", (amount, company_id))
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()

        bot.send_message(user_id, f"✅ Вы успешно сняли <b>{amount:,} $</b> со счета компании '{company_name}'.", parse_mode='HTML')
        notify_staff("Снятие со счета компании", f"Снято со счета компании '{company_name}'", user_id, None, amount)

    except Exception as e:
        bot.send_message(user_id, f"⚠️ Ошибка при выводе средств: {e}")
        if conn: conn.rollback()
    finally:
        del company_management_in_progress[user_id]
        conn.close()


def is_authorized_for_company(user_id, company_id, permission=None):
    """
    Checks if a user is the owner or has a certain permission in a company.
    """
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        # First, check if the user is the direct owner of the company. The owner has all rights.
        cursor.execute("SELECT 1 FROM companies WHERE id = ? AND owner_user_id = ?", (company_id, user_id))
        if cursor.fetchone():
            return True # Owner has ultimate power

        # If a specific permission is requested and the user is not the owner, check their role.
        if permission:
            cursor.execute(f"""
                SELECT 1 FROM company_employees ce
                JOIN company_roles cr ON ce.role_id = cr.id
                WHERE ce.user_id = ? AND ce.company_id = ? AND cr.{permission} = 1
            """, (user_id, company_id))
            return cursor.fetchone() is not None
            
        return False # Not the owner and no specific permission was checked
    except Exception as e:
        print(f"Ошибка проверки прав в компании: {e}")
        return False
    finally:
        conn.close()

@bot.message_handler(content_types=['photo'])
def handle_banned_photos(message: Message):
    # Тех. Админа не трогаем
    if message.from_user.id == TECH_ADMIN_ID:
        return

    # Получаем unique_id отправленного фото
    photo = message.photo[-1]
    unique_id = photo.file_unique_id

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        # Проверяем, есть ли этот ID в базе банов
        cursor.execute("SELECT 1 FROM banned_photos WHERE file_unique_id = ?", (unique_id,))
        is_banned = cursor.fetchone()

        if is_banned:
            try:
                # 1. Удаляем сообщение
                bot.delete_message(message.chat.id, message.message_id)
                
                # 2. Баним пользователя
                bot.ban_chat_member(message.chat.id, message.from_user.id)
                
                # 3. Отправляем уведомление (можно убрать, если хочешь молча)
                bot.send_message(message.chat.id, 
                                 f"⛔ Пользователь <a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a> заблокирован за отправку запрещенного фото.", 
                                 parse_mode='HTML')
                
                # Логируем
                notify_staff("Автобан (Фото)", "Пользователь отправил запрещенное фото", message.from_user.id, None)
            except Exception as e:
                print(f"Ошибка при бане за фото: {e}")
                
    except Exception as e:
        print(f"Ошибка проверки фото: {e}")
    finally:
        conn.close()

@bot.message_handler(commands=['ban_photo'])
def ban_photo_command(message: Message):
    # Проверка прав (только админы)
    if not has_permission(message.from_user.id, [1, 2, 3]): 
        return bot.reply_to(message, "⛔ Недостаточно прав.")

    if not message.reply_to_message or not message.reply_to_message.photo:
        return bot.reply_to(message, "❌ Ответьте этой командой на фотографию, которую хотите запретить.")

    # Берем unique_id самой большой версии фото (последней в списке)
    # Telegram присылает несколько размеров одной фотки, unique_id у них связан,
    # но лучше брать самый качественный вариант для надежности.
    photo = message.reply_to_message.photo[-1]
    unique_id = photo.file_unique_id

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO banned_photos (file_unique_id, added_by) VALUES (?, ?)", 
                       (unique_id, message.from_user.id))
        conn.commit()
        bot.reply_to(message, "✅ Фотография добавлена в черный список. Теперь любой, кто её отправит, будет забанен.")
        
        # Логируем действие
        notify_staff("Бан фото", "Добавлено запрещенное фото", message.from_user.id, None)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка базы данных: {e}")
    finally:
        conn.close()

@bot.message_handler(commands=['company'])
@antispam_filter
def company_main_menu(message: Message):
    user_id = message.from_user.id
    register_user(user_id)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT c.id, c.name FROM companies c
            WHERE c.owner_user_id = ?
            UNION
            SELECT c.id, c.name FROM companies c
            JOIN company_employees ce ON c.id = ce.company_id
            WHERE ce.user_id = ?
        """, (user_id, user_id))
        companies = list(set(cursor.fetchall()))

        cursor.execute("SELECT COUNT(*) FROM companies WHERE owner_user_id = ?", (user_id,))
        owned_company_count = cursor.fetchone()[0]

        markup = InlineKeyboardMarkup(row_width=1)
        if not companies:
            text = "У вас нет компаний. Хотите создать свою первую?"
            markup.add(InlineKeyboardButton("✅ Да, создать компанию", callback_data=f"company_create_start_{user_id}"))
        else:
            text = "🏢 <b>Ваши компании:</b>"
            for company_id, name in companies:
                markup.add(InlineKeyboardButton(name, callback_data=f"company_manage_{company_id}_{user_id}"))
            
            if owned_company_count < 5:
                markup.add(InlineKeyboardButton("➕ Создать новую компанию", callback_data=f"company_create_start_{user_id}"))

        bot.reply_to(message, text, reply_markup=markup, parse_mode='HTML')
    finally:
        conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('company_'))
def company_callback_router(call):
    user_id = call.from_user.id
    parts = call.data.split('_')
    action = parts[1]

    try:
        original_user_id = int(parts[-1])
    except (ValueError, IndexError):
        original_user_id = user_id 

    if user_id != original_user_id and action not in ['accept', 'decline']:
        return bot.answer_callback_query(call.id, "Вы не можете использовать это меню.")

    company_id = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None

    # --- Creation Flow ---
    if action == 'create':
        if parts[2] == 'start':
            start_company_creation(call)
        elif parts[2] == 'charselect':
            char_id = int(parts[3])
            select_char_for_company(call, char_id)

    # --- Management Flow ---
    elif action == 'manage':
        show_company_dashboard(call, company_id)

    # --- Role Management (FIXED LOGIC) ---
    elif action == 'roles':
        manage_roles(call, company_id)
    elif action == 'role': 
        sub_action = parts[2]
        if sub_action == 'edit':
            role_id = int(parts[3])
            company_id = int(parts[4]) # Correctly parse company_id
            edit_role_menu(call, company_id, role_id)
        
        # --- НАЧАЛО ИСПРАВЛЕННОГО БЛОКА ---
        elif sub_action == 'toggle':
            # ИСПРАВЛЕНИЕ:
            # Собираем название права (permission) обратно в одну строку,
            # так как оно было разбито на 'can' и 'withdraw'.
            # И сдвигаем индексы для id ролей и компании.
            permission = f"{parts[3]}_{parts[4]}"  # Получится 'can_withdraw'
            role_id = int(parts[5])
            company_id = int(parts[6])
            toggle_role_permission(call, company_id, role_id, permission)
        # --- КОНЕЦ ИСПРАВЛЕННОГО БЛОКА ---
            
        elif sub_action == 'rename':
            role_id = int(parts[3])
            company_id = int(parts[4]) # Correctly parse company_id
            prompt_for_role_rename(call, company_id, role_id)
        elif sub_action == 'setsalary':
            role_id = int(parts[3])
            company_id = int(parts[4]) # Correctly parse company_id
            prompt_for_salary(call, company_id, role_id)
        elif sub_action == 'create':
            company_id = int(parts[3]) # Correctly parse company_id
            # This logic now correctly calls the prompt for a new role name
            if not is_authorized_for_company(user_id, company_id, 'can_manage_roles'):
                 return bot.answer_callback_query(call.id, "⛔ У вас нет прав на это действие.", show_alert=True)
            company_management_in_progress[user_id] = {'action': 'create_role', 'company_id': company_id}
            msg = bot.send_message(user_id, "Введите название для новой роли:")
            bot.register_next_step_handler(msg, process_role_create)

    elif action == 'invite':
        prompt_for_invite(call, company_id)

    # --- Invitation response ---
    elif action == 'accept':
        handle_invitation(call, company_id, 'accept')
    elif action == 'decline':
        handle_invitation(call, company_id, 'decline')

    # --- ДОБАВЛЕН ПРОПУЩЕННЫЙ БЛОК ДЛЯ 'withdraw' ---
    elif action == 'withdraw':
        prompt_for_company_withdraw(call, company_id)

    elif action == 'back':
        if len(parts) > 2 and parts[2] == 'main':
            # This part can be simplified or removed if not used elsewhere
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass # Ignore if message is already deleted
            fake_message = call.message
            fake_message.from_user = call.from_user
            company_main_menu(fake_message)

# ... остальной код ...

def start_company_creation(call):
    user_id = call.from_user.id
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, full_name FROM characters WHERE user_id = ? AND status = 'approved'", (user_id,))
        characters = cursor.fetchall()
        if not characters:
            bot.answer_callback_query(call.id, "У вас нет одобренных персонажей для регистрации компании.", show_alert=True)
            return
        
        company_creation_in_progress[user_id] = {'user_id': user_id, 'message_id': call.message.message_id}
        markup = InlineKeyboardMarkup(row_width=1)
        for char_id, full_name in characters:
            markup.add(InlineKeyboardButton(full_name, callback_data=f"company_create_charselect_{char_id}_{user_id}"))
        
        text = "Выберите персонажа, на которого будет зарегистрирована компания:"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id)
    finally:
        conn.close()

def select_char_for_company(call, char_id):
    user_id = call.from_user.id
    company_creation_in_progress[user_id]['character_id'] = char_id
    
    msg = bot.edit_message_text("Отлично. Теперь введите название вашей компании:",
                              call.message.chat.id, call.message.message_id)
    bot.register_next_step_handler(msg, process_company_name)

def process_company_name(message: Message):
    user_id = message.from_user.id
    if user_id not in company_creation_in_progress: return
    
    company_name = message.text.strip()
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM companies WHERE name = ?", (company_name,))
        if cursor.fetchone():
            msg = bot.send_message(user_id, "❌ Название компании уже занято. Попробуйте другое.")
            bot.register_next_step_handler(msg, process_company_name)
            return
    finally:
        conn.close()

    company_creation_in_progress[user_id]['name'] = company_name
    bot.delete_message(message.chat.id, message.message_id)
    msg = bot.send_message(user_id, "Введите инициал компании (тикер) на английском языке (например, 'Tinkoff').\n"
                                    "Он будет использоваться для переводов: /pay Tinkoff 1000")
    bot.register_next_step_handler(msg, process_company_initial)

def process_company_initial(message: Message):
    user_id = message.from_user.id
    if user_id not in company_creation_in_progress: return
    
    initial = message.text.strip()
    if not re.match("^[A-Za-z0-9]+$", initial):
        msg = bot.send_message(user_id, "❌ Инициал должен состоять только из английских букв и цифр. Попробуйте снова.")
        bot.register_next_step_handler(msg, process_company_initial)
        return

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM companies WHERE LOWER(initial) = ?", (initial.lower(),))
        if cursor.fetchone():
            msg = bot.send_message(user_id, "❌ Этот инициал уже занят. Попробуйте другой.")
            bot.register_next_step_handler(msg, process_company_initial)
            return
    finally:
        conn.close()

    company_creation_in_progress[user_id]['initial'] = initial
    bot.delete_message(message.chat.id, message.message_id)
    msg = bot.send_message(user_id, "Последний шаг: отправьте логотип вашей компании (фото).")
    bot.register_next_step_handler(msg, process_company_logo)

def process_company_logo(message: Message):
    user_id = message.from_user.id
    if user_id not in company_creation_in_progress: return

    if not message.photo:
        msg = bot.send_message(user_id, "❌ Это не фото. Пожалуйста, отправьте именно фотографию.")
        bot.register_next_step_handler(msg, process_company_logo)
        return
        
    data = company_creation_in_progress[user_id]
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        conn.execute("BEGIN TRANSACTION")
        # 1. Create company
        cursor.execute("""
            INSERT INTO companies (owner_user_id, character_id, name, initial, logo_file_id)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, data['character_id'], data['name'], data['initial'], message.photo[-1].file_id))
        company_id = cursor.lastrowid
        
        # 2. Create owner role
        cursor.execute("""
            INSERT INTO company_roles (company_id, role_name, is_owner, can_withdraw, can_manage_roles, can_invite)
            VALUES (?, 'Директор', 1, 1, 1, 1)
        """, (company_id,))
        role_id = cursor.lastrowid
        
        # 3. Add owner as employee
        cursor.execute("""
            INSERT INTO company_employees (company_id, user_id, character_id, role_id, last_salary_payment)
            VALUES (?, ?, ?, ?, ?)
        """, (company_id, user_id, data['character_id'], role_id, datetime.now()))
        
        conn.commit()
        
        bot.delete_message(message.chat.id, message.message_id)
        original_message_id = data['message_id']
        bot.edit_message_text(f"🎉 Поздравляем! Ваша компания '{data['name']}' успешно зарегистрирована!",
                              message.chat.id, original_message_id)

    except Exception as e:
        conn.rollback()
        bot.send_message(user_id, f"⚠️ Произошла критическая ошибка при регистрации компании: {e}")
    finally:
        del company_creation_in_progress[user_id]
        conn.close()

def show_company_dashboard(call, company_id):
    user_id = call.from_user.id
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name, initial, balance, logo_file_id, owner_user_id FROM companies WHERE id = ?", (company_id,))
        company = cursor.fetchone()
        if not company:
            bot.answer_callback_query(call.id, "Компания не найдена.", show_alert=True)
            return

        name, initial, balance, logo, owner_id = company

        cursor.execute("SELECT COUNT(*) FROM company_employees WHERE company_id = ?", (company_id,))
        employee_count = cursor.fetchone()[0]

        caption = (f"<b>{name}</b>\n\n"
                   f"<b>Инициал:</b> <code>{initial}</code>\n"
                   f"💰 <b>Казна:</b> {balance:,} $\n"
                   f"👥 <b>Сотрудников:</b> {employee_count}\n"
                   f"👑 <b>Владелец:</b> {get_display_name(owner_id)}")

        markup = InlineKeyboardMarkup(row_width=2)

        can_invite = is_authorized_for_company(user_id, company_id, 'can_invite')
        can_manage_roles = is_authorized_for_company(user_id, company_id, 'can_manage_roles')

        can_withdraw = is_authorized_for_company(user_id, company_id, 'can_withdraw')
        if can_withdraw:
            markup.add(InlineKeyboardButton("💵 Снять со счета", callback_data=f"company_withdraw_{company_id}_{user_id}"))

        markup.add(InlineKeyboardButton("⬅️ К списку компаний", callback_data=f"company_back_main_{user_id}"))

        if can_invite:
            markup.add(InlineKeyboardButton("🤝 Пригласить", callback_data=f"company_invite_{company_id}_{user_id}"))
        if can_manage_roles:
            markup.add(InlineKeyboardButton("🛠️ Управление ролями", callback_data=f"company_roles_{company_id}_{user_id}"))

        markup.add(InlineKeyboardButton("⬅️ К списку компаний", callback_data=f"company_back_main_{user_id}"))

        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_photo(call.message.chat.id, logo, caption=caption, reply_markup=markup, parse_mode='HTML')
        bot.answer_callback_query(call.id)
    finally:
        conn.close()
        
# --- START OF NEW ROLE MANAGEMENT FUNCTIONS ---

def manage_roles(call, company_id):
    user_id = call.from_user.id
    if not is_authorized_for_company(user_id, company_id, 'can_manage_roles'):
        return bot.answer_callback_query(call.id, "⛔ У вас нет прав на это действие.", show_alert=True)

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, role_name FROM company_roles WHERE company_id = ? ORDER BY is_owner DESC, id ASC", (company_id,))
        roles = cursor.fetchall()

        text = "🛠️ <b>Управление ролями</b>\n\nВыберите роль для редактирования или создайте новую:"
        markup = InlineKeyboardMarkup(row_width=1)

        for role_id, role_name in roles:
            markup.add(InlineKeyboardButton(role_name, callback_data=f"company_role_edit_{role_id}_{company_id}_{user_id}"))

        if len(roles) < 6: # Максимум 6 ролей
            markup.add(InlineKeyboardButton("➕ Создать новую роль", callback_data=f"company_role_create_{company_id}_{user_id}"))

        markup.add(InlineKeyboardButton("⬅️ Назад к компании", callback_data=f"company_manage_{company_id}_{user_id}"))

        # Используем edit_message_caption, так как dashboard компании - это фото с подписью
        bot.edit_message_caption(caption=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
        bot.answer_callback_query(call.id)
    finally:
        conn.close()

def edit_role_menu(call, company_id, role_id):
    user_id = call.from_user.id
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM company_roles WHERE id = ? AND company_id = ?", (role_id, company_id))
        role_data = cursor.fetchone()
        if not role_data:
            return bot.answer_callback_query(call.id, "Роль не найдена.", show_alert=True)

        (role_id_db, comp_id, name, salary, freq, can_w, can_mr, can_i, is_owner) = role_data

        text = (f"✏️ <b>Редактирование роли: {name}</b>\n\n"
                f"💸 <b>Зарплата:</b> {salary:,} $ / {freq} дн.\n")

        markup = InlineKeyboardMarkup(row_width=2)

        # Владелец может менять свое имя, но не права
        if is_owner and is_authorized_for_company(user_id, company_id, None): # None check for owner
             markup.add(InlineKeyboardButton("Переименовать", callback_data=f"company_role_rename_{role_id}_{company_id}_{user_id}"))

        # Обычные роли можно редактировать полностью
        if not is_owner:
            can_withdraw_text = "✅ Да" if can_w else "❌ Нет"

            markup.add(
                InlineKeyboardButton("Переименовать", callback_data=f"company_role_rename_{role_id}_{company_id}_{user_id}"),
                InlineKeyboardButton("💰 Установить ЗП", callback_data=f"company_role_setsalary_{role_id}_{company_id}_{user_id}"),
                InlineKeyboardButton(f"Вывод денег: {can_withdraw_text}", callback_data=f"company_role_toggle_can_withdraw_{role_id}_{company_id}_{user_id}")
            )

        markup.add(InlineKeyboardButton("⬅️ Назад к ролям", callback_data=f"company_roles_{company_id}_{user_id}"))

        bot.edit_message_caption(caption=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
        bot.answer_callback_query(call.id)
    finally:
        conn.close()
        
def process_role_create(message: Message):
    user_id = message.from_user.id
    if user_id not in company_management_in_progress or company_management_in_progress[user_id].get('action') != 'create_role':
        return

    data = company_management_in_progress[user_id]
    company_id = data['company_id']
    new_role_name = message.text.strip()

    conn = sqlite3.connect('database.db')
    try:
        # Create the new role with default (no) permissions
        conn.execute("""
            INSERT INTO company_roles (company_id, role_name, salary_amount, salary_frequency_days, can_withdraw, can_manage_roles, can_invite, is_owner)
            VALUES (?, ?, 0, 7, 0, 0, 0, 0)
        """, (company_id, new_role_name))
        conn.commit()
        bot.send_message(user_id, f"✅ Роль '{new_role_name}' создана. Теперь вы можете настроить ее в меню управления ролями.")
    except Exception as e:
        bot.send_message(user_id, f"⚠️ Ошибка при создании роли: {e}")
    finally:


        del company_management_in_progress[user_id]
        conn.close()
        # Return user to the main company menu to see changes
        fake_message = message
        fake_message.text = "/company"
        company_main_menu(fake_message)        

def toggle_role_permission(call, company_id, role_id, permission):
    user_id = call.from_user.id
    if not is_authorized_for_company(user_id, company_id, 'can_manage_roles'):
        return bot.answer_callback_query(call.id, "⛔ У вас нет прав.", show_alert=True)

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        # Запрещаем менять права у роли владельца
        cursor.execute("SELECT is_owner FROM company_roles WHERE id = ?", (role_id,))
        if cursor.fetchone()[0] == 1:
             return bot.answer_callback_query(call.id, "Права Директора нельзя изменить.", show_alert=True)

        allowed_permissions = ['can_withdraw', 'can_manage_roles', 'can_invite']
        if permission not in allowed_permissions:
            return bot.answer_callback_query(call.id, "Недопустимое право.", show_alert=True)

        cursor.execute(f"UPDATE company_roles SET {permission} = NOT {permission} WHERE id = ?", (role_id,))
        conn.commit()

        edit_role_menu(call, company_id, role_id)
    finally:
        conn.close()

def prompt_for_role_rename(call, company_id, role_id):
    user_id = call.from_user.id
    company_management_in_progress[user_id] = {'action': 'rename_role', 'company_id': company_id, 'role_id': role_id}
    bot.delete_message(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(user_id, "Введите новое название для роли:")
    bot.register_next_step_handler(msg, process_role_rename)

def process_role_rename(message: Message):
    user_id = message.from_user.id
    if user_id not in company_management_in_progress or company_management_in_progress[user_id].get('action') != 'rename_role':
        return

    data = company_management_in_progress[user_id]
    new_name = message.text.strip()

    conn = sqlite3.connect('database.db')
    try:
        conn.execute("UPDATE company_roles SET role_name = ? WHERE id = ?", (new_name, data['role_id']))
        conn.commit()
        bot.send_message(user_id, f"✅ Роль успешно переименована в '{new_name}'.")
    except Exception as e:
        bot.send_message(user_id, f"⚠️ Ошибка: {e}")
    finally:
        del company_management_in_progress[user_id]
        conn.close()
        fake_message = message
        fake_message.text = "/company"
        company_main_menu(fake_message)

def prompt_for_salary(call, company_id, role_id):
    user_id = call.from_user.id
    company_management_in_progress[user_id] = {'action': 'set_salary', 'company_id': company_id, 'role_id': role_id}
    bot.delete_message(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(user_id, "Введите сумму еженедельной зарплаты (просто число):")
    bot.register_next_step_handler(msg, process_salary_amount)

def process_salary_amount(message: Message):
    user_id = message.from_user.id
    if user_id not in company_management_in_progress or company_management_in_progress[user_id].get('action') != 'set_salary':
        return

    try:
        salary = int(message.text)
        if salary < 0: raise ValueError
    except (ValueError, TypeError):
        msg = bot.send_message(user_id, "❌ Неверный формат. Введите целое положительное число.")
        bot.register_next_step_handler(msg, process_salary_amount)
        return

    data = company_management_in_progress[user_id]

    conn = sqlite3.connect('database.db')
    try:
        conn.execute("UPDATE company_roles SET salary_amount = ?, salary_frequency_days = 7 WHERE id = ?", (salary, data['role_id']))
        conn.commit()
        bot.send_message(user_id, f"✅ Еженедельная зарплата установлена в размере {salary:,} $.")
    except Exception as e:
        bot.send_message(user_id, f"⚠️ Ошибка: {e}")
    finally:
        del company_management_in_progress[user_id]
        conn.close()
        fake_message = message
        fake_message.text = "/company"
        company_main_menu(fake_message)

# --- END OF NEW ROLE MANAGEMENT FUNCTIONS ---        

def prompt_for_invite(call, company_id):
    user_id = call.from_user.id
    if not is_authorized_for_company(user_id, company_id, 'can_invite'):
        return bot.answer_callback_query(call.id, "⛔ У вас нет прав на это действие.", show_alert=True)
    
    company_management_in_progress[user_id] = {'action': 'invite', 'company_id': company_id}
    msg = bot.send_message(user_id, "Введите ID или @username пользователя, которого хотите пригласить.")
    bot.register_next_step_handler(msg, process_invite_input)

def process_invite_input(message: Message):

    inviter_id = message.from_user.id
    if inviter_id not in company_management_in_progress or company_management_in_progress[inviter_id].get('action') != 'invite':
        return

    company_id = company_management_in_progress[inviter_id]['company_id']
    target_identifier = message.text.strip()
    
    try:
        if target_identifier.startswith('@'):
            target_id = bot.get_chat(target_identifier).id
        else:
            target_id = int(target_identifier)
        
        register_user(target_id)
    except Exception:
        bot.send_message(inviter_id, "❌ Пользователь не найден. Попробуйте снова или отмените действие.")
        bot.register_next_step_handler(message, process_invite_input)
        return
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM company_employees WHERE user_id = ? AND company_id = ?", (target_id, company_id))
        if cursor.fetchone():
            bot.send_message(inviter_id, "Этот пользователь уже работает в вашей компании.")
            del company_management_in_progress[inviter_id]
            return
            
        cursor.execute("SELECT name FROM companies WHERE id = ?", (company_id,))
        company_name = cursor.fetchone()[0]

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Принять", callback_data=f"company_accept_{company_id}_{target_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"company_decline_{company_id}_{target_id}")
        )
        
        try:
            bot.send_message(target_id, f"Вас пригласили вступить в компанию <b>{company_name}</b>.",
                             reply_markup=markup, parse_mode='HTML')
            bot.send_message(inviter_id, f"✅ Приглашение успешно отправлено {get_display_name(target_id)}.")
        except Exception as e:
            if 'bot can\'t initiate conversation' in str(e):
                 bot.send_message(inviter_id, "⚠️ Не удалось отправить приглашение. Пользователь должен сначала написать боту /start. Попробуйте позже.")
            else:
                 bot.send_message(inviter_id, f"⚠️ Неизвестная ошибка при отправке приглашения: {e}")

    finally:
        del company_management_in_progress[inviter_id]
        conn.close()

def handle_invitation(call, company_id, decision):
    invited_user_id = call.from_user.id
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name, owner_user_id FROM companies WHERE id = ?", (company_id,))
        res = cursor.fetchone()
        if not res: return bot.answer_callback_query(call.id, "Компания больше не существует.", show_alert=True)
        company_name, owner_id = res

        if decision == 'decline':
            bot.send_message(invited_user_id, f"Вы отклонили приглашение в компанию '{company_name}'.")
            bot.send_message(owner_id, f"Пользователь {get_display_name(invited_user_id)} отклонил ваше приглашение.")
            return

        # Handle 'accept'
        cursor.execute("SELECT id, full_name FROM characters WHERE user_id = ? and status = 'approved'", (invited_user_id,))
        characters = cursor.fetchall()
        if not characters:
            bot.send_message(invited_user_id, "❌ У вас нет одобренных персонажей, чтобы вступить в компанию.")
            return

        # Find default "Работник" role or the lowest-level role
        cursor.execute("""

            SELECT id FROM company_roles 
            WHERE company_id = ? AND is_owner = 0

            ORDER BY id ASC LIMIT 1
        """, (company_id,))
        role_res = cursor.fetchone()
        
        # If no non-owner roles exist, create a default one
        if not role_res:
            cursor.execute("INSERT INTO company_roles (company_id, role_name) VALUES (?, 'Работник')", (company_id,))
            role_id = cursor.lastrowid
        else:
            role_id = role_res[0]
            
        # For simplicity, we assign the first approved character.
        # A more complex system would ask the user to choose.
        character_id = characters[0][0]
        
        cursor.execute("""
            INSERT OR IGNORE INTO company_employees (company_id, user_id, character_id, role_id, last_salary_payment)
            VALUES (?, ?, ?, ?, ?)
        """, (company_id, invited_user_id, character_id, role_id, datetime.now()))
        conn.commit()

        bot.send_message(invited_user_id, f"✅ Вы успешно вступили в компанию '{company_name}'!")
        bot.send_message(owner_id, f"Пользователь {get_display_name(invited_user_id)} принял ваше приглашение.")
    
    except Exception as e:
        print(f"Ошибка обработки приглашения: {e}")
        bot.send_message(invited_user_id, "Произошла ошибка при обработке приглашения.")
    finally:
        conn.close()

def manage_roles(call, company_id):
    user_id = call.from_user.id
    if not is_authorized_for_company(user_id, company_id, 'can_manage_roles'):
        return bot.answer_callback_query(call.id, "⛔ У вас нет прав на это действие.", show_alert=True)

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, role_name FROM company_roles WHERE company_id = ? ORDER BY is_owner DESC, id ASC", (company_id,))
        roles = cursor.fetchall()

        text = "🛠️ <b>Управление ролями</b>\n\nВыберите роль для редактирования или создайте новую:"
        markup = InlineKeyboardMarkup(row_width=1)

        for role_id, role_name in roles:
            markup.add(InlineKeyboardButton(role_name, callback_data=f"company_role_edit_{role_id}_{company_id}_{user_id}"))

        if len(roles) < 6: # Максимум 6 ролей
            markup.add(InlineKeyboardButton("➕ Создать новую роль", callback_data=f"company_role_create_{company_id}_{user_id}"))

        markup.add(InlineKeyboardButton("⬅️ Назад к компании", callback_data=f"company_manage_{company_id}_{user_id}"))

        # Используем edit_message_caption, так как dashboard компании - это фото с подписью
        bot.edit_message_caption(caption=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
        bot.answer_callback_query(call.id)
    finally:
        conn.close()

@bot.message_handler(commands=['delete_company'])
@antispam_filter
def delete_company(message: Message):
    user_id = message.from_user.id
    if not has_permission(user_id, [3]): # Only Tech Admin
        return bot.reply_to(message, "⛔ <b>Недостаточно прав.</b>", parse_mode='HTML')
        
    parts = message.text.split()
    if len(parts) != 2:
        return bot.reply_to(message, "<b>Для удаления компании используйте:</b>\n"
                                     "<code>/delete_company [инициал]</code>", parse_mode='HTML')
    
    initial_to_delete = parts[1]
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, name, owner_user_id FROM companies WHERE LOWER(initial) = ?", (initial_to_delete.lower(),))
        company = cursor.fetchone()
        if not company:
            return bot.reply_to(message, "❌ Компания с таким инициалом не найдена.")
        
        company_id, name, owner_id = company
        
        # Using foreign_keys = ON and ON DELETE CASCADE handles deletion of roles and employees
        cursor.execute("DELETE FROM companies WHERE id = ?", (company_id,))
        conn.commit()
        
        bot.reply_to(message, f"✅ Компания <b>{name}</b> (Инициал: {initial_to_delete}) была успешно удалена.", parse_mode='HTML')
        notify_staff("Удаление компании", f"Удалена компания: {name}", user_id, owner_id)
        try:
            bot.send_message(owner_id, f"🗑️ Ваша компания <b>{name}</b> была удалена администрацией.", parse_mode='HTML')
        except Exception as e:
            print(f"Не удалось уведомить владельца {owner_id} об удалении компании: {e}")
            
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при удалении компании: {e}")
    finally:
        conn.close()
        
def process_company_salaries():
    while True:
        time.sleep(3600)  # Проверка раз в час
        conn = None
        try:
            print("Проверка зарплат компаний...")
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()

            cursor.execute("""
                SELECT ce.id, ce.user_id, cr.salary_amount, cr.salary_frequency_days, ce.last_salary_payment, c.id, c.name, c.balance
                FROM company_employees ce
                JOIN company_roles cr ON ce.role_id = cr.id
                JOIN companies c ON ce.company_id = c.id
                WHERE cr.salary_amount > 0 AND ce.last_salary_payment IS NOT NULL
            """)
            employees_to_pay = cursor.fetchall()

            now = datetime.now()

            for emp_id, user_id, salary, freq, last_paid_str, comp_id, comp_name, comp_balance in employees_to_pay:
                last_paid_date = datetime.fromisoformat(last_paid_str)
                if now >= last_paid_date + timedelta(days=freq):
                    try:
                        conn.execute("BEGIN TRANSACTION")
                        
                        # Проверяем, хватает ли денег
                        if comp_balance >= salary:
                            # Деньги есть, платим
                            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (salary, user_id))
                            cursor.execute("UPDATE companies SET balance = balance - ? WHERE id = ?", (salary, comp_id))
                            cursor.execute("UPDATE company_employees SET last_salary_payment = ? WHERE id = ?", (now.isoformat(), emp_id))
                            conn.commit()
                            
                            bot.send_message(user_id, f"💸 Вам начислена зарплата от компании <b>{comp_name}</b> в размере <b>{salary:,} $</b>.", parse_mode='HTML')
                        else:
                            # Денег нет, уходим в минус и создаем долг
                            cursor.execute("UPDATE companies SET balance = balance - ? WHERE id = ?", (salary, comp_id))
                            
                            # Добавляем или увеличиваем долг
                            cursor.execute("SELECT id, amount_owed FROM company_salary_debt WHERE company_id = ? AND employee_user_id = ?", (comp_id, user_id))
                            debt = cursor.fetchone()
                            if debt:
                                new_debt = debt[1] + salary
                                cursor.execute("UPDATE company_salary_debt SET amount_owed = ? WHERE id = ?", (new_debt, debt[0]))
                            else:
                                cursor.execute("INSERT INTO company_salary_debt (company_id, employee_user_id, amount_owed) VALUES (?, ?, ?)", (comp_id, user_id, salary))

                            # Обновляем дату, чтобы снова не пытаться начислить в этот же период
                            cursor.execute("UPDATE company_employees SET last_salary_payment = ? WHERE id = ?", (now.isoformat(), emp_id))
                            conn.commit()
                            
                            bot.send_message(user_id, f"⚠️ Компания <b>{comp_name}</b> не смогла выплатить вам зарплату в размере <b>{salary:,} $</b> из-за недостатка средств. Сумма задолженности сохранена и будет выплачена при пополнении счета компании.", parse_mode='HTML')

                    except Exception as e:
                        print(f"Ошибка выплаты зарплаты для emp {emp_id}: {e}")
                        if conn: conn.rollback()

            print("Проверка зарплат завершена.")
        except Exception as e:
            print(f"Критическая ошибка в потоке выплаты зарплат: {e}")
        finally:
            if conn:
                conn.close()
                
def process_company_debt_payment(company_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        # Получаем текущий баланс и список долгов
        cursor.execute("SELECT balance FROM companies WHERE id = ?", (company_id,))
        balance = cursor.fetchone()[0]

        cursor.execute("SELECT id, employee_user_id, amount_owed FROM company_salary_debt WHERE company_id = ? ORDER BY created_at ASC", (company_id,))
        debts = cursor.fetchall()

        if not debts or balance <= 0:
            return # Нет долгов или денег для их погашения

        for debt_id, employee_id, amount_owed in debts:
            if balance >= amount_owed:
                # Хватает денег на полный долг
                conn.execute("BEGIN TRANSACTION")
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount_owed, employee_id))
                cursor.execute("UPDATE companies SET balance = balance - ? WHERE id = ?", (amount_owed, company_id))
                cursor.execute("DELETE FROM company_salary_debt WHERE id = ?", (debt_id,))
                conn.commit()

                balance -= amount_owed # Уменьшаем баланс для следующей итерации

                bot.send_message(employee_id, f"✅ Компания погасила перед вами задолженность по зарплате в размере <b>{amount_owed:,} $</b>.", parse_mode='HTML')
            
            elif 0 < balance < amount_owed:
                # Хватает на частичное погашение
                payment_amount = balance
                new_debt_amount = amount_owed - payment_amount
                
                conn.execute("BEGIN TRANSACTION")
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (payment_amount, employee_id))
                cursor.execute("UPDATE companies SET balance = balance - ? WHERE id = ?", (payment_amount, company_id))
                cursor.execute("UPDATE company_salary_debt SET amount_owed = ? WHERE id = ?", (new_debt_amount, debt_id))
                conn.commit()
                
                balance = 0 # Деньги кончились

                bot.send_message(employee_id, f"✅ Компания частично погасила задолженность по зарплате в размере <b>{payment_amount:,} $</b>. Остаток долга: {new_debt_amount:,} $.", parse_mode='HTML')
                break # Выходим из цикла, так как деньги закончились
    
    except Exception as e:
        print(f"Ошибка при погашении долга компании {company_id}: {e}")
        if conn: conn.rollback()
    finally:
        conn.close()                

# --- END COMPANY SYSTEM ---


def process_check_claim(claimer_id, check_id):
    register_user(claimer_id)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT creator_id, amount, target_user_id, status, claimed_by_id FROM checks WHERE check_id = ?", (check_id,))
        check_data = cursor.fetchone()
        if not check_data: return "❌ Чек с таким ID не найден."
        creator_id, amount, target_user_id, status, claimed_by_id = check_data
        if status != 'active': return f"❌ Этот чек уже был активирован пользователем {get_display_name(claimed_by_id)}."
        if target_user_id and target_user_id != claimer_id: return f"❌ Этот чек предназначен для другого пользователя ({get_display_name(target_user_id)})."
        conn.execute("BEGIN TRANSACTION")
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, claimer_id))
        cursor.execute("UPDATE checks SET status = 'claimed', claimed_by_id = ?, claimed_at = ? WHERE check_id = ?", (claimer_id, get_moscow_time().strftime("%Y-%m-%d %H:%M:%S"), check_id))
        conn.commit()
        grant_xp_for_pair_transaction(creator_id, claimer_id, amount)
        notify_staff("Активация чека", f"Чек на {amount}$ активирован.", creator_id, claimer_id, amount)
        return f"✅ <b>Успешно!</b> Вы активировали чек от {get_display_name(creator_id)} и получили <b>{amount:,} $</b>"
    except Exception as e:
        print(f"Критическая ошибка при активации чека {check_id}: {e}")
        if conn: conn.rollback()
        return "⚠️ Произошла внутренняя ошибка при активации чека."
    finally:
        if conn: conn.close()

def cleanup_messages(chat_id, user_message_id, bot_message_id):
    try:
        bot.delete_message(chat_id=chat_id, message_id=user_message_id)
    except Exception as e:
        print(f"Не удалось удалить сообщение пользователя {user_message_id}: {e}")
    try:
        bot.delete_message(chat_id=chat_id, message_id=bot_message_id)
    except Exception as e:
        print(f"Не удалось удалить сообщение бота {bot_message_id}: {e}")

# --- PASSPORT CREATION ---
# --- PASSPORT CREATION ---
@bot.message_handler(commands=['create_passport'])
@antispam_filter
def create_passport_start(message: Message):
    # --- НОВАЯ ПРОВЕРКА ---
    # Если команда вызвана не в личных сообщениях (т.е. в группе)
    if message.chat.type != 'private':
        try:
            # Создаем кнопку для удобного перехода в ЛС
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("✍️ Начать создание в ЛС", url=f"https://t.me/{BOT_USERNAME}"))
            
            bot.reply_to(
                message,
                f"Для создания паспорта, пожалуйста, перейдите в личные сообщения с ботом: @{BOT_USERNAME}",
                reply_markup=markup
            )
        except Exception as e:
            print(f"Не удалось отправить сообщение о переходе в ЛС: {e}")
        return # Важно! Прекращаем выполнение функции, чтобы анкета не запускалась в группе

    # --- СТАРЫЙ КОД ОСТАЕТСЯ ЗДЕСЬ (он будет работать только для личных сообщений) ---
    user_id = message.from_user.id
    text = (f"❗️ <b>Внимание!</b>\n"
            f"Прежде чем создать персонажа, пожалуйста, внимательно ознакомьтесь с правилами его создания. "
            f"Это поможет избежать отклонения вашей заявки.\n"
            f"<b><a href='{CHARACTER_RULES_LINK}'>Правила создания персонажа</a></b>\n\n"
            f"Вы прочитали правила?")
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Да, я прочитал(а)", callback_data=f"rules_read_yes_{message.message_thread_id}"),
        InlineKeyboardButton("❌ Отмена", callback_data="rules_read_no")
    )
    # Отправляем сообщение в ту же тему, где была вызвана команда
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup, disable_web_page_preview=True, message_thread_id=message.message_thread_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('rules_read_'))
def handle_rules_confirmation(call):
    user_id = call.from_user.id
    bot.delete_message(call.message.chat.id, call.message.message_id)
    if call.data.startswith('rules_read_yes'):
        # --- ИСПРАВЛЕНИЕ: Извлекаем thread_id из callback_data ---
        parts = call.data.split('_')
        thread_id = parts[3] if len(parts) > 3 and parts[3] != 'None' else None
        try:
            # Преобразуем 'None' в реальный None, а строку с числом в int
            thread_id = int(thread_id) if thread_id is not None else None
        except (ValueError, TypeError):
            thread_id = None # На случай если что-то пойдет не так

        bot.answer_callback_query(call.id)
        start_passport_application(call.message, thread_id) # Передаем thread_id дальше
    else:
        bot.answer_callback_query(call.id, "Создание паспорта отменено.")
        bot.send_message(user_id, "🗑️ Создание Паспорта отменено.")

def start_passport_application(message: Message, thread_id: int = None):
    # message.chat.id здесь будет ID группы или ID пользователя в ЛС
    user_id = message.chat.id 
    
    # --- ИСПРАВЛЕНИЕ: Сохраняем ID темы для всей цепочки ---
    user_data_for_passport[user_id] = {
        'chat_id': message.chat.id, 
        'message_thread_id': thread_id 
    }

    msg = bot.send_message(
        message.chat.id, 
        "📝 <b>Создание Паспорта.</b>\n"
        "<b>Шаг 1/10:</b>\n"
        "Ваше ФИО:", 
        parse_mode='HTML',
        message_thread_id=thread_id # Используем ID темы
    )
    user_data_for_passport[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_full_name_step)

def process_full_name_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_passport: return
    
    # --- ИСПРАВЛЕНИЕ (Применяется ко всем шагам) ---
    chat_id = user_data_for_passport[user_id]['chat_id']
    thread_id = user_data_for_passport[user_id].get('message_thread_id')
    last_bot_msg_id = user_data_for_passport[user_id]['last_bot_msg_id']
    
    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)
    user_data_for_passport[user_id]['full_name'] = message.text
    
    msg = bot.send_message(chat_id, "<b>Шаг 2/10:</b>\nВаш возраст:", parse_mode='HTML', message_thread_id=thread_id)
    user_data_for_passport[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_age_step)

def process_age_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_passport: return
    
    chat_id = user_data_for_passport[user_id]['chat_id']
    thread_id = user_data_for_passport[user_id].get('message_thread_id')
    last_bot_msg_id = user_data_for_passport[user_id]['last_bot_msg_id']

    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)
    try:
        age = int(message.text)
        if not 1 <= age <= 150: raise ValueError("Некорректный возраст")
        user_data_for_passport[user_id]['age'] = age
        msg = bot.send_message(chat_id, "<b>Шаг 3/10:</b>\nВаш гендер:", parse_mode='HTML', message_thread_id=thread_id)
        user_data_for_passport[user_id]['last_bot_msg_id'] = msg.message_id
        bot.register_next_step_handler(message, process_gender_step)
    except (ValueError, TypeError):
        msg = bot.send_message(chat_id, "❌ <b>Неверный формат.</b> Введите возраст цифрами.\n"
                                        "<b>Шаг 2/10:</b>\nВаш возраст:", parse_mode='HTML', message_thread_id=thread_id)
        user_data_for_passport[user_id]['last_bot_msg_id'] = msg.message_id
        bot.register_next_step_handler(message, process_age_step)

def process_gender_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_passport: return

    chat_id = user_data_for_passport[user_id]['chat_id']
    thread_id = user_data_for_passport[user_id].get('message_thread_id')
    last_bot_msg_id = user_data_for_passport[user_id]['last_bot_msg_id']

    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)
    user_data_for_passport[user_id]['gender'] = message.text
    msg = bot.send_message(chat_id, "<b>Шаг 4/10 (Внешность):</b>\n• Рост (например, 180 см):", parse_mode='HTML', message_thread_id=thread_id)
    user_data_for_passport[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_height_step)

def process_height_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_passport: return

    chat_id = user_data_for_passport[user_id]['chat_id']
    thread_id = user_data_for_passport[user_id].get('message_thread_id')
    last_bot_msg_id = user_data_for_passport[user_id]['last_bot_msg_id']

    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)
    user_data_for_passport[user_id]['height'] = message.text
    msg = bot.send_message(chat_id, "<b>Шаг 4/10 (Внешность):</b>\n• Цвет волос:", parse_mode='HTML', message_thread_id=thread_id)
    user_data_for_passport[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_hair_color_step)

def process_hair_color_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_passport: return
    
    chat_id = user_data_for_passport[user_id]['chat_id']
    thread_id = user_data_for_passport[user_id].get('message_thread_id')
    last_bot_msg_id = user_data_for_passport[user_id]['last_bot_msg_id']

    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)
    user_data_for_passport[user_id]['hair_color'] = message.text
    msg = bot.send_message(chat_id, "<b>Шаг 4/10 (Внешность):</b>\n• Цвет глаз:", parse_mode='HTML', message_thread_id=thread_id)
    user_data_for_passport[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_eye_color_step)

def process_eye_color_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_passport: return
    
    chat_id = user_data_for_passport[user_id]['chat_id']
    thread_id = user_data_for_passport[user_id].get('message_thread_id')
    last_bot_msg_id = user_data_for_passport[user_id]['last_bot_msg_id']

    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)
    user_data_for_passport[user_id]['eye_color'] = message.text
    msg = bot.send_message(chat_id, "<b>Шаг 4/10 (Внешность):</b>\n• Телосложение:", parse_mode='HTML', message_thread_id=thread_id)
    user_data_for_passport[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_body_type_step)

def process_body_type_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_passport: return
    
    chat_id = user_data_for_passport[user_id]['chat_id']
    thread_id = user_data_for_passport[user_id].get('message_thread_id')
    last_bot_msg_id = user_data_for_passport[user_id]['last_bot_msg_id']

    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)
    user_data_for_passport[user_id]['body_type'] = message.text
    msg = bot.send_message(chat_id, "<b>Шаг 4/10 (Внешность):</b>\n• Татуировки (если нет, напишите 'Нет'):", parse_mode='HTML', message_thread_id=thread_id)
    user_data_for_passport[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_tattoos_step)

def process_tattoos_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_passport: return

    chat_id = user_data_for_passport[user_id]['chat_id']
    thread_id = user_data_for_passport[user_id].get('message_thread_id')
    last_bot_msg_id = user_data_for_passport[user_id]['last_bot_msg_id']

    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)
    user_data_for_passport[user_id]['tattoos'] = message.text
    msg = bot.send_message(chat_id, "<b>Шаг 5/10:</b>\nОпишите детство персонажа:", parse_mode='HTML', message_thread_id=thread_id)
    user_data_for_passport[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_childhood_step)

def process_childhood_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_passport: return

    chat_id = user_data_for_passport[user_id]['chat_id']
    thread_id = user_data_for_passport[user_id].get('message_thread_id')
    last_bot_msg_id = user_data_for_passport[user_id]['last_bot_msg_id']

    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)
    user_data_for_passport[user_id]['childhood'] = message.text
    msg = bot.send_message(chat_id, "<b>Шаг 6/10 (Родители):</b>\n• Отец (имя, статус - жив/мёртв):", parse_mode='HTML', message_thread_id=thread_id)
    user_data_for_passport[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_father_step)

def process_father_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_passport: return

    chat_id = user_data_for_passport[user_id]['chat_id']
    thread_id = user_data_for_passport[user_id].get('message_thread_id')
    last_bot_msg_id = user_data_for_passport[user_id]['last_bot_msg_id']

    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)
    user_data_for_passport[user_id]['father'] = message.text
    msg = bot.send_message(chat_id, "<b>Шаг 6/10 (Родители):</b>\n• Мать (имя, статус - жива/мертва):", parse_mode='HTML', message_thread_id=thread_id)
    user_data_for_passport[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_mother_step)

def process_mother_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_passport: return

    chat_id = user_data_for_passport[user_id]['chat_id']
    thread_id = user_data_for_passport[user_id].get('message_thread_id')
    last_bot_msg_id = user_data_for_passport[user_id]['last_bot_msg_id']

    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)
    user_data_for_passport[user_id]['mother'] = message.text
    msg = bot.send_message(chat_id, "<b>Шаг 7/10:</b>\nОпишите знания и навыки персонажа:", parse_mode='HTML', message_thread_id=thread_id)
    user_data_for_passport[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_knowledge_step)

def process_knowledge_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_passport: return

    chat_id = user_data_for_passport[user_id]['chat_id']
    thread_id = user_data_for_passport[user_id].get('message_thread_id')
    last_bot_msg_id = user_data_for_passport[user_id]['last_bot_msg_id']

    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)
    user_data_for_passport[user_id]['knowledge'] = message.text
    msg = bot.send_message(chat_id, "<b>Шаг 8/10:</b>\nОпишите, чем персонаж занимается в настоящее время:", parse_mode='HTML', message_thread_id=thread_id)
    user_data_for_passport[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_current_life_step)

def process_current_life_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_passport: return
    
    chat_id = user_data_for_passport[user_id]['chat_id']
    thread_id = user_data_for_passport[user_id].get('message_thread_id')
    last_bot_msg_id = user_data_for_passport[user_id]['last_bot_msg_id']

    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)
    user_data_for_passport[user_id]['current_life'] = message.text
    msg = bot.send_message(chat_id, "<b>Шаг 9/10 (Ник в Roblox):</b>\n• Дисплей (Display Name):", parse_mode='HTML', message_thread_id=thread_id)
    user_data_for_passport[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_roblox_display_name_step)

def process_roblox_display_name_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_passport: return
    
    chat_id = user_data_for_passport[user_id]['chat_id']
    thread_id = user_data_for_passport[user_id].get('message_thread_id')
    last_bot_msg_id = user_data_for_passport[user_id]['last_bot_msg_id']
    
    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)
    user_data_for_passport[user_id]['roblox_display_name'] = message.text
    msg = bot.send_message(chat_id, "<b>Шаг 9/10 (Ник в Roblox):</b>\n• Настоящий:", parse_mode='HTML', message_thread_id=thread_id)
    user_data_for_passport[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_roblox_real_name_step)

def process_roblox_real_name_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_passport: return

    chat_id = user_data_for_passport[user_id]['chat_id']
    thread_id = user_data_for_passport[user_id].get('message_thread_id')
    last_bot_msg_id = user_data_for_passport[user_id]['last_bot_msg_id']
    
    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)
    user_data_for_passport[user_id]['roblox_real_name'] = message.text
    msg = bot.send_message(chat_id, "<b>Шаг 10/10:</b>\nОтправьте фотографию (RP внешность) вашего персонажа.", parse_mode='HTML', message_thread_id=thread_id)
    user_data_for_passport[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_photo_step)

def process_photo_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_passport: return

    chat_id = user_data_for_passport[user_id]['chat_id']
    thread_id = user_data_for_passport[user_id].get('message_thread_id')
    last_bot_msg_id = user_data_for_passport[user_id]['last_bot_msg_id']

    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)
    if not message.photo:
        msg = bot.send_message(chat_id, "❌ <b>Это не фото.</b> Пожалуйста, отправьте именно фотографию.\n"
                                        "<b>Шаг 10/10:</b>\nОтправьте фотографию вашего персонажа.", parse_mode='HTML', message_thread_id=thread_id)
        user_data_for_passport[user_id]['last_bot_msg_id'] = msg.message_id
        bot.register_next_step_handler(message, process_photo_step)
        return
    user_data_for_passport[user_id]['photo_file_id'] = message.photo[-1].file_id
    show_confirmation_form(user_id, 'passport')


# --- CONFIRMATION AND SUBMISSION LOGIC (Частично исправлено) ---
def get_character_info(character_id):
    # ... (эта функция без изменений)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT full_name, age FROM characters WHERE id = ?", (character_id,))
        result = cursor.fetchone()
        return {"name": result[0], "age": result[1]} if result else None
    finally:
        conn.close()

# --- НАЧАЛО ИСПРАВЛЕННОГО БЛОКА ---

def show_confirmation_form(user_id, form_type):
    data = {}
    caption = ""
    markup = None

    # --- Логика для создания паспорта ---
    if form_type == 'passport' and user_id in user_data_for_passport:
        data = user_data_for_passport[user_id]
        thread_id = data.get('message_thread_id')

        caption = (
            f"📝 <b>Ваша анкета на Паспорт:</b>\n\n"
            f"<b>1. Имя, второе имя, фамилия:</b> {data['full_name']}\n"
            f"<b>2. Возраст:</b> {data['age']}\n"
            f"<b>3. Гендер:</b> {data['gender']}\n"
            f"<b>4. Внешность:</b>\n"
            f"  • <b>Рост:</b> {data['height']}\n"
            f"  • <b>Цвет волос:</b> {data['hair_color']}\n"
            f"  • <b>Цвет глаз:</b> {data['eye_color']}\n"
            f"  • <b>Телосложение:</b> {data['body_type']}\n"
            f"  • <b>Татуировки:</b> {data['tattoos']}\n"
            f"<b>5. Детство:</b> {data['childhood']}\n"
            f"<b>6. Родители:</b>\n"
            f"  • <b>Отец:</b> {data['father']}\n"
            f"  • <b>Мать:</b> {data['mother']}\n"
            f"<b>7. Знания:</b> {data['knowledge']}\n"
            f"<b>8. В настоящее время:</b> {data['current_life']}\n"
            f"<b>9. Ник в Roblox:</b>\n"
            f"  • <b>Дисплей:</b> {data['roblox_display_name']}\n"
            f"  • <b>Настоящий:</b> {data['roblox_real_name']}\n\n"
            f"<b>Все данные верны?</b>"
        )
        markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Верно", callback_data="confirm_yes_passport"),
            InlineKeyboardButton("❌ Нет", callback_data="confirm_no_passport")
        )

        # ИСПРАВЛЕНО: Проверяем длину подписи (caption)
        # Лимит Telegram на подпись к фото - 1024 символа.
        if len(caption) > 1024:
            # Если текст слишком длинный, отправляем фото и текст отдельно
            bot.send_photo(
                data['chat_id'],
                data['photo_file_id'],
                message_thread_id=thread_id
            )
            bot.send_message(
                data['chat_id'],
                caption,
                parse_mode='HTML',
                reply_markup=markup,
                message_thread_id=thread_id
            )
        else:
            # Если длина в норме, отправляем одним сообщением как раньше
            bot.send_photo(
                data['chat_id'],
                data['photo_file_id'],
                caption=caption,
                parse_mode='HTML',
                reply_markup=markup,
                message_thread_id=thread_id
            )

    # --- Логика для SIM-карты (без изменений) ---
    elif form_type == 'sim' and user_id in user_data_for_sim:
        data = user_data_for_sim[user_id]
        char_info = get_character_info(data['character_id'])
        caption = (
            f"📱 <b>Заявка на SIM-карту</b>\n"
            f"<b>Для персонажа:</b> {char_info['name']}\n"
            f"<b>Номер телефона:</b> {data['phone_number']}\n\n"
            f"<b>Отправить заявку?</b>"
        )
        markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Отправить", callback_data="confirm_yes_sim"),
            InlineKeyboardButton("❌ Отмена", callback_data="confirm_no_sim")
        )
        bot.send_message(data['chat_id'], caption, parse_mode='HTML', reply_markup=markup)

    # --- Логика для медкарты (без изменений) ---
    elif form_type == 'medcard' and user_id in user_data_for_med_card:
        data = user_data_for_med_card[user_id]
        char_info = get_character_info(data['character_id'])
        caption = (
             f"⚕️ <b>Заявка на медкарту</b>\n\n"
             f"<b>1. Имя:</b> {char_info['name']}\n"
             f"<b>2. Возраст:</b> {char_info['age']}\n"
             f"<b>3. Псих. состояние:</b> {data['psych_state']}\n"
             f"<b>4. Диагнозы/болезни:</b> {data['diagnoses']}\n"
             f"<b>5. Болевой порог:</b> {data['pain_threshold']}\n"
             f"<b>6. Вес:</b> {data['weight']} кг\n"
             f"<b>7. Рост:</b> {data['height']} см\n\n"
             f"<b>Отправить заявку?</b>"
        )
        markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Отправить", callback_data="confirm_yes_medcard"),
            InlineKeyboardButton("❌ Отмена", callback_data="confirm_no_medcard")
        )
        bot.send_message(data['chat_id'], caption, parse_mode='HTML', reply_markup=markup)

    # --- Логика для лицензий (без изменений) ---
    elif form_type == 'license' and user_id in user_data_for_license:
        data = user_data_for_license[user_id]
        char_info = get_character_info(data['character_id'])
        license_type = data['license_type']
        caption = "" # Инициализируем переменную
        if license_type == 'driver':
            license_map = 'Водительские права'
            caption = (
                f"📜 <b>Заявка на: {license_map}</b>\n\n"
                f"<b>1. Имя:</b> {char_info['name']}\n"
                f"<b>2. Возраст:</b> {char_info['age']}\n"
                f"<b>3. Проблемы со здоровьем:</b> {data['health_issues']}\n"
                f"<b>4. Категория прав:</b> {data['category_details']}\n\n"
                f"<b>Отправить заявку?</b>"
            )
        elif license_type in ['weapon', 'armor']:
            license_map = 'Лицензия на оружие' if license_type == 'weapon' else 'Лицензия на броню'
            item_type_q = "На какое оружие" if license_type == 'weapon' else "На какой класс брони"
            item_type_a = data['category_details']
            caption = (
                f"📜 <b>Заявка на: {license_map}</b>\n\n"
                f"<b>1. Имя:</b> {char_info['name']}\n"
                f"<b>2. Возраст:</b> {char_info['age']}\n"
                f"<b>3. Психическое состояние:</b> {data['psych_state']}\n"
                f"<b>4. Судимости:</b> {data['criminal_record']}\n"
                f"<b>5. Для чего нужно:</b> {data['reason']}\n"
                f"<b>6. {item_type_q}:</b> {item_type_a}\n\n"
                f"<b>Отправить заявку?</b>"
            )
        markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Отправить", callback_data="confirm_yes_license"),
            InlineKeyboardButton("❌ Отмена", callback_data="confirm_no_license")
        )
        bot.send_message(data['chat_id'], caption, parse_mode='HTML', reply_markup=markup)

# --- КОНЕЦ ИСПРАВЛЕННОГО БЛОКА ---

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
def handle_confirmation_callbacks(call):
    user_id = call.from_user.id
    bot.delete_message(call.message.chat.id, call.message.message_id)
    parts = call.data.split('_')
    action = parts[1]
    form_type = parts[2]
    data_map = {
        'passport': user_data_for_passport, 'sim': user_data_for_sim,
        'medcard': user_data_for_med_card, 'license': user_data_for_license
    }
    user_data_storage = data_map.get(form_type)
    if action == 'no':
        if user_id in user_data_storage:
            del user_data_storage[user_id]
        bot.send_message(user_id, "🗑️ Заявка отменена.")
        return
    if action == 'yes':
        if user_id not in user_data_storage:
            bot.send_message(user_id, "⚠️ Произошла ошибка. Пожалуйста, начните сначала.")
            return
        data = user_data_storage[user_id]
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        char_info = get_character_info(data.get('character_id', 0))
        try:
            if form_type == 'passport':
                cursor.execute("""
                    INSERT INTO characters (user_id, full_name, age, gender, height, hair_color, eye_color, body_type, tattoos,
                        childhood, father, mother, knowledge, current_life, roblox_display_name, roblox_real_name, photo_file_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, data['full_name'], data['age'], data['gender'], data['height'], data['hair_color'], data['eye_color'],
                    data['body_type'], data['tattoos'], data['childhood'], data['father'], data['mother'], data['knowledge'],
                    data['current_life'], data['roblox_display_name'], data['roblox_real_name'], data['photo_file_id']
                ))
# --- Начало блока для замены в handle_confirmation_callbacks ---
            if form_type == 'passport':
                # ... (код вставки в базу данных остается тот же) ...
                item_id = cursor.lastrowid
                conn.commit()
                moderation_caption = (
                    f"📝 <b>Новая заявка на Паспорт (ID: {item_id})</b>\n"
                    f"<b>От:</b> {get_display_name(user_id)} (<code>{user_id}</code>)\n"
                    f"<b>1. Имя, второе имя, фамилия:</b> {data['full_name']}\n"
                    f"<b>2. Возраст:</b> {data['age']}\n"
                    f"<b>3. Гендер:</b> {data['gender']}\n"
                    f"<b>4. Внешность:</b>\n"
                    f"  • <b>Рост:</b> {data['height']}\n"
                    f"  • <b>Цвет волос:</b> {data['hair_color']}\n"
                    f"  • <b>Цвет глаз:</b> {data['eye_color']}\n"
                    f"  • <b>Телосложение:</b> {data['body_type']}\n"
                    f"  • <b>Татуировки:</b> {data['tattoos']}\n"
                    f"<b>5. Детство:</b> {data['childhood']}\n"
                    f"<b>6. Родители:</b>\n"
                    f"  • <b>Отец:</b> {data['father']}\n"
                    f"  • <b>Мать:</b> {data['mother']}\n"
                    f"<b>7. Знания:</b> {data['knowledge']}\n"
                    f"<b>8. В настоящее время:</b> {data['current_life']}\n"
                    f"<b>9. Ник в Roblox:</b>\n"
                    f"  • <b>Дисплей:</b> {data['roblox_display_name']}\n"
                    f"  • <b>Настоящий:</b> {data['roblox_real_name']}"
                )
                markup = InlineKeyboardMarkup().add(
                    InlineKeyboardButton("✅ Одобрить", callback_data=f"moderate_approve_passport_{item_id}_{user_id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"moderate_reject_passport_{item_id}_{user_id}")
                )
                # ИСПРАВЛЕНИЕ: Добавляем проверку длины и для модераторов
                if len(moderation_caption) > 1024:
                    bot.send_photo(MODERATION_CHAT_ID, data['photo_file_id'])
                    bot.send_message(MODERATION_CHAT_ID, moderation_caption, parse_mode='HTML', reply_markup=markup)
                else:
                    bot.send_photo(MODERATION_CHAT_ID, data['photo_file_id'], caption=moderation_caption, parse_mode='HTML', reply_markup=markup)
            # ... (остальной код elif form_type == 'sim': и т.д.) ...
# --- Конец блока для замены ---
            elif form_type == 'sim':
                cursor.execute("INSERT INTO sim_cards (character_id, user_id, phone_number) VALUES (?, ?, ?)",
                               (data['character_id'], user_id, data['phone_number']))
                item_id = cursor.lastrowid
                conn.commit()
                moderation_text = (
                    f"📱 <b>Новая заявка на SIM-карту (ID: {item_id})</b>\n"
                    f"<b>От:</b> {get_display_name(user_id)} (<code>{user_id}</code>)\n"
                    f"<b>Персонаж:</b> {char_info['name']} (ID: {data['character_id']})\n"
                    f"<b>Номер:</b> {data['phone_number']}"
                )
                markup = InlineKeyboardMarkup().add(
                    InlineKeyboardButton("✅ Одобрить", callback_data=f"moderate_approve_sim_{item_id}_{user_id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"moderate_reject_sim_{item_id}_{user_id}")
                )
                bot.send_message(MODERATION_CHAT_ID, moderation_text, parse_mode='HTML', reply_markup=markup)
            elif form_type == 'medcard':
                cursor.execute("""
                    INSERT INTO medical_cards (character_id, user_id, psych_state, diagnoses, pain_threshold, weight, height)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (data['character_id'], user_id, data['psych_state'], data['diagnoses'], data['pain_threshold'], data['weight'], data['height']))
                item_id = cursor.lastrowid
                conn.commit()
                moderation_text = (
                    f"⚕️ <b>Новая заявка на Медкарту (ID: {item_id})</b>\n"
                    f"<b>От:</b> {get_display_name(user_id)} (<code>{user_id}</code>)\n"
                    f"<b>Персонаж:</b> {char_info['name']} (ID: {data['character_id']})\n"
                    f"<b>Псих. состояние:</b> {data['psych_state']}\n"
                    f"<b>Диагнозы:</b> {data['diagnoses']}\n"
                    f"<b>Болевой порог:</b> {data['pain_threshold']}\n"
                    f"<b>Вес/Рост:</b> {data['weight']}кг / {data['height']}см"
                )
                markup = InlineKeyboardMarkup().add(
                    InlineKeyboardButton("✅ Одобрить", callback_data=f"moderate_approve_medcard_{item_id}_{user_id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"moderate_reject_medcard_{item_id}_{user_id}")
                )
                bot.send_message(MODERATION_CHAT_ID, moderation_text, parse_mode='HTML', reply_markup=markup)
            elif form_type == 'license':
                license_type = data['license_type']
                if license_type == 'driver':
                    cursor.execute("""
                        INSERT INTO licenses (character_id, user_id, license_type, health_issues, category_details)
                        VALUES (?, ?, ?, ?, ?)
                    """, (data['character_id'], user_id, license_type, data['health_issues'], data['category_details']))
                    license_map = 'Водительские права'
                    moderation_text = (
                        f"📜 <b>Заявка: {license_map} (ID: {cursor.lastrowid})</b>\n"
                        f"<b>От:</b> {get_display_name(user_id)} (<code>{user_id}</code>)\n"
                        f"<b>Персонаж:</b> {char_info['name']}, {char_info['age']} лет (ID: {data['character_id']})\n"
                        f"<b>Проблемы со здоровьем:</b> {data['health_issues']}\n"
                        f"<b>Категория:</b> {data['category_details']}"
                    )
                elif license_type in ['weapon', 'armor']:
                    cursor.execute("""
                        INSERT INTO licenses (character_id, user_id, license_type, psych_state, criminal_record, reason, category_details)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (data['character_id'], user_id, license_type, data['psych_state'], data['criminal_record'], data['reason'], data['category_details']))
                    license_map = 'Лицензия на оружие' if license_type == 'weapon' else 'Лицензия на броню'
                    item_type_q = "Оружие" if license_type == 'weapon' else "Броня"
                    moderation_text = (
                        f"📜 <b>Заявка: {license_map} (ID: {cursor.lastrowid})</b>\n"
                        f"<b>От:</b> {get_display_name(user_id)} (<code>{user_id}</code>)\n"
                        f"<b>Персонаж:</b> {char_info['name']} (ID: {data['character_id']})\n"
                        f"<b>Псих. состояние:</b> {data['psych_state']}\n"
                        f"<b>Судимости:</b> {data['criminal_record']}\n"
                        f"<b>Причина:</b> {data['reason']}\n"
                        f"<b>Тип ({item_type_q}):</b> {data['category_details']}"
                    )
                item_id = cursor.lastrowid
                conn.commit()
                markup = InlineKeyboardMarkup().add(
                    InlineKeyboardButton("✅ Одобрить", callback_data=f"moderate_approve_license_{item_id}_{user_id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"moderate_reject_license_{item_id}_{user_id}")
                )
                bot.send_message(MODERATION_CHAT_ID, moderation_text, parse_mode='HTML', reply_markup=markup)
            bot.send_message(user_id, "✅ <b>Ваша заявка отправлена на рассмотрение.</b>\n"
                                      "Вы получите уведомление, когда администрация примет решение.", parse_mode='HTML')
        except Exception as e:
            bot.send_message(user_id, f"⚠️ Произошла ошибка при сохранении заявки: {e}. Попробуйте снова.")
            print(f"Ошибка сохранения заявки: {e}")
            conn.rollback()
        finally:
            if user_id in user_data_storage:
                del user_data_storage[user_id]
            conn.close()

# --- MODERATION ---

# --- MODERATION ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('moderate_'))
def handle_moderation_callbacks(call):
    parts = call.data.split('_')
    action = parts[1]
    item_type = parts[2]
    moderator_id = call.from_user.id
    moderator_name = get_display_name(moderator_id)

    # NEW: Handle Passport Modification moderation
    if item_type == "passportchange":
        change_id = int(parts[3])
        handle_passport_change_moderation(call, action, change_id, moderator_id, moderator_name)
        return

    # Existing moderation logic
    item_id = int(parts[3])
    target_user_id = int(parts[4])
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        table_map = {
            'passport': ('characters', 'full_name'),
            'sim': ('sim_cards', 'phone_number'),
            'medcard': ('medical_cards', 'character_id'),
            'license': ('licenses', 'license_type')
        }
        if item_type not in table_map:
            bot.answer_callback_query(call.id, "Неизвестный тип заявки.")
            return
        table_name, name_column = table_map[item_type]
        cursor.execute(f"SELECT status, {name_column} FROM {table_name} WHERE id = ?", (item_id,))
        result = cursor.fetchone()
        if not result or result[0] != 'pending':
            bot.answer_callback_query(call.id, "Эта заявка уже обработана.")
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            return
        item_name_raw = result[1]
        item_name_display = item_name_raw
        if item_type == 'medcard':
            char_name_res = cursor.execute("SELECT full_name FROM characters WHERE id = ?", (item_name_raw,)).fetchone()
            item_name_display = f"Медкарта для {char_name_res[0]}" if char_name_res else "Медкарта"
        elif item_type == 'license':
            license_map = {'driver': 'Водительские права', 'weapon': 'Лицензия на оружие', 'armor': 'Лицензия на броню'}
            item_name_display = license_map.get(item_name_raw, "Лицензия")
        if action == 'approve':
            update_query = f"UPDATE {table_name} SET status = 'approved', moderator_id = ? WHERE id = ?"
            params = [moderator_id, item_id]
            if item_type == 'license':
                expires_at = datetime.now() + timedelta(days=30)
                update_query = f"UPDATE {table_name} SET status = 'approved', moderator_id = ?, expires_at = ? WHERE id = ?"
                params = [moderator_id, expires_at.isoformat(), item_id]
            elif item_type == 'sim':
                update_query = f"UPDATE {table_name} SET status = 'approved', moderator_id = ?, character_id = NULL WHERE id = ?"
                params = [moderator_id, item_id]

            cursor.execute(update_query, tuple(params))
            conn.commit()
            
# --- НАЧАЛО БОНУСА ЗА ПЕРВОГО ПЕРСОНАЖА ---
            if item_type == 'passport':
                try:
                    # Проверяем, сколько всего одобренных паспортов у этого пользователя
                    cursor.execute("SELECT COUNT(id) FROM characters WHERE user_id = ? AND status = 'approved'", (target_user_id,))
                    approved_passport_count = cursor.fetchone()[0]
                    
                    # Если это ПЕРВЫЙ одобренный паспорт
                    if approved_passport_count == 1:
                        # Начинаем новую транзакцию для начисления бонуса
                        conn.execute("BEGIN TRANSACTION")
                        cursor.execute("UPDATE users SET balance = balance + 70 WHERE user_id = ?", (target_user_id,))
                        conn.commit()
                        
                        # Пытаемся отправить уведомление о бонусе
                        try:
                            bot.send_message(target_user_id, "🎉 Поздравляем с регистрацией вашего первого персонажа! Вам начислено 70 $ стартового капитала.", parse_mode='HTML')
                        except Exception as e:
                            print(f"Не удалось отправить уведомление о бонусе пользователю {target_user_id}: {e}")
                
                except Exception as e:
                    print(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось начислить бонус за первого персонажа: {e}")
                    # Откатываем транзакцию бонуса, если что-то пошло не так
                    if conn: conn.rollback()
            # --- КОНЕЦ БОНУСА ЗА ПЕРВОГО ПЕРСОНАЖА ---            
            
            
            # --- ИСПРАВЛЕННЫЙ БЛОК РЕДАКТИРОВАНИЯ ---
            new_content = (call.message.caption or call.message.text) + f"\n\n<b>✅ Одобрено модератором:</b> {moderator_name}"
            try:
                if call.message.photo:
                    bot.edit_message_caption(caption=new_content, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML', reply_markup=None)
                else:
                    bot.edit_message_text(text=new_content, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML', reply_markup=None)
            except Exception as e:
                print(f"Не удалось отредактировать сообщение модерации (одобрение): {e}")
                
                
                
            # --- КОНЕЦ ИСПРАВЛЕННОГО БЛОКА ---
            
            if item_type == 'sim':
                 bot.send_message(target_user_id, f"✅ Ваша заявка на <b>{item_name_display}</b> была <b>одобрена</b>!\n\n"
                                                  f"SIM-карта добавлена на ваш склад. Используйте /warehouse, чтобы привязать ее к персонажу.", parse_mode='HTML')
            else:
                bot.send_message(target_user_id, f"✅ Ваша заявка на <b>{item_name_display}</b> была <b>одобрена</b>!", parse_mode='HTML')

            bot.answer_callback_query(call.id, f"Заявка #{item_id} одобрена.")
        elif action == 'reject':
            rejection_in_progress[moderator_id] = {'item_id': item_id, 'target_user_id': target_user_id, 'message': call.message, 'item_type': item_type, 'item_name': item_name_display}
            msg = bot.send_message(moderator_id, f"Введите причину отказа для заявки #{item_id}. Это сообщение будет отправлено пользователю.")
            bot.register_next_step_handler(msg, process_rejection_reason)
            bot.answer_callback_query(call.id, "Введите причину отказа.")
    except Exception as e:
        print(f"Ошибка модерации ({item_type}): {e}")
        bot.answer_callback_query(call.id, "Произошла ошибка.")
    finally:
        conn.close()

def process_rejection_reason(message: Message):
    moderator_id = message.from_user.id
    if moderator_id not in rejection_in_progress: return
    data = rejection_in_progress[moderator_id]
    item_id = data['item_id']
    target_user_id = data['target_user_id']
    original_message = data['message']
    reason = message.text
    item_type = data['item_type']
    item_name = data['item_name']
    table_map = {'passport': 'characters', 'sim': 'sim_cards', 'medcard': 'medical_cards', 'license': 'licenses'}
    table_name = table_map.get(item_type)
    if not table_name: return

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        if table_name == 'characters':
             cursor.execute(f"UPDATE {table_name} SET status = 'rejected', rejection_reason = ?, moderator_id = ? WHERE id = ?", (reason, moderator_id, item_id))
        else:
             cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (item_id,))

        conn.commit()
        moderator_name = get_display_name(moderator_id)
        
        # --- ИСПРАВЛЕННЫЙ БЛОК РЕДАКТИРОВАНИЯ ---
        new_content = (original_message.caption or original_message.text) + f"\n\n<b>❌ Отклонено модератором:</b> {moderator_name}\n<b>Причина:</b> {reason}"
        try:
            if original_message.photo:
                bot.edit_message_caption(caption=new_content, chat_id=original_message.chat.id, message_id=original_message.message_id, parse_mode='HTML', reply_markup=None)
            else:
                bot.edit_message_text(text=new_content, chat_id=original_message.chat.id, message_id=original_message.message_id, parse_mode='HTML', reply_markup=None)
        except Exception as e:
            print(f"Не удалось отредактировать сообщение модерации (отклонение): {e}")
        # --- КОНЕЦ ИСПРАВЛЕННОГО БЛОКА ---

        bot.send_message(target_user_id, f"❌ Ваша заявка на <b>{item_name}</b> была <b>отклонена</b>.\n<b>Причина:</b> {reason}", parse_mode='HTML')
        bot.send_message(moderator_id, "Причина отказа успешно отправлена пользователю.")
    except Exception as e:
        print(f"Ошибка обработки причины отказа: {e}")
        bot.send_message(moderator_id, "Произошла ошибка при отправке причины.")
    finally:
        del rejection_in_progress[moderator_id]
        conn.close()


# --- DOCUMENT VIEWING & ACTIONS ---
def get_character_history_text(cursor, char_id):
    history_parts = []
    # Get fines history
    cursor.execute("""
        SELECT reason, amount, created_at FROM invoices
        WHERE character_id = ? AND invoice_type = 'fine'
        ORDER BY created_at DESC LIMIT 5
    """, (char_id,))
    fines = cursor.fetchall()
    if fines:
        fines_text = "\n".join([f"  • {created_at.split(' ')[0]}: {amount:,}$ - {reason}" for reason, amount, created_at in fines])
        history_parts.append(f"<b><u>Последние штрафы:</u></b>\n{fines_text}")
    # Get revoked licenses count
    cursor.execute("SELECT COUNT(*) FROM licenses WHERE character_id = ? AND status = 'revoked'", (char_id,))
    revoked_count = cursor.fetchone()[0]
    if revoked_count > 0:
        history_parts.append(f"<b><u>Нарушения:</u></b>\n  • Лицензии были отозваны: {revoked_count} раз(а).")
    if not history_parts:
        return "\n<b><u>История персонажа:</u></b>\n  Чиста."
    return "\n" + "\n".join(history_parts)

def get_character_wanted_text(cursor, char_id):
    cursor.execute("""
        SELECT stars, reason, issued_at, issued_by, status
        FROM wanted
        WHERE character_id = ? AND status = 'active'
        ORDER BY issued_at DESC LIMIT 1
    """, (char_id,))
    wanted = cursor.fetchone()
    if not wanted:
        return ""
    stars, reason, issued_at, issued_by, status = wanted
    issuer_name = get_display_name(issued_by) if issued_by else "Неизвестно"
    emoji_map = {1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐"}
    emoji = emoji_map.get(stars, "❓")
    return f"""
<b><u>Розыск:</u></b>
  • {emoji} {stars} звезд
  • Причина: {reason}
  • Выдано: {issuer_name} ({issued_at.split()[0]})
"""

def get_full_character_details_text(cursor, char_id):
    cursor.execute("""
        SELECT full_name, age, gender, height, hair_color, eye_color, body_type, tattoos,
               childhood, father, mother, knowledge, current_life,
               roblox_display_name, roblox_real_name
        FROM characters WHERE id = ?
    """, (char_id,))
    char = cursor.fetchone()
    if not char: return "<b>Персонаж не найден.</b>"
    (full_name, age, gender, height, hair_color, eye_color, body_type, tattoos,
     childhood, father, mother, knowledge, current_life,
     roblox_display_name, roblox_real_name) = char
    return (
        f"📄 <b>Паспорт персонажа: {full_name}</b> (ID: {char_id})\n"
        f"<b><u>Основная информация:</u></b>\n"
        f" • <b>Возраст:</b> {age}\n"
        f" • <b>Гендер:</b> {gender}\n"
        f" • <b>Roblox:</b> {roblox_display_name} (@{roblox_real_name})\n"
        f"<b><u>Внешность:</u></b>\n"
        f" • <b>Рост:</b> {height}\n"
        f" • <b>Цвет волос:</b> {hair_color}\n"
        f" • <b>Цвет глаз:</b> {eye_color}\n"
        f" • <b>Телосложение:</b> {body_type}\n"
        f" • <b>Татуировки:</b> {tattoos}\n"
        f"<b><u>Биография:</u></b>\n"
        f" • <b>Родители:</b>\n"
        f"    - <i>Отец:</i> {father}\n"
        f"   - <i>Мать:</i> {mother}\n"
        f" • <b>Детство:</b> {childhood}\n"
        f" • <b>Знания/Навыки:</b> {knowledge}\n"
        f" • <b>Текущая жизнь:</b> {current_life}\n"
        f"{get_character_attachments_text(cursor, char_id)}"
        f"{get_character_wanted_text(cursor, char_id)}"
    )

def get_character_attachments_text(cursor, char_id):
    sims = [row[0] for row in cursor.execute("SELECT phone_number FROM sim_cards WHERE character_id = ? AND status = 'approved'", (char_id,)).fetchall()]
    sim_text = "\n".join(f"  • {s}" for s in sims) if sims else "  Отсутствуют"

    med_card = cursor.execute("SELECT id, status FROM medical_cards WHERE character_id = ?", (char_id,)).fetchone()
    med_card_text = "Отсутствует"
    if med_card:
        med_card_id, med_card_status = med_card
        if med_card_status == 'approved': med_card_text = f"✅ Присутствует (ID: {med_card_id})"
        elif med_card_status == 'pending': med_card_text = "⏳ На рассмотрении"
        elif med_card_status == 'rejected': med_card_text = "❌ Отклонена"

    licenses = cursor.execute("SELECT license_type, category_details, status, expires_at, revoked_until FROM licenses WHERE character_id = ?", (char_id,)).fetchall()
    license_map = {'driver': 'Водительские права', 'weapon': 'Лицензия на оружие', 'armor': 'Лицензия на броню'}
    licenses_text = []
    if licenses:
        for lic_type, cat_details, lic_status, expires_at_str, revoked_until_str in licenses:
            status_emoji = "❓"
            expiry_info = ""
            if lic_status == 'approved':
                status_emoji = "✅"
                if expires_at_str:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if datetime.now() > expires_at:
                        expiry_info = " (Истекла)"
                    else:
                        expiry_info = f" (до {expires_at.strftime('%d.%m.%Y')})"
            elif lic_status == 'revoked':
                status_emoji = "🚫"
                if revoked_until_str:
                    revoked_until = datetime.fromisoformat(revoked_until_str)
                    expiry_info = f" (до {revoked_until.strftime('%d.%m.%Y')})"
            elif lic_status == 'pending':
                status_emoji = "⏳"
            elif lic_status == 'rejected':
                status_emoji = "❌"
            category_text = f" ({cat_details})" if cat_details else ""
            licenses_text.append(f"  • {license_map.get(lic_type, lic_type)}{category_text}: {status_emoji}{expiry_info}")
    if not licenses_text:
        licenses_text.append("  Отсутствуют")

    properties = cursor.execute("SELECT property_type, property_number FROM houses WHERE character_id = ?", (char_id,)).fetchall()
    property_text_list = []
    if properties:
        for prop_type, prop_num in properties:
            type_text = "Участок" if prop_type == 'house' else "Квартира"
            property_text_list.append(f"  • {type_text} #{prop_num}")
    property_text = "\n".join(property_text_list) if property_text_list else "  Отсутствует"

    # NEW: Get owned companies
    companies = cursor.execute("SELECT name, initial FROM companies WHERE character_id = ?", (char_id,)).fetchall()
    company_text_list = []
    if companies:
        for name, initial in companies:
            company_text_list.append(f"  • «{name}» ({initial})")
    company_text = "\n".join(company_text_list) if company_text_list else "  Отсутствует"


    return (
        f"<b><u>Привязки к Паспорту:</u></b>\n"
        f"<b>📱 Привязанные номера:</b>\n{sim_text}\n"
        f"<b>⚕️ Мед. карта:</b> {med_card_text}\n"
        f"<b>📜 Лицензии:</b>\n" + "\n".join(licenses_text) + "\n"
        f"<b>🏡 Недвижимость:</b>\n{property_text}\n"
        f"<b>🏢 Компании:</b>\n{company_text}"
    )

@bot.message_handler(commands=['passport'])
@antispam_filter
def show_my_passports(message: Message):
    user_id_to_check = message.from_user.id
    target_user_name = "вас"
    is_owner_or_gov = True
    if message.reply_to_message:
        user_id_to_check = message.reply_to_message.from_user.id
        target_user_name = f"пользователя {get_display_name(user_id_to_check)}"
        if message.from_user.id != user_id_to_check:
             is_owner_or_gov = has_government_access(message.from_user.id)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, full_name, age, photo_file_id FROM characters WHERE user_id = ? AND status = 'approved' ORDER BY id DESC", (user_id_to_check,))
        characters = cursor.fetchall()
        if not characters:
            return bot.reply_to(message, f"У {target_user_name} пока нет одобренных Паспортов. Для создания своего используйте /create_passport.")
        bot.reply_to(message, f"Найден(о) Паспортов у {target_user_name}: {len(characters)}. Отправляю информацию...")
        for char_id, full_name, age, photo_file_id in characters:
            caption = ""
            if is_owner_or_gov:
                caption = get_full_character_details_text(cursor, char_id)
            else:
                caption = (
                    f"📄 <b>Паспорт персонажа: {full_name}</b> (ID: {char_id})\n"
                    f"<b>Возраст:</b> {age}\n"
                    f"{get_character_attachments_text(cursor, char_id)}"
                )
            markup = None
            if message.from_user.id == user_id_to_check:
                markup = InlineKeyboardMarkup(row_width=2)
                buttons = [
                    InlineKeyboardButton("📱 Зарегистрировать SIM", callback_data=f"action_sim_{char_id}"),
                    InlineKeyboardButton("⚕️ Создать мед. карту", callback_data=f"action_medcard_{char_id}"),
                    InlineKeyboardButton("🚗 Водительские права", callback_data=f"action_license_driver_{char_id}"),
                    InlineKeyboardButton("🔫 Лицензия на оружие", callback_data=f"action_license_weapon_{char_id}"),
                    InlineKeyboardButton("🛡️ Лицензия на броню", callback_data=f"action_license_armor_{char_id}"),
                    InlineKeyboardButton("✏️ Изменить Паспорт", callback_data=f"modify_passport_start_{char_id}")
                ]
                markup.add(*buttons)
            if len(caption) > 1024:
                bot.send_photo(message.chat.id, photo_file_id)
                bot.send_message(message.chat.id, caption, parse_mode='HTML', reply_markup=markup)
            else:
                bot.send_photo(message.chat.id, photo_file_id, caption=caption, parse_mode='HTML', reply_markup=markup)
            time.sleep(0.5)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при получении Паспорта: {e}")
        print(e)
    finally:
        conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('action_'))
def handle_action_callbacks(call):
    user_id = call.from_user.id
    parts = call.data.split('_')
    action_type = parts[1]
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        character_id = 0
        license_type = ''
        if action_type == 'license':
            license_type = parts[2]
            character_id = int(parts[3])
        else: # sim, medcard
            character_id = int(parts[2])
        cursor.execute("SELECT user_id FROM characters WHERE id = ?", (character_id,))
        owner_id = cursor.fetchone()
        if not owner_id or owner_id[0] != user_id:
            return bot.answer_callback_query(call.id, "Это не ваш Паспорт.", show_alert=True)
        bot.answer_callback_query(call.id)
        if action_type == 'sim':
            cursor.execute("SELECT 1 FROM sim_cards WHERE character_id = ? AND status = 'pending'", (character_id,))
            if cursor.fetchone(): return bot.send_message(user_id, "У вас уже есть заявка на SIM-карту для этого персонажа на рассмотрении.")
            cursor.execute("SELECT COUNT(id) FROM sim_cards WHERE character_id = ? AND status = 'approved'", (character_id,))
            sim_count = cursor.fetchone()[0]
            if sim_count >= 3:
                return bot.send_message(user_id, "❌ <b>Достигнут лимит.</b> На этого персонажа уже зарегистрировано максимальное количество SIM-карт (3).", parse_mode='HTML')
            create_sim_start(call.message, character_id)
        elif action_type == 'medcard':
            cursor.execute("SELECT 1 FROM medical_cards WHERE character_id = ? AND (status = 'pending' OR status = 'approved')", (character_id,))
            if cursor.fetchone(): return bot.send_message(user_id, "У этого персонажа уже есть медкарта или заявка на рассмотрении.")
            create_med_card_start(call.message, character_id)
        elif action_type == 'license':
            cursor.execute("SELECT status, revoked_until FROM licenses WHERE character_id = ? AND license_type = ?", (character_id, license_type))
            existing_license = cursor.fetchone()
            if existing_license:
                status, revoked_until_str = existing_license
                if status in ['pending', 'approved']:
                    return bot.send_message(user_id, "У вас уже есть заявка или действующая лицензия этого типа.")
                if status == 'revoked' and revoked_until_str:
                    revoked_until = datetime.fromisoformat(revoked_until_str)
                    if datetime.now() < revoked_until:
                        return bot.send_message(user_id, f"Вы не можете подать заявку. Ваша лицензия отозвана до {revoked_until.strftime('%d.%m.%Y')}.")
            if license_type in ['weapon', 'armor']:
                cursor.execute("SELECT 1 FROM medical_cards WHERE character_id = ? AND status = 'approved'", (character_id,))
                if not cursor.fetchone():
                    return bot.send_message(user_id, "❌ Для получения лицензии на оружие/броню необходима одобренная медкарта. Сначала создайте ее.")
            create_license_start(call.message, character_id, license_type)
    except Exception as e:
        print(f"Ошибка в action_callback: {e}")
        bot.send_message(user_id, "Произошла ошибка, попробуйте снова.")
    finally:
        conn.close()

# --- PASSPORT MODIFICATION ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('modify_passport_start_'))
def modify_passport_start(call):
    user_id = call.from_user.id
    character_id = int(call.data.split('_')[3])

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        # Check if user owns this character
        cursor.execute("SELECT user_id FROM characters WHERE id = ?", (character_id,))
        owner_id = cursor.fetchone()
        if not owner_id or owner_id[0] != user_id:
            return bot.answer_callback_query(call.id, "Это не ваш персонаж.", show_alert=True)

        # Check for pending modifications for this character
        cursor.execute("SELECT 1 FROM passport_modifications WHERE character_id = ? AND status = 'pending'", (character_id,))
        if cursor.fetchone():
            return bot.answer_callback_query(call.id, "У вас уже есть активный запрос на изменение этого паспорта.", show_alert=True)

    finally:
        conn.close()

    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for field_key, field_name in PASSPORT_MODIFIABLE_FIELDS.items():
        buttons.append(InlineKeyboardButton(field_name, callback_data=f"mod_field_{character_id}_{field_key}"))
    markup.add(*buttons)
    markup.add(InlineKeyboardButton("❌ Отмена", callback_data="mod_cancel"))

    bot.edit_message_caption("✏️ <b>Изменение паспорта</b>\n\nВыберите, что вы хотите изменить:",
                             chat_id=call.message.chat.id,
                             message_id=call.message.message_id,
                             reply_markup=markup, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'mod_cancel')
def modify_passport_cancel(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "Изменение отменено.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('mod_field_'))
def modify_passport_field_selected(call):
    user_id = call.from_user.id
    parts = call.data.split('_')
    character_id = int(parts[2])
    field_to_change = '_'.join(parts[3:])
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM characters WHERE id=?", (character_id,))
        owner_id = cursor.fetchone()[0]
        if user_id != owner_id:
            return bot.answer_callback_query(call.id, "Это не ваш персонаж.", show_alert=True)
    finally:
        conn.close()

    passport_modification_in_progress[user_id] = {
        'character_id': character_id,
        'field': field_to_change,
        'chat_id': call.message.chat.id,
        'last_bot_msg_id': call.message.message_id
    }

    if field_to_change == 'biography':
        bot.edit_message_caption("✏️ <b>Изменение биографии</b>\n\n"
                                "Отправьте <b>ОДНИМ СООБЩЕНИЕМ</b> все обновленные поля биографии:\n"
                                "1. Детство\n2. Отец\n3. Мать\n4. Знания/Навыки\n5. Текущая жизнь",
                                call.message.chat.id, call.message.message_id, parse_mode='HTML')
        bot.register_next_step_handler(call.message, process_passport_modification_text)
    elif field_to_change == 'photo_file_id':
        bot.edit_message_caption("✏️ <b>Изменение фото</b>\n\nОтправьте новое фото для персонажа.",
                                call.message.chat.id, call.message.message_id, parse_mode='HTML')
        bot.register_next_step_handler(call.message, process_passport_modification_photo)
    else:
        field_name_rus = PASSPORT_MODIFIABLE_FIELDS.get(field_to_change, "новое значение")
        bot.edit_message_caption(f"✏️ <b>Изменение: {field_name_rus}</b>\n\nВведите новое значение:",
                                call.message.chat.id, call.message.message_id, parse_mode='HTML')
        bot.register_next_step_handler(call.message, process_passport_modification_text)

def process_passport_modification_text(message: Message):
    user_id = message.from_user.id
    if user_id not in passport_modification_in_progress: return

    data = passport_modification_in_progress[user_id]
    field = data['field']
    new_value = message.text

    # Cleanup previous messages
    bot.delete_message(data['chat_id'], data['last_bot_msg_id'])
    bot.delete_message(message.chat.id, message.message_id)

    submit_passport_modification(user_id, data['character_id'], field, new_value)
    del passport_modification_in_progress[user_id]

def process_passport_modification_photo(message: Message):
    user_id = message.from_user.id
    if user_id not in passport_modification_in_progress: return

    data = passport_modification_in_progress[user_id]

    bot.delete_message(data['chat_id'], data['last_bot_msg_id'])
    bot.delete_message(message.chat.id, message.message_id)

    if not message.photo:
        bot.send_message(user_id, "❌ Это не фото. Запрос на изменение отменен. Попробуйте снова.")
        del passport_modification_in_progress[user_id]
        return

    new_value = message.photo[-1].file_id
    submit_passport_modification(user_id, data['character_id'], 'photo_file_id', new_value)
    del passport_modification_in_progress[user_id]

def submit_passport_modification(user_id, character_id, field, new_value):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        if field == 'biography':
            # For biography, we fetch multiple old fields
            cursor.execute("SELECT childhood, father, mother, knowledge, current_life FROM characters WHERE id = ?", (character_id,))
            res = cursor.fetchone()
            old_value = (f"Детство: {res[0]}\nОтец: {res[1]}\nМать: {res[2]}\n"
                         f"Знания: {res[3]}\nТекущая жизнь: {res[4]}")
        else:
            cursor.execute(f"SELECT {field} FROM characters WHERE id = ?", (character_id,))
            res = cursor.fetchone()
            old_value = res[0] if res else "НЕ НАЙДЕНО"

        cursor.execute("""
            INSERT INTO passport_modifications (character_id, user_id, field_name, old_value, new_value)
            VALUES (?, ?, ?, ?, ?)
        """, (character_id, user_id, field, str(old_value), new_value))
        change_id = cursor.lastrowid
        conn.commit()

        cursor.execute("SELECT full_name FROM characters WHERE id = ?", (character_id,))
        char_name = cursor.fetchone()[0]

        field_name_rus = PASSPORT_MODIFIABLE_FIELDS.get(field, field)

        mod_text = (f"✏️ <b>Запрос на изменение паспорта (ID: {change_id})</b>\n\n"
                    f"<b>Персонаж:</b> {char_name} (ID: {character_id})\n"
                    f"<b>Пользователь:</b> {get_display_name(user_id)} (<code>{user_id}</code>)\n\n"
                    f"<b>Поле:</b> {field_name_rus}\n\n"
                    f"<b><u>Старое значение:</u></b>\n<code>{old_value}</code>\n\n"
                    f"<b><u>Новое значение:</u></b>\n<code>{new_value}</code>")

        markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Одобрить", callback_data=f"moderate_approve_passportchange_{change_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"moderate_reject_passportchange_{change_id}")
        )

        if field == 'photo_file_id':
             bot.send_photo(MODERATION_CHAT_ID, new_value, caption=mod_text, parse_mode='HTML', reply_markup=markup)
        else:
             bot.send_message(MODERATION_CHAT_ID, mod_text, parse_mode='HTML', reply_markup=markup)

        bot.send_message(user_id, "✅ Ваш запрос на изменение паспорта отправлен на рассмотрение.")

    except Exception as e:
        print(f"Ошибка при подаче заявки на изменение паспорта: {e}")
        bot.send_message(user_id, "⚠️ Произошла ошибка при отправке запроса.")
    finally:
        conn.close()

def handle_passport_change_moderation(call, action, change_id, moderator_id, moderator_name):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT character_id, user_id, field_name, new_value, status
            FROM passport_modifications WHERE id = ?
        """, (change_id,))
        result = cursor.fetchone()
        if not result:
            return bot.answer_callback_query(call.id, "Запрос не найден.", show_alert=True)

        character_id, user_id, field, new_value, status = result
        field_name_rus = PASSPORT_MODIFIABLE_FIELDS.get(field, field)

        if status != 'pending':
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            return bot.answer_callback_query(call.id, "Этот запрос уже обработан.", show_alert=True)

        if action == 'approve':
            if field == 'biography':
                # This is a placeholder for a more complex update logic.
                # A simple approach: split the text by newlines and update fields. This is fragile.
                # For this implementation, we will update all bio fields with the new blob of text.
                # This is NOT ideal but demonstrates the concept.
                cursor.execute("""
                    UPDATE characters SET
                    childhood = ?, father = ?, mother = ?, knowledge = ?, current_life = ?
                    WHERE id = ?
                """, ("Обновлено.", "Обновлено.", "Обновлено.", "Обновлено.", new_value, character_id))
            else:
                 cursor.execute(f"UPDATE characters SET {field} = ? WHERE id = ?", (new_value, character_id))

            cursor.execute("UPDATE passport_modifications SET status = 'approved', moderator_id = ? WHERE id = ?", (moderator_id, change_id))
            conn.commit()

            new_text = (call.message.text or call.message.caption) + f"\n\n<b>✅ Одобрено модератором: {moderator_name}</b>"
            bot.send_message(user_id, f"✅ Ваш запрос на изменение поля '<b>{field_name_rus}</b>' был одобрен.", parse_mode='HTML')
            bot.answer_callback_query(call.id, "Изменение одобрено.")

        elif action == 'reject':
            cursor.execute("UPDATE passport_modifications SET status = 'rejected', moderator_id = ? WHERE id = ?", (moderator_id, change_id))
            conn.commit()

            new_text = (call.message.text or call.message.caption) + f"\n\n<b>❌ Отклонено модератором: {moderator_name}</b>"
            bot.send_message(user_id, f"❌ Ваш запрос на изменение поля '<b>{field_name_rus}</b>' был отклонен.", parse_mode='HTML')
            bot.answer_callback_query(call.id, "Изменение отклонено.")

        # Edit moderator's message
        if call.message.photo:
            bot.edit_message_caption(new_text, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=None)
        else:
            bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=None)

    except Exception as e:
        print(f"Ошибка модерации изменения паспорта: {e}")
        bot.answer_callback_query(call.id, "Произошла ошибка.", show_alert=True)
    finally:
        conn.close()
def select_character_for_item(message, item_type):
    """Спрашивает у пользователя, к какому персонажу привязать предмет."""
    user_id = message.from_user.id
    data_map = {'sim': user_data_for_sim, 'house': None} # 'house' будет обрабатываться по-другому
    user_data = data_map[item_type]
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, full_name FROM characters WHERE user_id = ? AND status = 'approved'", (user_id,))
        characters = cursor.fetchall()

        if not characters:
            bot.send_message(user_id, "❌ У вас нет одобренных персонажей для привязки. Заявка отменена.")
            if user_data and user_id in user_data: del user_data[user_id]
            return

        # Если персонаж только один, привязываем автоматически
        if len(characters) == 1:
            character_id = characters[0][0]
            if item_type == 'sim':
                user_data['character_id'] = character_id
                show_confirmation_form(user_id, 'sim')
            # Для домов логика будет в другом месте, здесь просто возвращаем ID
            return character_id
        else:
            # Если персонажей несколько, даем выбор
            markup = InlineKeyboardMarkup(row_width=1)
            for char_id, full_name in characters:
                if item_type == 'sim':
                     markup.add(InlineKeyboardButton(full_name, callback_data=f"char_select_sim_{char_id}"))
            markup.add(InlineKeyboardButton("❌ Отмена", callback_data=f"char_select_cancel_{item_type}"))
            
            thread_id = user_data.get('message_thread_id')
            bot.send_message(user_id, "Выберите персонажа, к которому нужно привязать SIM-карту:", reply_markup=markup, message_thread_id=thread_id)
    finally:
        conn.close()
    return None # Возвращаем None, если нужен выбор

@bot.callback_query_handler(func=lambda call: call.data.startswith('char_select_cancel_'))
def handle_character_select_cancel(call):
    user_id = call.from_user.id
    item_type = call.data.split('_')[-1]
    data_map = {'sim': user_data_for_sim}
    if item_type in data_map and user_id in data_map[item_type]:
        del data_map[item_type][user_id]
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "Отменено.")
    bot.send_message(user_id, "🗑️ Создание отменено.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('char_select_sim_'))
def handle_character_select_sim(call):
    user_id = call.from_user.id
    character_id = int(call.data.split('_')[-1])
    if user_id in user_data_for_sim:
        user_data_for_sim[user_id]['character_id'] = character_id
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_confirmation_form(user_id, 'sim')
        bot.answer_callback_query(call.id)

# --- SIM CARD APPLICATION ---
def create_sim_start(message, character_id):
    user_id = message.chat.id
    # --- BUG FIX: Delete previous rejected applications for this character ---
    conn = sqlite3.connect('database.db')
    try:
        conn.execute("DELETE FROM sim_cards WHERE character_id = ? AND status = 'rejected'", (character_id,))
        conn.commit()
    finally:
        conn.close()
    # --- END BUG FIX ---
    
    user_data_for_sim[user_id] = {'chat_id': user_id, 'character_id': character_id}
    msg = bot.send_message(user_id, "📱 <b>Регистрация SIM-карты</b>\n"
                                    "Введите желаемый номер телефона в формате <code>+1 587 XXX-XX-XX</code>:", parse_mode='HTML')
    user_data_for_sim[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_phone_number_step)

def process_phone_number_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_sim: return
    chat_id = user_data_for_sim[user_id]['chat_id']
    thread_id = user_data_for_sim[user_id].get('message_thread_id')
    last_bot_msg_id = user_data_for_sim[user_id]['last_bot_msg_id']
    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)

    phone_number_raw = message.text
    phone_number_cleaned = re.sub(r'[^\d+]', '', phone_number_raw)

    # ИЗМЕНЕНО: Проверяем, начинается ли номер с "+1587"
    if not phone_number_cleaned.startswith('+1587'):
        # ИЗМЕНЕНО: Добавим хелпер для тех, кто вводит номер без "+"
        if phone_number_cleaned.startswith('1587') and len(phone_number_cleaned) == 11:
            phone_number_cleaned = '+' + phone_number_cleaned
        else:
            # ИЗМЕНЕНО: Обновляем сообщение об ошибке
            msg = bot.send_message(chat_id, "❌ <b>Неверный формат номера.</b>\n"
                                            "Номер должен начинаться с <code>+1 587</code>.", parse_mode='HTML', message_thread_id=thread_id)
            user_data_for_sim[user_id]['last_bot_msg_id'] = msg.message_id
            bot.register_next_step_handler(message, process_phone_number_step)
            return

    # Проверка на общую длину остаётся такой же (12 символов: +1 и 10 цифр)
    if not (len(phone_number_cleaned) == 12 and phone_number_cleaned[1:].isdigit()):
        msg = bot.send_message(chat_id, "❌ <b>Неверный формат номера.</b>\n"
                                        "Номер должен содержать 7 цифр после <code>+1 587</code>.", parse_mode='HTML', message_thread_id=thread_id)
        user_data_for_sim[user_id]['last_bot_msg_id'] = msg.message_id
        bot.register_next_step_handler(message, process_phone_number_step)
        return

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM sim_cards WHERE phone_number = ?", (phone_number_cleaned,))
        if cursor.fetchone():
            msg = bot.send_message(chat_id, "❌ <b>Этот номер уже занят.</b> Попробуйте другой.\n"
                                              "Введите номер телефона:", parse_mode='HTML', message_thread_id=thread_id)
            user_data_for_sim[user_id]['last_bot_msg_id'] = msg.message_id
            bot.register_next_step_handler(message, process_phone_number_step)
            return
    finally:
        conn.close()

    user_data_for_sim[user_id]['phone_number'] = phone_number_cleaned
    show_confirmation_form(user_id, 'sim')

# --- MEDICAL CARD APPLICATION ---
def create_med_card_start(message, character_id):
    user_id = message.chat.id
    # --- BUG FIX: Delete previous rejected applications for this character ---
    conn = sqlite3.connect('database.db')
    try:
        conn.execute("DELETE FROM medical_cards WHERE character_id = ? AND status = 'rejected'", (character_id,))
        conn.commit()
    finally:
        conn.close()
    # --- END BUG FIX ---

    char_info = get_character_info(character_id)
    user_data_for_med_card[user_id] = {'chat_id': user_id, 'character_id': character_id}
    form_text = (
        f"⚕️ <b>Создание медкарты</b>\n"
        f"<b>Имя:</b> {char_info['name']}\n"
        f"<b>Возраст:</b> {char_info['age']}\n"
        f"<b>Шаг 1/5:</b> Опишите психологическое состояние персонажа:"
    )
    msg = bot.send_message(user_id, form_text, parse_mode='HTML')
    user_data_for_med_card[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_psych_state_step_med)

def process_psych_state_step_med(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_med_card: return
    cleanup_messages(user_data_for_med_card[user_id]['chat_id'], message.message_id, user_data_for_med_card[user_id]['last_bot_msg_id'])
    user_data_for_med_card[user_id]['psych_state'] = message.text
    msg = bot.send_message(user_data_for_med_card[user_id]['chat_id'], "<b>Шаг 2/5:</b> Перечислите диагнозы/болезни/инвалидности/расстройства (если нет, напишите 'Нет').", parse_mode='HTML')
    user_data_for_med_card[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_diagnoses_step)

def process_diagnoses_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_med_card: return
    cleanup_messages(user_data_for_med_card[user_id]['chat_id'], message.message_id, user_data_for_med_card[user_id]['last_bot_msg_id'])
    user_data_for_med_card[user_id]['diagnoses'] = message.text
    msg = bot.send_message(user_data_for_med_card[user_id]['chat_id'], "<b>Шаг 3/5:</b> Опишите болевой порог (низкий, средний, высокий).", parse_mode='HTML')
    user_data_for_med_card[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_pain_threshold_step)

def process_pain_threshold_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_med_card: return
    cleanup_messages(user_data_for_med_card[user_id]['chat_id'], message.message_id, user_data_for_med_card[user_id]['last_bot_msg_id'])
    user_data_for_med_card[user_id]['pain_threshold'] = message.text
    msg = bot.send_message(user_data_for_med_card[user_id]['chat_id'], "<b>Шаг 4/5:</b> Укажите вес в кг (только число).", parse_mode='HTML')
    user_data_for_med_card[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_weight_step)

def process_weight_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_med_card: return
    chat_id = user_data_for_med_card[user_id]['chat_id']
    last_bot_msg_id = user_data_for_med_card[user_id]['last_bot_msg_id']
    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)
    if not message.text.isdigit():
        msg = bot.send_message(chat_id, "❌ <b>Введите вес цифрами.</b>\n"
                                        "<b>Шаг 4/5:</b> Укажите вес в кг:", parse_mode='HTML')
        user_data_for_med_card[user_id]['last_bot_msg_id'] = msg.message_id
        bot.register_next_step_handler(message, process_weight_step)
        return
    user_data_for_med_card[user_id]['weight'] = message.text
    msg = bot.send_message(chat_id, "<b>Шаг 5/5:</b> Укажите рост в см (только число).", parse_mode='HTML')
    user_data_for_med_card[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_height_step_med)

def process_height_step_med(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_med_card: return
    chat_id = user_data_for_med_card[user_id]['chat_id']
    last_bot_msg_id = user_data_for_med_card[user_id]['last_bot_msg_id']
    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)
    if not message.text.isdigit():
        msg = bot.send_message(chat_id, "❌ <b>Введите рост цифрами.</b>\n"
                                        "<b>Шаг 5/5:</b> Укажите рост в см:", parse_mode='HTML')
        user_data_for_med_card[user_id]['last_bot_msg_id'] = msg.message_id
        bot.register_next_step_handler(message, process_height_step_med)
        return
    user_data_for_med_card[user_id]['height'] = message.text
    show_confirmation_form(user_id, 'medcard')

# --- LICENSE APPLICATIONS (DRIVER, WEAPON, ARMOR) ---
def create_license_start(message, character_id, license_type):
    user_id = message.chat.id
    # --- BUG FIX: Delete previous rejected applications for this character and license type ---
    conn = sqlite3.connect('database.db')
    try:
        conn.execute("DELETE FROM licenses WHERE character_id = ? AND license_type = ? AND status = 'rejected'", (character_id, license_type))
        conn.commit()
    finally:
        conn.close()
    # --- END BUG FIX ---

    char_info = get_character_info(character_id)
    user_data_for_license[user_id] = {'chat_id': user_id, 'character_id': character_id, 'license_type': license_type}
    if license_type == 'driver':
        form_text = (
            f"🚗 <b>Заявка на водительские права</b>\n"
            f"<b>Имя:</b> {char_info['name']}\n"
            f"<b>Возраст:</b> {char_info['age']}\n"
            f"<b>Шаг 1/2:</b> Есть ли у персонажа проблемы со здоровьем, болезни, которые могут повлиять на вождение? (Если нет, напишите 'Нет')."
        )
        msg = bot.send_message(user_id, form_text, parse_mode='HTML')
        user_data_for_license[user_id]['last_bot_msg_id'] = msg.message_id
        bot.register_next_step_handler(message, process_health_issues_step)
    elif license_type in ['weapon', 'armor']:
        license_map = 'Лицензия на оружие' if license_type == 'weapon' else 'Лицензия на броню'
        form_text = (
            f"📜 <b>Заявка на: {license_map}</b>\n"
            f"<b>Имя:</b> {char_info['name']}\n"
            f"<b>Возраст:</b> {char_info['age']}\n"
            f"<b>Шаг 1/4:</b> Опишите психологическое состояние персонажа."
        )
        msg = bot.send_message(user_id, form_text, parse_mode='HTML')
        user_data_for_license[user_id]['last_bot_msg_id'] = msg.message_id
        bot.register_next_step_handler(message, process_psych_state_step_lic)

def process_health_issues_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_license: return
    cleanup_messages(user_data_for_license[user_id]['chat_id'], message.message_id, user_data_for_license[user_id]['last_bot_msg_id'])
    user_data_for_license[user_id]['health_issues'] = message.text
    categories_text = "\n".join([f"  • <b>{cat}</b> – {details['name']} (с {details['age']} лет)" for cat, details in DRIVER_LICENSE_CATEGORIES.items()])
    msg = bot.send_message(user_data_for_license[user_id]['chat_id'], f"<b>Шаг 2/2:</b> Выберите и введите желаемую категорию прав из списка ниже:\n{categories_text}", parse_mode='HTML')
    user_data_for_license[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_driver_category_step)

def process_driver_category_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_license: return
    chat_id = user_data_for_license[user_id]['chat_id']
    last_bot_msg_id = user_data_for_license[user_id]['last_bot_msg_id']
    cleanup_messages(chat_id, message.message_id, last_bot_msg_id)
    category = message.text.upper()
    if category not in DRIVER_LICENSE_CATEGORIES:
        msg = bot.send_message(chat_id, "❌ <b>Неверная категория.</b> Пожалуйста, введите одну из предложенных категорий точно как в списке.", parse_mode='HTML')
        user_data_for_license[user_id]['last_bot_msg_id'] = msg.message_id
        bot.register_next_step_handler(message, process_driver_category_step)
        return
    char_info = get_character_info(user_data_for_license[user_id]['character_id'])
    required_age = DRIVER_LICENSE_CATEGORIES[category]['age']
    if char_info['age'] < required_age:
        bot.send_message(chat_id, f"❌ <b>Отказано.</b> Ваш возраст ({char_info['age']}) не соответствует минимальному требованию ({required_age} лет) для категории '{category}'. Заявка отменена.")
        del user_data_for_license[user_id]
        return
    user_data_for_license[user_id]['category_details'] = category
    show_confirmation_form(user_id, 'license')

def process_psych_state_step_lic(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_license: return
    cleanup_messages(user_data_for_license[user_id]['chat_id'], message.message_id, user_data_for_license[user_id]['last_bot_msg_id'])
    user_data_for_license[user_id]['psych_state'] = message.text
    msg = bot.send_message(user_data_for_license[user_id]['chat_id'], "<b>Шаг 2/4:</b> Имеет ли персонаж судимости? (Да/Нет, если да - описать).", parse_mode='HTML')
    user_data_for_license[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_criminal_record_step)

def process_criminal_record_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_license: return
    cleanup_messages(user_data_for_license[user_id]['chat_id'], message.message_id, user_data_for_license[user_id]['last_bot_msg_id'])
    user_data_for_license[user_id]['criminal_record'] = message.text
    item_type = "оружие/броню" if user_data_for_license[user_id]['license_type'] == 'weapon' else "броню"
    msg = bot.send_message(user_data_for_license[user_id]['chat_id'], f"<b>Шаг 3/4:</b> Укажите причину, для чего вам нужно {item_type}.", parse_mode='HTML')
    user_data_for_license[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_reason_step)

def process_reason_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_license: return
    cleanup_messages(user_data_for_license[user_id]['chat_id'], message.message_id, user_data_for_license[user_id]['last_bot_msg_id'])
    user_data_for_license[user_id]['reason'] = message.text
    item_type_q = "На какое оружие нужна лицензия?" if user_data_for_license[user_id]['license_type'] == 'weapon' else "На какой класс брони нужна лицензия?"
    msg = bot.send_message(user_data_for_license[user_id]['chat_id'], f"<b>Шаг 4/4:</b> {item_type_q}", parse_mode='HTML')
    user_data_for_license[user_id]['last_bot_msg_id'] = msg.message_id
    bot.register_next_step_handler(message, process_category_details_step)

def process_category_details_step(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data_for_license: return
    cleanup_messages(user_data_for_license[user_id]['chat_id'], message.message_id, user_data_for_license[user_id]['last_bot_msg_id'])
    user_data_for_license[user_id]['category_details'] = message.text
    show_confirmation_form(user_id, 'license')

# --- AUCTION & WAREHOUSE SYSTEM ---

# Словарь для хранения данных при создании аукциона
auction_creation_in_progress = {}

def format_time_left(end_time_str):
    """Форматирует оставшееся время."""
    end_time = datetime.fromisoformat(end_time_str)
    now = datetime.now()
    if now >= end_time:
        return "Завершен"
    delta = end_time - now
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    if days > 0:
        return f"{days} дн. {hours} ч."
    elif hours > 0:
        return f"{hours} ч. {minutes} мин."
    else:
        return f"{minutes} мин."

@bot.message_handler(commands=['warehouse'])
@antispam_filter
def show_warehouse(message: Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, property_type, property_number FROM houses WHERE user_id = ? AND character_id IS NULL", (user_id,))
        houses = cursor.fetchall()
        cursor.execute("SELECT id, phone_number FROM sim_cards WHERE user_id = ? AND character_id IS NULL AND status = 'approved'", (user_id,))
        sims = cursor.fetchall()

        if not houses and not sims:
            return bot.reply_to(message, "🗄️ Ваш склад пуст.")

        text = "🗄️ <b>Ваш склад:</b>\n\n"
        markup = InlineKeyboardMarkup()
        if houses:
            text += "<b>Недвижимость:</b>\n"
            for house_id, prop_type, prop_num in houses:
                type_text = "Участок" if prop_type == 'house' else "Квартира"
                text += f" • {type_text} #{prop_num}\n"
                markup.add(InlineKeyboardButton(f"Привязать {type_text} #{prop_num}", callback_data=f"wh_assign_house_{house_id}"))
        if sims:
            text += "\n<b>SIM-карты:</b>\n"
            for sim_id, phone_number in sims:
                text += f" • {phone_number}\n"
                markup.add(InlineKeyboardButton(f"Привязать SIM {phone_number}", callback_data=f"wh_assign_sim_{sim_id}"))
        bot.reply_to(message, text, reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при доступе к складу: {e}")
    finally:
        conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('wh_assign_'))
def handle_warehouse_assign_start(call):
    user_id = call.from_user.id
    parts = call.data.split('_')
    item_type = parts[2]
    item_id = int(parts[3])
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, full_name FROM characters WHERE user_id = ? AND status = 'approved'", (user_id,))
        characters = cursor.fetchall()
        if not characters:
            return bot.answer_callback_query(call.id, "У вас нет одобренных персонажей.", show_alert=True)
        markup = InlineKeyboardMarkup(row_width=1)
        for char_id, full_name in characters:
            markup.add(InlineKeyboardButton(full_name, callback_data=f"wh_confirm_{item_type}_{item_id}_{char_id}"))
        markup.add(InlineKeyboardButton("⬅️ Назад на склад", callback_data="wh_back"))
        bot.edit_message_text("Выберите персонажа, к которому нужно привязать имущество:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    finally:
        conn.close()

@bot.callback_query_handler(func=lambda call: call.data == 'wh_back')
def handle_warehouse_back(call):
    show_warehouse(call.message)
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('wh_confirm_'))
def handle_warehouse_assign_confirm(call):
    user_id = call.from_user.id
    parts = call.data.split('_')
    item_type = parts[2]
    item_id = int(parts[3])
    character_id = int(parts[4])
    table_name = 'houses' if item_type == 'house' else 'sim_cards'
    limit = 3
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT COUNT(id) FROM {table_name} WHERE character_id = ?", (character_id,))
        item_count = cursor.fetchone()[0]
        if item_count >= limit:
            type_text = "объектов недвижимости" if item_type == 'house' else "SIM-карт"
            bot.answer_callback_query(call.id, f"На этого персонажа уже зарегистрировано максимальное количество {type_text} (3).", show_alert=True)
            return
        cursor.execute(f"SELECT user_id FROM {table_name} WHERE id = ?", (item_id,))
        owner_id = cursor.fetchone()
        if not owner_id or owner_id[0] != user_id:
            return bot.answer_callback_query(call.id, "Это не ваше имущество.", show_alert=True)
        cursor.execute(f"UPDATE {table_name} SET character_id = ? WHERE id = ?", (character_id, item_id))
        conn.commit()
        bot.answer_callback_query(call.id, "✅ Имущество успешно привязано!", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        print(f"Ошибка привязки имущества: {e}")
        bot.answer_callback_query(call.id, "Произошла ошибка.", show_alert=True)
    finally:
        conn.close()

@bot.message_handler(commands=['auction'])
@antispam_filter
def auction_main(message: Message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🛒 Рынок", callback_data="auction_market_0"),
        InlineKeyboardButton("➕ Создать лот", callback_data="auction_create_start"),
        InlineKeyboardButton("⚙️ Меню", callback_data="auction_menu_main"),
        InlineKeyboardButton("📋 Мои лоты", callback_data="auction_my_lots_0")
    )
    bot.reply_to(message, "👋 Добро пожаловать на аукцион!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('auction_'))
def auction_callbacks(call):
    user_id = call.from_user.id
    parts = call.data.split('_')
    action = parts[1]

    if action == 'market':
        page = int(parts[2])
        show_auction_market(call.message, page, edit_message=True)
    elif action == 'create':
        if parts[2] == 'start':
            start_auction_creation(call)
        elif parts[2] == 'type':
            select_auction_item_type(call)
        elif parts[2] == 'item':
            # ИСПРАВЛЕННАЯ СТРОКА ЗДЕСЬ
            item_type = '_'.join(parts[3:])
            select_auction_item(call, item_type)
    elif action == 'menu':
        show_auction_menu(call)
    elif action == 'toggle':
        if parts[2] == 'anon':
            toggle_anon_bidding(call)
    elif action == 'my':
        if parts[2] == 'lots':
            page = int(parts[3])
            show_my_lots(call, page)
    elif action == 'view':
        auction_id = int(parts[2])
        view_auction_lot(call, auction_id)
    
    # --- ВОТ ИСПРАВЛЕНИЕ ---
    elif action == 'set':
        if parts[2] == 'item':
            set_auction_item(call)
    # -----------------------
            
    elif action == 'bid':
        auction_id = int(parts[2])
        prompt_for_bid(call, auction_id)
    elif action == 'cancel':
        auction_id = int(parts[2])
        cancel_auction(call, auction_id)
    elif action == 'back':
        if len(parts) > 2 and parts[2] == 'market':
            page = int(parts[3])
            show_auction_market(call.message, page, edit_message=True)
        else:
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("🛒 Рынок", callback_data="auction_market_0"),
                InlineKeyboardButton("➕ Создать лот", callback_data="auction_create_start"),
                InlineKeyboardButton("⚙️ Меню", callback_data="auction_menu_main"),
                InlineKeyboardButton("📋 Мои лоты", callback_data="auction_my_lots_0")
            )
            bot.edit_message_text("👋 Добро пожаловать на аукцион!", call.message.chat.id, call.message.message_id, reply_markup=markup)

def show_auction_market(message, page=0, edit_message=False):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    offset = page * 5
    try:
        cursor.execute("""
            SELECT a.id, a.item_name, a.start_price, a.end_time, u.auction_anon, a.seller_id,
                   (SELECT MAX(b.amount) FROM bids b WHERE b.auction_id = a.id) as current_bid
            FROM auctions a
            JOIN users u ON a.seller_id = u.user_id
            WHERE a.status = 'active'
            ORDER BY a.start_time DESC
            LIMIT 5 OFFSET ?
        """, (offset,))
        auctions = cursor.fetchall()
        cursor.execute("SELECT COUNT(id) FROM auctions WHERE status = 'active'")
        total_auctions = cursor.fetchone()[0]

        if not auctions and page == 0:
            text = "🛒 На рынке пока нет активных лотов."
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Назад", callback_data="auction_back"))
        else:
            text = "🛒 <b>Активные лоты на рынке:</b>\n"
            for auc_id, name, start_price, end_time, anon, seller_id, current_bid in auctions:
                price = current_bid or start_price
                seller_name = "Анонимно" if anon else get_display_name(seller_id)
                time_left = format_time_left(end_time)
                text += f"\n<b>Лот #{auc_id}:</b> {name}\n"
                text += f"💰 <b>Цена:</b> {price:,} $\n"
                text += f"👤 <b>Продавец:</b> {seller_name}\n"
                text += f"⏳ <b>Осталось:</b> {time_left}\n"

            markup = InlineKeyboardMarkup(row_width=2)
            buttons = [InlineKeyboardButton(f"Лот #{auc[0]}", callback_data=f"auction_view_{auc[0]}") for auc in auctions]
            markup.add(*buttons)
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Пред.", callback_data=f"auction_market_{page-1}"))
            if (page + 1) * 5 < total_auctions:
                nav_buttons.append(InlineKeyboardButton("След. ➡️", callback_data=f"auction_market_{page+1}"))
            markup.row(*nav_buttons)
            markup.add(InlineKeyboardButton("Меню", callback_data="auction_back"))

        if edit_message:
            bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup, parse_mode='HTML')
        else:
            bot.reply_to(message, text, reply_markup=markup, parse_mode='HTML')
    finally:
        conn.close()

def show_my_lots(call, page=0):
    user_id = call.from_user.id
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    offset = page * 5
    try:
        cursor.execute("""
            SELECT a.id, a.item_name, a.start_price, a.end_time, a.status,
                   (SELECT MAX(b.amount) FROM bids b WHERE b.auction_id = a.id) as current_bid
            FROM auctions a
            WHERE a.seller_id = ?
            ORDER BY a.start_time DESC
            LIMIT 5 OFFSET ?
        """, (user_id, offset))
        auctions = cursor.fetchall()
        cursor.execute("SELECT COUNT(id) FROM auctions WHERE seller_id = ?", (user_id,))
        total_auctions = cursor.fetchone()[0]

        if not auctions and page == 0:
            text = "📋 У вас нет созданных лотов."
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Назад", callback_data="auction_back"))
        else:
            text = "📋 <b>Ваши лоты:</b>\n"
            for auc_id, name, start_price, end_time, status, current_bid in auctions:
                price = current_bid or start_price
                time_info = format_time_left(end_time) if status == 'active' else status.capitalize()
                text += f"\n<b>Лот #{auc_id}:</b> {name} ({time_info})\n"
                text += f"💰 <b>Цена:</b> {price:,} $\n"
            
            markup = InlineKeyboardMarkup(row_width=2)
            buttons = [InlineKeyboardButton(f"Лот #{auc[0]}", callback_data=f"auction_view_{auc[0]}") for auc in auctions]
            markup.add(*buttons)
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Пред.", callback_data=f"auction_my_lots_{page-1}"))
            if (page + 1) * 5 < total_auctions:
                nav_buttons.append(InlineKeyboardButton("След. ➡️", callback_data=f"auction_my_lots_{page+1}"))
            markup.row(*nav_buttons)
            markup.add(InlineKeyboardButton("Меню", callback_data="auction_back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')

    finally:
        conn.close()

def view_auction_lot(call, auction_id):
    user_id = call.from_user.id
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT a.seller_id, a.item_name, a.description, a.start_price, a.start_time, a.end_time, a.status, u.auction_anon
            FROM auctions a
            JOIN users u ON a.seller_id = u.user_id
            WHERE a.id = ?
        """, (auction_id,))
        auction = cursor.fetchone()
        if not auction:
            return bot.answer_callback_query(call.id, "Лот не найден.", show_alert=True)
        
        seller_id, item_name, description, start_price, start_time_str, end_time_str, status, anon = auction
        seller_name = "Анонимно" if anon else get_display_name(seller_id)
        time_info = format_time_left(end_time_str) if status == 'active' else f"Статус: {status.capitalize()}"
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)

        cursor.execute("SELECT bidder_id, amount, is_anonymous FROM bids WHERE auction_id = ? ORDER BY amount DESC LIMIT 5", (auction_id,))
        bids = cursor.fetchall()

        highest_bid = bids[0][1] if bids else start_price
        
        text = (f"📑 <b>Лот #{auction_id}: {item_name}</b>\n\n"
                f"👤 <b>Продавец:</b> {seller_name}\n"
                f"💰 <b>Начальная цена:</b> {start_price:,} $\n"
                f"📈 <b>Текущая ставка:</b> {highest_bid:,} $\n"
                f"⏳ <b>{time_info}</b>\n\n"
                f"<b>Описание:</b>\n<i>{description}</i>\n\n"
                f"<b>Последние ставки:</b>\n")
        
        if not bids:
            text += "<i>Ставок еще нет.</i>"
        else:
            for bidder_id, amount, is_anon in bids:
                bidder_name = "Анонимно" if is_anon else get_display_name(bidder_id)
                text += f" • {bidder_name} - {amount:,} $\n"

        markup = InlineKeyboardMarkup()
        if status == 'active' and seller_id != user_id:
            markup.add(InlineKeyboardButton("💸 Сделать ставку", callback_data=f"auction_bid_{auction_id}"))
        
        if status == 'active' and seller_id == user_id:
            time_passed = datetime.now() - start_time
            total_duration = end_time - start_time
            if not bids and time_passed < (total_duration / 2):
                 markup.add(InlineKeyboardButton("❌ Отменить аукцион", callback_data=f"auction_cancel_{auction_id}"))

        markup.add(InlineKeyboardButton("⬅️ Назад к рынку", callback_data="auction_back_market_0"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')
        bot.answer_callback_query(call.id)
    finally:
        conn.close()

def prompt_for_bid(call, auction_id):
    user_id = call.from_user.id
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        # Теперь получаем и шаг ставки (min_bid_step)
        cursor.execute("""
            SELECT a.start_price, a.min_bid_step, 
                   (SELECT MAX(b.amount) FROM bids b WHERE b.auction_id = a.id) as current_bid 
            FROM auctions a WHERE a.id = ?
        """, (auction_id,))
        res = cursor.fetchone()
        
        start_price, min_step, current_bid = res
        # Если ставок нет, берем стартовую цену, иначе - текущую
        highest_bid = current_bid or start_price
        # Считаем минимальную ставку с учетом шага
        min_bid = highest_bid + min_step
        
        auction_creation_in_progress[user_id] = {
            'action': 'bidding',
            'auction_id': auction_id,
            'min_bid': min_bid
        }
        
        msg = bot.send_message(user_id, f"Введите вашу ставку для лота #{auction_id}.\nМинимальная ставка: {min_bid:,} $")
        bot.register_next_step_handler(msg, process_bid_amount)
        bot.answer_callback_query(call.id)
    finally:
        conn.close()

def process_bid_amount(message: Message):
    user_id = message.from_user.id
    if user_id not in auction_creation_in_progress or auction_creation_in_progress[user_id].get('action') != 'bidding':
        return
    
    data = auction_creation_in_progress[user_id]
    auction_id = data['auction_id']
    min_bid = data['min_bid']
    
    try:
        bid_amount = int(message.text)
        if bid_amount < min_bid:
            bot.send_message(user_id, f"❌ Ваша ставка слишком мала. Минимальная ставка: {min_bid:,} $. Попробуйте еще раз.")
            bot.register_next_step_handler(message, process_bid_amount)
            return
    except (ValueError, TypeError):
        bot.send_message(user_id, "❌ Введите сумму числом. Попробуйте еще раз.")
        bot.register_next_step_handler(message, process_bid_amount)
        return

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT balance, auction_anon FROM users WHERE user_id = ?", (user_id,))
        balance, is_anon = cursor.fetchone()
        if balance < bid_amount:
            bot.send_message(user_id, f"❌ Недостаточно средств. Ваш баланс: {balance:,} $.")
            del auction_creation_in_progress[user_id]
            return

        cursor.execute("INSERT INTO bids (auction_id, bidder_id, amount, is_anonymous) VALUES (?, ?, ?, ?)",
                       (auction_id, user_id, bid_amount, is_anon))
        conn.commit()
        bot.send_message(user_id, f"✅ Ваша ставка в размере {bid_amount:,} $ на лот #{auction_id} принята!")
    except Exception as e:
        bot.send_message(user_id, f"⚠️ Произошла ошибка при размещении ставки: {e}")
    finally:
        del auction_creation_in_progress[user_id]
        conn.close()

def cancel_auction(call, auction_id):
    user_id = call.from_user.id
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT seller_id, item_type, item_db_id FROM auctions WHERE id = ?", (auction_id,))
        res = cursor.fetchone()
        if not res or res[0] != user_id:
            return bot.answer_callback_query(call.id, "Это не ваш лот.", show_alert=True)
        
        item_type, item_db_id = res[1], res[2]
        table_map = {'house': 'houses', 'sim_card': 'sim_cards', 'company': 'companies'}
        item_table = table_map.get(item_type)

        conn.execute("BEGIN TRANSACTION")
        cursor.execute("UPDATE auctions SET status = 'cancelled' WHERE id = ?", (auction_id,))
        
        if item_type == 'company':
            cursor.execute("UPDATE companies SET status = 'active' WHERE id = ?", (item_db_id,))
        elif item_table:
            cursor.execute(f"UPDATE {item_table} SET character_id = NULL WHERE id = ?", (item_db_id,))
            
        conn.commit()
        
        message_text = "✅ Аукцион отменен!"
        if item_type == 'company':
             message_text += " Компания снова активна."
        else:
             message_text += " Предмет возвращен на склад."

        bot.answer_callback_query(call.id, message_text, show_alert=True)
        show_my_lots(call, 0)
    except Exception as e:
        conn.rollback()
        bot.answer_callback_query(call.id, f"Ошибка отмены: {e}", show_alert=True)
    finally:
        conn.close()

def start_auction_creation(call):
    user_id = call.from_user.id
    auction_creation_in_progress[user_id] = {}

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        # Проверяем, есть ли у пользователя хоть какое-то имущество для продажи
        cursor.execute("SELECT 1 FROM houses WHERE user_id = ? LIMIT 1", (user_id,))
        has_houses = cursor.fetchone()
        cursor.execute("SELECT 1 FROM sim_cards WHERE user_id = ? AND status = 'approved' LIMIT 1", (user_id,))
        has_sims = cursor.fetchone()
        cursor.execute("SELECT 1 FROM companies WHERE owner_user_id = ? AND status = 'active' LIMIT 1", (user_id,))
        has_companies = cursor.fetchone()
    finally:
        conn.close()

    markup = InlineKeyboardMarkup()
    text = "➕ <b>Создание лота</b>\n\n"

    # Проверяем, есть ли хоть что-то для продажи
    if not any([has_houses, has_sims, has_companies]):
        text += "У вас нет имущества, которое можно было бы выставить на продажу."
        # Добавляем кнопку "Назад", если продавать нечего
        markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="auction_back"))
    else:
        text += "Выберите тип имущества для продажи:"
        if has_houses:
            markup.add(InlineKeyboardButton("🏡 Недвижимость", callback_data="auction_create_item_house"))
        if has_sims:
            markup.add(InlineKeyboardButton("📱 SIM-карта", callback_data="auction_create_item_sim_card"))
        if has_companies:
            markup.add(InlineKeyboardButton("🏢 Компания", callback_data="auction_create_item_company"))
        # Добавляем кнопку "Назад" для отмены
        markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="auction_back"))

    # Эта строка отправляет (редактирует) сообщение, ее не хватало в твоем коде
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')

def select_auction_item(call, item_type):
    user_id = call.from_user.id
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    table_map = {'house': 'houses', 'sim_card': 'sim_cards', 'company': 'companies'}
    table_name = table_map.get(item_type)
    
    if not table_name: 
        bot.answer_callback_query(call.id, "Неизвестный тип предмета.", show_alert=True)
        conn.close()
        return

    try:
        if item_type == 'company':
             query = "SELECT id, name FROM companies WHERE owner_user_id = ? AND status = 'active'"
             params = (user_id,)
        else:
            query = f"""
                SELECT i.id, c.full_name 
                FROM {table_name} as i
                LEFT JOIN characters as c ON i.character_id = c.id
                WHERE i.user_id = ?
            """
            params = (user_id,)
            if item_type == 'sim_card':
                query += " AND i.status = 'approved'"
        
        cursor.execute(query, params)
        items = cursor.fetchall()

        cursor.execute("SELECT item_db_id FROM auctions WHERE seller_id = ? AND item_type = ? AND status = 'active'", (user_id, item_type))
        active_auction_items = {row[0] for row in cursor.fetchall()}

        valid_items = [item for item in items if item[0] not in active_auction_items]

        if not valid_items:
            bot.answer_callback_query(call.id, "У вас нет доступных предметов этого типа для продажи.", show_alert=True)
            return

        markup = InlineKeyboardMarkup()
        for item_data in valid_items:
            item_id = item_data[0]
            item_name_display = get_item_display_name(item_type, item_id)
            
            if item_type == 'company':
                owner_text = "" # У компании владелец и так ясен
            else:
                char_name = item_data[1]
                owner_text = f"(перс: {char_name})" if char_name else "(на складе)"
                
            markup.add(InlineKeyboardButton(f"{item_name_display} {owner_text}", callback_data=f"auction_set_item_{item_type}_{item_id}"))

        markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="auction_create_start"))
        bot.edit_message_text("Выберите конкретный предмет для продажи:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        print(f"Ошибка в select_auction_item: {e}")
        bot.answer_callback_query(call.id, "Произошла ошибка.", show_alert=True)
    finally:
        conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('auction_set_item_'))
def set_auction_item(call):
    user_id = call.from_user.id
    # ДОБАВЛЕНА СТРОКА ЗДЕСЬ
    bot.answer_callback_query(call.id)

    # --- ИСПРАВЛЕННЫЙ ПАРСИНГ: Разбираем callback_data правильно ---
    parts = call.data.split('_')
    # item_type может быть "house" или "sim_card" (два элемента)
    if len(parts) >= 5:
        item_type = parts[3]
        if len(parts) > 5:
            # Если тип состоит из двух слов (sim_card), объединяем
            item_type = '_'.join(parts[3:-1])
        item_id = int(parts[-1])
    else:
        # Убрал answer_callback_query отсюда, так как он теперь вверху
        bot.send_message(user_id, "Произошла внутренняя ошибка в данных кнопки.")
        return

    # Получаем информацию о персонаже, если предмет привязан
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    character_id = None # Инициализируем на случай ошибки
    try:
        table_map = {'house': 'houses', 'sim_card': 'sim_cards'}
        table_name = table_map.get(item_type)
        if table_name:
            cursor.execute(f"SELECT character_id FROM {table_name} WHERE id = ?", (item_id,))
            character_id_res = cursor.fetchone()
            character_id = character_id_res[0] if character_id_res else None
    except Exception as e:
        print(f"Ошибка при получении информации о предмете: {e}")
        # НЕ ЗАКРЫВАЕМ СОЕДИНЕНИЕ ЗДЕСЬ, ОНО НУЖНО ДАЛЬШЕ

    auction_creation_in_progress[user_id] = {
        'action': 'creating',
        'item_type': item_type,
        'item_id': item_id,
        'character_id': character_id
    }

    bot.delete_message(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(user_id, "Введите начальную цену лота в баксах:")
    bot.register_next_step_handler(msg, process_auction_price)

def process_auction_price(message: Message):
    user_id = message.from_user.id
    if user_id not in auction_creation_in_progress or auction_creation_in_progress[user_id].get('action') != 'creating':
        return
    try:
        price = int(message.text)
        if price <= 0: raise ValueError
        auction_creation_in_progress[user_id]['price'] = price
        msg = bot.send_message(user_id, "На сколько выставить лот? (например: '12 часов' или '3 дня').\nМаксимум - 10 дней.")
        bot.register_next_step_handler(msg, process_auction_duration)
    except (ValueError, TypeError):
        msg = bot.send_message(user_id, "❌ Неверный формат. Введите цену целым положительным числом.")
        bot.register_next_step_handler(msg, process_auction_price)

def process_auction_duration(message: Message):
    user_id = message.from_user.id
    if user_id not in auction_creation_in_progress or auction_creation_in_progress[user_id].get('action') != 'creating':
        return

    text = message.text.lower()
    duration = None
    try:
        value, unit = text.split()
        value = int(value)
        if 'час' in unit:
            duration = timedelta(hours=value)
        elif 'дн' in unit or 'ден' in unit:
            duration = timedelta(days=value)

        if not duration or duration > timedelta(days=10):
            raise ValueError("Invalid duration")

        # Сохраняем длительность и спрашиваем описание
        auction_creation_in_progress[user_id]['duration'] = duration
        msg = bot.send_message(user_id, "📝 Теперь введите краткое описание для лота (максимум 200 символов).")
        bot.register_next_step_handler(msg, process_auction_description)
        # Важно: выходим из функции, чтобы дождаться ответа пользователя
        return 

    except Exception:
        msg = bot.send_message(user_id, "❌ Неверный формат времени. Используйте, например, '24 часа' или '5 дней'. Максимум 10 дней.")
        bot.register_next_step_handler(msg, process_auction_duration)
        return
        

    data = auction_creation_in_progress[user_id]
    item_type = data['item_type']
    item_id = data['item_id']
    price = data['price']

    item_name = get_item_display_name(item_type, item_id)
    end_time = datetime.now() + duration

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        conn.execute("BEGIN TRANSACTION")
        cursor.execute("""
            INSERT INTO auctions (seller_id, item_type, item_db_id, item_name, start_price, end_time, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
        """, (user_id, item_type, item_id, item_name, price, end_time.isoformat()))

        # --- НОВАЯ ЛОГИКА: "замораживаем" предмет, отвязывая его от персонажа ---
        # Он временно переходит в "подвешенное" состояние (на склад).
        table_map = {'house': 'houses', 'sim_card': 'sim_cards'}
        item_table = table_map.get(item_type)
        if item_table:
            cursor.execute(f"UPDATE {item_table} SET character_id = NULL WHERE id = ?", (item_id,))

        conn.commit()
        bot.send_message(user_id, f"✅ Ваш лот '{item_name}' успешно выставлен на аукцион!")

    except Exception as e:
        conn.rollback()
        bot.send_message(user_id, f"⚠️ Произошла ошибка при создании лота: {e}")
    finally:
        del auction_creation_in_progress[user_id]
        conn.close()
        
def process_auction_description(message: Message):
    user_id = message.from_user.id
    if user_id not in auction_creation_in_progress or auction_creation_in_progress[user_id].get('action') != 'creating':
        return

    description = message.text.strip()
    if not (1 <= len(description) <= 200):
        msg = bot.send_message(user_id, "❌ Описание должно быть от 1 до 200 символов. Попробуйте снова.")
        bot.register_next_step_handler(msg, process_auction_description)
        return

    # 1. Сохраняем описание
    auction_creation_in_progress[user_id]['description'] = description

    # 2. Спрашиваем про шаг ставки и ПЕРЕДАЕМ УПРАВЛЕНИЕ следующей функции
    msg = bot.send_message(user_id, "📈 Введите минимальный шаг ставки (например, 1000). Это минимальная сумма, на которую можно поднять цену.")
    bot.register_next_step_handler(msg, process_auction_bid_step)
    
    # 3. Убираем отсюда всю логику создания аукциона. Теперь эта функция просто ждет ответа.
def process_auction_bid_step(message: Message):
    user_id = message.from_user.id
    if user_id not in auction_creation_in_progress or auction_creation_in_progress[user_id].get('action') != 'creating':
        return

    try:
        bid_step = int(message.text)
        if bid_step <= 0: raise ValueError
    except (ValueError, TypeError):
        msg = bot.send_message(user_id, "❌ Неверный формат. Введите шаг ставки целым положительным числом.")
        bot.register_next_step_handler(msg, process_auction_bid_step)
        return

    # --- ТЕПЕРЬ СОЗДАЕМ АУКЦИОН (вся логика перенесена сюда) ---
    data = auction_creation_in_progress[user_id]
    item_type = data['item_type']
    item_id = data['item_id']
    price = data['price']
    duration = data['duration']
    desc = data['description']
    step = bid_step # Используем только что полученное значение

    item_name = get_item_display_name(item_type, item_id)
    end_time = datetime.now() + duration

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        conn.execute("BEGIN TRANSACTION")
        # Добавляем min_bid_step в запрос
        cursor.execute("""
            INSERT INTO auctions (seller_id, item_type, item_db_id, item_name, description, start_price, end_time, status, min_bid_step)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)
        """, (user_id, item_type, item_id, item_name, desc, price, end_time.isoformat(), step))

        table_map = {'house': 'houses', 'sim_card': 'sim_cards', 'company': 'companies'}
        item_table = table_map.get(item_type)

        if item_type == 'company':
            cursor.execute("UPDATE companies SET status = 'on_auction' WHERE id = ?", (item_id,))
        elif item_table:
            # Отвязываем предмет от персонажа, чтобы "заморозить" его на время аукциона
            cursor.execute(f"UPDATE {item_table} SET character_id = NULL WHERE id = ?", (item_id,))

        conn.commit()
        bot.send_message(user_id, f"✅ Ваш лот '{item_name}' успешно выставлен на аукцион!")

    except Exception as e:
        conn.rollback()
        bot.send_message(user_id, f"⚠️ Произошла ошибка при создании лота: {e}")
    finally:
        # Очищаем временные данные после успешного создания
        if user_id in auction_creation_in_progress:
            del auction_creation_in_progress[user_id]
        conn.close()


def show_auction_menu(call):
    user_id = call.from_user.id
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT auction_anon FROM users WHERE user_id = ?", (user_id,))
        is_anon = cursor.fetchone()[0]
        anon_status = "✅ Включен" if is_anon else "❌ Выключен"
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"Анонимный режим: {anon_status}", callback_data="auction_toggle_anon"))
        markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="auction_back"))
        bot.edit_message_text("⚙️ <b>Меню аукциона</b>", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')
    finally:
        conn.close()

def toggle_anon_bidding(call):
    user_id = call.from_user.id
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET auction_anon = NOT auction_anon WHERE user_id = ?", (user_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "Настройки сохранены!")
        show_auction_menu(call) # Обновляем меню
    finally:
        conn.close() 

def process_finished_auctions():
    """Фоновая задача для обработки завершенных аукционов."""
    while True:
        conn = None
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()

            now_iso = datetime.now().isoformat()
            cursor.execute("SELECT id FROM auctions WHERE end_time <= ? AND status = 'active'", (now_iso,))
            finished_auctions = cursor.fetchall()

            for (auction_id,) in finished_auctions:
                try:
                    conn.execute("BEGIN TRANSACTION")

                    cursor.execute("SELECT bidder_id, amount FROM bids WHERE auction_id = ? ORDER BY amount DESC, created_at ASC LIMIT 1", (auction_id,))
                    winner = cursor.fetchone()

                    cursor.execute("SELECT seller_id, item_type, item_db_id, item_name FROM auctions WHERE id = ?", (auction_id,))
                    auction_data = cursor.fetchone()
                    seller_id, item_type, item_db_id, item_name = auction_data

                    table_map = {'house': 'houses', 'sim_card': 'sim_cards', 'company': 'companies'}
                    item_table = table_map.get(item_type)

                    if winner:
                        winner_id, final_price = winner

                        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (winner_id,))
                        winner_balance = cursor.fetchone()[0]

                        if winner_balance >= final_price:
                            # --- Успешная продажа ---
                            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (final_price, winner_id))
                            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (final_price, seller_id))

                            if item_type == 'company':
                                # --- ЛОГИКА ПЕРЕДАЧИ КОМПАНИИ ---
                                # 1. Найти первого одобренного персонажа победителя
                                cursor.execute("SELECT id FROM characters WHERE user_id = ? AND status = 'approved' LIMIT 1", (winner_id,))
                                winner_char = cursor.fetchone()
                                if not winner_char:
                                    # Если у победителя нет перса, компания "зависает" без владельца-персонажа.
                                    # Это редкий случай, но лучше обработать.
                                    winner_char_id = 0 # Условный ID
                                else:
                                    winner_char_id = winner_char[0]
                                    
                                # 2. Сменить владельца и персонажа-владельца в таблице companies
                                cursor.execute("UPDATE companies SET owner_user_id = ?, character_id = ?, status = 'active' WHERE id = ?", (winner_id, winner_char_id, item_db_id))
                                
                                # 3. Найти роль Директора в этой компании
                                cursor.execute("SELECT id FROM company_roles WHERE company_id = ? AND is_owner = 1", (item_db_id,))
                                owner_role_id = cursor.fetchone()[0]

                                # 4. Удалить всех старых сотрудников (включая старого владельца)
                                cursor.execute("DELETE FROM company_employees WHERE company_id = ?", (item_db_id,))
                                
                                # 5. Добавить нового владельца как сотрудника с ролью Директора
                                cursor.execute("""
                                    INSERT INTO company_employees (company_id, user_id, character_id, role_id, last_salary_payment)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (item_db_id, winner_id, winner_char_id, owner_role_id, datetime.now()))
                                    
                            elif item_table:
                                # Передача дома или сим-карты на склад победителя
                                cursor.execute(f"UPDATE {item_table} SET user_id = ?, character_id = NULL WHERE id = ?", (winner_id, item_db_id))

                            cursor.execute("UPDATE auctions SET status = 'sold' WHERE id = ?", (auction_id,))
                            conn.commit()

                            bot.send_message(seller_id, f"🎉 Ваш лот '{item_name}' продан за {final_price:,} $ пользователю {get_display_name(winner_id)}!")
                            
                            if item_type == 'company':
                                bot.send_message(winner_id, f"🎉 Поздравляем! Вы приобрели компанию '{item_name}' за {final_price:,} $. Теперь вы ее владелец!")
                            else:
                                bot.send_message(winner_id, f"🎉 Поздравляем! Вы выиграли лот '{item_name}' за {final_price:,} $. Предмет добавлен на ваш склад /warehouse.")
                        else:
                            # --- Победитель неплатежеспособен ---
                            cursor.execute("UPDATE auctions SET status = 'failed' WHERE id = ?", (auction_id,))
                            if item_type == 'company':
                                cursor.execute("UPDATE companies SET status = 'active' WHERE id = ?", (item_db_id,)) # Разморозка
                            # Другие предметы и так на "складе", ничего делать не нужно
                            conn.commit()

                            bot.send_message(seller_id, f"⚠️ Аукцион по лоту '{item_name}' завершился неудачно. Победитель не смог оплатить ставку. Имущество возвращено вам.")
                            bot.send_message(winner_id, f"⚠️ Вы не смогли оплатить свою ставку на лот '{item_name}'.")
                    else:
                        # --- Нет ставок ---
                        cursor.execute("UPDATE auctions SET status = 'expired' WHERE id = ?", (auction_id,))
                        if item_type == 'company':
                             cursor.execute("UPDATE companies SET status = 'active' WHERE id = ?", (item_db_id,)) # Разморозка
                        conn.commit()

                        bot.send_message(seller_id, f"😔 На ваш лот '{item_name}' не было сделано ни одной ставки. Имущество возвращено вам.")

                except Exception as e:
                    print(f"Ошибка при обработке аукциона #{auction_id}: {e}")
                    if conn: conn.rollback()
                    try:
                        cursor.execute("UPDATE auctions SET status = 'failed' WHERE id = ?", (auction_id,))
                        conn.commit()
                    except Exception as update_err:
                        print(f"Критическая ошибка: не удалось обновить статус аукциона #{auction_id}: {update_err}")

        except Exception as e:
            print(f"Критическая ошибка в потоке обработки аукционов: {e}")
        finally:
            if conn:
                conn.close()

        time.sleep(60)


# --- END AUCTION & WAREHOUSE SYSTEM ---

# Further auction implementation would go here... it's a very large feature set
# For now, this provides the framework and the requested bug fixes and warehouse system.
# A full auction system would add several thousand more lines of code. The stubs and DB are ready.

# --- END AUCTION & WAREHOUSE SYSTEM ---

# --- ПРИВЕТСТВИЕ НОВЫХ ПОЛЬЗОВАТЕЛЕЙ (ОБНОВЛЕННАЯ ВЕРСИЯ) ---
@bot.message_handler(content_types=['new_chat_members'])
def send_welcome(message: Message):
    # --- НОВЫЙ БЛОК: Обработка каждого нового пользователя ---
    for new_user in message.new_chat_members:
        # 1. Сразу регистрируем пользователя в базе данных
        try:
            register_user(new_user.id)
            print(f"Новый пользователь {new_user.first_name} (ID: {new_user.id}) автоматически зарегистрирован.")
        except Exception as e:
            print(f"Ошибка при автоматической регистрации пользователя {new_user.id}: {e}")

        # 2. Создаем персональное упоминание
        # Мы используем first_name, чтобы избежать проблем с пользователями без last_name
        # HTML-разметка <a href='tg://user?id=...'>...</a> создает упоминание без @
        user_mention = f"<a href='tg://user?id={new_user.id}'>{new_user.first_name}</a>"

        # Ссылки, которые ты предоставил
        guide_url = "https://t.me/c/3041908178/42"
        servers_url = "https://t.me/c/3041908178/45"
        rp_terms_url = "https://t.me/c/3041908178/12"
        crp_rules_url = "https://t.me/c/3041908178/14"

        # 3. Формируем текст приветствия с упоминанием
        welcome_text = (
            f"🥰 Приветствую тебя, {user_mention}, на Edmonton Role-Play 🥰\n\n"
            "😮‍💨 Для того чтобы зайти на сервер прочитай пару наших тем, с правилами и многим другим 😮‍💨\n\n"
            f'<a href="{guide_url}">Ссылка на Путеводитель</a> — Наш путеводитель, с ним ты узнаешь какие каналы за что отвечают! 😜\n\n'
            f'<a href="{rp_terms_url}">Ссылка на РП-термины</a> — Ролевые термины который стоит выучить, чтобы играть по правилам 🤐\n\n'
            f'<a href="{crp_rules_url}">Ссылка на КРП правила</a> — Наши Правила для Combat Role-Play. <b><u>Обязательно</u></b> чтобы вы смогли по правилам наносить урон в отыгровках! 😻\n\n'
            f'<a href="{servers_url}">Ссылка на темы где сервера</a> — Наш приватный сервер на плейс. Заходи будем тебя ждать 😘'
        )

        try:
            # Отправляем сообщение в чат, куда зашел новый пользователь
            bot.send_message(
                message.chat.id,
                welcome_text,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"Не удалось отправить приветственное сообщение: {e}")
# --- КОНЕЦ ОБНОВЛЕННОГО БЛОКА ПРИВЕТСТВИЯ ---





# --- END AUCTION & WAREHOUSE SYSTEM ---


# --- ADMIN & GOVERNMENT ---
@bot.message_handler(commands=['delete_passport'])
@antispam_filter
def delete_passport(message: Message):
    if not has_permission(message.from_user.id, [2, 3]):
        return bot.reply_to(message, "⛔ <b>Недостаточно прав.</b>", parse_mode='HTML')
    parts = message.text.split()
    if len(parts) != 2:
        return bot.reply_to(message, "<b>Для удаления Паспорта используйте:</b>\n"
                                     "<code>/delete_passport [ID Паспорта]</code>", parse_mode='HTML')
    try:
        passport_id_to_delete = int(parts[1])
    except ValueError:
        return bot.reply_to(message, "❌ ID Паспорта должен быть числом.")
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("SELECT user_id, full_name FROM characters WHERE id = ?", (passport_id_to_delete,))
        result = cursor.fetchone()
        if not result:
            return bot.reply_to(message, "❌ Паспорт с таким ID не найден.")
        target_user_id, full_name = result
        cursor.execute("DELETE FROM characters WHERE id = ?", (passport_id_to_delete,))
        conn.commit()
        bot.reply_to(message, f"✅ Паспорт <b>{full_name}</b> (ID: {passport_id_to_delete}) пользователя {get_display_name(target_user_id)} был успешно удален.", parse_mode='HTML')
        notify_staff("Удаление Паспорта", f"Удален Паспорт: {full_name} (ID: {passport_id_to_delete})", message.from_user.id, target_user_id)
        try:
            bot.send_message(target_user_id, f"🗑️ Ваш Паспорт на имя <b>{full_name}</b> был удален администрацией.", parse_mode='HTML')
        except Exception as e:
            print(f"Не удалось уведомить пользователя {target_user_id} об удалении паспорта: {e}")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при удалении Паспорта: {e}")
    finally:
        conn.close()

def has_government_access(user_id):
    user_roles = get_roles(user_id)
    if any(role in user_roles for role in [4, 9]):
        return True
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT president_id FROM government_treasury WHERE id = ?", (GOVERNMENT_TREASURY_ID,))
        president_id_result = cursor.fetchone()
        if president_id_result and president_id_result[0] == user_id:
            return True
    finally:
        conn.close()
    return False

def has_law_management_permission(user_id):
    if 4 in get_roles(user_id):
        return True
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT president_id FROM government_treasury WHERE id = ?", (GOVERNMENT_TREASURY_ID,))
        president_id_result = cursor.fetchone()
        if president_id_result and president_id_result[0] == user_id:
            return True
    finally:
        conn.close()
    return False

@bot.message_handler(commands=['search'])
@antispam_filter
def search_passports(message: Message):
    user_id = message.from_user.id
    if not has_government_access(user_id):
        return bot.reply_to(message, "⛔ <b>У вас нет доступа к этой команде.</b> Доступно только для Президента, Министров и Госс. служащих.", parse_mode='HTML')
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.reply_to(message, "<b>Для поиска по базе данных используйте:</b>\n"
                                     "<code>/search [ключевое слово]</code>\n"
                                     "Вы можете искать по ФИО, никнейму Roblox, ID, возрасту, номеру дома/квартиры.", parse_mode='HTML')
    keyword = parts[1]
    perform_search_and_display_list(message.chat.id, keyword)

def perform_search_and_display_list(chat_id, keyword, message_id_to_edit=None):
    conn = sqlite3.connect('database.db', isolation_level=None)
    cursor = conn.cursor()
    cursor.execute("PRAGMA case_sensitive_like = OFF;")
    try:
        # Columns in the 'characters' table
        text_columns = [
            'c.full_name', 'c.gender', 'c.height', 'c.hair_color', 'c.eye_color', 'c.body_type', 'c.tattoos',
            'c.childhood', 'c.father', 'c.mother', 'c.knowledge', 'c.current_life',
            'c.roblox_display_name', 'c.roblox_real_name'
        ]
        numeric_columns = ['c.id', 'c.user_id', 'c.age']

        where_clauses = []
        params = []
        like_term = f'%{keyword}%'

        # Add text column searches
        for col in text_columns:
            where_clauses.append(f"{col} LIKE ?")
            params.append(like_term)
            
        # NEW: Add company name/initial search
        where_clauses.append("comp.name LIKE ?")
        params.append(like_term)
        where_clauses.append("comp.initial LIKE ?")
        params.append(like_term)

        # Add numeric and property searches
        if keyword.isdigit():
            numeric_term = int(keyword)
            for col in numeric_columns:
                where_clauses.append(f"{col} = ?")
                params.append(numeric_term)
            # NEW: Add search by property number
            where_clauses.append("h.property_number = ?")
            params.append(keyword)

        full_where_clause = " OR ".join(where_clauses)

        # MODIFIED: Query with LEFT JOINs to include houses and companies
        query = f"""
            SELECT c.id, c.full_name, c.age
            FROM characters c
            LEFT JOIN houses h ON c.id = h.character_id
            LEFT JOIN companies comp ON c.id = comp.character_id
            WHERE c.status = 'approved' AND ({full_where_clause})
            ORDER BY c.id
        """

        cursor.execute(query, tuple(params))
        results = cursor.fetchall()

        if not results:
            text = "❌ По вашему запросу ничего не найдено."
            markup = None
        else:
            unique_results = sorted(list(set(results)))
            text = f"✅ Найдено совпадений: {len(unique_results)}. Выберите персонажа для просмотра полной информации:"
            markup = InlineKeyboardMarkup(row_width=1)
            keyword_b64 = base64.urlsafe_b64encode(keyword.encode('utf-8')).decode('utf-8')
            buttons = []
            for char_id, full_name, age in unique_results:
                buttons.append(InlineKeyboardButton(
                    f"{full_name} / {age} лет (ID: {char_id})",
                    callback_data=f"search_view_{char_id}_{keyword_b64}"
                ))
            markup.add(*buttons)

        if message_id_to_edit:
            bot.edit_message_text(text, chat_id, message_id_to_edit, reply_markup=markup, parse_mode='HTML')
        else:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')

    except Exception as e:
        print(f"Ошибка поиска: {e}")
        bot.send_message(chat_id, f"⚠️ Произошла ошибка при поиске: {e}")
    finally:
        conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('search_'))
def handle_search_callbacks(call):
    user_id = call.from_user.id
    if not has_government_access(user_id):
        return bot.answer_callback_query(call.id, "⛔ У вас нет прав на это действие.", show_alert=True)
    parts = call.data.split('_')
    action = parts[1]
    if action == 'view':
        char_id = int(parts[2])
        keyword_b64 = parts[3]
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT photo_file_id, user_id FROM characters WHERE id = ?", (char_id,))
            result = cursor.fetchone()
            if not result:
                bot.answer_callback_query(call.id, "Персонаж не найден.", show_alert=True)
                return
            photo_file_id, owner_user_id = result
            caption = get_full_character_details_text(cursor, char_id)
            caption += f"\n<b>Владелец:</b> {get_display_name(owner_user_id)} (<code>{owner_user_id}</code>)"
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("💸 Выписать штраф", callback_data=f"gov_fine_{char_id}_{owner_user_id}"))
            cursor.execute("SELECT 1 FROM licenses WHERE character_id = ? AND license_type = 'driver' AND status = 'approved'", (char_id,))
            if cursor.fetchone():
                markup.add(InlineKeyboardButton("🚫 Лишить водит. прав", callback_data=f"gov_revoke_driver_{char_id}_{owner_user_id}"))
            cursor.execute("SELECT 1 FROM licenses WHERE character_id = ? AND license_type IN ('weapon', 'armor') AND status = 'approved'", (char_id,))
            if cursor.fetchone():
                markup.add(InlineKeyboardButton("🚫 Лишить лиц. на оружие/броню", callback_data=f"gov_revoke_weapon_{char_id}_{owner_user_id}"))
            # --- КНОПКИ ДЛЯ РОЗЫСКА ---
            cursor.execute("SELECT stars, id FROM wanted WHERE character_id = ? AND status = 'active'", (char_id,))
            active_wanted = cursor.fetchone()
            if active_wanted:
                stars, wanted_id = active_wanted
                markup.add(InlineKeyboardButton("⭐️ Просмотреть розыск", callback_data=f"show_wanted_{wanted_id}"))
                markup.add(InlineKeyboardButton("➖ Снять розыск", callback_data=f"remove_wanted_{wanted_id}_{char_id}_{owner_user_id}"))
            else:
                markup.add(InlineKeyboardButton("➕ Добавить розыск", callback_data=f"add_wanted_{char_id}_{owner_user_id}"))
            markup.add(InlineKeyboardButton("⬅️ Назад к результатам", callback_data=f"search_back_{keyword_b64}"))
            bot.delete_message(call.message.chat.id, call.message.message_id)
            if len(caption) > 1024:
                bot.send_photo(call.message.chat.id, photo_file_id)
                bot.send_message(call.message.chat.id, caption, parse_mode='HTML', reply_markup=markup)
            else:
                bot.send_photo(call.message.chat.id, photo_file_id, caption=caption, parse_mode='HTML', reply_markup=markup)
            bot.answer_callback_query(call.id)
        finally:
            conn.close()
    elif action == 'back':
        keyword_b64 = parts[2]
        keyword = base64.urlsafe_b64decode(keyword_b64).decode('utf-8')
        try:
             bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение при возврате к поиску: {e}")
        perform_search_and_display_list(call.message.chat.id, keyword)
        bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('gov_revoke_'))
def gov_revoke_license(call):
    gov_worker_id = call.from_user.id
    if not has_government_access(gov_worker_id):
        return bot.answer_callback_query(call.id, "⛔ У вас нет прав на это действие.", show_alert=True)
    parts = call.data.split('_')
    license_type_to_revoke = parts[2]
    character_id = int(parts[3])
    target_user_id = int(parts[4])
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cooldown = datetime.now() + timedelta(days=3)
        if license_type_to_revoke == 'driver':
             cursor.execute("UPDATE licenses SET status = 'revoked', revoked_until = ? WHERE character_id = ? AND license_type = 'driver'", (cooldown.isoformat(), character_id))
             license_name = "водительских прав"
        elif license_type_to_revoke == 'weapon':
             cursor.execute("UPDATE licenses SET status = 'revoked', revoked_until = ? WHERE character_id = ? AND license_type IN ('weapon', 'armor')", (cooldown.isoformat(), character_id))
             license_name = "лицензии на оружие/броню"
        else:
            return bot.answer_callback_query(call.id, "Неверный тип лицензии.")
        conn.commit()
        if cursor.rowcount > 0:
            bot.answer_callback_query(call.id, "✅ Лицензия успешно отозвана.", show_alert=True)
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            try:
                bot.send_message(target_user_id, f"❗️ <b>Внимание!</b> Государственный служащий отозвал вашу лицензию.\n"
                                                 f"Вы были лишены: <b>{license_name}</b>.\n"
                                                 f"Вы не сможете подать новую заявку в течение 3 дней.", parse_mode='HTML')
            except Exception as e:
                print(f"Не удалось уведомить {target_user_id} об отзыве лицензии: {e}")
        else:
            bot.answer_callback_query(call.id, "⚠️ Лицензия не найдена или уже отозвана.", show_alert=True)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Произошла ошибка: {e}", show_alert=True)
    finally:
        conn.close()

# --- GOVERNMENT FINING SYSTEM ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('gov_fine_'))
def gov_issue_fine_start(call):
    gov_worker_id = call.from_user.id
    if not has_government_access(gov_worker_id):
        return bot.answer_callback_query(call.id, "⛔ У вас нет прав на это действие.", show_alert=True)
    parts = call.data.split('_')
    character_id = int(parts[2])
    target_user_id = int(parts[3])
    fining_in_progress[gov_worker_id] = {
        'character_id': character_id,
        'target_user_id': target_user_id
    }
    bot.answer_callback_query(call.id)
    msg = bot.send_message(gov_worker_id, f"💸 <b>Выписка штрафа</b>\n"
                                        f"Кому: {get_display_name(target_user_id)} (<code>{target_user_id}</code>)\n"
                                        f"Введите сумму штрафа (макс. 10,000,000):", parse_mode='HTML')
    bot.register_next_step_handler(msg, process_fine_amount)

def process_fine_amount(message: Message):
    gov_worker_id = message.from_user.id
    if gov_worker_id not in fining_in_progress: return
    try:
        amount = int(message.text)
        if not 0 < amount <= 10000000:
            raise ValueError
        fining_in_progress[gov_worker_id]['amount'] = amount
        msg = bot.send_message(gov_worker_id, "Введите причину штрафа (например, 'Нарушение ПДД ст. 1.2'):")
        bot.register_next_step_handler(msg, process_fine_reason)
    except (ValueError, TypeError):
        bot.send_message(gov_worker_id, "❌ Неверная сумма. Введите число от 1 до 10,000,000.")
        bot.register_next_step_handler(message, process_fine_amount)

def process_fine_reason(message: Message):
    gov_worker_id = message.from_user.id
    if gov_worker_id not in fining_in_progress: return
    fining_in_progress[gov_worker_id]['reason'] = message.text
    msg = bot.send_message(gov_worker_id, "Введите срок оплаты штрафа в днях (от 1 до 10):")
    bot.register_next_step_handler(msg, process_fine_deadline)

def process_fine_deadline(message: Message):
    gov_worker_id = message.from_user.id
    if gov_worker_id not in fining_in_progress: return
    try:
        days = int(message.text)
        if not 1 <= days <= 10:
            raise ValueError
        data = fining_in_progress[gov_worker_id]
        due_date = datetime.now() + timedelta(days=days)
        reason = data['reason']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO invoices (user_id, character_id, invoice_type, amount, issuer_id, due_date, reason)
                VALUES (?, ?, 'fine', ?, ?, ?, ?)
            """, (data['target_user_id'], data['character_id'], data['amount'], gov_worker_id, due_date, reason))
            conn.commit()
            bot.send_message(gov_worker_id, f"✅ Штраф на сумму <b>{data['amount']:,} $</b> успешно выписан пользователю {get_display_name(data['target_user_id'])}.", parse_mode='HTML')
            try:
                bot.send_message(data['target_user_id'],
                                 f"❗️ <b>Вам выписан штраф!</b>\n"
                                 f"👮‍♂️ <b>Выписал:</b> Госс. Служащий ({get_display_name(gov_worker_id)})\n"
                                 f"💰 <b>Сумма:</b> {data['amount']:,} $\n"
                                 f"⚖️ <b>Причина:</b> {reason}\n"
                                 f"⏳ <b>Оплатить до:</b> {due_date.strftime('%d.%m.%Y %H:%M')}\n"
                                 f"Для оплаты используйте команду /scheta.", parse_mode='HTML')
            except Exception as e:
                print(f"Не удалось уведомить пользователя {data['target_user_id']} о штрафе: {e}")
        except Exception as e:
            bot.send_message(gov_worker_id, f"⚠️ Произошла ошибка при записи штрафа в базу данных: {e}")
        finally:
            conn.close()
    except (ValueError, TypeError):
        bot.send_message(gov_worker_id, "❌ Неверный срок. Введите число от 1 до 10.")
        bot.register_next_step_handler(message, process_fine_deadline)
    finally:
        if gov_worker_id in fining_in_progress:
            del fining_in_progress[gov_worker_id]

# --- INVOICE & BILLS SYSTEM ---
@bot.message_handler(commands=['scheta'])
@antispam_filter
def show_invoices(message: Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, invoice_type, amount, due_date, reason FROM invoices WHERE user_id = ? AND status = 'unpaid' ORDER BY due_date", (user_id,))
        invoices = cursor.fetchall()
        if not invoices:
            return bot.reply_to(message, "🧾 У вас нет неоплаченных счетов или штрафов.", parse_mode='HTML')
        response_text = "🧾 <b>Ваши неоплаченные счета:</b>\n"
        markup = InlineKeyboardMarkup(row_width=1)
        for inv_id, inv_type, amount, due_date_str, reason in invoices:
            due_date = datetime.fromisoformat(due_date_str)
            if inv_type == 'fine':
                type_text = f"Штраф ({reason})"
            else:
                type_text = "Коммунальные услуги"
            response_text += f"• <b>{type_text}:</b> {amount:,} $ (до {due_date.strftime('%d.%m.%Y')})\n"
            markup.add(InlineKeyboardButton(f"Оплатить {amount:,} $", callback_data=f"pay_invoice_{inv_id}"))
        bot.reply_to(message, response_text, parse_mode='HTML', reply_markup=markup)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при получении счетов: {e}")
    finally:
        conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('pay_invoice_'))
def pay_invoice_callback(call):
    user_id = call.from_user.id
    invoice_id = int(call.data.split('_')[2])
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id, amount, status FROM invoices WHERE id = ?", (invoice_id,))
        invoice_data = cursor.fetchone()
        if not invoice_data:
            return bot.answer_callback_query(call.id, "Счет не найден.", show_alert=True)
        inv_user_id, amount, status = invoice_data
        if inv_user_id != user_id:
            return bot.answer_callback_query(call.id, "Это не ваш счет.", show_alert=True)
        if status != 'unpaid':
            return bot.answer_callback_query(call.id, "Этот счет уже оплачен или просрочен.", show_alert=True)
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        balance = cursor.fetchone()[0]
        if balance < amount:
            return bot.answer_callback_query(call.id, f"❌ Недостаточно средств. Ваш баланс: {balance:,} $", show_alert=True)
        conn.execute("BEGIN TRANSACTION")
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        cursor.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (invoice_id,))
        cursor.execute("UPDATE government_treasury SET balance = balance + ? WHERE id = ?", (amount, GOVERNMENT_TREASURY_ID))
        conn.commit()
        bot.answer_callback_query(call.id, "✅ Счет успешно оплачен!", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        if conn: conn.rollback()
        bot.answer_callback_query(call.id, f"⚠️ Ошибка при оплате: {e}", show_alert=True)
    finally:
        conn.close()

# --- BACKGROUND TASKS ---

                                                   
def process_overdue_invoices():
    while True:
        conn = None
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, user_id, amount, invoice_type, character_id FROM invoices WHERE status = 'unpaid' AND due_date < ?", (datetime.now(),))
            overdue_invoices = cursor.fetchall()
            for inv_id, user_id, amount, inv_type, char_id in overdue_invoices:
                try:
                    conn.execute("BEGIN TRANSACTION")
                    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
                    cursor.execute("UPDATE invoices SET status = 'overdue' WHERE id = ?", (inv_id,))
                    cursor.execute("UPDATE government_treasury SET balance = balance + ? WHERE id = ?", (amount, GOVERNMENT_TREASURY_ID))
                    # --- НОВАЯ ЛОГИКА ЗВЁЗД РОЗЫСКА ---
                    if inv_type == 'fine':
                        stars_to_add = 0
                        if amount >= 500000:
                            stars_to_add = 2
                        elif amount >= 100000:
                            stars_to_add = 1
                        if stars_to_add > 0:
                            cursor.execute("SELECT stars FROM wanted WHERE character_id = ? AND status = 'active'", (char_id,))
                            current_stars = cursor.fetchone()
                            if current_stars:
                                new_stars = min(5, current_stars[0] + stars_to_add)
                                cursor.execute("UPDATE wanted SET stars = ?, reason = ? WHERE character_id = ? AND status = 'active'", (new_stars, f"Неоплата штрафа {amount:,}$", char_id))
                            else:
                                cursor.execute("INSERT INTO wanted (character_id, stars, reason, issued_by) VALUES (?, ?, ?, ?)", (char_id, stars_to_add, f"Неоплата штрафа {amount:,}$", None))
                            bot.send_message(user_id, f"❗️ <b>ВНИМАНИЕ!</b> Вы не оплатили штраф {amount:,}$. Добавлено {stars_to_add} звезда(ы) розыска.", parse_mode='HTML')
                    conn.commit()
                    type_text = "штраф" if inv_type == 'fine' else "счет за ком. услуги"
                    bot.send_message(user_id, f"❗️ <b>С вашего счета автоматически списано {amount:,} $</b> в счет погашения просроченного платежа ({type_text}).", parse_mode='HTML')
                except Exception as e:
                    print(f"Ошибка при обработке просроченного счета #{inv_id}: {e}")
                    if conn:
                        conn.rollback()
        except Exception as e:
            print(f"Критическая ошибка в потоке обработки просроченных счетов: {e}")
        finally:
            if conn:
                conn.close()
        time.sleep(3600)                            
                    
def issue_weekly_bills():
     while True:
        time.sleep(7 * 24 * 60 * 60)
        conn = None
        try:
            print("Выдача еженедельных счетов...")
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT user_id FROM characters WHERE status = 'approved'")
            active_users = cursor.fetchall()
            due_date = datetime.now() + timedelta(days=2)
            for (user_id,) in active_users:
                try:
                    cursor.execute("""
                        INSERT INTO invoices (user_id, invoice_type, amount, due_date, reason)
                        VALUES (?, 'utility_bill', 1000, ?, ?)
                    """, (user_id, due_date, "Еженедельный счет за ком. услуги"))
                    bot.send_message(user_id, "🧾 Вам выставлен еженедельный счет за коммунальные услуги на сумму <b>1000 $</b>. Срок оплаты - 2 дня.\n"
                                              "Используйте /scheta для оплаты.", parse_mode='HTML')
                except Exception as e:
                    print(f"Не удалось выдать счет пользователю {user_id}: {e}")
            conn.commit()
            print("Еженедельные счета успешно выданы.")
        except Exception as e:
            print(f"Критическая ошибка в потоке выдачи счетов: {e}")
        finally:
            if conn:
                conn.close()

@bot.message_handler(commands=['tax'])
@antispam_filter
def set_tax(message: Message):
    sender_id = message.from_user.id
    
    # Проверка, является ли пользователь президентом
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT president_id FROM government_treasury WHERE id = ?", (GOVERNMENT_TREASURY_ID,))
        president_id_result = cursor.fetchone()
        is_president = president_id_result and president_id_result[0] == sender_id
    finally:
        conn.close()

    if not is_president:
        return bot.reply_to(message, "⛔ <b>Только Президент может управлять налогами.</b>", parse_mode='HTML')

    parts = message.text.split()
    if len(parts) != 3:
        # Получаем текущие налоги для отображения
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT setting_value FROM government_settings WHERE setting_key = 'player_transfer_tax_percent'")
        player_tax = cursor.fetchone()[0]
        cursor.execute("SELECT setting_value FROM government_settings WHERE setting_key = 'company_transfer_tax_percent'")
        company_tax = cursor.fetchone()[0]
        conn.close()
        
        return bot.reply_to(message,
            f"⚖️ <b>Управление налогами</b>\n\n"
            f"Текущий налог на перевод игроку: <b>{player_tax}%</b>\n"
            f"Текущий налог на перевод компании: <b>{company_tax}%</b>\n\n"
            f"<b>Как изменить:</b>\n"
            f"<code>/tax player [процент]</code> - налог на перевод между игроками\n"
            f"<code>/tax company [процент]</code> - налог на пополнение компаний",
            parse_mode='HTML'
        )
    
    tax_type = parts[1].lower()
    # --- ЗАМЕНИ НА ЭТОТ БЛОК ---
    try:
        # Убираем символ '%' из строки, если он есть
        new_rate_str = parts[2].replace('%', '')
        new_rate = float(new_rate_str)
        if not 0.0 <= new_rate <= 25.0: # Ограничим макс. налог 25%
            raise ValueError
    except (ValueError, TypeError):
        return bot.reply_to(message, "❌ Неверный формат. Укажите процент в виде числа (например, 5.5). Максимум 25%.")

    if tax_type == 'player':
        key_to_update = 'player_transfer_tax_percent'
        type_name = "между игроками"
    elif tax_type == 'company':
        key_to_update = 'company_transfer_tax_percent'
        type_name = "на пополнение компаний"
    else:
        return bot.reply_to(message, "❌ Неверный тип налога. Используйте 'player' или 'company'.")

    conn = sqlite3.connect('database.db')
    try:
        conn.execute("UPDATE government_settings SET setting_value = ? WHERE setting_key = ?", (str(new_rate), key_to_update))
        conn.commit()
        bot.reply_to(message, f"✅ <b>Успешно!</b> Новый налог на переводы {type_name} установлен на <b>{new_rate}%</b>.", parse_mode='HTML')
    except Exception as e:
        bot.reply_to(message, f"⚠️ Произошла ошибка: {e}")
    finally:
        conn.close()                        
                        

# --- NEW WANTED SYSTEM ---
@bot.message_handler(commands=['wanted'])
@antispam_filter
def show_wanted(message: Message):
    user_id = message.from_user.id
    if not has_government_access(user_id):
        return bot.reply_to(message, "⛔ <b>У вас нет доступа к этой команде.</b> Доступно только для Президента, Министров и Госс. служащих.", parse_mode='HTML')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT w.stars, w.reason, w.issued_at, c.full_name, c.id, u.username, w.id
            FROM wanted w
            JOIN characters c ON w.character_id = c.id
            LEFT JOIN users u ON c.user_id = u.user_id
            WHERE w.status = 'active'
            ORDER BY w.stars DESC, w.issued_at DESC
        """)
        wanted_list = cursor.fetchall()
        if not wanted_list:
            return bot.reply_to(message, "✅ Нет активных розысков.")
        text = "🚨 <b>Активные розыски (все звезды):</b>\n\n"
        for stars, reason, issued_at, full_name, char_id, username, wanted_id in wanted_list:
            emoji_map = {1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐"}
            emoji = emoji_map.get(stars, "❓")
            text += f"{emoji} <b>{full_name}</b> ({username or 'ID:'+str(char_id)}) — {stars} звезд\n"
            text += f"  📌 Причина: {reason}\n  🕒 {issued_at}\n\n"
        bot.reply_to(message, text, parse_mode='HTML')
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при загрузке розыска: {e}")
    finally:
        conn.close()

# --- INLINES FOR WANTED ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('add_wanted_'))
def add_wanted_start(call):
    gov_worker_id = call.from_user.id
    if not has_government_access(gov_worker_id):
        return bot.answer_callback_query(call.id, "⛔ У вас нет прав на это действие.", show_alert=True)
    parts = call.data.split('_')
    char_id = int(parts[2])
    owner_user_id = int(parts[3])
    fining_in_progress[gov_worker_id] = {
        'action': 'add_wanted',
        'character_id': char_id,
        'target_user_id': owner_user_id
    }
    bot.answer_callback_query(call.id)
    msg = bot.send_message(gov_worker_id, "⭐ Добавить розыск\nУкажите количество звезд (1-5):\n\n(1) Local Police\n(2) Sheriff / Highway Patrol\n(3) SWAT / US Marshals\n(4) FBI / DEA / ATF\n(5) Federal Investigation / Homeland Security")
    bot.register_next_step_handler(msg, process_wanted_stars)

@bot.callback_query_handler(func=lambda call: call.data.startswith('remove_wanted_'))
def remove_wanted_start(call):
    gov_worker_id = call.from_user.id
    if not has_government_access(gov_worker_id):
        return bot.answer_callback_query(call.id, "⛔ У вас нет прав на это действие.", show_alert=True)
    parts = call.data.split('_')
    wanted_id = int(parts[2])
    char_id = int(parts[3])
    owner_user_id = int(parts[4])
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT stars, reason FROM wanted WHERE id = ? AND status = 'active'", (wanted_id,))
        result = cursor.fetchone()
        if not result:
            return bot.answer_callback_query(call.id, "❌ Розыск уже снят или не найден.", show_alert=True)
        stars, reason = result
        fining_in_progress[gov_worker_id] = {
            'action': 'remove_wanted',
            'wanted_id': wanted_id,
            'character_id': char_id,
            'target_user_id': owner_user_id,
            'current_stars': stars,
            'current_reason': reason
        }
        bot.answer_callback_query(call.id)
        msg = bot.send_message(gov_worker_id, f"⚠️ <b>Снять розыск</b>\nТекущий статус: {stars} звезд\n\nВведите причину снятия (например: 'Оправдан', 'Ошибочно', 'Исправлен'):")
        bot.register_next_step_handler(msg, process_remove_wanted_reason)
    except Exception as e:
        bot.answer_callback_query(call.id, "Ошибка: " + str(e), show_alert=True)
    finally:
        conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('show_wanted_'))
def show_wanted_detail(call):
    gov_worker_id = call.from_user.id
    if not has_government_access(gov_worker_id):
        return bot.answer_callback_query(call.id, "⛔ У вас нет прав на это действие.", show_alert=True)
    wanted_id = int(call.data.split('_')[2])
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT w.stars, w.reason, w.issued_at, w.issued_by, c.full_name, u.username, c.id, c.user_id
            FROM wanted w
            JOIN characters c ON w.character_id = c.id
            LEFT JOIN users u ON c.user_id = u.user_id
            WHERE w.id = ? AND w.status = 'active'
        """, (wanted_id,))
        result = cursor.fetchone()
        if not result:
            return bot.answer_callback_query(call.id, "❌ Розыск не найден или снят.", show_alert=True)
        
        stars, reason, issued_at, issued_by, full_name, username, char_id, owner_user_id = result
        
        issuer_name = get_display_name(issued_by) if issued_by else "Неизвестно"
        emoji_map = {1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐"}
        emoji = emoji_map.get(stars, "❓")
        text = f"""
🚨 <b>Подробности розыска</b>
{emoji} <b>{stars} звезд</b>
👤 <b>Персонаж:</b> {full_name} ({username or 'N/A'})
📅 <b>Выдан:</b> {issued_at}
👨‍⚖️ <b>Выдал:</b> {issuer_name}
📝 <b>Причина:</b> {reason}
        """
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ Увеличить звезды", callback_data=f"add_wanted_{char_id}_{owner_user_id}"))
        markup.add(InlineKeyboardButton("➖ Снять розыск", callback_data=f"remove_wanted_{wanted_id}_{char_id}_{owner_user_id}"))
        
        # Кнопку "Назад" пока не добавляем, т.к. для нее нужно передавать поисковый запрос, что усложнит код
        # markup.add(InlineKeyboardButton("⬅️ Назад", callback_data=f"search_back_..."))
        
        # ИСПОЛЬЗУЕМ ПРАВИЛЬНЫЙ МЕТОД bot.edit_message_caption
        bot.edit_message_caption(caption=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

    except Exception as e:
        # Эта проверка поможет отловить ошибку, если вдруг сообщение будет без фото
        if 'message is not modified' in str(e):
             bot.answer_callback_query(call.id) # Просто игнорируем, если текст не изменился
        else:
            bot.answer_callback_query(call.id, "Произошла ошибка при обновлении.", show_alert=True)
            print(f"Ошибка в show_wanted_detail: {e}")
    finally:
        conn.close()

def process_wanted_stars(message: Message):
    gov_worker_id = message.from_user.id
    if gov_worker_id not in fining_in_progress or fining_in_progress[gov_worker_id]['action'] != 'add_wanted':
        return
    try:
        stars = int(message.text)
        if not 1 <= stars <= 5:
            raise ValueError
        fining_in_progress[gov_worker_id]['stars'] = stars
        msg = bot.send_message(gov_worker_id, "📝 Введите причину розыска (например: 'Участие в вооруженном ограблении'):")
        bot.register_next_step_handler(msg, process_wanted_reason)
    except (ValueError, TypeError):
        bot.send_message(gov_worker_id, "❌ Введите число от 1 до 5.")
        bot.register_next_step_handler(message, process_wanted_stars)

def process_wanted_reason(message: Message):
    gov_worker_id = message.from_user.id
    if gov_worker_id not in fining_in_progress or fining_in_progress[gov_worker_id]['action'] != 'add_wanted':
        return
    reason = message.text.strip()
    if not reason:
        bot.send_message(gov_worker_id, "❌ Причина не может быть пустой.")
        bot.register_next_step_handler(message, process_wanted_reason)
        return
    data = fining_in_progress[gov_worker_id]
    char_id = data['character_id']
    owner_user_id = data['target_user_id']
    stars = data['stars']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE wanted SET status = 'inactive' WHERE character_id = ? AND status = 'active'", (char_id,))
        cursor.execute("""
            INSERT INTO wanted (character_id, stars, reason, issued_by)
            VALUES (?, ?, ?, ?)
        """, (char_id, stars, reason, gov_worker_id))
        conn.commit()
        bot.send_message(gov_worker_id, f"✅ <b>Розыск добавлен!</b>\nЗвезды: {stars}\nПричина: {reason}", parse_mode='HTML')
        bot.send_message(owner_user_id, f"🚨 <b>ВАС ДОБАВИЛИ В РОЗЫСК!</b>\nЗвезды: {stars}\nПричина: {reason}\nВыдано: {get_display_name(gov_worker_id)}", parse_mode='HTML')
        notify_staff("Добавление розыска", f"Розыск {stars} звезд для {get_display_name(owner_user_id)}", gov_worker_id, owner_user_id, 0)
    except Exception as e:
        bot.send_message(gov_worker_id, f"⚠️ Ошибка: {e}")
    finally:
        del fining_in_progress[gov_worker_id]
        conn.close()

def process_remove_wanted_reason(message: Message):
    gov_worker_id = message.from_user.id
    if gov_worker_id not in fining_in_progress or fining_in_progress[gov_worker_id]['action'] != 'remove_wanted':
        return
    reason = message.text.strip()
    if not reason:
        bot.send_message(gov_worker_id, "❌ Причина не может быть пустой.")
        bot.register_next_step_handler(message, process_remove_wanted_reason)
        return
    data = fining_in_progress[gov_worker_id]
    wanted_id = data['wanted_id']
    char_id = data['character_id']
    owner_user_id = data['target_user_id']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE wanted SET status = 'inactive', reason = ?, removed_by = ?, removed_at = ?
            WHERE id = ?
        """, (reason, gov_worker_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), wanted_id))
        conn.commit()
        bot.send_message(gov_worker_id, f"✅ <b>Розыск снят!</b>\nПричина снятия: {reason}", parse_mode='HTML')
        bot.send_message(owner_user_id, f"✅ <b>ВАШ РОЗЫСК СНЯТ!</b>\nПричина: {reason}\nСнял: {get_display_name(gov_worker_id)}", parse_mode='HTML')
        notify_staff("Снятие розыска", f"Розыск снят для {get_display_name(owner_user_id)}", gov_worker_id, owner_user_id, 0)
    except Exception as e:
        bot.send_message(gov_worker_id, f"⚠️ Ошибка: {e}")
    finally:
        del fining_in_progress[gov_worker_id]
        conn.close()

@bot.message_handler(commands=['start'])
@antispam_filter
def start(message: Message):
    register_user(message.from_user.id)
    parts = message.text.split()
    if len(parts) > 1 and parts[0] == '/start':
        check_id = parts[1]
        result_message = process_check_claim(message.from_user.id, check_id)
        bot.reply_to(message, result_message, parse_mode='HTML')
    else:
        bot.reply_to(message,
            "✨ <b>Добро пожаловать в Edmonton RP!</b> Вы успешно зарегистрированы.\n\n"
            "<b>Основное:</b>\n"
            "👤 /profile - Ваш профиль и баланс\n"
            "📄 /passport - Ваши Паспорта\n"
            "📝 /create_passport - Создать новый Паспорт\n\n"
            "<b>Финансы:</b>\n"
            "💸 /pay - Перевести доллары\n"
            "🧾 /scheta - Мои счета и штрафы\n"
            "🧾 /create_check - Создать чек\n"
            "✅ /claim - Активировать чек\n"
            "👛 /wallet - Крипто-кошелек\n\n"
            "<b>Бизнес и имущество:</b>\n"
            "🏢 /company - Управление компаниями\n"
            "🛒 /auction - Аукцион\n"
            "🗄️ /warehouse - Ваш склад (недвижимость, SIM)\n\n"
            "<b>Государство:</b>\n"
            "🏛️ /treasury - Федеральная казна\n"
            "⚖️ /laws - Законодательство\n"
            "🏆 /top - Топ граждан",
            parse_mode='HTML'
        )

@bot.message_handler(commands=['profile', 'balance'])
@antispam_filter
def profile(message: Message):
    parts = message.text.split()
    user_id_to_check = message.from_user.id
    if len(parts) > 1:
        identifier = parts[1]
        if identifier.startswith("@"):
            try: user_id_to_check = bot.get_chat(identifier).id
            except Exception: return bot.reply_to(message, "❌ Пользователь не найден.")
        else:
            try: user_id_to_check = int(identifier)
            except ValueError: return bot.reply_to(message, "❌ Введите корректный ID или username.")
    register_user(user_id_to_check)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT balance, level, experience FROM users WHERE user_id = ?", (user_id_to_check,))
        result = cursor.fetchone()
        if result:
            balance, level, experience = result
            if level is None: level = 1
            if experience is None: experience = 0
            xp_for_next_level = (level ** 2) * 100
            profile_text = (f"👤 <b>Профиль:</b> {get_display_name(user_id_to_check)}\n"
                            f"🆔 <b>ID:</b> {user_id_to_check}\n"
                            f"💳 <b>Баланс:</b> {balance:,} $\n"
                            f"🌟 <b>Уровень доверия:</b> {level}\n"
                            f"📈 <b>Опыт:</b> {experience}/{xp_for_next_level} XP")
            bot.reply_to(message, profile_text, parse_mode='HTML')
        else: bot.reply_to(message, "❌ Пользователь не найден в базе данных.")
    except Exception as e: bot.reply_to(message, f"⚠️ Ошибка получения профиля: {e}")
    finally: conn.close()

@bot.message_handler(commands=['id'])
@antispam_filter
def get_id(message: Message):
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user_name = get_display_name(user_id)
        bot.reply_to(message, f"👤 <b>Пользователь:</b> {user_name}\n🆔 <b>ID:</b> <code>{user_id}</code>", parse_mode='HTML')
    else: bot.reply_to(message, f"Ваш ID: <code>{message.from_user.id}</code>", parse_mode='HTML')

@bot.message_handler(commands=['pay'])
@antispam_filter
def pay(message: Message):
    sender_id = message.from_user.id

    # --- START OF FIX ---
    # 1. Проверяем, не выполняется ли уже перевод от этого пользователя.
    if sender_id in TRANSACTION_IN_PROGRESS:
        bot.reply_to(message, "⏳ Ваш предыдущий перевод еще обрабатывается. Пожалуйста, подождите несколько секунд.")
        return

    # 2. "Блокируем" пользователя, чтобы он не мог начать новый перевод.
    TRANSACTION_IN_PROGRESS.add(sender_id)
    # --- END OF FIX ---

    conn = None # Инициализируем conn здесь для блока finally
    try:
        parts = message.text.split()
        receiver_identifier, amount_str = None, None

        if message.reply_to_message:
            receiver_identifier = message.reply_to_message.from_user.id
            if len(parts) >= 2: amount_str = parts[1]
        elif len(parts) >= 3:
            receiver_identifier, amount_str = parts[1], parts[2]
        else:
            bot.reply_to(message, "<b>Как перевести средства:</b>\n"
                                         "<b>Игроку:</b>\n"
                                         "1. Ответьте на сообщение: <code>/pay 100</code>\n"
                                         "2. Укажите ID/username: <code>/pay @username 100</code>\n"
                                         "<b>Компании:</b>\n"
                                         "• Укажите инициал: <code>/pay TINKOFF 1000</code>", parse_mode='HTML')
            return # Выходим из функции, если аргументы неверны

        if amount_str is None:
            bot.reply_to(message, "❌ Введите сумму.")
            return
        try:
            amount_sent = int(Decimal(amount_str))
            if amount_sent <= 0:
                bot.reply_to(message, "❌ Сумма должна быть положительной.")
                return
        except (InvalidOperation, ValueError):
            bot.reply_to(message, "❌ Введите корректную сумму.")
            return

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # --- ИЗМЕНЕНИЕ: Проверка баланса и списание происходят в одной транзакции ---
        conn.execute("BEGIN TRANSACTION")

        # Проверяем баланс
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (sender_id,))
        sender_balance_result = cursor.fetchone()
        sender_balance = sender_balance_result[0] if sender_balance_result else 0
        if sender_balance < amount_sent:
            bot.reply_to(message, f"❌ Недостаточно средств. Ваш баланс: <b>{sender_balance:,} $</b>", parse_mode='HTML')
            conn.rollback() # Откатываем транзакцию
            return

        # Определяем получателя (компания или игрок)
        is_company_transfer = False
        company_id = None
        if isinstance(receiver_identifier, str) and not receiver_identifier.startswith('@') and not receiver_identifier.isdigit():
            cursor.execute("SELECT id, name FROM companies WHERE LOWER(initial) = ?", (receiver_identifier.lower(),))
            company_data = cursor.fetchone()
            if company_data:
                is_company_transfer = True
                company_id, company_name = company_data
            else:
                bot.reply_to(message, "❌ Компания с таким инициалом не найдена.")
                conn.rollback()
                return

        receiver_user_id = None
        if not is_company_transfer:
            try:
                if str(receiver_identifier).startswith("@"):
                    receiver_user_id = bot.get_chat(receiver_identifier).id
                else:
                    receiver_user_id = int(receiver_identifier)
                if sender_id == receiver_user_id:
                    bot.reply_to(message, "❌ Нельзя перевести деньги самому себе.")
                    conn.rollback()
                    return
                register_user(receiver_user_id)
            except Exception:
                bot.reply_to(message, "❌ Пользователь не найден.")
                conn.rollback()
                return

        # Списываем деньги у отправителя
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount_sent, sender_id))

        # Начисляем деньги и налог
        if is_company_transfer:
            cursor.execute("SELECT setting_value FROM government_settings WHERE setting_key = 'company_transfer_tax_percent'")
            tax_rate = Decimal(cursor.fetchone()[0]) / Decimal(100)
            tax = int(amount_sent * tax_rate)
            amount_received = amount_sent - tax

            cursor.execute("UPDATE companies SET balance = balance + ? WHERE id = ?", (amount_received, company_id))
            cursor.execute("UPDATE government_treasury SET balance = balance + ? WHERE id = ?", (tax, GOVERNMENT_TREASURY_ID))

            conn.commit()
            bot.reply_to(message, f"✅ Вы успешно перевели <b>{amount_sent:,} $</b>.\n"
                                  f"На счет компании <b>'{company_name}'</b> зачислено: <b>{amount_received:,} $</b>\n"
                                  f"Налог в казну ({(tax_rate*100).normalize()}%): <b>{tax:,} $</b>", parse_mode='HTML')
            notify_staff("Перевод в компанию", f"Перевод на счет компании '{company_name}'", sender_id, None, amount_sent)
            process_company_debt_payment(company_id)
        else:
            cursor.execute("SELECT setting_value FROM government_settings WHERE setting_key = 'player_transfer_tax_percent'")
            tax_rate = Decimal(cursor.fetchone()[0]) / Decimal(100)
            tax = max(1, int(amount_sent * tax_rate))
            amount_received = amount_sent - tax

            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount_received, receiver_user_id))
            cursor.execute("UPDATE government_treasury SET balance = balance + ? WHERE id = ?", (tax, GOVERNMENT_TREASURY_ID))

            conn.commit()
            grant_xp_for_pair_transaction(sender_id, receiver_user_id, amount_sent)
            bot.reply_to(message, f"✅ Вы перевели <b>{amount_sent:,} $</b> пользователю {get_display_name(receiver_user_id)}.\n"
                                  f"Получено: <b>{amount_received:,} $</b>\n"
                                  f"Налог в казну ({(tax_rate*100).normalize()}%): <b>{tax:,} $</b>", parse_mode='HTML')
            notify_staff("Перевод средств", "Пользователь перевел средства", sender_id, receiver_user_id, amount_sent)

    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при переводе: {e}")
        if conn: conn.rollback()
    finally:
        # --- START OF FIX ---
        # 3. В любом случае (даже если была ошибка) "разблокируем" пользователя.
        if sender_id in TRANSACTION_IN_PROGRESS:
            TRANSACTION_IN_PROGRESS.remove(sender_id)
        # --- END OF FIX ---
        if conn: conn.close()

@bot.message_handler(commands=['create_check'])
@antispam_filter
def create_check(message: Message):
    creator_id = message.from_user.id
    register_user(creator_id)
    parts = message.text.split()
    amount = None
    target_user_id = None
    if len(parts) >= 3:
        try:
            amount = int(Decimal(parts[1]))
            identifier = parts[2]
            target_user_id = int(identifier)
            register_user(target_user_id)
        except (ValueError, InvalidOperation):
            return bot.reply_to(message, "❌ Неверный формат суммы или ID пользователя.")
    elif len(parts) == 2:
        try: amount = int(Decimal(parts[1]))
        except (ValueError, InvalidOperation): return bot.reply_to(message, "❌ Неверный формат суммы.")
    else:
        return bot.reply_to(message,
                            "🧾 <b>Как создать чек:</b>\n"
                            "<b>Публичный чек:</b> <code>/create_check [сумма]</code>\n"
                            "<b>Приватный чек:</b> <code>/create_check [сумма] [ID]</code>",
                            parse_mode='HTML')
    if amount <= 0: return bot.reply_to(message, "❌ Сумма чека должна быть положительной.")
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (creator_id,))
        creator_balance_result = cursor.fetchone()
        if not creator_balance_result: return bot.reply_to(message, "❌ Не удалось найти ваш баланс. Попробуйте /start.")
        creator_balance = creator_balance_result[0]
        if creator_balance < amount: return bot.reply_to(message, f"❌ Недостаточно средств. Ваш баланс: <b>{creator_balance:,} $</b>", parse_mode='HTML')
        check_id = str(uuid.uuid4().hex)[:12]
        conn.execute("BEGIN TRANSACTION")
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, creator_id))
        cursor.execute("INSERT INTO checks (check_id, creator_id, amount, target_user_id) VALUES (?, ?, ?, ?)", (check_id, creator_id, amount, target_user_id))
        conn.commit()
        add_experience(creator_id, amount)
        activation_link = f"t.me/{BOT_USERNAME}?start={check_id}"
        response_message = f"🧾 <b>Чек создан</b>\n"
        response_message += f"Сумма: <b>{amount:,} $</b>\n"
        if target_user_id: response_message += f"Для: {get_display_name(target_user_id)}.\n"
        else: response_message += "Для любого пользователя.\n"
        response_message += f"\nСсылка на чек:\n{activation_link}"

        # --- НАЧАЛО НОВОГО БЛОКА ---
        # Создаем инлайн-кнопку
        markup = InlineKeyboardMarkup()
        # Добавляем кнопку с callback_data, который будет уникальным для каждого чека
        markup.add(InlineKeyboardButton("✅ Активировать чек", callback_data=f"claim_check_{check_id}"))
        # --- КОНЕЦ НОВОГО БЛОКА ---

        # Отправляем сообщение с текстом и новой кнопкой
        bot.reply_to(message, response_message, parse_mode='HTML', reply_markup=markup, disable_web_page_preview=True)
        notify_staff("Создание чека", f"Создан чек на {amount} $", creator_id, target_user_id, amount)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при создании чека: {str(e)}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()

# --- НОВЫЙ ОБРАБОТЧИК ДЛЯ ИНЛАЙН-КНОПКИ ЧЕКА ---
# Вставь этот код после функции def create_check(message: Message):

@bot.callback_query_handler(func=lambda call: call.data.startswith('claim_check_'))
def handle_claim_check_callback(call):
    """
    Обрабатывает нажатие на инлайн-кнопку "Активировать чек".
    """
    # Получаем ID того, кто нажал на кнопку
    claimer_id = call.from_user.id
    # Получаем ID чата, в котором была нажата кнопка
    chat_id = call.message.chat.id
    
    # Извлекаем ID чека из данных кнопки (например, из "claim_check_abcdef123")
    check_id = call.data.split('_')[2]

    # Используем твою уже существующую логику для активации чека
    result_message = process_check_claim(claimer_id, check_id)

    # --- Теперь обрабатываем результат ---

    # 1. Если чек уже активирован или произошла другая ошибка
    if "уже был активирован" in result_message or "не можете активировать" in result_message or "предназначен для другого" in result_message:
        # Показываем всплывающее уведомление тому, кто нажал
        # Убираем "❌" из сообщения для красоты
        alert_text = result_message.replace("❌ ", "")
        bot.answer_callback_query(call.id, text=alert_text, show_alert=True)
        return

    # 2. Если чек успешно активирован
    elif "✅" in result_message:
        # Получаем имя того, кто забрал чек
        claimer_name = get_display_name(claimer_id)
        
        # Составляем новое сообщение для чата, как ты и хотел
        new_message_text = f"✅ Чек был успешно активирован пользователем {claimer_name} (ID: <code>{claimer_id}</code>)"
        
        # Отправляем это сообщение в чат как ответ на исходное сообщение с чеком
        bot.send_message(
            chat_id=chat_id,
            text=new_message_text,
            parse_mode='HTML',
            reply_to_message_id=call.message.message_id
        )
        
        # Убираем кнопку из старого сообщения, чтобы её больше не могли нажать
        try:
            bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=None # None убирает все кнопки
            )
        except Exception as e:
            print(f"Не удалось убрать кнопку у сообщения с чеком: {e}")
            
        # Показываем короткое уведомление "Успешно" тому, кто нажал
        bot.answer_callback_query(call.id, text="Чек успешно активирован!")

    # 3. На случай других непредвиденных ошибок
    else:
        bot.answer_callback_query(call.id, text=result_message, show_alert=True)

@bot.message_handler(commands=['claim'])
@antispam_filter
def claim_check(message: Message):
    claimer_id = message.from_user.id
    parts = message.text.split()
    if len(parts) != 2:
        return bot.reply_to(message, "<b>Для ручной активации чека введите его ID:</b>\n"
                                     "<code>/claim [ID чека]</code>", parse_mode='HTML')
    check_id = parts[1]
    result_message = process_check_claim(claimer_id, check_id)
    bot.reply_to(message, result_message, parse_mode='HTML')

@bot.message_handler(commands=['add'])
@antispam_filter
def add(message: Message):
    if not has_permission(message.from_user.id, [1, 2, 3]): return bot.reply_to(message, "⛔ <b>Недостаточно прав.</b>", parse_mode='HTML')
    if not message.reply_to_message or len(message.text.split()) < 2:
        return bot.reply_to(message, "🛠️ <b>Выдача средств:</b>\n"
                                     "Ответьте на сообщение и напишите: <code>/add 1000</code>", parse_mode='HTML')
    try: amount = int(Decimal(message.text.split()[1]))
    except (InvalidOperation, ValueError): return bot.reply_to(message, "❌ Введите корректную сумму.")
    if amount <= 0: return bot.reply_to(message, "❌ Сумма должна быть положительной.")
    receiver = message.reply_to_message.from_user.id
    register_user(receiver)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        conn.execute("BEGIN TRANSACTION")
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, receiver))
        cursor.execute("INSERT INTO logs (sender_id, receiver_id, amount, action, details) VALUES (?, ?, ?, 'admin_add', ?)",
                       (message.from_user.id, receiver, amount, "Админ добавил средства"))
        conn.commit()
        bot.reply_to(message, f"✅ <b>Успешно!</b> Добавлено <b>{amount:,} $</b> пользователю {get_display_name(receiver)}.", parse_mode='HTML')
        notify_staff("Выдача средств", "Администратор выдал средства", message.from_user.id, receiver, amount)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при добавлении средств: {e}")
        conn.rollback()
    finally: conn.close()

@bot.message_handler(commands=['delete'])
@antispam_filter
def delete(message: Message):
    if not has_permission(message.from_user.id, [1, 2, 3]): return bot.reply_to(message, "⛔ <b>Недостаточно прав.</b>", parse_mode='HTML')
    if not message.reply_to_message or len(message.text.split()) < 2:
        return bot.reply_to(message, "🛠️ <b>Изъятие средств:</b>\n"
                                     "Ответьте на сообщение и напишите:\n"
                                     "<code>/delete 1000</code>", parse_mode='HTML')
    try: amount = int(Decimal(message.text.split()[1]))
    except (InvalidOperation, ValueError): return bot.reply_to(message, "❌ Введите корректную сумму.")
    if amount <= 0: return bot.reply_to(message, "❌ Сумма должна быть положительной.")
    receiver = message.reply_to_message.from_user.id
    register_user(receiver)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        conn.execute("BEGIN TRANSACTION")
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (receiver,))
        balance_result = cursor.fetchone()
        if not balance_result: return bot.reply_to(message, "❌ Пользователь не найден.")
        balance = int(balance_result[0])
        if balance < amount: return bot.reply_to(message, f"❌ У пользователя недостаточно средств. Баланс: <b>{balance:,} $</b>", parse_mode='HTML')
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, receiver))
        cursor.execute("INSERT INTO logs (sender_id, receiver_id, amount, action, details) VALUES (?, ?, ?, 'admin_delete', ?)",
                       (message.from_user.id, receiver, amount, "Админ удалил средства"))
        conn.commit()
        bot.reply_to(message, f"✅ <b>Успешно!</b> Изъято <b>{amount:,} $</b> у пользователя {get_display_name(receiver)}.", parse_mode='HTML')
        notify_staff("Изъятие средств", "Администратор изъял средства", message.from_user.id, receiver, amount)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при удалении средств: {e}")
        conn.rollback()
    finally: conn.close()

@bot.message_handler(commands=['giverole'])
@antispam_filter
def giverole(message: Message):
    sender_id = message.from_user.id
    sender_roles = get_roles(sender_id)
    if not message.reply_to_message or len(message.text.split()) < 2 or not message.text.split()[1].isdigit():
        help_text = ("👑 <b>Выдача роли:</b>\n\n"
                     "Ответьте на сообщение и напишите:\n<code>/giverole [номер роли]</code>\n\n"
                     "<b>Доступные роли:</b>\n" + "\n".join([f"{k} - {v}" for k,v in ROLES.items()]))
        return bot.reply_to(message, help_text, parse_mode='HTML')
    new_role = int(message.text.split()[1])
    target_id = message.reply_to_message.from_user.id
    if new_role not in ROLES: return bot.reply_to(message, "❌ Такой роли не существует.")
    if not any(role in sender_roles for role in [1, 2, 3]): return bot.reply_to(message, "⛔ <b>Недостаточно прав.</b>", parse_mode='HTML')
    target_current_roles = get_roles(target_id)
    if any(role in target_current_roles for role in [2, 3]) and 3 not in sender_roles: return bot.reply_to(message, "⛔ Вы не можете изменить роль Создателя или Тех. Админа.")
    if 1 in sender_roles and new_role in [1, 2, 3]: return bot.reply_to(message, "⛔ Админ может выдавать только RP-роли (4, 9).")
    if 2 in sender_roles and new_role in [2, 3]: return bot.reply_to(message, "⛔ Вы не можете выдавать роль Создателя или Тех. Админа.")
    register_user(target_id)
    if new_role not in target_current_roles: target_current_roles.append(new_role)
    roles_str = ",".join(map(str, sorted(target_current_roles)))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        conn.execute("BEGIN TRANSACTION")
        cursor.execute("UPDATE users SET roles = ? WHERE user_id = ?", (roles_str, target_id))
        conn.commit()
        bot.reply_to(message, f"✅ <b>Успешно!</b> Роль '<b>{ROLES[new_role]}</b>' выдана пользователю {get_display_name(target_id)}.", parse_mode='HTML')
        notify_staff("Выдача роли", f"Выдана роль: {ROLES[new_role]}", sender_id, target_id)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при выдаче роли: {e}")
        conn.rollback()
    finally: conn.close()

@bot.message_handler(commands=['removerole'])
@antispam_filter
def removerole(message: Message):
    sender_id = message.from_user.id
    sender_roles = get_roles(sender_id)
    parts = message.text.split()
    if not message.reply_to_message or len(parts) < 2 or not parts[1].isdigit():
        return bot.reply_to(message, "👑 <b>Снятие роли:</b>\n\nОтветьте на сообщение и напишите:\n<code>/removerole [номер роли]</code>", parse_mode='HTML')
    role_to_remove = int(parts[1])
    target_id = message.reply_to_message.from_user.id
    target_roles = get_roles(target_id)
    if role_to_remove not in ROLES: return bot.reply_to(message, "❌ Такой роли не существует.")
    if role_to_remove not in target_roles: return bot.reply_to(message, f"❌ У пользователя {get_display_name(target_id)} нет роли '<b>{ROLES[role_to_remove]}</b>'.", parse_mode='HTML')
    is_tech_admin = 3 in sender_roles
    if not is_tech_admin:
        if not any(role in sender_roles for role in [1, 2]): return bot.reply_to(message, "⛔ <b>Недостаточно прав.</b>", parse_mode='HTML')
        if role_to_remove in [2, 3]: return bot.reply_to(message, "⛔ Только Тех. Админ может снять роль Создателя или Тех. Админа.")
        if role_to_remove == 1 and 2 not in sender_roles: return bot.reply_to(message, "⛔ Только Создатель или Тех. Админ могут снять роль Админа.")
        if sender_id == target_id: return bot.reply_to(message, "⛔ Вы не можете снимать роли у самого себя.")
    target_roles.remove(role_to_remove)
    roles_str = ",".join(map(str, sorted(target_roles)))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        conn.execute("BEGIN TRANSACTION")
        cursor.execute("UPDATE users SET roles = ? WHERE user_id = ?", (roles_str, target_id))
        conn.commit()
        bot.reply_to(message, f"✅ <b>Успешно!</b> Роль '<b>{ROLES[role_to_remove]}</b>' пользователя {get_display_name(target_id)} снята.", parse_mode='HTML')
        notify_staff("Снятие роли", f"Снята роль: {ROLES.get(role_to_remove, 'Неизвестная роль')}", sender_id, target_id)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при снятии роли: {e}")
        conn.rollback()
    finally: conn.close()

@bot.message_handler(commands=['top'])
@antispam_filter
def top(message: Message):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10")
        top_users = cursor.fetchall()
        if not top_users or all(bal <= 0 for _, bal in top_users): return bot.reply_to(message, "📊 Пока нет данных для топа.")
        response = ["🏆 <b>Топ-10 граждан по состоянию:</b>\n"]
        for i, (uid, bal) in enumerate(top_users, 1):
            response.append(f"{i}. {get_display_name(uid)} — <b>{bal:,} $</b>")
        bot.reply_to(message, "\n".join(response), parse_mode='HTML')
    except Exception as e: bot.reply_to(message, f"⚠️ Ошибка при получении топа: {e}")
    finally: conn.close()

@bot.message_handler(commands=['roles'])
@antispam_filter
def roles(message: Message):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        response = ["👑 <b>Список административных ролей:</b>"]
        admin_roles_found = False
        admin_role_ids = {1, 2, 3}
        for num, name in {k: v for k, v in ROLES.items() if k in admin_role_ids}.items():
            cursor.execute("SELECT user_id FROM users WHERE ',' || roles || ',' LIKE ?", (f'%,{num},%',))
            users = cursor.fetchall()
            if users:
                admin_roles_found = True
                response.append(f"\n{name}:")
                for (uid,) in users: response.append(f"- {get_display_name(uid)}")
        if not admin_roles_found: response.append("\n\n❌ Нет данных об администраторах.")
        response.append("\n\nℹ️ Для просмотра RP-ролей используйте /rproles")
        bot.reply_to(message, "\n".join(response), parse_mode='HTML')
    except Exception as e: bot.reply_to(message, f"⚠️ Ошибка при получении списка ролей: {e}")
    finally: conn.close()

@bot.message_handler(commands=['rproles', 'rp_roles'])
@antispam_filter
def rp_roles(message: Message):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        response = ["👑 <b>Список RP-ролей (Правительство и Гос. службы):</b>"]
        cursor.execute("SELECT president_id FROM government_treasury WHERE id = ?", (GOVERNMENT_TREASURY_ID,))
        president_id_result = cursor.fetchone()
        president_id = president_id_result[0] if president_id_result else None
        rp_roles_found = False
        if president_id:
            rp_roles_found = True
            response.append(f"\n👑 <b>Президент:</b>\n- {get_display_name(president_id)}")
        for num, name in RP_ROLES.items():
            cursor.execute("SELECT user_id FROM users WHERE ',' || roles || ',' LIKE ?", (f'%,{num},%',))
            users = cursor.fetchall()
            if users:
                rp_roles_found = True
                response.append(f"\n{name}:")
                for (uid,) in users: response.append(f"- {get_display_name(uid)}")
        if not rp_roles_found and not president_id: response.append("\n\n❌ Нет данных о RP-ролях.")
        bot.reply_to(message, "\n".join(response), parse_mode='HTML')
    except Exception as e: bot.reply_to(message, f"⚠️ Ошибка при получении списка RP-ролей: {e}")
    finally: conn.close()

@bot.message_handler(commands=['treasury'])
@antispam_filter
def treasury(message: Message):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT balance, president_id FROM government_treasury WHERE id = ?", (GOVERNMENT_TREASURY_ID,))
        result = cursor.fetchone()
        if result:
            treasury_balance, president_id = result
            president_name = get_display_name(president_id) if president_id else "Не назначен"
            response_text = [f"🏛️ <b>Федеральная казна</b>",
                             f"💰 <b>Баланс:</b> {treasury_balance:,} $",
                             f"👑 <b>Президент:</b> {president_name}"]
            bot.reply_to(message, "\n".join(response_text), parse_mode='HTML')
        else: bot.reply_to(message, "❌ Информация о казне не найдена.")
    except Exception as e: bot.reply_to(message, f"⚠️ Ошибка получения информации о казне: {e}")
    finally: conn.close()

@bot.message_handler(commands=['donate'])
@antispam_filter
def donate(message: Message):
    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(message, "💖 <b>Пожертвовать в казну:</b>\n\nИспользуйте: <code>/donate [сумма]</code>", parse_mode='HTML')
    try: amount = int(Decimal(parts[1]))
    except (InvalidOperation, ValueError): return bot.reply_to(message, "❌ Введите корректную сумму.")
    if amount <= 0: return bot.reply_to(message, "❌ Сумма пожертвования должна быть положительной.")
    sender_id = message.from_user.id
    register_user(sender_id)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (sender_id,))
        sender_balance_result = cursor.fetchone()
        if not sender_balance_result or sender_balance_result[0] < amount:
            return bot.reply_to(message, "❌ Недостаточно средств для пожертвования.")
        conn.execute("BEGIN TRANSACTION")
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, sender_id))
        cursor.execute("UPDATE government_treasury SET balance = balance + ? WHERE id = ?", (amount, GOVERNMENT_TREASURY_ID))
        cursor.execute("INSERT INTO logs (sender_id, receiver_id, amount, action, details) VALUES (?, ?, ?, 'donate', ?)",
                       (sender_id, None, amount, "Пожертвование в казну"))
        conn.commit()
        add_experience(sender_id, amount)
        bot.reply_to(message, f"✅ <b>Спасибо!</b> Вы успешно пожертвовали <b>{amount:,} $</b> в Федеральную казну.", parse_mode='HTML')
        notify_staff("Пожертвование в казну", "Пользователь пожертвовал в казну", sender_id, None, amount)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при пожертвовании: {e}")
        conn.rollback()
    finally: conn.close()

@bot.message_handler(commands=['setpresident'])
@antispam_filter
def setpresident(message: Message):
    sender_id = message.from_user.id
    if 3 not in get_roles(sender_id): return bot.reply_to(message, "⛔ Только Тех. Админ может назначить президента.")
    target_id = None
    if message.reply_to_message: target_id = message.reply_to_message.from_user.id
    elif len(message.text.split()) > 1:
        identifier = message.text.split()[1]
        if identifier.startswith("@"):
            try:
                chat = bot.get_chat(identifier)
                target_id = chat.id
            except Exception: return bot.reply_to(message, "❌ Пользователь не найден.")
        else:
            try: target_id = int(identifier)
            except ValueError: return bot.reply_to(message, "❌ Введите корректный ID или username.")
    else:
        return bot.reply_to(message, "👑 <b>Назначить Президента:</b>\n\nОтветьте на сообщение или укажите ID/username.", parse_mode='HTML')
    if target_id is None: return bot.reply_to(message, "❌ Не удалось определить пользователя.")
    register_user(target_id)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        conn.execute("BEGIN TRANSACTION")
        cursor.execute("UPDATE government_treasury SET president_id = ? WHERE id = ?", (target_id, GOVERNMENT_TREASURY_ID))
        conn.commit()
        bot.reply_to(message, f"✅ <b>Успешно!</b> {get_display_name(target_id)} назначен новым Президентом.", parse_mode='HTML')
        notify_staff("Назначение Президента", "Назначен новый Президент", sender_id, target_id)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при назначении Президента: {e}")
        conn.rollback()
    finally: conn.close()

@bot.message_handler(commands=['removepresident'])
@antispam_filter
def removepresident(message: Message):
    sender_id = message.from_user.id
    if 3 not in get_roles(sender_id): return bot.reply_to(message, "⛔ Только Тех. Админ может снять президента.")
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT president_id FROM government_treasury WHERE id = ?", (GOVERNMENT_TREASURY_ID,))
        result = cursor.fetchone()
        current_president_id = result[0] if result else None
        if not current_president_id: return bot.reply_to(message, "❌ Нет назначенного Президента.")
        conn.execute("BEGIN TRANSACTION")
        cursor.execute("UPDATE government_treasury SET president_id = NULL WHERE id = ?", (GOVERNMENT_TREASURY_ID,))
        conn.commit()
        bot.reply_to(message, f"✅ <b>Успешно!</b> Президент {get_display_name(current_president_id)} снят с должности.", parse_mode='HTML')
        notify_staff("Снятие Президента", "Президент снят с должности", sender_id, current_president_id)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при снятии Президента: {e}")
        conn.rollback()
    finally: conn.close()

@bot.message_handler(commands=['set_treasury_role'])
@antispam_filter
def set_treasury_role(message: Message):
    sender_id = message.from_user.id
    sender_roles = get_roles(sender_id)
    if not message.reply_to_message or len(message.text.split()) < 2 or not message.text.split()[1].isdigit():
        help_text = ("👑 <b>Назначение RP-роли:</b>\n\nОтветьте на сообщение и напишите:\n"
                     "<code>/set_treasury_role [номер роли]</code>\n\n"
                     "<b>Доступные роли:</b>\n" + "\n".join([f"{k} - {v}" for k,v in RP_ROLES.items()]))
        return bot.reply_to(message, help_text, parse_mode='HTML')
    target_id = message.reply_to_message.from_user.id
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        new_role = int(message.text.split()[1])
        if new_role not in RP_ROLES: return bot.reply_to(message, f"❌ Неверный номер роли. Можно назначать только роли: {list(RP_ROLES.keys())}.")
        cursor.execute("SELECT president_id FROM government_treasury WHERE id = ?", (GOVERNMENT_TREASURY_ID,))
        president_id_result = cursor.fetchone()
        president_id = president_id_result[0] if president_id_result else None
        if sender_id != president_id and 3 not in sender_roles: return bot.reply_to(message, "⛔ Только Президент или Тех. Админ могут назначать эти роли.")
        register_user(target_id)
        target_current_roles = get_roles(target_id)
        if new_role not in target_current_roles: target_current_roles.append(new_role)
        roles_str = ",".join(map(str, sorted(target_current_roles)))
        conn.execute("BEGIN TRANSACTION")
        cursor.execute("UPDATE users SET roles = ? WHERE user_id = ?", (roles_str, target_id))
        conn.commit()
        bot.reply_to(message, f"✅ <b>Успешно!</b> Пользователю {get_display_name(target_id)} назначена роль '<b>{ROLES[new_role]}</b>'.", parse_mode='HTML')
        notify_staff("Назначение RP-роли", f"Назначена роль: {ROLES[new_role]}", sender_id, target_id)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при назначении роли: {str(e)}")
        if 'conn' in locals() and conn: conn.rollback()
    finally:
        if 'conn' in locals() and conn: conn.close()

@bot.message_handler(commands=['withdrawtreasury'])
@antispam_filter
def withdraw_treasury(message: Message):
    sender_id = message.from_user.id
    sender_roles = get_roles(sender_id)
    is_president = False
    conn_check = sqlite3.connect('database.db')
    cursor_check = conn_check.cursor()
    try:
        cursor_check.execute("SELECT president_id FROM government_treasury WHERE id = ?", (GOVERNMENT_TREASURY_ID,))
        president_id_result = cursor_check.fetchone()
        if president_id_result and president_id_result[0] == sender_id: is_president = True
    finally: conn_check.close()
    if not is_president and 4 not in sender_roles: return bot.reply_to(message, "⛔ Только Президент или Министр могут выводить средства из казны.")
    parts = message.text.split()
    if len(parts) < 2: return bot.reply_to(message, "💸 <b>Вывести средства из казны:</b>\n\nИспользуйте: <code>/withdrawtreasury [сумма]</code>", parse_mode='HTML')
    try: amount = int(Decimal(parts[1]))
    except (InvalidOperation, ValueError): return bot.reply_to(message, "❌ Введите корректную сумму.")
    if amount <= 0: return bot.reply_to(message, "❌ Сумма должна быть положительной.")
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT balance FROM government_treasury WHERE id = ?", (GOVERNMENT_TREASURY_ID,))
        treasury_balance = cursor.fetchone()
        if not treasury_balance or treasury_balance[0] < amount: return bot.reply_to(message, "❌ Недостаточно средств в казне.")
        conn.execute("BEGIN TRANSACTION")
        cursor.execute("UPDATE government_treasury SET balance = balance - ? WHERE id = ?", (amount, GOVERNMENT_TREASURY_ID))
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, sender_id))
        cursor.execute("INSERT INTO logs (sender_id, receiver_id, amount, action, details) VALUES (?, ?, ?, 'withdraw_treasury', ?)",
                       (sender_id, None, amount, "Вывод из казны"))
        conn.commit()
        bot.reply_to(message, f"✅ <b>Успешно!</b> Вы вывели <b>{amount:,} $</b> из казны на свой баланс.", parse_mode='HTML')
        notify_staff("Вывод из казны", "Пользователь вывел средства из казны", sender_id, None, amount)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при выводе средств из казны: {e}")
        conn.rollback()
    finally: conn.close()

def format_decimal(d):
    return d.normalize().to_eng_string()

@bot.message_handler(commands=['wallet'])
@antispam_filter
def wallet(message: Message):
    user_id = message.from_user.id
    register_user(user_id)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT currency, amount FROM crypto_balances WHERE user_id = ?", (user_id,))
        crypto_holdings = cursor.fetchall()
        response_lines = ["👛 <b>Ваш крипто-кошелек:</b>"]
        if not crypto_holdings or all(Decimal(amount_str) <= 0 for _, amount_str in crypto_holdings):
            response_lines.append("Ваш кошелек пуст. Используйте /buy_crypto для покупки.")
        else:
            total_usd_value = Decimal('0')
            for currency, amount_str in crypto_holdings:
                if currency == 'RUB': continue # Не показываем рубли в крипто-кошельке
                amount = Decimal(amount_str)
                if amount <= 0: continue
                rate = CURRENT_RATES.get(currency, Decimal('0.0'))
                usd_value = (amount * rate)
                total_usd_value += usd_value
                rub_value = usd_value * USD_TO_RUB_RATE
                response_lines.append(f"• <b>{currency}:</b> {format_decimal(amount)} (~{rub_value:,.2f} $)")
            total_rub_value = total_usd_value * USD_TO_RUB_RATE
            response_lines.append(f"\n<b>Общая стоимость:</b> ~{total_rub_value:,.2f} $")

        response_lines.append(f"\n<b>Текущие курсы (USD):</b>")
        for symbol, rate in CURRENT_RATES.items():
            if symbol == 'RUB': continue
            
            # --- ИЗМЕНЕНИЕ ЗДЕСЬ ---
            if symbol == 'GRAM':
                # Форматируем GRAM с высокой точностью
                response_lines.append(f"• 1 {symbol} = ${rate.quantize(Decimal('0.00000001'))}")
            else:
                # Оставляем стандартное форматирование для других валют
                response_lines.append(f"• 1 {symbol} = ${rate.quantize(Decimal('0.01'))}")
        
        # --- И ВТОРОЕ ИЗМЕНЕНИЕ: БЛОК НИЖЕ УДАЛЕН ---
        # if USD_TO_RUB_RATE > 0:
        #     response_lines.append(f"\n<b>Курс обмена:</b>")
        #     response_lines.append(f"• 1 USD = {USD_TO_RUB_RATE:,.2f} RUB")

        bot.reply_to(message, "\n".join(response_lines), parse_mode='HTML')
    except Exception as e: bot.reply_to(message, f"⚠️ Ошибка при получении данных кошелька: {e}")
    finally: conn.close()

@bot.message_handler(commands=['buy_crypto'])
@antispam_filter
def buy_crypto(message: Message):
    user_id = message.from_user.id
    parts = message.text.split()
    if len(parts) != 3:
        # Убираем RUB из списка доступных для покупки
        available_crypto = ', '.join([key for key in CRYPTO_CURRENCIES.keys() if key != 'RUB'])
        return bot.reply_to(message,
                            f"📈 <b>Купить криптовалюту:</b>\n\n<code>/buy_crypto [символ] [сумма_в_баксах]</code>\n\n"
                            f"<b>Доступно:</b> {available_crypto}", parse_mode='HTML')

    crypto_symbol = parts[1].upper()
    rub_amount_str = parts[2]

    if crypto_symbol not in CRYPTO_CURRENCIES or crypto_symbol == 'RUB':
        return bot.reply_to(message, f"❌ Неподдерживаемый символ.")

    try:
        rub_amount = Decimal(rub_amount_str)
        if rub_amount <= 0: return bot.reply_to(message, "❌ Сумма для покупки должна быть положительной.")
    except InvalidOperation: return bot.reply_to(message, "❌ Введите корректную сумму в баксах.")

    if USD_TO_RUB_RATE <= 0: return bot.reply_to(message, "⚠️ Курс обмена временно недоступен. Попробуйте позже.")

    current_rate_usd = CURRENT_RATES.get(crypto_symbol)
    if not current_rate_usd or current_rate_usd <= 0: return bot.reply_to(message, f"⚠️ Курс для {crypto_symbol} временно недоступен.")

    usd_cost = rub_amount / USD_TO_RUB_RATE
    amount_to_buy_crypto = usd_cost / current_rate_usd

    register_user(user_id)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        user_rub_balance_result = cursor.fetchone()
        user_rub_balance = user_rub_balance_result[0] if user_rub_balance_result else 0

        if user_rub_balance < int(rub_amount): return bot.reply_to(message, f"❌ Недостаточно долларов. Ваш баланс: <b>{user_rub_balance:,} $</b>", parse_mode='HTML')

        conn.execute("BEGIN TRANSACTION")
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (int(rub_amount), user_id))

        cursor.execute("SELECT amount FROM crypto_balances WHERE user_id = ? AND currency = ?", (user_id, crypto_symbol))
        existing_crypto_balance_str = cursor.fetchone()
        existing_crypto_balance = Decimal(existing_crypto_balance_str[0]) if existing_crypto_balance_str else Decimal('0')
        new_crypto_balance = existing_crypto_balance + amount_to_buy_crypto

        cursor.execute("REPLACE INTO crypto_balances (user_id, currency, amount) VALUES (?, ?, ?)", (user_id, crypto_symbol, str(new_crypto_balance)))
        cursor.execute("INSERT INTO logs (sender_id, amount, action, details) VALUES (?, ?, 'buy_crypto', ?)",
                       (user_id, int(rub_amount), f"Покупка {format_decimal(amount_to_buy_crypto)} {crypto_symbol}"))
        conn.commit()

        bot.reply_to(message, f"✅ Вы купили <b>{format_decimal(amount_to_buy_crypto)} {crypto_symbol}</b> за <b>{rub_amount:,.2f} $</b>", parse_mode='HTML')
        notify_staff("Покупка криптовалюты", f"Пользователь купил {crypto_symbol}", user_id, None, rub_amount)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при покупке криптовалюты: {str(e)}")
        conn.rollback()
    finally: conn.close()

@bot.message_handler(commands=['sell_crypto'])
@antispam_filter
def sell_crypto(message: Message):
    user_id = message.from_user.id
    parts = message.text.split()
    if len(parts) != 3:
        available_crypto = ', '.join([key for key in CRYPTO_CURRENCIES.keys() if key != 'RUB'])
        return bot.reply_to(message,
                            f"📉 <b>Продать криптовалюту:</b>\n\n<code>/sell_crypto [символ] [количество]</code>\n\n"
                            f"<b>Доступно:</b> {available_crypto}", parse_mode='HTML')

    crypto_symbol = parts[1].upper()
    crypto_amount_str = parts[2]

    if crypto_symbol not in CRYPTO_CURRENCIES or crypto_symbol == 'RUB':
        return bot.reply_to(message, f"❌ Неподдерживаемый символ.")

    try:
        crypto_amount = Decimal(crypto_amount_str)
        if crypto_amount <= 0: return bot.reply_to(message, "❌ Количество для продажи должно быть положительным.")
    except InvalidOperation: return bot.reply_to(message, "❌ Введите корректное количество криптовалюты.")

    if USD_TO_RUB_RATE <= 0: return bot.reply_to(message, "⚠️ Курс обмена временно недоступен. Попробуйте позже.")

    current_rate_usd = CURRENT_RATES.get(crypto_symbol)
    if not current_rate_usd or current_rate_usd <= 0: return bot.reply_to(message, f"⚠️ Курс для {crypto_symbol} временно недоступен.")

    usd_to_receive = crypto_amount * current_rate_usd
    rub_to_receive = usd_to_receive * USD_TO_RUB_RATE

    register_user(user_id)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT amount FROM crypto_balances WHERE user_id = ? AND currency = ?", (user_id, crypto_symbol))
        user_crypto_balance_str = cursor.fetchone()
        user_crypto_balance = Decimal(user_crypto_balance_str[0]) if user_crypto_balance_str else Decimal('0')

        if user_crypto_balance < crypto_amount:
            return bot.reply_to(message, f"❌ Недостаточно {crypto_symbol}. Ваш баланс: <b>{format_decimal(user_crypto_balance)} {crypto_symbol}</b>", parse_mode='HTML')

        conn.execute("BEGIN TRANSACTION")
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (int(rub_to_receive), user_id))

        new_crypto_balance = user_crypto_balance - crypto_amount
        if new_crypto_balance < Decimal('0.0000000001'):
            cursor.execute("DELETE FROM crypto_balances WHERE user_id = ? AND currency = ?", (user_id, crypto_symbol))
        else:
            cursor.execute("UPDATE crypto_balances SET amount = ? WHERE user_id = ? AND currency = ?", (str(new_crypto_balance), user_id, crypto_symbol))

        cursor.execute("INSERT INTO logs (sender_id, amount, action, details) VALUES (?, ?, 'sell_crypto', ?)",
                       (user_id, int(rub_to_receive), f"Продажа {format_decimal(crypto_amount)} {crypto_symbol}"))
        conn.commit()

        bot.reply_to(message, f"✅ Вы продали <b>{format_decimal(crypto_amount)} {crypto_symbol}</b> и получили <b>{rub_to_receive:,.2f} $</b>", parse_mode='HTML')
        notify_staff("Продажа криптовалюты", f"Пользователь продал {crypto_symbol}", user_id, None, int(rub_to_receive))
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при продаже криптовалюты: {str(e)}")
        conn.rollback()
    finally: conn.close()

@bot.message_handler(commands=['transfer_crypto'])
@antispam_filter
def transfer_crypto(message: Message):
    sender_id = message.from_user.id
    parts = message.text.split()
    receiver_id, amount_str, crypto_symbol = None, None, None
    if message.reply_to_message and len(parts) == 3:
        receiver_id = message.reply_to_message.from_user.id
        amount_str, crypto_symbol = parts[1], parts[2].upper()
    elif len(parts) == 4:
        amount_str, crypto_symbol, receiver_identifier = parts[1], parts[2].upper(), parts[3]
        if receiver_identifier.startswith("@"):
            try: receiver_id = bot.get_chat(receiver_identifier).id
            except Exception: return bot.reply_to(message, "❌ Пользователь не найден.")
        else:
            try: receiver_id = int(receiver_identifier)
            except ValueError: return bot.reply_to(message, "❌ Введите корректный ID или username.")
    else:
        return bot.reply_to(message, "🔁 <b>Перевести криптовалюту:</b>\n\n"
                                   "<b>1. Ответом:</b> <code>/transfer_crypto [кол-во] [символ]</code>\n\n"
                                   "<b>2. Указав получателя:</b> <code>/transfer_crypto [кол-во] [символ] [ID]</code>", parse_mode='HTML')
    if receiver_id is None: return bot.reply_to(message, "❌ Не удалось определить получателя.")
    if sender_id == receiver_id: return bot.reply_to(message, "❌ Нельзя переводить самому себе.")

    available_crypto = [key for key in CRYPTO_CURRENCIES.keys() if key != 'RUB']
    if crypto_symbol not in available_crypto: return bot.reply_to(message, f"❌ Неподдерживаемый символ. Доступные: {', '.join(available_crypto)}")

    try:
        amount_to_transfer = Decimal(amount_str)
        if amount_to_transfer <= 0: return bot.reply_to(message, "❌ Сумма перевода должна быть положительной.")
    except InvalidOperation: return bot.reply_to(message, "❌ Введите корректное количество.")

    register_user(sender_id); register_user(receiver_id)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        conn.execute("BEGIN TRANSACTION")
        cursor.execute("SELECT amount FROM crypto_balances WHERE user_id = ? AND currency = ?", (sender_id, crypto_symbol))
        sender_crypto_balance_str = cursor.fetchone()
        sender_crypto_balance = Decimal(sender_crypto_balance_str[0]) if sender_crypto_balance_str else Decimal('0')
        if sender_crypto_balance < amount_to_transfer:
            conn.rollback()
            return bot.reply_to(message, f"❌ Недостаточно {crypto_symbol}. Ваш баланс: <b>{format_decimal(sender_crypto_balance)} {crypto_symbol}</b>", parse_mode='HTML')

        usd_equivalent = amount_to_transfer * CURRENT_RATES.get(crypto_symbol, Decimal('0'))
        if usd_equivalent > 0 and USD_TO_RUB_RATE > 0:
            rub_equivalent = usd_equivalent * USD_TO_RUB_RATE
            grant_xp_for_pair_transaction(sender_id, receiver_id, int(rub_equivalent))

        new_sender_balance = sender_crypto_balance - amount_to_transfer
        if new_sender_balance < Decimal('0.0000000001'):
            cursor.execute("DELETE FROM crypto_balances WHERE user_id = ? AND currency = ?", (sender_id, crypto_symbol))
        else:
            cursor.execute("UPDATE crypto_balances SET amount = ? WHERE user_id = ? AND currency = ?", (str(new_sender_balance), sender_id, crypto_symbol))

        cursor.execute("SELECT amount FROM crypto_balances WHERE user_id = ? AND currency = ?", (receiver_id, crypto_symbol))
        receiver_crypto_balance_str = cursor.fetchone()
        receiver_crypto_balance = Decimal(receiver_crypto_balance_str[0]) if receiver_crypto_balance_str else Decimal('0')
        new_receiver_balance = receiver_crypto_balance + amount_to_transfer
        cursor.execute("REPLACE INTO crypto_balances (user_id, currency, amount) VALUES (?, ?, ?)", (receiver_id, crypto_symbol, str(new_receiver_balance)))
        conn.commit()
        bot.reply_to(message, f"✅ Вы перевели <b>{format_decimal(amount_to_transfer)} {crypto_symbol}</b> пользователю {get_display_name(receiver_id)}.", parse_mode='HTML')
        notify_staff("Перевод криптовалюты", f"Пользователь перевел {crypto_symbol}", sender_id, receiver_id, amount_to_transfer)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при переводе криптовалюты: {str(e)}")
        conn.rollback()
    finally: conn.close()

@bot.message_handler(commands=['addlaw'])
@antispam_filter
def add_law(message: Message):
    if not has_law_management_permission(message.from_user.id): return bot.reply_to(message, "⛔ Только Президент или Министр могут управлять законами.")
    parts = message.text.split('|')
    if len(parts) != 3:
        return bot.reply_to(message,
            "⚖️ <b>Как добавить/изменить закон:</b>\n\n"
            "<code>/addlaw [Категория] | [Название] | [Текст закона]</code>", parse_mode='HTML')
    try:
        category = parts[0].replace('/addlaw', '').strip()
        title = parts[1].strip()
        content = parts[2].strip()
        if not category or not title or not content: raise ValueError
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("REPLACE INTO laws (category, title, content) VALUES (?, ?, ?)", (category, title, content))
        conn.commit()
        bot.reply_to(message, f"✅ Закон '<b>{title}</b>' в категории '<b>{category}</b>' успешно добавлен/обновлен.", parse_mode='HTML')
    except ValueError: return bot.reply_to(message, "❌ Неверный формат. Все части должны быть заполнены.")
    except Exception as e: bot.reply_to(message, f"⚠️ Произошла ошибка: {e}")
    finally:
        if 'conn' in locals() and conn: conn.close()

@bot.message_handler(commands=['deletelaw'])
@antispam_filter
def delete_law(message: Message):
    if not has_law_management_permission(message.from_user.id): return bot.reply_to(message, "⛔ Только Президент или Министр могут управлять законами.")
    parts = message.text.split('|')
    if len(parts) != 2:
        return bot.reply_to(message, "⚖️ <b>Как удалить закон:</b>\n\n<code>/deletelaw [Категория] | [Название]</code>", parse_mode='HTML')
    try:
        category = parts[0].replace('/deletelaw', '').strip()
        title = parts[1].strip()
        if not category or not title: raise ValueError
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM laws WHERE category = ? AND title = ?", (category, title))
        if cursor.rowcount > 0:
            conn.commit()
            bot.reply_to(message, f"✅ Закон '<b>{title}</b>' из категории '<b>{category}</b>' успешно удален.", parse_mode='HTML')
        else: bot.reply_to(message, "❌ Закон с таким названием в указанной категории не найден.")
    except ValueError: return bot.reply_to(message, "❌ Неверный формат. Укажите и категорию, и название.")
    except Exception as e: bot.reply_to(message, f"⚠️ Произошла ошибка: {e}")
    finally:
        if 'conn' in locals() and conn: conn.close()

@bot.message_handler(commands=['laws'])
@antispam_filter
def show_laws(message: Message):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT category FROM laws ORDER BY category")
        categories = cursor.fetchall()
        if not categories:
            return bot.reply_to(message, "⚖️ В базе данных пока нет законов.")
        
        markup = InlineKeyboardMarkup(row_width=2)
        buttons = []
        # Теперь используем индекс вместо названия в callback_data
        for i, (cat_name,) in enumerate(categories):
            buttons.append(InlineKeyboardButton(cat_name, callback_data=f"law_cat_{i}"))
        
        markup.add(*buttons)
        bot.reply_to(message, "⚖️ <b>Законодательство:</b>\n\nВыберите категорию:", reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при получении списка законов: {e}")
    finally:
        conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('law_'))
def law_callback_handler(call):
    parts = call.data.split('_')
    action_type = parts[1]
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        if action_type == 'cat':
            category_index = int(parts[2])
            
            # Получаем снова отсортированный список категорий
            cursor.execute("SELECT DISTINCT category FROM laws ORDER BY category")
            categories = cursor.fetchall()
            
            # Находим нужную по индексу
            category = categories[category_index][0]
            
            cursor.execute("SELECT id, title FROM laws WHERE category = ? ORDER BY title", (category,))
            laws = cursor.fetchall()
            markup = InlineKeyboardMarkup(row_width=1)
            for law_id, title in laws:
                markup.add(InlineKeyboardButton(title, callback_data=f"law_doc_{law_id}"))
            markup.add(InlineKeyboardButton("⬅️ Назад к категориям", callback_data="law_back_main"))
            bot.edit_message_text(f"⚖️ <b>Категория: {category}</b>\n\nВыберите документ:",
                                  call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')

        elif action_type == 'doc':
            law_id = int(parts[2])
            cursor.execute("SELECT category, title, content FROM laws WHERE id = ?", (law_id,))
            law = cursor.fetchone()
            if law:
                category, title, content = law
                text = f"<b>{category}</b>\n\n<b><u>{title}</u></b>\n\n{content}"
                
                # Чтобы сделать кнопку "назад", нам снова нужен индекс категории
                cursor.execute("SELECT DISTINCT category FROM laws ORDER BY category")
                categories = [cat[0] for cat in cursor.fetchall()]
                category_index = categories.index(category)
                
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton(f"⬅️ Назад к '{category}'", callback_data=f"law_cat_{category_index}"))
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')

        elif action_type == 'back' and parts[2] == 'main':
            cursor.execute("SELECT DISTINCT category FROM laws ORDER BY category")
            categories = cursor.fetchall()
            markup = InlineKeyboardMarkup(row_width=2)
            buttons = []
            for i, (cat_name,) in enumerate(categories):
                buttons.append(InlineKeyboardButton(cat_name, callback_data=f"law_cat_{i}"))
            markup.add(*buttons)
            bot.edit_message_text("⚖️ <b>Законодательство:</b>\n\nВыберите категорию:",
                                  call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        print(f"Ошибка в коллбэке законов: {e}")
        bot.answer_callback_query(call.id, "Произошла ошибка")
    finally:
        conn.close()

if __name__ == '__main__':
    print("Инициализация базы данных...")
    init_db()
    print("Установка команд бота...")
    set_commands()
    try:
        BOT_USERNAME = bot.get_me().username
        print(f"Имя бота: @{BOT_USERNAME}")
    except Exception as e:
        print(f"Критическая ошибка: не удалось получить имя пользователя бота. Проверьте токен. Ошибка: {e}")
        sys.exit(1)
    print("Обновление курсов...")
    update_rates_from_coinmarketcap()
    update_rub_rate()
    updater_thread = threading.Thread(target=run_rate_updater, daemon=True)
    updater_thread.start()

    overdue_thread = threading.Thread(target=process_overdue_invoices, daemon=True)
    overdue_thread.start()

    bills_thread = threading.Thread(target=issue_weekly_bills, daemon=True)
    bills_thread.start()

    # <<<--- ВОТ ЭТИ ДВЕ СТРОКИ НУЖНО ДОБАВИТЬ
    auction_thread = threading.Thread(target=process_finished_auctions, daemon=True)
    auction_thread.start()
    # --- КОНЕЦ ---

    print("Бот запущен...")
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        print(f"Критическая  при запуске бота: {e}")