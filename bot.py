import logging
import sqlite3
import random
import asyncio
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Конфигурация
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8331254765:AAGIzkKOSIekInIyUP-7rVVp3zLFkxIMtgQ')
ADMIN_IDS = [7973988177]
STARTING_BONUS = 10.0

# База данных
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('/tmp/casino_bot.db', check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT, first_name TEXT,
                balance_real REAL DEFAULT 0.0, balance_bonus REAL DEFAULT 10.0,
                total_wagered REAL DEFAULT 0.0, registered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
    
    def get_user(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        if user:
            return {'user_id': user[0], 'username': user[1], 'first_name': user[2], 
                    'balance_real': user[3], 'balance_bonus': user[4], 'total_wagered': user[5]}
        return None
    
    def create_user(self, user_id: int, username: str, first_name: str):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)', 
                      (user_id, username, first_name))
        self.conn.commit()

db = Database()

# Основной класс бота
class CasinoBot:
    def __init__(self):
        self.app = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CallbackQueryHandler(self.button_handler))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = db.get_user(user.id)
        
        if not user_data:
            db.create_user(user.id, user.username, user.first_name)
            welcome_text = f"""🎰 Добро пожаловать в NEEZEEX CASINO, {user.first_name}!

💰 Вам начислен стартовый бонус: ${STARTING_BONUS}

🎮 Доступные игры:
• 🎲 Кости
• 🏀 Баскетбол
• ⚽ Футбол
• 🎳 Боулинг"""
        else:
            welcome_text = f"🎰 С возвращением, {user.first_name}!"
        
        await update.message.reply_text(welcome_text, reply_markup=self.get_main_keyboard())
    
    def get_main_keyboard(self):
        keyboard = [["🎮 Игры", "💰 Баланс"], ["📥 Пополнить", "🆘 Поддержка"]]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text
        
        if text == "🎮 Игры":
            keyboard = [
                [InlineKeyboardButton("🎲 Кости", callback_data="game_dice")],
                [InlineKeyboardButton("🏀 Баскетбол", callback_data="game_basketball")],
                [InlineKeyboardButton("⚽ Футбол", callback_data="game_football")],
                [InlineKeyboardButton("🎳 Боулинг", callback_data="game_bowling")]
            ]
            await update.message.reply_text("🎮 Выберите игру:", reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif text == "💰 Баланс":
            user_data = db.get_user(user_id)
            balance_text = f"""💰 Ваши балансы:

💵 Реальный: ${user_data['balance_real']:.2f}
🎁 Бонусный: ${user_data['balance_bonus']:.2f}"""
            await update.message.reply_text(balance_text)
        
        elif text == "📥 Пополнить":
            await update.message.reply_text("💵 Для пополнения напишите @nezeexcasino")
        
        elif text == "🆘 Поддержка":
            await update.message.reply_text("🆘 Поддержка: @nezeexcasino")

# Запуск бота
def main():
    bot = CasinoBot()
    print("🤖 Бот запущен на bothost.ru!")
    bot.app.run_polling()

if __name__ == "__main__":
    main()
