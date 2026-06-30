# models.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class User:
    id: int
    username: str
    email: str
    password: str
    created_at: datetime
    is_verified: bool = False
    avatar: str = ''
    spheres: int = 0
    language: str = 'ru'
    accent_color: str = 'BLUE'
    background_image: str = ''
    gifts: List[int] = None

@dataclass
class Message:
    id: int
    sender_id: int
    receiver_id: int
    content: str
    timestamp: datetime
    is_read: bool = False
    is_gift: bool = False
    gift_id: int = 0

@dataclass
class Gift:
    id: int
    name: str
    emoji: str
    description: str
    price: int
    rarity: str  # 'common', 'uncommon', 'rare', 'epic', 'legendary'

@dataclass
class UserGift:
    id: int
    user_id: int
    gift_id: int
    from_user_id: int
    received_at: datetime

@dataclass
class SphereTransaction:
    id: int
    user_id: int
    amount: int
    reason: str
    created_at: datetime

@dataclass
class VerificationCode:
    email: str
    code: str
    created_at: datetime