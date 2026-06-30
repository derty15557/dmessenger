# email_sender.py
import asyncio
import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class EmailSender:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.email = "dmessenger400@gmail.com"
        self.password = "keth adgt xpcp ekqi"

    def generate_code(self, length=6) -> str:
        return ''.join(random.choices(string.digits, k=length))

    def send_verification_code_sync(self, to_email: str, code: str) -> bool:
        try:
            subject = "🔐 Подтверждение регистрации DMessenger"
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h1>📱 DMessenger</h1>
                <h2>Код подтверждения</h2>
                <h1 style="font-size: 48px; letter-spacing: 10px;">{code}</h1>
                <p>Код действителен 5 минут</p>
            </body>
            </html>
            """

            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email
            msg['To'] = to_email
            html_part = MIMEText(body, 'html')
            msg.attach(html_part)

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email, self.password)
            server.send_message(msg)
            server.quit()

            print(f"✅ Код отправлен на {to_email}")
            return True

        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")
            return False

    async def send_verification_code(self, to_email: str, code: str) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.send_verification_code_sync,
            to_email,
            code
        )