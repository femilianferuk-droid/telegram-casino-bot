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

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('casino_bot.db', check_same_thread=False)
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
            return {
                'user_id': user[0], 'username': user[1], 'first_name': user[2],
                'balance_real': user[3], 'balance_bonus': user[4], 'total_wagered': user[5]
            }
        return None
    
    def create_user(self, user_id: int, username: str, first_name: str):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)', 
                      (user_id, username, first_name))
        self.conn.commit()
    
    def update_balance(self, user_id: int, amount: float, balance_type: str):
        cursor = self.conn.cursor()
        if balance_type == 'real':
            cursor.execute('UPDATE users SET balance_real = balance_real + ? WHERE user_id = ?', (amount, user_id))
        else:
            cursor.execute('UPDATE users SET balance_bonus = balance_bonus + ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()
    
    def get_all_users(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        return [row[0] for row in cursor.fetchall()]

db = Database()

class CasinoBot:
    def __init__(self):
        self.app = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("admin", self.admin_panel))
        self.app.add_handler(CallbackQueryHandler(self.button_handler, pattern="^main_"))
        self.app.add_handler(CallbackQueryHandler(self.games_handler, pattern="^game_"))
        self.app.add_handler(CallbackQueryHandler(self.balance_handler, pattern="^balance_"))
        self.app.add_handler(CallbackQueryHandler(self.deposit_handler, pattern="^deposit_"))
        self.app.add_handler(CallbackQueryHandler(self.bet_handler, pattern="^bet_"))
        self.app.add_handler(CallbackQueryHandler(self.admin_handler, pattern="^admin_"))
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
            welcome_text = f"🎰 С возвращением в NEEZEEX CASINO, {user.first_name}!"

        await update.message.reply_text(welcome_text, reply_markup=self.get_main_keyboard())
    
    def get_main_keyboard(self):
        keyboard = [
            ["🎮 Игры", "💰 Баланс"],
            ["📥 Пополнить", "📤 Вывести"],
            ["📊 История", "🆘 Поддержка"]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def get_games_keyboard(self):
        keyboard = [
            [
                InlineKeyboardButton("🎲 Кости", callback_data="game_dice"),
                InlineKeyboardButton("🏀 Баскетбол", callback_data="game_basketball")
            ],
            [
                InlineKeyboardButton("⚽ Футбол", callback_data="game_football"),
                InlineKeyboardButton("🎳 Боулинг", callback_data="game_bowling")
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_balance_keyboard(self):
        keyboard = [
            [
                InlineKeyboardButton("📥 Пополнить", callback_data="balance_deposit"),
                InlineKeyboardButton("📤 Вывести", callback_data="balance_withdraw")
            ],
            [
                InlineKeyboardButton("📊 История", callback_data="balance_history"),
                InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_bet_keyboard(self, game_type: str):
        bets = {
            'dice': [1.0, 5.0, 10.0],
            'basketball': [2.0, 5.0, 15.0],
            'football': [3.0, 7.0, 20.0],
            'bowling': [1.0, 3.0, 8.0]
        }
        
        keyboard = []
        for bet in bets[game_type]:
            keyboard.append([InlineKeyboardButton(f"${bet}", callback_data=f"bet_{game_type}_{bet}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_games")])
        return InlineKeyboardMarkup(keyboard)
    
    def get_admin_keyboard(self):
        keyboard = [
            [
                InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
                InlineKeyboardButton("👤 Изменить баланс", callback_data="admin_balance")
            ],
            [
                InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"),
                InlineKeyboardButton("👥 Все пользователи", callback_data="admin_users")
            ],
            [
                InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "main_menu":
            await query.edit_message_text(
                "🎰 Главное меню NEEZEEX CASINO",
                reply_markup=self.get_games_keyboard()
            )
        elif data == "main_games":
            await query.edit_message_text(
                "🎮 Выберите игру:",
                reply_markup=self.get_games_keyboard()
            )
        elif data == "main_balance":
            user_data = db.get_user(query.from_user.id)
            balance_text = f"""💰 Ваши балансы:

💵 Реальный: ${user_data['balance_real']:.2f}
🎁 Бонусный: ${user_data['balance_bonus']:.2f}

💸 Общий выигрыш: ${user_data['total_wagered']:.2f}"""
            await query.edit_message_text(
                balance_text,
                reply_markup=self.get_balance_keyboard()
            )
    
    async def games_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        game_type = query.data.replace("game_", "")
        
        game_names = {
            'dice': '🎲 Кости',
            'basketball': '🏀 Баскетбол', 
            'football': '⚽ Футбол',
            'bowling': '🎳 Боулинг'
        }
        
        await query.edit_message_text(
            f"{game_names[game_type]}\n\nВыберите сумму ставки:",
            reply_markup=self.get_bet_keyboard(game_type)
        )
    
    async def bet_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data_parts = query.data.split('_')
        game_type = data_parts[1]
        bet_amount = float(data_parts[2])
        
        user_data = db.get_user(user_id)
        
        # Проверяем баланс
        if user_data['balance_real'] + user_data['balance_bonus'] < bet_amount:
            await query.edit_message_text(f"❌ Недостаточно средств. Ваш баланс: ${user_data['balance_real'] + user_data['balance_bonus']:.2f}")
            return
        
        # Используем сначала бонусные средства
        if user_data['balance_bonus'] >= bet_amount:
            balance_type = 'bonus'
            db.update_balance(user_id, -bet_amount, 'bonus')
        else:
            balance_type = 'real'
            db.update_balance(user_id, -bet_amount, 'real')
        
        # Играем в выбранную игру
        try:
            message = await query.message.reply_dice(emoji=self.get_dice_emoji(game_type))
            dice_value = message.dice.value
            await asyncio.sleep(2)
            
            win_amount = self.calculate_win(game_type, dice_value, bet_amount)
            
            # Начисляем выигрыш
            if win_amount > 0:
                if balance_type == 'bonus':
                    db.update_balance(user_id, win_amount, 'real')
                else:
                    db.update_balance(user_id, win_amount, 'real')
            
            result_text = self.get_game_result_text(game_type, dice_value, bet_amount, win_amount)
            
            # Обновляем баланс пользователя
            user_data = db.get_user(user_id)
            
            result_text += f"\n\n💰 Ваш баланс:\n💵 Реальный: ${user_data['balance_real']:.2f}\n🎁 Бонусный: ${user_data['balance_bonus']:.2f}"
            
            keyboard = [
                [InlineKeyboardButton("🎮 Еще раз", callback_data=f"game_{game_type}")],
                [InlineKeyboardButton("🔙 К играм", callback_data="main_games")]
            ]
            
            await query.edit_message_text(
                result_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка в игре: {str(e)}")
    
    def get_dice_emoji(self, game_type: str) -> str:
        emojis = {
            'dice': '🎲',
            'basketball': '🏀', 
            'football': '⚽',
            'bowling': '🎳'
        }
        return emojis.get(game_type, '🎲')
    
    def calculate_win(self, game_type: str, dice_value: int, bet_amount: float) -> float:
        if game_type == 'dice':
            return bet_amount * 2 if dice_value >= 4 else 0
        elif game_type == 'basketball':
            return bet_amount * 2 if dice_value >= 4 else 0
        elif game_type == 'football':
            return bet_amount * 2 if dice_value >= 3 else 0
        elif game_type == 'bowling':
            if dice_value >= 5:
                return bet_amount * 3
            elif dice_value >= 3:
                return bet_amount * 1.5
            else:
                return 0
        return 0
    
    def get_game_result_text(self, game_type: str, dice_value: int, bet_amount: float, win_amount: float) -> str:
        base_text = f"🎯 Результат: {dice_value}\n💰 Ставка: ${bet_amount}\n"
        
        if win_amount > 0:
            return base_text + f"🎉 Вы выиграли! +${win_amount}"
        else:
            return base_text + "😔 Вы проиграли"
    
    async def balance_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "balance_deposit":
            deposit_text = """📥 Заполните анкету для пополнения:

💳 Чем вы хотите пополнить баланс (реальными рублями/testnet)
💰 Сколько хотите пополнить (от 20₽)

📨 Пришлите заполненую анкету ему: @nezeexcasino"""
            
            await query.edit_message_text(deposit_text, reply_markup=self.get_balance_keyboard())
        
        elif data == "balance_withdraw":
            withdraw_text = """📤 Заполните анкету для вывода:

💳 Что вы хотите вывести? (реальные рубли/testnet)
💰 Какую сумму (от 20₽)

📨 Пришлите заполненую анкету @nezeexcasino"""
            
            await query.edit_message_text(withdraw_text, reply_markup=self.get_balance_keyboard())
        
        elif data == "balance_history":
            await query.edit_message_text("📊 История транзакций будет доступна в ближайшее время", 
                                        reply_markup=self.get_balance_keyboard())
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ Доступ запрещен")
            return
        
        await update.message.reply_text(
            "🛠️ АДМИН-ПАНЕЛЬ 🛠️\n\nВыберите действие:",
            reply_markup=self.get_admin_keyboard()
        )
    
    async def admin_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            await query.edit_message_text("❌ Доступ запрещен")
            return
        
        data = query.data
        
        if data == "admin_stats":
            # Статистика бота
            all_users = db.get_all_users()
            total_users = len(all_users)
            
            stats_text = f"""📊 СТАТИСТИКА БОТА

👥 Пользователей: {total_users}
🆔 Ваш ID: {user_id}
🎯 Админ: @nezeexcasino"""
            
            await query.edit_message_text(stats_text, reply_markup=self.get_admin_keyboard())
        
        elif data == "admin_broadcast":
            context.user_data['awaiting_broadcast'] = True
            await query.edit_message_text(
                "📢 Введите сообщение для рассылки всем пользователям:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="admin_back")]])
            )
        
        elif data == "admin_balance":
            context.user_data['awaiting_balance_user'] = True
            await query.edit_message_text(
                "👤 Введите ID пользователя для изменения баланса:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="admin_back")]])
            )
        
        elif data == "admin_users":
            all_users = db.get_all_users()
            users_text = f"👥 Всего пользователей: {len(all_users)}\n\n"
            users_text += "📋 Список ID пользователей:\n"
            
            for i, user_id in enumerate(all_users[:50], 1):  # Показываем первые 50
                users_text += f"{i}. {user_id}\n"
            
            if len(all_users) > 50:
                users_text += f"\n... и еще {len(all_users) - 50} пользователей"
            
            await query.edit_message_text(users_text, reply_markup=self.get_admin_keyboard())
        
        elif data == "admin_back":
            await query.edit_message_text(
                "🛠️ АДМИН-ПАНЕЛЬ 🛠️\n\nВыберите действие:",
                reply_markup=self.get_admin_keyboard()
            )
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # Обработка админских команд
        if user_id in ADMIN_IDS:
            if context.user_data.get('awaiting_broadcast'):
                context.user_data['awaiting_broadcast'] = False
                
                all_users = db.get_all_users()
                success = 0
                failed = 0
                
                for chat_id in all_users:
                    try:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"📢 Рассылка от администратора:\n\n{message_text}"
                        )
                        success += 1
                    except:
                        failed += 1
                
                await update.message.reply_text(
                    f"✅ Рассылка завершена:\n"
                    f"✅ Успешно: {success}\n"
                    f"❌ Не доставлено: {failed}",
                    reply_markup=self.get_admin_keyboard()
                )
                return
            
            elif context.user_data.get('awaiting_balance_user'):
                context.user_data['awaiting_balance_user'] = False
                context.user_data['balance_user_id'] = message_text
                context.user_data['awaiting_balance_type'] = True
                
                keyboard = [
                    [InlineKeyboardButton("💵 Реальный", callback_data="balance_type_real")],
                    [InlineKeyboardButton("🎁 Бонусный", callback_data="balance_type_bonus")],
                    [InlineKeyboardButton("🔙 Отмена", callback_data="admin_back")]
                ]
                
                await update.message.reply_text(
                    f"👤 Пользователь: {message_text}\n\nВыберите тип баланса:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
        
        # Обработка основных кнопок
        if message_text == "🎮 Игры":
            await update.message.reply_text(
                "🎮 Выберите игру:",
                reply_markup=self.get_games_keyboard()
            )
        elif message_text == "💰 Баланс":
            user_data = db.get_user(user_id)
            balance_text = f"""💰 Ваши балансы:

💵 Реальный: ${user_data['balance_real']:.2f}
🎁 Бонусный: ${user_data['balance_bonus']:.2f}

💸 Общий выигрыш: ${user_data['total_wagered']:.2f}"""
            await update.message.reply_text(
                balance_text,
                reply_markup=self.get_balance_keyboard()
            )
        elif message_text == "📥 Пополнить":
            deposit_text = """📥 Заполните анкету для пополнения:

💳 Чем вы хотите пополнить баланс (реальными рублями/testnet)
💰 Сколько хотите пополнить (от 20₽)

📨 Пришлите заполненую анкету ему: @nezeexcasino"""
            await update.message.reply_text(deposit_text)
        elif message_text == "📤 Вывести":
            withdraw_text = """📤 Заполните анкету для вывода:

💳 Что вы хотите вывести? (реальные рубли/testnet)
💰 Какую сумму (от 20₽)

📨 Пришлите заполненую анкету @nezeexcasino"""
            await update.message.reply_text(withdraw_text)
        elif message_text == "📊 История":
            await update.message.reply_text("📊 История транзакций будет доступна в ближайшее время")
        elif message_text == "🆘 Поддержка":
            await update.message.reply_text("🆘 Поддержка: @nezeexcasino")

if __name__ == "__main__":
    bot = CasinoBot()
    print("🤖 Бот запущен!")
    bot.app.run_polling()
