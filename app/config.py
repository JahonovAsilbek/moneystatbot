import hashlib

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    OWNER_ID: int

    # Ommaviy HTTPS manzil (webhook + Mini App). Bo'sh bo'lsa — polling rejimi.
    PUBLIC_URL: str = ""
    PORT: int = 10000

    # Userbot (MTProto) — avtomatik o'qish uchun. Bo'sh bo'lsa userbot ishlamaydi.
    API_ID: int = 0
    API_HASH: str = ""
    SESSION_STRING: str = ""

    # Vaqt zonasi (eslatma jadvali uchun)
    TIMEZONE: str = "Asia/Tashkent"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def userbot_enabled(self) -> bool:
        return bool(self.API_ID and self.API_HASH and self.SESSION_STRING)

    @property
    def public_url(self) -> str:
        return self.PUBLIC_URL.rstrip("/")

    @property
    def webhook_secret(self) -> str:
        """Telegram webhook so'rovlarini tasdiqlash uchun maxfiy token.

        Alohida sozlama emas, bot tokenidan keltirib chiqariladi. Sabab:
        serverdagi .env ni qo'lda tahrirlash shart bo'lmasin va token
        almashtirilganda sir ham o'zi yangilansin. Xesh bir tomonlama —
        bu qiymatdan bot tokenini tiklab bo'lmaydi.
        """
        return hashlib.sha256(f"webhook:{self.BOT_TOKEN}".encode()).hexdigest()


settings = Settings()
