# main.py
import flet as ft
import asyncio
import json
import websockets
from datetime import datetime
import os
import base64


class MessengerApp:
    def __init__(self):
        self.ws = None
        self.current_user = None
        self.current_user_id = None
        self.current_user_email = None
        self.current_user_avatar = None
        self.current_user_spheres = 0
        self.current_user_language = 'ru'
        self.current_user_accent = 'BLUE'
        self.current_user_bg = ''
        self.messages = {}
        self.users = []
        self.active_chat = None
        self.username_check_task = None
        self.pending_email = None
        self.remember_me = False
        self.profile_overlay = None
        self.gifts_overlay = None
        self.settings_overlay = None
        self.pending_username_check = None
        self.auto_login_in_progress = False
        self.gifts_data = []
        self.user_gifts = []
        self.db = None
        self.earn_btn = None
        self.is_bot_chat = False

    def main(self, page: ft.Page):
        self.page = page
        page.title = "DMessenger"
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.theme_mode = ft.ThemeMode.DARK
        page.padding = 20

        # --- Поля ввода ---
        self.username_field = ft.TextField(
            label="Имя пользователя",
            width=300,
            border_color=ft.Colors.BLUE,
            on_change=self.on_username_change,
        )

        self.username_status = ft.Row([
            ft.Icon(icon=ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, visible=False, size=20),
            ft.Icon(icon=ft.Icons.ERROR, color=ft.Colors.RED, visible=False, size=20),
            ft.Text("", size=12, color=ft.Colors.GREY_400, visible=False)
        ], spacing=5, visible=False)

        self.email_field = ft.TextField(
            label="Email (для регистрации)",
            width=300,
            border_color=ft.Colors.BLUE,
            hint_text="example@gmail.com"
        )
        self.password_field = ft.TextField(
            label="Пароль",
            password=True,
            can_reveal_password=True,
            width=300,
            border_color=ft.Colors.BLUE
        )

        self.verification_field = ft.TextField(
            label="Код подтверждения",
            width=300,
            border_color=ft.Colors.BLUE,
            hint_text="Введите код из письма",
            visible=False
        )

        self.remember_checkbox = ft.Checkbox(
            label="Запомнить меня",
            value=False,
            fill_color=ft.Colors.BLUE,
            check_color=ft.Colors.WHITE,
            on_change=self.on_remember_change
        )

        self.status_text = ft.Text("", color=ft.Colors.GREY_400)

        # --- Кнопки ---
        login_btn = ft.FilledButton(
            "Войти",
            icon=ft.Icons.LOGIN,
            on_click=self.login,
            width=140
        )
        register_btn = ft.OutlinedButton(
            "Зарегистрироваться",
            icon=ft.Icons.PERSON_ADD,
            on_click=self.register,
            width=180
        )

        self.verify_btn = ft.FilledButton(
            "Подтвердить",
            icon=ft.Icons.VERIFIED,
            on_click=self.verify_email,
            width=140,
            visible=False
        )

        self.resend_btn = ft.OutlinedButton(
            "Отправить код повторно",
            on_click=self.resend_code,
            width=180,
            visible=False
        )

        # --- Экран авторизации ---
        self.auth_view = ft.Container(
            content=ft.Column([
                ft.Text("📱 DMessenger", size=32, weight=ft.FontWeight.BOLD),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                ft.Row([
                    ft.Text("@", size=16, color=ft.Colors.GREY_400, width=20),
                    self.username_field
                ], spacing=0, alignment=ft.MainAxisAlignment.CENTER),
                self.username_status,
                self.email_field,
                self.password_field,
                self.verification_field,
                self.remember_checkbox,
                ft.Row([self.verify_btn, self.resend_btn], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([login_btn, register_btn], alignment=ft.MainAxisAlignment.CENTER),
                self.status_text
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=400,
            padding=30,
            bgcolor=ft.Colors.GREY_900,
            border_radius=20,
        )

        # --- Чат ---
        self.contact_list = ft.ListView(expand=True, spacing=5, padding=10)
        self.message_list = ft.ListView(expand=True, spacing=10, padding=10, auto_scroll=True)

        self.empty_chat_text = ft.Text(
            "💬 Выберите контакт, чтобы начать общение",
            size=16,
            color=ft.Colors.GREY_400,
            visible=True
        )

        self.message_field = ft.TextField(
            hint_text="Введите сообщение...",
            expand=True,
            border_radius=30,
            filled=True,
            bgcolor=ft.Colors.GREY_800,
            on_submit=self.send_message,
            disabled=True
        )

        self.send_btn = ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED,
            icon_size=30,
            icon_color=ft.Colors.BLUE,
            on_click=self.send_message,
            disabled=True
        )

        self.gift_btn = ft.IconButton(
            icon=ft.Icons.CARD_GIFTCARD,
            icon_size=30,
            icon_color=ft.Colors.PINK,
            on_click=self.show_gifts_panel,
            tooltip="Отправить подарок",
            disabled=True
        )

        self.settings_btn = ft.IconButton(
            icon=ft.Icons.SETTINGS,
            icon_size=24,
            icon_color=ft.Colors.GREY_400,
            on_click=self.show_settings_panel,
            tooltip="Настройки"
        )

        self.chat_title = ft.Text("Выберите контакт", size=20, weight=ft.FontWeight.BOLD)

        self.profile_btn = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Stack([
                        ft.CircleAvatar(
                            content=ft.Text(
                                self.current_user[0].upper() if self.current_user else "?",
                                size=16,
                                weight=ft.FontWeight.BOLD
                            ),
                            bgcolor=ft.Colors.BLUE_700,
                            radius=18,
                        ),
                        ft.Container(
                            width=10,
                            height=10,
                            bgcolor=ft.Colors.GREY_500,
                            border=ft.Border.all(width=2, color=ft.Colors.BLACK),
                            border_radius=5,
                            left=24,
                            top=24,
                        ),
                    ]),
                ),
                ft.Text(
                    self.current_user if self.current_user else "Профиль",
                    size=14,
                    weight=ft.FontWeight.W_500,
                    color=ft.Colors.WHITE
                ),
                ft.Icon(
                    ft.Icons.KEYBOARD_ARROW_DOWN,
                    size=16,
                    color=ft.Colors.GREY_400
                )
            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
            on_click=self.show_profile,
            padding=8,
            border_radius=20,
            ink=True,
        )

        logout_btn = ft.IconButton(
            icon=ft.Icons.LOGOUT,
            on_click=self.logout,
            tooltip="Выйти"
        )

        self.chat_header = ft.Container(
            content=ft.Row([
                ft.Row([self.profile_btn, self.settings_btn], spacing=5),
                logout_btn
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=10,
            bgcolor=ft.Colors.GREY_900,
            border_radius=ft.BorderRadius(top_left=10, top_right=10, bottom_left=0, bottom_right=0)
        )

        self.chat_footer = ft.Container(
            content=ft.Row([self.message_field, self.gift_btn, self.send_btn]),
            padding=10,
            bgcolor=ft.Colors.GREY_900,
            border_radius=ft.BorderRadius(top_left=0, top_right=0, bottom_left=10, bottom_right=10)
        )

        self.message_container = ft.Container(
            content=ft.Stack([
                self.message_list,
                ft.Container(content=self.empty_chat_text, alignment=ft.Alignment(0, 0), expand=True)
            ]),
            expand=True,
            bgcolor=ft.Colors.BLACK,
        )

        chat_column = ft.Column([self.chat_header, self.message_container, self.chat_footer], expand=True, spacing=0)

        left_panel = ft.Container(
            content=ft.Column([
                ft.Text("👥 Контакты", weight=ft.FontWeight.BOLD),
                self.contact_list
            ]),
            width=250,
            padding=10,
            bgcolor=ft.Colors.GREY_900,
            border_radius=10
        )

        self.chat_view = ft.Container(
            content=ft.Row([
                left_panel,
                ft.Container(content=chat_column, expand=True, bgcolor=ft.Colors.GREY_900, border_radius=10)
            ], expand=True, spacing=10),
            expand=True,
            visible=False
        )

        # --- Оверлеи ---
        self.profile_overlay = ft.Container(
            content=ft.Container(
                content=self.create_profile_content(),
                alignment=ft.Alignment(0, 0),
                expand=True,
            ),
            expand=True,
            visible=False,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
        )

        self.gifts_overlay = ft.Container(
            content=ft.Container(
                content=self.create_gifts_content(),
                alignment=ft.Alignment(0, 0),
                expand=True,
            ),
            expand=True,
            visible=False,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
        )

        self.settings_overlay = ft.Container(
            content=ft.Container(
                content=self.create_settings_content(),
                alignment=ft.Alignment(0, 0),
                expand=True,
            ),
            expand=True,
            visible=False,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
        )

        page.add(
            ft.Stack([
                ft.Container(
                    content=ft.Stack([
                        ft.Container(
                            content=self.auth_view,
                            alignment=ft.Alignment(0, 0),
                            expand=True
                        ),
                        self.chat_view
                    ]),
                    expand=True,
                    animate=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
                ),
                self.profile_overlay,
                self.gifts_overlay,
                self.settings_overlay
            ], expand=True)
        )

        self.load_saved_credentials()
        asyncio.create_task(self.connect_to_server())
        page.update()

    # ==================== АВТОМАТИЧЕСКИЙ ВХОД ====================

    async def try_auto_login(self):
        if self.auto_login_in_progress:
            return
        if not self.remember_me:
            return
        username = self.username_field.value
        password = self.password_field.value
        if not username or not password:
            return
        print(f"🔄 Попытка автоматического входа для {username}")
        self.auto_login_in_progress = True
        self.status_text.value = "⏳ Автоматический вход..."
        self.page.update()
        await self.send_auth('login', username, password)

    # ==================== НАСТРОЙКИ ====================

    def create_settings_content(self):
        if not self.current_user:
            return ft.Container()

        def close_settings(e):
            self.close_settings()

        def save_settings(e):
            language = lang_dropdown.value
            accent_color = color_dropdown.value
            background = bg_field.value
            asyncio.create_task(self.update_settings(language, accent_color, background))
            self.close_settings()

        lang_dropdown = ft.Dropdown(
            label="Язык",
            value=self.current_user_language if hasattr(self, 'current_user_language') else 'ru',
            options=[
                ft.dropdown.Option("ru", "🇷🇺 Русский"),
                ft.dropdown.Option("en", "🇬🇧 English"),
                ft.dropdown.Option("uz", "🇺🇿 O'zbekcha"),
            ],
            width=200,
        )

        color_dropdown = ft.Dropdown(
            label="Акцентный цвет",
            value=self.current_user_accent if hasattr(self, 'current_user_accent') else 'BLUE',
            options=[
                ft.dropdown.Option("BLUE", "🔵 Синий"),
                ft.dropdown.Option("RED", "🔴 Красный"),
                ft.dropdown.Option("GREEN", "🟢 Зелёный"),
                ft.dropdown.Option("PINK", "🩷 Розовый"),
                ft.dropdown.Option("PURPLE", "🟣 Фиолетовый"),
                ft.dropdown.Option("ORANGE", "🟠 Оранжевый"),
            ],
            width=200,
        )

        bg_field = ft.TextField(
            label="URL фона",
            hint_text="https://example.com/bg.jpg",
            value=self.current_user_bg if hasattr(self, 'current_user_bg') else '',
            width=200,
        )

        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.SETTINGS, color=ft.Colors.BLUE_400, size=28),
                        ft.Text("Настройки", size=22, weight=ft.FontWeight.BOLD),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            on_click=close_settings,
                            icon_color=ft.Colors.GREY_400,
                            tooltip="Закрыть"
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.Padding(left=16, right=8, top=12, bottom=8),
                    border_radius=ft.BorderRadius(top_left=12, top_right=12, bottom_left=0, bottom_right=0),
                    bgcolor=ft.Colors.GREY_800,
                ),
                ft.Container(
                    content=ft.Column([
                        lang_dropdown,
                        color_dropdown,
                        bg_field,
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        ft.Row([
                            ft.FilledButton(
                                "Сохранить",
                                icon=ft.Icons.SAVE,
                                on_click=save_settings,
                                width=120
                            ),
                            ft.OutlinedButton(
                                "Отмена",
                                on_click=close_settings,
                                width=100
                            ),
                        ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                    ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=20,
                    expand=True,
                ),
            ], spacing=0),
            width=400,
            height=400,
            bgcolor=ft.Colors.GREY_900,
            border_radius=16,
            shadow=ft.BoxShadow(
                spread_radius=4,
                blur_radius=20,
                color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK)
            ),
            alignment=ft.Alignment(0, 0),
        )

    def show_settings_panel(self, e):
        if not self.current_user:
            return
        self.settings_overlay.content = ft.Container(
            content=self.create_settings_content(),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )
        self.settings_overlay.visible = True
        self.settings_overlay.opacity = 1
        self.page.update()

    def close_settings(self):
        self.settings_overlay.visible = False
        self.settings_overlay.opacity = 0
        self.page.update()

    async def update_settings(self, language, accent_color, background_image):
        try:
            await self.ws.send(json.dumps({
                'action': 'update_settings',
                'user_id': self.current_user_id,
                'language': language,
                'accent_color': accent_color,
                'background_image': background_image
            }))
        except Exception as e:
            print(f"Ошибка: {e}")

    # ==================== ПРОФИЛЬ ====================

    def create_profile_content(self):
        if not self.current_user:
            return ft.Container()

        user_info = None
        for user in self.users:
            if user['id'] == self.current_user_id:
                user_info = user
                break

        if not user_info:
            user_info = {
                'username': self.current_user,
                'email': self.current_user_email if self.current_user_email else 'не указан',
                'online': True,
                'verified': True,
                'avatar': self.current_user_avatar if hasattr(self, 'current_user_avatar') else None,
                'spheres': self.current_user_spheres,
            }

        verified_text = "✅ Подтверждён" if user_info.get('verified', False) else "❌ Не подтверждён"
        verified_color = ft.Colors.GREEN if user_info.get('verified', False) else ft.Colors.RED

        def close_profile(e):
            self.close_profile()

        self.avatar_path_field = ft.TextField(
            label="Путь к аватарке",
            width=280,
            border_color=ft.Colors.BLUE,
            hint_text="C:/Users/.../photo.jpg",
            on_change=self.on_avatar_path_change
        )

        self.avatar_status = ft.Text("", size=11, visible=False)

        self.edit_username = ft.TextField(
            label="@ Имя пользователя",
            value=self.current_user,
            width=280,
            border_color=ft.Colors.BLUE,
            on_change=lambda e: asyncio.create_task(self.check_username_edit(e.data))
        )

        self.username_edit_status = ft.Text("", size=11, visible=False)

        def save_profile(e):
            asyncio.create_task(self.save_profile_changes())

        avatar_image = user_info.get('avatar') or self.current_user_avatar
        spheres = user_info.get('spheres', 0)

        user_gifts = self.user_gifts if hasattr(self, 'user_gifts') else []

        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.PERSON, color=ft.Colors.BLUE_400, size=28),
                        ft.Text("Мой профиль", size=22, weight=ft.FontWeight.BOLD),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            on_click=close_profile,
                            icon_color=ft.Colors.GREY_400,
                            tooltip="Закрыть"
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.Padding(left=16, right=8, top=12, bottom=8),
                    border_radius=ft.BorderRadius(top_left=12, top_right=12, bottom_left=0, bottom_right=0),
                    bgcolor=ft.Colors.GREY_800,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Container(
                            content=ft.Stack([
                                ft.CircleAvatar(
                                    content=ft.Text(
                                        self.current_user[0].upper(),
                                        size=36,
                                        weight=ft.FontWeight.BOLD
                                    ) if not avatar_image else None,
                                    bgcolor=ft.Colors.BLUE_700,
                                    radius=55,
                                    foreground_image_src=avatar_image,
                                ),
                                ft.Container(
                                    width=14,
                                    height=14,
                                    bgcolor=ft.Colors.GREEN,
                                    border=ft.Border.all(width=2, color=ft.Colors.BLACK),
                                    border_radius=7,
                                    left=76,
                                    top=76,
                                ),
                            ]),
                            alignment=ft.Alignment(0, 0),
                            padding=10,
                        ),
                        ft.Text(f"⭐ {spheres} сфер", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER),
                        ft.Container(
                            content=ft.Column([
                                self.avatar_path_field,
                                self.avatar_status,
                            ], spacing=2),
                            width=280,
                        ),
                        ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Text("@", size=14, color=ft.Colors.GREY_400, width=20),
                                    self.edit_username
                                ], spacing=0, alignment=ft.MainAxisAlignment.CENTER),
                                self.username_edit_status,
                            ], spacing=2),
                            width=280,
                        ),
                        ft.Divider(height=8, color=ft.Colors.TRANSPARENT),
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.Icons.EMAIL, color=ft.Colors.BLUE_400, size=16),
                                    ft.Text(f"Email: {user_info.get('email', 'не указан')}", size=12,
                                            color=ft.Colors.GREY_400)
                                ], spacing=8),
                                ft.Row([
                                    ft.Icon(ft.Icons.VERIFIED, color=verified_color, size=16),
                                    ft.Text(f"Статус: {verified_text}", size=12, color=verified_color)
                                ], spacing=8),
                                ft.Row([
                                    ft.Icon(ft.Icons.WIFI,
                                            color=ft.Colors.GREEN if user_info.get('online', False) else ft.Colors.RED,
                                            size=16),
                                    ft.Text(f"Онлайн: {'🟢 Да' if user_info.get('online', False) else '🔴 Нет'}", size=12)
                                ], spacing=8),
                            ], spacing=5),
                            padding=10,
                            bgcolor=ft.Colors.GREY_900,
                            border_radius=8,
                        ),
                        ft.Divider(height=5, color=ft.Colors.GREY_800),
                        ft.Text("🎁 Полученные подарки:", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_300),
                        ft.Container(
                            content=ft.GridView(
                                expand=True,
                                runs_count=4,
                                max_extent=70,
                                child_aspect_ratio=1.0,
                                spacing=5,
                                run_spacing=5,
                                controls=[
                                    ft.Container(
                                        content=ft.Column([
                                            ft.Text(gift['emoji'], size=28, text_align=ft.TextAlign.CENTER),
                                            ft.Text(gift['name'], size=10, text_align=ft.TextAlign.CENTER,
                                                    color=ft.Colors.GREY_400),
                                            ft.Text(f"от {gift['from_username']}", size=8,
                                                    text_align=ft.TextAlign.CENTER, color=ft.Colors.GREY_500),
                                        ], spacing=1, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                        padding=5,
                                        bgcolor=ft.Colors.GREY_800,
                                        border_radius=8,
                                    )
                                    for gift in user_gifts[:12]
                                ] if user_gifts else [ft.Text("Нет подарков", size=12, color=ft.Colors.GREY_400)]
                            ),
                            height=150 if user_gifts else 40,
                        ),
                        ft.Row([
                            ft.FilledButton(
                                "Сохранить",
                                icon=ft.Icons.SAVE,
                                on_click=save_profile,
                                width=120
                            ),
                            ft.OutlinedButton(
                                "Отмена",
                                on_click=close_profile,
                                width=100
                            ),
                        ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                    ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=20,
                    expand=True,
                ),
            ], spacing=0),
            width=450,
            height=680,
            bgcolor=ft.Colors.GREY_900,
            border_radius=16,
            shadow=ft.BoxShadow(
                spread_radius=4,
                blur_radius=20,
                color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK)
            ),
            alignment=ft.Alignment(0, 0),
        )

    def on_avatar_path_change(self, e):
        path = self.avatar_path_field.value
        if not path:
            self.avatar_status.visible = False
            self.page.update()
            return
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    image_data = f.read()
                    base64_avatar = base64.b64encode(image_data).decode('utf-8')
                    self.current_user_avatar = base64_avatar
                    self.avatar_status.value = "✅ Файл найден"
                    self.avatar_status.color = ft.Colors.GREEN
                    self.avatar_status.visible = True
                    self.update_profile_avatar()
                    self.page.update()
            except Exception as e:
                self.avatar_status.value = f"❌ Ошибка: {str(e)}"
                self.avatar_status.color = ft.Colors.RED
                self.avatar_status.visible = True
                self.page.update()
        else:
            self.avatar_status.value = "❌ Файл не найден"
            self.avatar_status.color = ft.Colors.RED
            self.avatar_status.visible = True
            self.page.update()

    def update_profile_avatar(self):
        if self.profile_overlay.visible and self.current_user_avatar:
            self.profile_overlay.content = ft.Container(
                content=self.create_profile_content(),
                alignment=ft.Alignment(0, 0),
                expand=True,
            )
            self.page.update()
        self.update_profile_button()

    async def check_username_edit(self, username):
        if not username or len(username) < 2:
            self.username_edit_status.value = "❌ Минимум 2 символа"
            self.username_edit_status.color = ft.Colors.RED
            self.username_edit_status.visible = True
            self.page.update()
            return
        if username == self.current_user:
            self.username_edit_status.visible = False
            self.page.update()
            return
        try:
            await self.ws.send(json.dumps({
                'action': 'check_username',
                'username': username
            }))
            self.pending_username_check = username
        except Exception as e:
            print(f"Ошибка проверки: {e}")

    async def save_profile_changes(self):
        new_avatar = self.current_user_avatar if self.current_user_avatar else ''
        try:
            await self.ws.send(json.dumps({
                'action': 'update_avatar',
                'user_id': self.current_user_id,
                'avatar': new_avatar
            }))
            self.status_text.value = "⏳ Сохранение..."
            self.page.update()
        except Exception as e:
            print(f"Ошибка сохранения: {e}")

    def show_profile(self, e):
        if not self.current_user:
            return
        self.profile_overlay.content = ft.Container(
            content=self.create_profile_content(),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )
        self.profile_overlay.visible = True
        self.profile_overlay.opacity = 1
        self.page.update()

    def close_profile(self):
        self.profile_overlay.visible = False
        self.profile_overlay.opacity = 0
        self.page.update()

    # ==================== ПОДАРКИ ====================

    def create_gifts_content(self):
        if not self.current_user:
            return ft.Container()

        def close_gifts(e):
            self.close_gifts()

        gifts = [
            {"id": 1, "name": "Роза", "emoji": "🌹", "price": 10, "rarity": "common", "gif": "assets/rosses.gif"},
            {"id": 2, "name": "Сердце", "emoji": "❤️", "price": 10, "rarity": "common", "gif": "assets/heart.gif"},
            {"id": 3, "name": "Звезда", "emoji": "⭐", "price": 10, "rarity": "uncommon", "gif": "assets/stars.gif"},
            {"id": 4, "name": "Торт", "emoji": "🎂", "price": 10, "rarity": "uncommon", "gif": None},
            {"id": 5, "name": "Пицца", "emoji": "🍕", "price": 10, "rarity": "common", "gif": "assets/pizza.gif"},
            {"id": 6, "name": "Цветы", "emoji": "💐", "price": 10, "rarity": "uncommon", "gif": None},
            {"id": 7, "name": "Шоколад", "emoji": "🍫", "price": 10, "rarity": "common", "gif": "assets/chocolate.gif"},
            {"id": 8, "name": "Котик", "emoji": "🐱", "price": 10, "rarity": "rare", "gif": None},
            {"id": 9, "name": "Пёсик", "emoji": "🐶", "price": 10, "rarity": "rare", "gif": None},
            {"id": 10, "name": "Ракета", "emoji": "🚀", "price": 10, "rarity": "rare", "gif": None},
            {"id": 11, "name": "Алмаз", "emoji": "💎", "price": 10, "rarity": "epic", "gif": None},
            {"id": 12, "name": "Пиво", "emoji": "🍺", "price": 20, "rarity": "common", "gif": "assets/beer.gif"},
            {"id": 13, "name": "Мороженое", "emoji": "🍦", "price": 20, "rarity": "common", "gif": "assets/ice.gif"},
            {"id": 14, "name": "Смайлик", "emoji": "😊", "price": 20, "rarity": "common", "gif": "assets/smile.gif"},
            {"id": 15, "name": "Кекс", "emoji": "🧁", "price": 20, "rarity": "common", "gif": "assets/cupcake.gif"},
            {"id": 16, "name": "Подарок", "emoji": "🎁", "price": 20, "rarity": "uncommon", "gif": None},
            {"id": 17, "name": "Солнце", "emoji": "☀️", "price": 35, "rarity": "uncommon", "gif": None},
            {"id": 18, "name": "Луна", "emoji": "🌙", "price": 35, "rarity": "uncommon", "gif": None},
            {"id": 19, "name": "Дракон", "emoji": "🐉", "price": 75, "rarity": "epic", "gif": None},
            {"id": 20, "name": "Единорог", "emoji": "🦄", "price": 75, "rarity": "epic", "gif": None},
            {"id": 21, "name": "Корона", "emoji": "👑", "price": 100, "rarity": "legendary", "gif": None},
            {"id": 22, "name": "Феникс", "emoji": "🔥", "price": 100, "rarity": "legendary", "gif": None},
            {"id": 23, "name": "Пегас", "emoji": "🐴", "price": 100, "rarity": "legendary", "gif": None},
            {"id": 24, "name": "Космос", "emoji": "🌌", "price": 100, "rarity": "legendary", "gif": None},
        ]

        gifts_by_rarity = {'common': [], 'uncommon': [], 'rare': [], 'epic': [], 'legendary': []}
        for gift in gifts:
            rarity = gift.get('rarity', 'common')
            if rarity in gifts_by_rarity:
                gifts_by_rarity[rarity].append(gift)

        rarity_names = {
            'common': '🟢 Обычные (10 сфер)',
            'uncommon': '🟡 Необычные (20 сфер)',
            'rare': '🔵 Редкие (35 сфер)',
            'epic': '🟣 Эпические (75 сфер)',
            'legendary': '🔴 Легендарные (100 сфер)'
        }

        rarity_colors = {
            'common': ft.Colors.GREEN_400,
            'uncommon': ft.Colors.AMBER,
            'rare': ft.Colors.BLUE_400,
            'epic': ft.Colors.PURPLE_400,
            'legendary': ft.Colors.RED_400
        }

        def send_gift(gift_id, gift_name, gift_emoji, gift_price, gift_rarity, gift_gif):
            def on_send(e):
                if not self.active_chat or self.active_chat == -1:
                    self.status_text.value = "❌ Сначала выберите контакт"
                    self.page.update()
                    return
                if self.current_user_spheres < gift_price:
                    self.status_text.value = f"❌ Недостаточно сфер! Нужно {gift_price} сфер"
                    self.status_text.color = ft.Colors.RED
                    self.page.update()
                    return
                asyncio.create_task(self.send_gift_to_server(gift_id, gift_gif))
                self.close_gifts()
                self.status_text.value = f"🎁 Отправка подарка..."
                self.status_text.color = ft.Colors.BLUE
                self.page.update()

            return on_send

        contact_name = "контакту"
        if self.active_chat and self.active_chat != -1:
            for user in self.users:
                if user['id'] == self.active_chat:
                    contact_name = user['username']
                    break

        gift_controls = []
        for rarity in ['common', 'uncommon', 'rare', 'epic', 'legendary']:
            if not gifts_by_rarity[rarity]:
                continue

            gift_controls.append(
                ft.Text(rarity_names[rarity], size=14, weight=ft.FontWeight.BOLD, color=rarity_colors[rarity])
            )

            gift_cards = []
            for gift in gifts_by_rarity[rarity]:
                gift_cards.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(gift["emoji"], size=32, text_align=ft.TextAlign.CENTER),
                            ft.Text(gift["name"], size=10, text_align=ft.TextAlign.CENTER, color=ft.Colors.GREY_300),
                            ft.Text(f"⭐{gift['price']}", size=10, text_align=ft.TextAlign.CENTER, color=ft.Colors.AMBER,
                                    weight=ft.FontWeight.BOLD),
                            ft.Text("🎬 GIF" if gift.get("gif") else "", size=8, color=ft.Colors.PINK) if gift.get(
                                "gif") else None,
                        ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=10,
                        bgcolor=ft.Colors.GREY_800,
                        border_radius=12,
                        border=ft.Border.all(width=2, color=rarity_colors[rarity]) if rarity in ['epic',
                                                                                                 'legendary'] else None,
                        on_click=send_gift(gift["id"], gift["name"], gift["emoji"], gift["price"], gift["rarity"],
                                           gift.get("gif")),
                        ink=True,
                    )
                )

            gift_controls.append(
                ft.Container(
                    content=ft.GridView(
                        expand=True,
                        runs_count=4,
                        max_extent=90,
                        child_aspect_ratio=1.0,
                        spacing=8,
                        run_spacing=8,
                        controls=gift_cards
                    ),
                    height=130 if len(gifts_by_rarity[rarity]) <= 4 else 190,
                )
            )
            gift_controls.append(ft.Divider(height=5, color=ft.Colors.TRANSPARENT))

        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CARD_GIFTCARD, color=ft.Colors.PINK, size=28),
                        ft.Text(f"🎁 Подарки для @{contact_name}", size=22, weight=ft.FontWeight.BOLD),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            on_click=close_gifts,
                            icon_color=ft.Colors.GREY_400,
                            tooltip="Закрыть"
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.Padding(left=16, right=8, top=12, bottom=8),
                    border_radius=ft.BorderRadius(top_left=12, top_right=12, bottom_left=0, bottom_right=0),
                    bgcolor=ft.Colors.GREY_800,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"💰 Ваши сферы: ⭐ {self.current_user_spheres}", size=14, color=ft.Colors.GREY_400),
                        ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                        ft.Text("Выберите подарок для отправки:", size=14, color=ft.Colors.GREY_400),
                        ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                        ft.Column(gift_controls, spacing=5, height=420, scroll=ft.ScrollMode.AUTO),
                    ], spacing=5),
                    padding=20,
                    expand=True,
                ),
            ], spacing=0),
            width=450,
            height=580,
            bgcolor=ft.Colors.GREY_900,
            border_radius=16,
            shadow=ft.BoxShadow(
                spread_radius=4,
                blur_radius=20,
                color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK)
            ),
            alignment=ft.Alignment(0, 0),
        )

    def show_gifts_panel(self, e):
        if not self.current_user:
            return
        if not self.active_chat or self.active_chat == -1:
            self.status_text.value = "❌ Сначала выберите контакт"
            self.page.update()
            return
        self.gifts_overlay.content = ft.Container(
            content=self.create_gifts_content(),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )
        self.gifts_overlay.visible = True
        self.gifts_overlay.opacity = 1
        self.page.update()

    def close_gifts(self):
        self.gifts_overlay.visible = False
        self.gifts_overlay.opacity = 0
        self.page.update()

    async def send_gift_to_server(self, gift_id, gift_gif=None):
        try:
            await self.ws.send(json.dumps({
                'action': 'send_gift',
                'user_id': self.current_user_id,
                'receiver_id': self.active_chat,
                'gift_id': gift_id,
                'gift_gif': gift_gif
            }))
        except Exception as e:
            print(f"Ошибка отправки подарка: {e}")
            self.status_text.value = f"❌ Ошибка: {e}"
            self.status_text.color = ft.Colors.RED
            self.page.update()

    # ==================== SPHERE BOT (как чат) ====================

    def open_bot_chat(self):
        """Открывает чат с Sphere Bot"""
        self.active_chat = -1
        self.is_bot_chat = True
        self.gift_btn.disabled = True
        self.chat_title.value = "🤖 Sphere Bot"
        self.message_field.disabled = False
        self.send_btn.disabled = False
        self.message_list.controls.clear()
        self.empty_chat_text.visible = False

        # Приветствие бота
        welcome_msg = {
            'sender': 'Sphere Bot',
            'content': '👋 Привет! Я помогу тебе заработать сферы!\n\nНапиши "заработать" или нажми кнопку 🎯 Заработать, чтобы получить случайное количество сфер.\n\n📊 Шансы выпадения:\n🟢 1 сфера — 40%\n🟢 2 сферы — 25%\n🟡 3 сферы — 15%\n🟡 4 сферы — 10%\n🔵 5 сфер — 5%\n🔵 6-7 сфер — 3%\n🔴 8-10 сфер — 2%',
            'timestamp': datetime.now().isoformat(),
            'is_read': False,
            'is_gift': False,
            'is_bot': True
        }
        self.message_list.controls.append(self.create_message_widget(welcome_msg))

        # Кнопка "Заработать" в footer
        self.earn_btn = ft.IconButton(
            icon=ft.Icons.ADD_CIRCLE,
            icon_size=30,
            icon_color=ft.Colors.GREEN,
            on_click=lambda e: asyncio.create_task(self.earn_spheres()),
            tooltip="Заработать сферу"
        )

        self.chat_footer.content = ft.Row([self.message_field, self.earn_btn, self.send_btn])

        self.update_contact_list()
        self.page.update()

    # ==================== ЗАПОМНИТЬ МЕНЯ ====================

    def on_remember_change(self, e):
        self.remember_me = self.remember_checkbox.value

    def save_credentials(self, username: str, password: str):
        if self.remember_me:
            try:
                with open("session.txt", "w") as f:
                    f.write(f"{username}\n{password}")
                print("✅ Данные сохранены")
            except Exception as e:
                print(f"❌ Ошибка сохранения: {e}")
        else:
            try:
                if os.path.exists("session.txt"):
                    os.remove("session.txt")
            except:
                pass

    def load_saved_credentials(self):
        try:
            if os.path.exists("session.txt"):
                with open("session.txt", "r") as f:
                    lines = f.readlines()
                    if len(lines) >= 2:
                        username = lines[0].strip()
                        password = lines[1].strip()
                        self.username_field.value = username
                        self.password_field.value = password
                        self.remember_checkbox.value = True
                        self.remember_me = True
                        self.page.update()
                        print(f"✅ Загружены данные для {username}")
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")

    # ==================== СЕТЕВЫЕ МЕТОДЫ ====================

    async def connect_to_server(self):
        while True:
            try:
                self.ws = await websockets.connect("wss://dmessenger.onrender.com")
                print("🟢 Подключено к серверу")
                await self.try_auto_login()
                await self.listen_messages()
            except websockets.exceptions.ConnectionClosed:
                print("🔴 Соединение разорвано, переподключение через 3 секунды...")
                await asyncio.sleep(3)
            except Exception as e:
                print(f"❌ Ошибка подключения: {e}")
                if hasattr(self, 'status_text') and self.status_text:
                    self.status_text.value = f"❌ Ошибка подключения: {str(e)}"
                    self.page.update()
                await asyncio.sleep(5)

    async def listen_messages(self):
        try:
            async for message in self.ws:
                print(f"📨 Получено: {message}")
                data = json.loads(message)
                msg_type = data.get('type')

                if msg_type == 'welcome':
                    self.status_text.value = "✅ Подключено к серверу! Войдите или зарегистрируйтесь."
                    self.page.update()

                elif msg_type == 'username_check':
                    available = data.get('available', False)
                    reason = data.get('reason', '')
                    if self.pending_username_check:
                        if available:
                            self.username_edit_status.value = "✅ Доступно"
                            self.username_edit_status.color = ft.Colors.GREEN
                            self.username_edit_status.visible = True
                        else:
                            self.username_edit_status.value = f"❌ {reason}"
                            self.username_edit_status.color = ft.Colors.RED
                            self.username_edit_status.visible = True
                        self.pending_username_check = None
                    else:
                        self.update_username_status(available, reason)
                    self.page.update()

                elif msg_type == 'login_success':
                    self.current_user_id = data['user_id']
                    self.current_user = data['username']
                    self.current_user_email = data.get('email', 'не указан')
                    self.current_user_avatar = data.get('avatar', None)
                    self.current_user_spheres = data.get('spheres', 0)
                    self.current_user_language = data.get('language', 'ru')
                    self.current_user_accent = data.get('accent_color', 'BLUE')
                    self.current_user_bg = data.get('background_image', '')
                    self.save_credentials(self.username_field.value, self.password_field.value)
                    self.update_profile_button()
                    self.status_text.value = f"✅ Добро пожаловать, {data['username']}!"
                    self.auth_view.visible = False
                    self.chat_view.visible = True
                    self.auto_login_in_progress = False
                    self.page.update()

                elif msg_type == 'avatar_update_success':
                    self.status_text.value = "✅ Аватарка обновлена!"
                    self.status_text.color = ft.Colors.GREEN
                    self.page.update()
                    self.close_profile()

                elif msg_type == 'settings_update_success':
                    self.current_user_language = data.get('language', 'ru')
                    self.current_user_accent = data.get('accent_color', 'BLUE')
                    self.current_user_bg = data.get('background_image', '')
                    self.status_text.value = "✅ Настройки сохранены!"
                    self.status_text.color = ft.Colors.GREEN
                    self.page.update()

                elif msg_type == 'register_success':
                    self.status_text.value = "✅ Регистрация успешна! Теперь войдите."
                    self.status_text.color = ft.Colors.GREEN
                    self.page.update()

                elif msg_type == 'verification_required':
                    self.pending_email = data.get('email')
                    self.verification_field.visible = True
                    self.verify_btn.visible = True
                    self.resend_btn.visible = True
                    self.status_text.value = "📧 Код отправлен на почту. Введите его ниже."
                    self.status_text.color = ft.Colors.BLUE
                    self.page.update()

                elif msg_type == 'verification_success':
                    self.status_text.value = "✅ Email подтверждён! Теперь войдите."
                    self.status_text.color = ft.Colors.GREEN
                    self.verification_field.visible = False
                    self.verify_btn.visible = False
                    self.resend_btn.visible = False
                    self.verification_field.value = ""
                    self.page.update()

                elif msg_type == 'verification_fail':
                    self.status_text.value = f"❌ {data.get('error', 'Ошибка подтверждения')}"
                    self.status_text.color = ft.Colors.RED
                    self.page.update()

                elif msg_type in ['login_fail', 'register_fail']:
                    error = data.get('error', 'Ошибка')
                    self.status_text.value = f"❌ {error}"
                    self.status_text.color = ft.Colors.RED
                    self.auto_login_in_progress = False
                    self.page.update()

                elif msg_type == 'contact_history':
                    contact_id = data['contact_id']
                    contact_name = data['contact_name']
                    messages = data['messages']
                    if contact_id not in self.messages:
                        self.messages[contact_id] = []
                    for msg in messages:
                        if msg['sender'] == self.current_user:
                            msg['sender'] = self.current_user
                        self.messages[contact_id].append(msg)
                    if self.active_chat == contact_id:
                        self.message_list.controls.clear()
                        if self.messages[contact_id]:
                            self.empty_chat_text.visible = False
                            for msg in self.messages[contact_id]:
                                self.message_list.controls.append(self.create_message_widget(msg))
                        else:
                            self.empty_chat_text.visible = True
                            self.empty_chat_text.value = "💬 Нет сообщений. Напишите что-нибудь!"
                        self.page.update()

                elif msg_type == 'new_message':
                    msg = data['message']
                    sender_name = msg['sender']
                    sender_id = None
                    for user in self.users:
                        if user['username'] == sender_name:
                            sender_id = user['id']
                            break
                    if sender_id:
                        if sender_id not in self.messages:
                            self.messages[sender_id] = []
                        self.messages[sender_id].append(msg)
                        if self.active_chat == sender_id:
                            self.message_list.controls.append(self.create_message_widget(msg))
                            self.empty_chat_text.visible = False
                            self.page.update()

                # ==================== ПОДАРКИ ====================

                elif msg_type == 'gift_received':
                    from_user = data.get('from_user')
                    gift = data.get('gift')
                    gift_gif = data.get('gift_gif')
                    msg = data.get('message')
                    self.status_text.value = msg
                    self.status_text.color = ft.Colors.PINK
                    self.page.update()

                    snack = ft.SnackBar(
                        content=ft.Row([
                            ft.Text(f"{gift['emoji']} ", size=20),
                            ft.Text(f"Подарок {gift['name']} от {from_user}!", size=14),
                        ], spacing=5),
                        bgcolor=ft.Colors.GREEN_900,
                        duration=3000,
                        shape=ft.RoundedRectangleBorder(radius=10),
                    )
                    self.page.overlay.append(snack)
                    snack.open = True
                    self.page.update()

                    gift_msg = {
                        'sender': from_user,
                        'content': f"🎁 {gift['emoji']} {gift['name']}",
                        'timestamp': datetime.now().isoformat(),
                        'is_read': False,
                        'is_gift': True,
                        'gift': gift,
                        'gift_gif': gift_gif
                    }
                    if self.active_chat and self.active_chat != -1:
                        if self.active_chat not in self.messages:
                            self.messages[self.active_chat] = []
                        self.messages[self.active_chat].append(gift_msg)
                        self.message_list.controls.append(self.create_message_widget(gift_msg))
                        self.empty_chat_text.visible = False
                        self.page.update()

                elif msg_type == 'gift_sent':
                    gift = data.get('gift')
                    gift_gif = data.get('gift_gif')
                    to_user = data.get('to_user')
                    msg = data.get('message')
                    self.status_text.value = msg
                    self.status_text.color = ft.Colors.GREEN
                    self.page.update()

                    snack = ft.SnackBar(
                        content=ft.Row([
                            ft.Text(f"{gift['emoji']} ", size=20),
                            ft.Text(f"Вы отправили подарок {gift['name']} → {to_user}!", size=14),
                        ], spacing=5),
                        bgcolor=ft.Colors.BLUE_900,
                        duration=3000,
                        shape=ft.RoundedRectangleBorder(radius=10),
                    )
                    self.page.overlay.append(snack)
                    snack.open = True
                    self.page.update()

                    gift_msg = {
                        'sender': self.current_user,
                        'content': f"🎁 {gift['emoji']} {gift['name']}",
                        'timestamp': datetime.now().isoformat(),
                        'is_read': False,
                        'is_gift': True,
                        'gift': gift,
                        'gift_gif': gift_gif
                    }
                    if self.active_chat and self.active_chat != -1:
                        if self.active_chat not in self.messages:
                            self.messages[self.active_chat] = []
                        self.messages[self.active_chat].append(gift_msg)
                        self.message_list.controls.append(self.create_message_widget(gift_msg))
                        self.empty_chat_text.visible = False
                        self.page.update()

                elif msg_type == 'user_list':
                    self.users = data['users']
                    self.update_contact_list()
                    self.page.update()

                elif msg_type == 'gifts_list':
                    self.gifts_data = data.get('gifts', [])
                    print(f"✅ Загружено {len(self.gifts_data)} подарков")

                elif msg_type == 'user_gifts':
                    self.user_gifts = data.get('gifts', [])
                    print(f"✅ Загружено {len(self.user_gifts)} подарков пользователя")

                # ==================== СФЕРЫ ====================

                elif msg_type == 'spheres_earned':
                    amount = data.get('amount', 0)
                    spheres = data.get('spheres', 0)
                    msg = data.get('message', '')
                    self.current_user_spheres = spheres

                    if self.active_chat == -1 and self.is_bot_chat:
                        reply = {
                            'sender': 'Sphere Bot',
                            'content': f'✨ **{msg}**\n\n💰 Всего сфер: ⭐ {spheres}',
                            'timestamp': datetime.now().isoformat(),
                            'is_read': False,
                            'is_gift': False,
                            'is_bot': True
                        }
                        self.message_list.controls.append(self.create_message_widget(reply))
                        self.page.update()
                    else:
                        self.status_text.value = msg
                        self.status_text.color = ft.Colors.AMBER
                        self.page.update()

                        snack = ft.SnackBar(
                            content=ft.Row([
                                ft.Text("✨ ", size=20),
                                ft.Text(f"Вы заработали {amount} сфер! ⭐{spheres}", size=14),
                            ], spacing=5),
                            bgcolor=ft.Colors.GREEN_900,
                            duration=3000,
                            shape=ft.RoundedRectangleBorder(radius=10),
                        )
                        self.page.overlay.append(snack)
                        snack.open = True
                        self.page.update()

                elif msg_type == 'spheres_update':
                    spheres = data.get('spheres', 0)
                    self.current_user_spheres = spheres
                    self.status_text.value = f"💰 Сферы обновлены: ⭐{spheres}"
                    self.status_text.color = ft.Colors.AMBER
                    self.page.update()

        except websockets.exceptions.ConnectionClosed:
            print("🔴 Соединение разорвано")
            raise

    # ==================== МЕТОДЫ ИНТЕРФЕЙСА ====================

    def update_profile_button(self):
        if self.current_user:
            avatar_to_show = self.current_user_avatar if hasattr(self,
                                                                 'current_user_avatar') and self.current_user_avatar else None
            self.profile_btn.content = ft.Row([
                ft.Container(
                    content=ft.Stack([
                        ft.CircleAvatar(
                            content=ft.Text(
                                self.current_user[0].upper(),
                                size=16,
                                weight=ft.FontWeight.BOLD
                            ) if not avatar_to_show else None,
                            bgcolor=ft.Colors.BLUE_700,
                            radius=18,
                            foreground_image_src=avatar_to_show,
                        ),
                        ft.Container(
                            width=10,
                            height=10,
                            bgcolor=ft.Colors.GREEN,
                            border=ft.Border.all(width=2, color=ft.Colors.BLACK),
                            border_radius=5,
                            left=24,
                            top=24,
                        ),
                    ]),
                ),
                ft.Text(self.current_user, size=14, weight=ft.FontWeight.W_500, color=ft.Colors.WHITE),
                ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=16, color=ft.Colors.GREY_400)
            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER)
            self.page.update()

    def update_username_status(self, available: bool, reason: str):
        self.username_status.visible = True
        self.username_status.controls[0].visible = False
        self.username_status.controls[1].visible = False
        self.username_status.controls[2].visible = True
        if available:
            self.username_status.controls[0].visible = True
            self.username_status.controls[2].value = "✅ Доступно"
            self.username_status.controls[2].color = ft.Colors.GREEN
        else:
            self.username_status.controls[1].visible = True
            self.username_status.controls[2].value = f"❌ {reason}"
            self.username_status.controls[2].color = ft.Colors.RED
        self.page.update()

    def on_username_change(self, e):
        username = self.username_field.value
        if not username or len(username) < 2:
            self.username_status.visible = False
            self.page.update()
            return
        self.username_status.visible = True
        self.username_status.controls[0].visible = False
        self.username_status.controls[1].visible = False
        self.username_status.controls[2].visible = True
        self.username_status.controls[2].value = "⏳ Проверка..."
        self.username_status.controls[2].color = ft.Colors.GREY_400
        self.page.update()
        if self.username_check_task:
            self.username_check_task.cancel()
        self.username_check_task = asyncio.create_task(self.check_username_delayed(username))

    async def check_username_delayed(self, username):
        await asyncio.sleep(0.3)
        await self.check_username(username)

    async def check_username(self, username):
        try:
            await self.ws.send(json.dumps({
                'action': 'check_username',
                'username': username
            }))
        except Exception as e:
            print(f"Ошибка проверки имени: {e}")

    def create_message_widget(self, msg_data):
        sender = msg_data['sender']
        content = msg_data['content']
        timestamp = datetime.fromisoformat(msg_data['timestamp'])
        time_str = timestamp.strftime("%H:%M")
        is_mine = sender == self.current_user
        is_bot = msg_data.get('is_bot', False)

        is_gift = msg_data.get('is_gift', False)
        gift = msg_data.get('gift', None)
        gift_gif = msg_data.get('gift_gif', None)

        if is_gift and gift:
            if gift_gif:
                display_content = ft.Container(
                    content=ft.Column([
                        ft.Image(
                            src=gift_gif,
                            width=100,
                            height=100,
                            fit="contain",
                        ),
                        ft.Text(f"{gift['name']}", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text(f"от {sender}", size=11, color=ft.Colors.GREY_400),
                    ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=15,
                    bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.PINK),
                    border_radius=16,
                    border=ft.Border.all(width=1, color=ft.Colors.with_opacity(0.2, ft.Colors.PINK)),
                    width=130,
                    alignment=ft.Alignment(0, 0),
                )
            else:
                display_content = ft.Container(
                    content=ft.Column([
                        ft.Text(gift['emoji'], size=48, text_align=ft.TextAlign.CENTER),
                        ft.Text(f"{gift['name']}", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text(f"от {sender}", size=11, color=ft.Colors.GREY_400),
                    ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=15,
                    bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.PINK),
                    border_radius=16,
                    border=ft.Border.all(width=1, color=ft.Colors.with_opacity(0.2, ft.Colors.PINK)),
                    width=120,
                    alignment=ft.Alignment(0, 0),
                )
        elif is_bot:
            display_content = ft.Text(content, size=14, selectable=True)
        else:
            display_content = ft.Text(content, size=14)

        sender_avatar = None
        sender_online = False

        if is_bot:
            sender_avatar = None
            sender_online = True
            sender_name = "🤖 Sphere Bot"
        else:
            for user in self.users:
                if user['username'] == sender:
                    sender_avatar = user.get('avatar', None)
                    sender_online = user.get('online', False)
                    break

        if is_mine:
            sender_avatar = self.current_user_avatar
            sender_online = True

        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Stack([
                        ft.CircleAvatar(
                            content=ft.Text(
                                sender[0].upper() if sender else "?",
                                size=14,
                                weight=ft.FontWeight.BOLD
                            ) if not sender_avatar else None,
                            bgcolor=ft.Colors.GREEN_700 if is_bot else ft.Colors.BLUE_700,
                            radius=18,
                            foreground_image_src=sender_avatar,
                        ),
                        ft.Container(
                            width=12,
                            height=12,
                            bgcolor=ft.Colors.GREEN if sender_online else ft.Colors.GREY_500,
                            border=ft.Border.all(width=2, color=ft.Colors.BLACK),
                            border_radius=6,
                            left=24,
                            top=24,
                        ),
                    ]),
                    margin=ft.Margin(left=0, top=0, right=8, bottom=0),
                    visible=not is_mine,
                ),
                ft.Column([
                    ft.Row([
                        ft.Text(
                            sender_name if is_bot else (sender if not is_mine else "Я"),
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.AMBER if is_bot else (ft.Colors.PINK if is_gift and not is_mine else (
                                ft.Colors.BLUE if not is_mine else ft.Colors.GREEN)),
                        ),
                        ft.Text(time_str, size=10, color=ft.Colors.GREY_400)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    display_content,
                ], spacing=2, expand=True),
                ft.Container(
                    content=ft.Stack([
                        ft.CircleAvatar(
                            content=ft.Text(
                                self.current_user[0].upper() if self.current_user else "?",
                                size=14,
                                weight=ft.FontWeight.BOLD
                            ) if not self.current_user_avatar else None,
                            bgcolor=ft.Colors.GREEN_700,
                            radius=18,
                            foreground_image_src=self.current_user_avatar,
                        ),
                        ft.Container(
                            width=12,
                            height=12,
                            bgcolor=ft.Colors.GREEN,
                            border=ft.Border.all(width=2, color=ft.Colors.BLACK),
                            border_radius=6,
                            left=24,
                            top=24,
                        ),
                    ]),
                    margin=ft.Margin(left=8, top=0, right=0, bottom=0),
                    visible=is_mine,
                ),
            ], alignment=ft.MainAxisAlignment.START),
            padding=10,
            bgcolor=ft.Colors.BLUE_900 if is_mine else (ft.Colors.GREY_800 if not is_bot else ft.Colors.GREY_900),
            border_radius=10,
            margin=ft.Margin(left=50 if is_mine else 0, top=5, right=0 if is_mine else 50, bottom=5),
            alignment=ft.Alignment(0, 0)
        )

    def update_contact_list(self):
        self.contact_list.controls.clear()

        # Sphere Bot
        bot_avatar = ft.Icon(ft.Icons.ATTACH_MONEY, color=ft.Colors.AMBER, size=20)
        self.contact_list.controls.append(
            ft.ListTile(
                leading=ft.Container(
                    content=ft.Stack([
                        ft.CircleAvatar(
                            content=bot_avatar,
                            bgcolor=ft.Colors.GREEN_700,
                            radius=20,
                        ),
                        ft.Container(
                            width=10,
                            height=10,
                            bgcolor=ft.Colors.GREEN,
                            border=ft.Border.all(width=2, color=ft.Colors.BLACK),
                            border_radius=5,
                            left=26,
                            top=26,
                        ),
                    ]),
                ),
                title=ft.Text(
                    "🤖 Sphere Bot",
                    color=ft.Colors.WHITE,
                    weight=ft.FontWeight.BOLD,
                ),
                subtitle=ft.Text("Зарабатывай сферы!", size=10, color=ft.Colors.AMBER),
                selected=self.active_chat == -1,
                on_click=lambda e: self.open_bot_chat()
            )
        )

        # Остальные контакты
        for user in self.users:
            if user['id'] == self.current_user_id:
                continue
            user_avatar = user.get('avatar', None)
            is_online = user.get('online', False)
            gifts_count = user.get('gifts_count', 0)
            unread_count = 0
            if user['id'] in self.messages:
                for msg in self.messages[user['id']]:
                    if not msg.get('is_read', False) and msg['sender'] != self.current_user:
                        unread_count += 1
            title_text = f"{user['username']}"
            if gifts_count > 0:
                title_text += f" 🎁{gifts_count}"
            if unread_count > 0:
                title_text += f" 🔵{unread_count}"
            self.contact_list.controls.append(
                ft.ListTile(
                    leading=ft.Container(
                        content=ft.Stack([
                            ft.CircleAvatar(
                                content=ft.Text(
                                    user['username'][0].upper(),
                                    size=16,
                                    weight=ft.FontWeight.BOLD
                                ) if not user_avatar else None,
                                bgcolor=ft.Colors.BLUE_700,
                                radius=20,
                                foreground_image_src=user_avatar,
                            ),
                            ft.Container(
                                width=10,
                                height=10,
                                bgcolor=ft.Colors.GREEN if is_online else ft.Colors.GREY_500,
                                border=ft.Border.all(width=2, color=ft.Colors.BLACK),
                                border_radius=5,
                                left=26,
                                top=26,
                            ),
                        ]),
                    ),
                    title=ft.Text(
                        title_text,
                        color=ft.Colors.WHITE if is_online else ft.Colors.GREY_400,
                    ),
                    selected=self.active_chat == user['id'],
                    on_click=lambda e, u=user: self.open_chat(u['id'])
                )
            )

    def open_chat(self, user_id):
        self.active_chat = user_id
        self.is_bot_chat = False
        self.gift_btn.disabled = False
        self.chat_footer.content = ft.Row([self.message_field, self.gift_btn, self.send_btn])
        self.earn_btn = None

        user = next((u for u in self.users if u['id'] == user_id), None)
        if user:
            self.chat_title.value = f"💬 {user['username']}"
        self.message_field.disabled = False
        self.send_btn.disabled = False
        self.message_list.controls.clear()
        if user_id in self.messages and self.messages[user_id]:
            self.empty_chat_text.visible = False
            for msg in self.messages[user_id]:
                self.message_list.controls.append(self.create_message_widget(msg))
        else:
            self.empty_chat_text.visible = True
            self.empty_chat_text.value = "💬 Нет сообщений. Напишите что-нибудь!"
        self.update_contact_list()
        self.page.update()

    # ==================== АВТОРИЗАЦИЯ ====================

    def login(self, e):
        username = self.username_field.value
        password = self.password_field.value
        if not username or not password:
            self.status_text.value = "❌ Заполните имя и пароль"
            self.page.update()
            return
        self.save_credentials(username, password)
        self.status_text.value = "⏳ Вход..."
        self.page.update()
        asyncio.create_task(self.send_auth('login', username, password))

    def register(self, e):
        username = self.username_field.value
        email = self.email_field.value
        password = self.password_field.value
        if not username or not email or not password:
            self.status_text.value = "❌ Заполните все поля"
            self.page.update()
            return
        if '@' not in email:
            self.status_text.value = "❌ Введите корректный email"
            self.page.update()
            return
        self.status_text.value = "⏳ Регистрация..."
        self.page.update()
        asyncio.create_task(self.send_auth('register', username, email, password))

    def verify_email(self, e):
        email = self.email_field.value
        code = self.verification_field.value
        if not email or not code:
            self.status_text.value = "❌ Введите email и код"
            self.status_text.color = ft.Colors.RED
            self.page.update()
            return
        self.status_text.value = "⏳ Проверка кода..."
        self.status_text.color = ft.Colors.GREY_400
        self.page.update()
        asyncio.create_task(self.send_verify(email, code))

    async def send_verify(self, email, code):
        try:
            await self.ws.send(json.dumps({
                'action': 'verify',
                'email': email,
                'code': code
            }))
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")

    def resend_code(self, e):
        email = self.email_field.value
        if not email:
            self.status_text.value = "❌ Введите email"
            self.status_text.color = ft.Colors.RED
            self.page.update()
            return
        self.status_text.value = "⏳ Отправка кода..."
        self.status_text.color = ft.Colors.GREY_400
        self.page.update()
        asyncio.create_task(self.send_resend_code(email))

    async def send_resend_code(self, email):
        try:
            await self.ws.send(json.dumps({
                'action': 'resend_code',
                'email': email
            }))
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")

    async def send_auth(self, action, username, password_or_email, password=None):
        try:
            if action == 'register':
                message = {'action': action, 'username': username, 'email': password_or_email, 'password': password}
            else:
                message = {'action': action, 'username': username, 'password': password_or_email}
            await self.ws.send(json.dumps(message))
        except Exception as e:
            self.status_text.value = f"❌ Ошибка: {str(e)}"
            self.page.update()

    # ==================== СООБЩЕНИЯ ====================

    def send_message(self, e):
        content = self.message_field.value
        if not content or not self.current_user_id:
            return

        if self.active_chat == -1 and self.is_bot_chat:
            self.message_field.value = ""
            self.page.update()

            temp_msg = {
                'sender': self.current_user,
                'content': content,
                'timestamp': datetime.now().isoformat(),
                'is_read': False,
                'is_gift': False,
                'is_bot': False
            }
            self.message_list.controls.append(self.create_message_widget(temp_msg))

            if content.lower() in ['заработать', 'earn', 'сфера', 'sphere', 'начать', 'start']:
                asyncio.create_task(self.earn_spheres())
            else:
                reply = {
                    'sender': 'Sphere Bot',
                    'content': f'❌ Неизвестная команда "{content}".\n\nДоступные команды:\n• "заработать" - получить сферы\n• "сфера" - получить сферы\n• "начать" - показать приветствие',
                    'timestamp': datetime.now().isoformat(),
                    'is_read': False,
                    'is_gift': False,
                    'is_bot': True
                }
                self.message_list.controls.append(self.create_message_widget(reply))
                self.page.update()
            return

        if not self.active_chat:
            return

        temp_msg = {
            'sender': self.current_user,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'is_read': False,
            'is_gift': False,
            'is_bot': False
        }
        if self.active_chat not in self.messages:
            self.messages[self.active_chat] = []
        self.messages[self.active_chat].append(temp_msg)
        self.message_list.controls.append(self.create_message_widget(temp_msg))
        self.empty_chat_text.visible = False
        self.message_field.value = ""
        self.page.update()
        asyncio.create_task(self.send_message_to_server(content, self.active_chat))

    async def send_message_to_server(self, content, receiver_id):
        try:
            await self.ws.send(json.dumps({
                'action': 'message',
                'user_id': self.current_user_id,
                'content': content,
                'receiver_id': receiver_id
            }))
        except Exception as e:
            print(f"Ошибка отправки: {e}")

    async def earn_spheres(self):
        try:
            await self.ws.send(json.dumps({
                'action': 'earn_spheres',
                'user_id': self.current_user_id
            }))
        except Exception as e:
            print(f"Ошибка: {e}")
            if self.active_chat == -1 and self.is_bot_chat:
                reply = {
                    'sender': 'Sphere Bot',
                    'content': f'❌ Ошибка: {e}',
                    'timestamp': datetime.now().isoformat(),
                    'is_read': False,
                    'is_gift': False,
                    'is_bot': True
                }
                self.message_list.controls.append(self.create_message_widget(reply))
                self.page.update()

    # ==================== ВЫХОД ====================

    def logout(self, e):
        self.current_user = None
        self.current_user_id = None
        self.current_user_email = None
        self.current_user_avatar = None
        self.current_user_spheres = 0
        self.messages = {}
        self.active_chat = None
        self.is_bot_chat = False
        self.message_list.controls.clear()
        self.empty_chat_text.visible = True
        self.empty_chat_text.value = "💬 Выберите контакт, чтобы начать общение"
        self.message_field.disabled = True
        self.send_btn.disabled = True
        self.gift_btn.disabled = True
        self.chat_title.value = "Выберите контакт"
        self.chat_view.visible = False
        self.auth_view.visible = True
        self.verification_field.visible = False
        self.verify_btn.visible = False
        self.resend_btn.visible = False
        self.verification_field.value = ""
        self.status_text.value = "👋 Выход выполнен"
        self.status_text.color = ft.Colors.GREY_400
        self.earn_btn = None
        self.chat_footer.content = ft.Row([self.message_field, self.gift_btn, self.send_btn])

        if not self.remember_me:
            try:
                if os.path.exists("session.txt"):
                    os.remove("session.txt")
            except:
                pass

        self.profile_btn.content = ft.Row([
            ft.Container(
                content=ft.Stack([
                    ft.CircleAvatar(
                        content=ft.Text("?", size=16, weight=ft.FontWeight.BOLD),
                        bgcolor=ft.Colors.BLUE_700,
                        radius=18,
                    ),
                    ft.Container(
                        width=10,
                        height=10,
                        bgcolor=ft.Colors.GREY_500,
                        border=ft.Border.all(width=2, color=ft.Colors.BLACK),
                        border_radius=5,
                        left=24,
                        top=24,
                    ),
                ]),
            ),
            ft.Text("Профиль", size=14, weight=ft.FontWeight.W_500, color=ft.Colors.WHITE),
            ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=16, color=ft.Colors.GREY_400)
        ], spacing=8, alignment=ft.MainAxisAlignment.CENTER)

        self.page.update()


if __name__ == "__main__":
    app = MessengerApp()
    ft.run(main=app.main)