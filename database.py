# database.py
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
from models import User, Message, Gift, UserGift, SphereTransaction
import random


class Database:
    def __init__(self, db_path="messenger.db"):
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._init_tables()
        self._init_gifts()

    def _connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def _init_tables(self):
        cursor = self.conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_verified BOOLEAN DEFAULT 0,
                avatar TEXT DEFAULT '',
                spheres INTEGER DEFAULT 0,
                language TEXT DEFAULT 'ru',
                accent_color TEXT DEFAULT 'BLUE',
                background_image TEXT DEFAULT ''
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_read BOOLEAN DEFAULT 0,
                is_gift BOOLEAN DEFAULT 0,
                gift_id INTEGER DEFAULT 0,
                FOREIGN KEY (sender_id) REFERENCES users (id),
                FOREIGN KEY (receiver_id) REFERENCES users (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used BOOLEAN DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                emoji TEXT NOT NULL,
                description TEXT,
                price INTEGER DEFAULT 1,
                rarity TEXT DEFAULT 'common'
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_gifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                gift_id INTEGER NOT NULL,
                from_user_id INTEGER NOT NULL,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (from_user_id) REFERENCES users (id),
                FOREIGN KEY (gift_id) REFERENCES gifts (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sphere_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        self.conn.commit()
        print("✅ База данных инициализирована")

    def _init_gifts(self):
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM gifts")
        count = cursor.fetchone()[0]

        if count == 0:
            gifts = [
                # Обычные (common) - цена 10
                ("Роза", "🌹", "Красивая роза", 10, "common"),
                ("Сердце", "❤️", "Любовь", 10, "common"),
                ("Пицца", "🍕", "Вкусный подарок", 10, "common"),
                ("Шоколад", "🍫", "Сладкий подарок", 10, "common"),
                ("Пиво", "🍺", "Отдыхай!", 10, "common"),
                ("Мороженое", "🍦", "Освежающий подарок", 10, "common"),
                ("Смайлик", "😊", "Улыбнись!", 10, "common"),
                ("Кекс", "🧁", "Сладкий кекс", 10, "common"),
                # Необычные (uncommon) - цена 20
                ("Звезда", "⭐", "Ты звезда!", 20, "uncommon"),
                ("Торт", "🎂", "С днём рождения!", 20, "uncommon"),
                ("Цветы", "💐", "Букет цветов", 20, "uncommon"),
                ("Солнце", "☀️", "Свети ярко!", 20, "uncommon"),
                ("Луна", "🌙", "Спокойной ночи", 20, "uncommon"),
                ("Подарок", "🎁", "Сюрприз!", 20, "uncommon"),
                # Редкие (rare) - цена 35
                ("Котик", "🐱", "Милый котик", 35, "rare"),
                ("Пёсик", "🐶", "Верный пёсик", 35, "rare"),
                ("Ракета", "🚀", "К успеху!", 35, "rare"),
                # Эпические (epic) - цена 75
                ("Алмаз", "💎", "Бесценный подарок", 75, "epic"),
                ("Дракон", "🐉", "Сила и мощь", 75, "epic"),
                ("Единорог", "🦄", "Волшебство", 75, "epic"),
                # Легендарные (legendary) - цена 100
                ("Корона", "👑", "Ты король!", 100, "legendary"),
                ("Феникс", "🔥", "Возрождение", 100, "legendary"),
                ("Пегас", "🐴", "Свобода и скорость", 100, "legendary"),
                ("Космос", "🌌", "Бесконечность", 100, "legendary"),
            ]

            for name, emoji, description, price, rarity in gifts:
                cursor.execute(
                    "INSERT INTO gifts (name, emoji, description, price, rarity) VALUES (?, ?, ?, ?, ?)",
                    (name, emoji, description, price, rarity)
                )

            self.conn.commit()
            print("✅ Добавлены подарки с редкостями")

    # ==================== ПОЛЬЗОВАТЕЛИ ====================

    def create_user(self, username: str, email: str, password: str) -> Optional[User]:
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password, is_verified) VALUES (?, ?, ?, 0)",
                (username, email, password)
            )
            self.conn.commit()
            user_id = cursor.lastrowid
            return self.get_user_by_id(user_id)
        except sqlite3.IntegrityError as e:
            print(f"❌ Ошибка создания пользователя: {e}")
            return None

    def verify_user(self, email: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE users SET is_verified = 1 WHERE email = ?",
            (email,)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def update_user_avatar(self, user_id: int, avatar: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE users SET avatar = ? WHERE id = ?",
            (avatar, user_id)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def update_user_settings(self, user_id: int, language: str, accent_color: str, background_image: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE users SET language = ?, accent_color = ?, background_image = ? WHERE id = ?",
            (language, accent_color, background_image, user_id)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            try:
                return User(
                    id=row['id'],
                    username=row['username'],
                    email=row['email'],
                    password=row['password'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    is_verified=bool(row['is_verified']),
                    avatar=row['avatar'] if row['avatar'] else '',
                    spheres=row['spheres'] if row['spheres'] else 0,
                    language=row['language'] if row['language'] else 'ru',
                    accent_color=row['accent_color'] if row['accent_color'] else 'BLUE',
                    background_image=row['background_image'] if row['background_image'] else '',
                    gifts=self.get_user_gifts_ids(user_id)
                )
            except:
                return None
        return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row:
                try:
                    return User(
                        id=row['id'],
                        username=row['username'],
                        email=row['email'],
                        password=row['password'],
                        created_at=datetime.fromisoformat(row['created_at']),
                        is_verified=bool(row['is_verified']),
                        avatar=row['avatar'] if row['avatar'] else '',
                        spheres=row['spheres'] if row['spheres'] else 0,
                        language=row['language'] if row['language'] else 'ru',
                        accent_color=row['accent_color'] if row['accent_color'] else 'BLUE',
                        background_image=row['background_image'] if row['background_image'] else '',
                        gifts=self.get_user_gifts_ids(row['id'])
                    )
                except:
                    return None
        except:
            pass
        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        if row:
            try:
                return User(
                    id=row['id'],
                    username=row['username'],
                    email=row['email'],
                    password=row['password'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    is_verified=bool(row['is_verified']),
                    avatar=row['avatar'] if row['avatar'] else '',
                    spheres=row['spheres'] if row['spheres'] else 0,
                    language=row['language'] if row['language'] else 'ru',
                    accent_color=row['accent_color'] if row['accent_color'] else 'BLUE',
                    background_image=row['background_image'] if row['background_image'] else '',
                    gifts=self.get_user_gifts_ids(row['id'])
                )
            except:
                return None
        return None

    def get_all_users(self) -> List[User]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY username")
        rows = cursor.fetchall()
        users = []
        for row in rows:
            try:
                users.append(User(
                    id=row['id'],
                    username=row['username'],
                    email=row['email'],
                    password=row['password'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    is_verified=bool(row['is_verified']),
                    avatar=row['avatar'] if row['avatar'] else '',
                    spheres=row['spheres'] if row['spheres'] else 0,
                    language=row['language'] if row['language'] else 'ru',
                    accent_color=row['accent_color'] if row['accent_color'] else 'BLUE',
                    background_image=row['background_image'] if row['background_image'] else '',
                    gifts=self.get_user_gifts_ids(row['id'])
                ))
            except:
                continue
        return users

    # ==================== КОДЫ ПОДТВЕРЖДЕНИЯ ====================

    def save_verification_code(self, email: str, code: str) -> bool:
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO verification_codes (email, code) VALUES (?, ?)",
                (email, code)
            )
            self.conn.commit()
            return True
        except:
            return False

    def verify_code(self, email: str, code: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM verification_codes 
            WHERE email = ? AND code = ? AND used = 0 
            AND created_at > datetime('now', '-5 minutes')
            ORDER BY created_at DESC LIMIT 1
        ''', (email, code))

        row = cursor.fetchone()
        if row:
            cursor.execute(
                "UPDATE verification_codes SET used = 1 WHERE id = ?",
                (row['id'],)
            )
            self.conn.commit()
            return True
        return False

    # ==================== СООБЩЕНИЯ ====================

    def save_message(self, sender_id: int, content: str, receiver_id: int, is_gift: bool = False,
                     gift_id: int = 0) -> Message:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO messages (sender_id, receiver_id, content, is_gift, gift_id) VALUES (?, ?, ?, ?, ?)",
            (sender_id, receiver_id, content, 1 if is_gift else 0, gift_id)
        )
        self.conn.commit()
        msg_id = cursor.lastrowid
        return self.get_message_by_id(msg_id)

    def get_message_by_id(self, msg_id: int) -> Optional[Message]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE id = ?", (msg_id,))
        row = cursor.fetchone()
        if row:
            try:
                return Message(
                    id=row['id'],
                    sender_id=row['sender_id'],
                    receiver_id=row['receiver_id'],
                    content=row['content'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    is_read=bool(row['is_read']),
                    is_gift=bool(row['is_gift']),
                    gift_id=row['gift_id'] if row['gift_id'] else 0
                )
            except:
                return None
        return None

    def get_private_messages(self, user_id: int, limit: int = 100) -> List[Message]:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM messages 
            WHERE sender_id = ? OR receiver_id = ?
            ORDER BY timestamp DESC LIMIT ?
        ''', (user_id, user_id, limit))
        rows = cursor.fetchall()
        messages = []
        for row in rows:
            try:
                messages.append(Message(
                    id=row['id'],
                    sender_id=row['sender_id'],
                    receiver_id=row['receiver_id'],
                    content=row['content'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    is_read=bool(row['is_read']),
                    is_gift=bool(row['is_gift']),
                    gift_id=row['gift_id'] if row['gift_id'] else 0
                ))
            except:
                continue
        return messages[::-1]

    def mark_as_read(self, message_ids: List[int]):
        cursor = self.conn.cursor()
        if message_ids:
            ids = ','.join('?' * len(message_ids))
            cursor.execute(
                f"UPDATE messages SET is_read = 1 WHERE id IN ({ids})",
                message_ids
            )
            self.conn.commit()

    # ==================== ПОДАРКИ ====================

    def get_all_gifts(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM gifts ORDER BY price, id")
        rows = cursor.fetchall()
        return [
            {
                'id': row['id'],
                'name': row['name'],
                'emoji': row['emoji'],
                'description': row['description'],
                'price': row['price'] if row['price'] else 1,
                'rarity': row['rarity'] if row['rarity'] else 'common'
            }
            for row in rows
        ]

    def get_gift_by_id(self, gift_id: int) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM gifts WHERE id = ?", (gift_id,))
        row = cursor.fetchone()
        if row:
            return {
                'id': row['id'],
                'name': row['name'],
                'emoji': row['emoji'],
                'description': row['description'],
                'price': row['price'] if row['price'] else 1,
                'rarity': row['rarity'] if row['rarity'] else 'common'
            }
        return None

    def add_user_gift(self, user_id: int, gift_id: int, from_user_id: int) -> bool:
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO user_gifts (user_id, gift_id, from_user_id) VALUES (?, ?, ?)",
                (user_id, gift_id, from_user_id)
            )
            self.conn.commit()
            return True
        except:
            return False

    def get_user_gifts(self, user_id: int) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT ug.*, g.name, g.emoji, g.description, g.price, g.rarity, u.username as from_username
            FROM user_gifts ug
            JOIN gifts g ON ug.gift_id = g.id
            JOIN users u ON ug.from_user_id = u.id
            WHERE ug.user_id = ?
            ORDER BY ug.received_at DESC
        ''', (user_id,))
        rows = cursor.fetchall()
        return [
            {
                'id': row['id'],
                'gift_id': row['gift_id'],
                'from_user_id': row['from_user_id'],
                'from_username': row['from_username'],
                'name': row['name'],
                'emoji': row['emoji'],
                'description': row['description'],
                'price': row['price'] if row['price'] else 1,
                'rarity': row['rarity'] if row['rarity'] else 'common',
                'received_at': datetime.fromisoformat(row['received_at']).isoformat()
            }
            for row in rows
        ]

    def get_user_gifts_ids(self, user_id: int) -> List[int]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT gift_id FROM user_gifts WHERE user_id = ?",
            (user_id,)
        )
        rows = cursor.fetchall()
        return [row['gift_id'] for row in rows]

    # ==================== СФЕРЫ ====================

    def add_spheres(self, user_id: int, amount: int, reason: str) -> bool:
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET spheres = spheres + ? WHERE id = ?",
                (amount, user_id)
            )
            cursor.execute(
                "INSERT INTO sphere_transactions (user_id, amount, reason) VALUES (?, ?, ?)",
                (user_id, amount, reason)
            )
            self.conn.commit()
            return True
        except:
            return False

    def spend_spheres(self, user_id: int, amount: int, reason: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT spheres FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row['spheres'] >= amount:
            try:
                cursor.execute(
                    "UPDATE users SET spheres = spheres - ? WHERE id = ?",
                    (amount, user_id)
                )
                cursor.execute(
                    "INSERT INTO sphere_transactions (user_id, amount, reason) VALUES (?, ?, ?)",
                    (user_id, -amount, reason)
                )
                self.conn.commit()
                return True
            except:
                return False
        return False

    def get_user_spheres(self, user_id: int) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT spheres FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return row['spheres'] if row else 0

    def get_sphere_transactions(self, user_id: int, limit: int = 20) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM sphere_transactions 
            WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT ?
        ''', (user_id, limit))
        rows = cursor.fetchall()
        return [
            {
                'id': row['id'],
                'amount': row['amount'],
                'reason': row['reason'],
                'created_at': datetime.fromisoformat(row['created_at']).isoformat()
            }
            for row in rows
        ]

    # ==================== SPHERE BOT ====================

    def earn_spheres(self, user_id: int) -> int:
        rand = random.random()
        if rand < 0.40:
            amount = 1
        elif rand < 0.65:
            amount = 2
        elif rand < 0.80:
            amount = 3
        elif rand < 0.90:
            amount = 4
        elif rand < 0.95:
            amount = 5
        elif rand < 0.98:
            amount = random.randint(6, 7)
        else:
            amount = random.randint(8, 10)

        self.add_spheres(user_id, amount, 'earn')
        return amount

    def close(self):
        if self.conn:
            self.conn.close()