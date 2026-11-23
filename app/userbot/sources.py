"""Avtomatik o'qiladigan manba botlar ro'yxati.

Karta turi (uzcard/humo) xabar mazmunidan parserlar orqali aniqlanadi —
bu yerdagi `label` faqat ma'lumot uchun. `username` — userbot qaysi
chatlarni tinglashini va toggle kalitini belgilaydi.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceBot:
    username: str  # @ belgisiz
    label: str
    default_enabled: bool


SOURCE_BOTS: list[SourceBot] = [
    SourceBot(username="CardXabarBot", label="UzCard", default_enabled=True),
    SourceBot(username="HUMOcardbot", label="Humo", default_enabled=False),
]

SOURCE_BY_USERNAME: dict[str, SourceBot] = {
    s.username.lower(): s for s in SOURCE_BOTS
}


def toggle_key(username: str) -> str:
    return f"source_enabled:{username}"
