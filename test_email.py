# test_email.py
import asyncio
from email_sender import EmailSender


async def test():
    sender = EmailSender()
    code = sender.generate_code()

    # Отправь тестовое письмо СЕБЕ НА ПОЧТУ
    success = await sender.send_verification_code("dmessenger400@gmail.com", code)

    if success:
        print(f"✅ Письмо отправлено! Код: {code}")
        print("📧 Проверь почту (в том числе спам)")
    else:
        print("❌ Ошибка отправки")


if __name__ == "__main__":
    asyncio.run(test())