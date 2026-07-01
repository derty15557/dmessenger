# server.py
import asyncio
import json
import websockets
from datetime import datetime
from database import Database
from models import User, Message
from email_sender import EmailSender
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import os


# ============ HTTP СЕРВЕР ДЛЯ HEALTH CHECK ============
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Server is running!')

    def log_message(self, format, *args):
        pass


def run_http_server():
    port = int(os.environ.get("PORT", 8765))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"🟢 HTTP Health Check сервер запущен на порту {port}")
    server.serve_forever()


# ============ ОСНОВНОЙ ЧАТ-СЕРВЕР (WebSocket) ============
class ChatServer:
    def __init__(self):
        self.db = Database()
        self.email_sender = EmailSender()
        self.clients = {}
        self.username_to_id = {}

    async def register(self, websocket, username: str, email: str, password: str):
        if '@' not in email:
            await websocket.send(json.dumps({
                'type': 'register_fail',
                'error': 'Введите корректный email'
            }))
            return None

        existing_user = self.db.get_user_by_email(email)
        if existing_user:
            await websocket.send(json.dumps({
                'type': 'register_fail',
                'error': 'Этот email уже зарегистрирован'
            }))
            return None

        existing_user = self.db.get_user_by_username(username)
        if existing_user:
            await websocket.send(json.dumps({
                'type': 'register_fail',
                'error': 'Имя пользователя уже занято'
            }))
            return None

        user = self.db.create_user(username, email, password)
        if not user:
            await websocket.send(json.dumps({
                'type': 'register_fail',
                'error': 'Ошибка создания пользователя'
            }))
            return None

        code = self.email_sender.generate_code()
        self.db.save_verification_code(email, code)
        sent = await self.email_sender.send_verification_code(email, code)

        if sent:
            await websocket.send(json.dumps({
                'type': 'verification_required',
                'email': email,
                'message': 'Код подтверждения отправлен на вашу почту'
            }))
        else:
            await websocket.send(json.dumps({
                'type': 'register_fail',
                'error': 'Не удалось отправить код. Проверьте email.'
            }))
            return None

        return user

    async def verify_email(self, websocket, email: str, code: str):
        is_valid = self.db.verify_code(email, code)

        if is_valid:
            self.db.verify_user(email)
            user = self.db.get_user_by_email(email)

            if user:
                await websocket.send(json.dumps({
                    'type': 'verification_success',
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'message': 'Email успешно подтверждён!'
                }))
                return user

        await websocket.send(json.dumps({
            'type': 'verification_fail',
            'error': 'Неверный или просроченный код'
        }))
        return None

    async def login(self, websocket, username: str, password: str):
        user = self.db.get_user_by_username(username)

        if not user or user.password != password:
            await websocket.send(json.dumps({
                'type': 'login_fail',
                'error': 'Неверное имя пользователя или пароль'
            }))
            return None

        if not user.is_verified:
            await websocket.send(json.dumps({
                'type': 'login_fail',
                'error': 'Email не подтверждён. Проверьте почту.'
            }))
            return None

        self.clients[user.id] = websocket
        self.username_to_id[username] = user.id

        await websocket.send(json.dumps({
            'type': 'login_success',
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'avatar': user.avatar or '',
            'spheres': user.spheres,
            'language': user.language,
            'accent_color': user.accent_color,
            'background_image': user.background_image or ''
        }))

        all_messages = self.db.get_private_messages(user.id)
        messages_by_contact = {}

        for msg in all_messages:
            if msg.sender_id == user.id:
                contact_id = msg.receiver_id
            else:
                contact_id = msg.sender_id

            if contact_id not in messages_by_contact:
                messages_by_contact[contact_id] = []

            sender = self.db.get_user_by_id(msg.sender_id)

            gift_info = None
            if msg.is_gift and msg.gift_id > 0:
                gift_info = self.db.get_gift_by_id(msg.gift_id)

            messages_by_contact[contact_id].append({
                'id': msg.id,
                'sender': sender.username if sender else 'unknown',
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat(),
                'is_read': msg.is_read,
                'is_gift': msg.is_gift,
                'gift': gift_info
            })

        for contact_id, messages in messages_by_contact.items():
            contact = self.db.get_user_by_id(contact_id)
            if contact:
                await websocket.send(json.dumps({
                    'type': 'contact_history',
                    'contact_id': contact_id,
                    'contact_name': contact.username,
                    'messages': messages
                }))

        await self.broadcast_user_list()
        return user

    async def check_username(self, websocket, username: str):
        if not username or len(username) < 2:
            await websocket.send(json.dumps({
                'type': 'username_check',
                'username': username,
                'available': False,
                'reason': 'Минимум 2 символа'
            }))
            return

        user = self.db.get_user_by_username(username)
        if user:
            await websocket.send(json.dumps({
                'type': 'username_check',
                'username': username,
                'available': False,
                'reason': 'Имя уже занято'
            }))
        else:
            await websocket.send(json.dumps({
                'type': 'username_check',
                'username': username,
                'available': True,
                'reason': 'Доступно'
            }))

    async def update_avatar(self, websocket, data):
        user_id = data.get('user_id')
        avatar = data.get('avatar')

        self.db.update_user_avatar(user_id, avatar)

        await websocket.send(json.dumps({
            'type': 'avatar_update_success'
        }))

        await self.broadcast_user_list()

    async def update_settings(self, websocket, data):
        user_id = data.get('user_id')
        language = data.get('language', 'ru')
        accent_color = data.get('accent_color', 'BLUE')
        background_image = data.get('background_image', '')

        self.db.update_user_settings(user_id, language, accent_color, background_image)

        await websocket.send(json.dumps({
            'type': 'settings_update_success',
            'language': language,
            'accent_color': accent_color,
            'background_image': background_image
        }))

        await self.broadcast_user_list()

    async def send_gift(self, websocket, data):
        from_user_id = data.get('user_id')
        to_user_id = data.get('receiver_id')
        gift_id = data.get('gift_id')
        gift_gif = data.get('gift_gif')

        print(f"🎁 Отправка подарка: от {from_user_id} к {to_user_id}, подарок {gift_id}")

        receiver = self.db.get_user_by_id(to_user_id)
        if not receiver:
            await websocket.send(json.dumps({
                'type': 'gift_error',
                'error': 'Пользователь не найден'
            }))
            return

        gift = self.db.get_gift_by_id(gift_id)
        if not gift:
            await websocket.send(json.dumps({
                'type': 'gift_error',
                'error': 'Подарок не найден'
            }))
            return

        price = gift.get('price', 1)
        rarity = gift.get('rarity', 'common')

        if not self.db.spend_spheres(from_user_id, price, f'send_gift_{gift_id}'):
            await websocket.send(json.dumps({
                'type': 'gift_error',
                'error': f'Недостаточно сфер! Нужно {price} сфер'
            }))
            return

        self.db.add_user_gift(to_user_id, gift_id, from_user_id)
        sender = self.db.get_user_by_id(from_user_id)

        rarity_emojis = {
            'common': '🟢',
            'uncommon': '🟡',
            'rare': '🔵',
            'epic': '🟣',
            'legendary': '🔴'
        }
        rarity_emoji = rarity_emojis.get(rarity, '🟢')

        gift_message = f"{rarity_emoji} {gift['emoji']} {gift['name']} от {sender.username} [{rarity.upper()}]"
        self.db.save_message(from_user_id, gift_message, to_user_id, is_gift=True, gift_id=gift_id)

        if to_user_id in self.clients:
            await self.clients[to_user_id].send(json.dumps({
                'type': 'gift_received',
                'from_user': sender.username,
                'gift': gift,
                'gift_gif': gift_gif,
                'message': f"{rarity_emoji} Вы получили {gift['emoji']} {gift['name']} [{rarity.upper()}] от {sender.username}!"
            }))

        await websocket.send(json.dumps({
            'type': 'gift_sent',
            'gift': gift,
            'gift_gif': gift_gif,
            'to_user': receiver.username,
            'message': f"{rarity_emoji} Вы отправили {gift['emoji']} {gift['name']} [{rarity.upper()}] пользователю {receiver.username}! (-{price} сфер)"
        }))

        new_spheres = self.db.get_user_spheres(from_user_id)
        if from_user_id in self.clients:
            await self.clients[from_user_id].send(json.dumps({
                'type': 'spheres_update',
                'spheres': new_spheres
            }))

        await self.broadcast_user_list()

    async def get_gifts(self, websocket, data):
        gifts = self.db.get_all_gifts()
        await websocket.send(json.dumps({
            'type': 'gifts_list',
            'gifts': gifts
        }))

    async def get_user_gifts(self, websocket, data):
        user_id = data.get('user_id')
        user_gifts = self.db.get_user_gifts(user_id)
        await websocket.send(json.dumps({
            'type': 'user_gifts',
            'gifts': user_gifts
        }))

    async def earn_spheres(self, websocket, data):
        user_id = data.get('user_id')
        amount = self.db.earn_spheres(user_id)
        new_spheres = self.db.get_user_spheres(user_id)

        await websocket.send(json.dumps({
            'type': 'spheres_earned',
            'amount': amount,
            'spheres': new_spheres,
            'message': f'✨ Вы заработали {amount} сфер!'
        }))

        await self.broadcast_user_list()

    async def get_spheres(self, websocket, data):
        user_id = data.get('user_id')
        spheres = self.db.get_user_spheres(user_id)
        transactions = self.db.get_sphere_transactions(user_id, 20)

        await websocket.send(json.dumps({
            'type': 'spheres_info',
            'spheres': spheres,
            'transactions': transactions
        }))

    async def handle_message(self, websocket, data: dict):
        user_id = data.get('user_id')
        content = data.get('content')
        receiver_id = data.get('receiver_id')

        if not receiver_id:
            await websocket.send(json.dumps({
                'type': 'error',
                'error': 'Не указан получатель'
            }))
            return

        msg = self.db.save_message(user_id, content, receiver_id)
        sender = self.db.get_user_by_id(user_id)

        response = {
            'type': 'new_message',
            'message': {
                'id': msg.id,
                'sender': sender.username if sender else 'unknown',
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat(),
                'is_read': msg.is_read,
                'is_gift': msg.is_gift,
                'gift': None
            }
        }

        if receiver_id in self.clients:
            await self.clients[receiver_id].send(json.dumps(response))

        if user_id in self.clients:
            await self.clients[user_id].send(json.dumps(response))

    async def broadcast(self, message: str):
        for client in self.clients.values():
            try:
                await client.send(message)
            except:
                pass

    async def broadcast_user_list(self):
        users = self.db.get_all_users()
        user_list = [
            {
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'avatar': u.avatar or '',
                'online': u.id in self.clients,
                'verified': u.is_verified,
                'gifts_count': len(u.gifts) if u.gifts else 0
            }
            for u in users
        ]
        await self.broadcast(json.dumps({
            'type': 'user_list',
            'users': user_list
        }))

    # 👇 ИЗМЕНЕНО: ДОБАВЛЕН ПАРАМЕТР path
    async def handle_connection(self, websocket, path=None):
        print(f"🟢 Новое подключение: {websocket.remote_address}")

        # Разрешаем подключение по любому пути
        if path:
            print(f"📂 Путь подключения: {path}")

        await websocket.send(json.dumps({
            'type': 'welcome',
            'message': 'Подключено к серверу DMessenger!'
        }))

        try:
            async for message in websocket:
                print(f"📨 Получено: {message}")
                try:
                    data = json.loads(message)
                    action = data.get('action')

                    if action == 'register':
                        await self.register(websocket, data['username'], data['email'], data['password'])
                    elif action == 'verify':
                        await self.verify_email(websocket, data['email'], data['code'])
                    elif action == 'login':
                        await self.login(websocket, data['username'], data['password'])
                    elif action == 'check_username':
                        await self.check_username(websocket, data.get('username', ''))
                    elif action == 'message':
                        await self.handle_message(websocket, data)
                    elif action == 'update_avatar':
                        await self.update_avatar(websocket, data)
                    elif action == 'update_settings':
                        await self.update_settings(websocket, data)
                    elif action == 'send_gift':
                        await self.send_gift(websocket, data)
                    elif action == 'get_gifts':
                        await self.get_gifts(websocket, data)
                    elif action == 'get_user_gifts':
                        await self.get_user_gifts(websocket, data)
                    elif action == 'earn_spheres':
                        await self.earn_spheres(websocket, data)
                    elif action == 'get_spheres':
                        await self.get_spheres(websocket, data)
                    elif action == 'resend_code':
                        email = data.get('email')
                        if email:
                            code = self.email_sender.generate_code()
                            self.db.save_verification_code(email, code)
                            sent = await self.email_sender.send_verification_code(email, code)
                            if sent:
                                await websocket.send(json.dumps({
                                    'type': 'verification_required',
                                    'email': email,
                                    'message': 'Код отправлен повторно'
                                }))
                            else:
                                await websocket.send(json.dumps({
                                    'type': 'error',
                                    'error': 'Не удалось отправить код'
                                }))
                    else:
                        await websocket.send(json.dumps({
                            'type': 'error',
                            'error': f'Неизвестное действие: {action}'
                        }))
                except json.JSONDecodeError as e:
                    print(f"❌ Ошибка JSON: {e}")
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'error': 'Неверный формат сообщения'
                    }))
                except Exception as e:
                    print(f"❌ Ошибка обработки: {e}")
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'error': str(e)
                    }))

        except websockets.exceptions.ConnectionClosed:
            print(f"🔴 Соединение разорвано: {websocket.remote_address}")
        finally:
            for user_id, ws in list(self.clients.items()):
                if ws == websocket:
                    del self.clients[user_id]
                    for username, uid in list(self.username_to_id.items()):
                        if uid == user_id:
                            del self.username_to_id[username]
                            break
                    break
            await self.broadcast_user_list()


# ============ ЗАПУСК ============
async def main():
    # Запускаем HTTP сервер для Health Check в отдельном потоке
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    # Запускаем WebSocket сервер
    server = ChatServer()
    try:
        async with websockets.serve(server.handle_connection, "0.0.0.0", 8766):
            print("🟢 WebSocket сервер запущен на ws://0.0.0.0:8766")
            print("📱 Ожидание подключений...")
            await asyncio.Future()
    except OSError as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(main())