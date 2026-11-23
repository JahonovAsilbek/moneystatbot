"""Userbot uchun SESSION_STRING yaratish (bir martalik, LOKAL ishga tushiriladi).

Foydalanish:
    1. https://my.telegram.org  -> "API development tools" -> API_ID va API_HASH oling
    2. Loyihaning .env fayliga yozing:
         API_ID=12345
         API_HASH=xxxxxxxx
    3. Terminalda:  docker compose run --rm bot python scripts/gen_session.py
       (yoki Python o'rnatilgan bo'lsa:  python scripts/gen_session.py)
    4. Telefon raqam + Telegram'dan kelgan kod (+ 2FA parol bo'lsa) kiriting
    5. Chiqqan SESSION_STRING'ni .env fayliga joylang (git'ga QO'YMANG!)

Eslatma: SESSION_STRING akkauntingizga to'liq kirish beradi — uni hech kimga bermang.
"""
import asyncio
import os

from dotenv import load_dotenv
from pyrogram import Client  # Kurigram 'pyrogram' nomi bilan import qilinadi

load_dotenv()  # .env dan API_ID / API_HASH ni o'qiydi


async def main() -> None:
    if not os.environ.get("API_ID") or not os.environ.get("API_HASH"):
        raise SystemExit("❌ .env faylida API_ID va API_HASH bo'lishi kerak (my.telegram.org dan oling).")

    api_id = int(os.environ["API_ID"])
    api_hash = os.environ["API_HASH"]

    async with Client(name="gen", api_id=api_id, api_hash=api_hash, in_memory=True) as app:
        session_string = await app.export_session_string()
        me = await app.get_me()
        print("\n" + "=" * 60)
        print(f"Kirdingiz: {me.first_name} (@{me.username or me.id})")
        print("=" * 60)
        print("\nSESSION_STRING (buni .env dagi SESSION_STRING= ga qo'ying):\n")
        print(session_string)
        print()


if __name__ == "__main__":
    asyncio.run(main())
