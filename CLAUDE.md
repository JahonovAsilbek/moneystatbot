# MoneyStatBot

Shaxsiy xarajat kuzatuvchi Telegram bot (self-hosted, open-source). UzCard/Humo bank botlarining
xabarlarini o'qib, xarajatlarni kategoriyalarga ajratadi. Har bir nusxa bitta
foydalanuvchi uchun (`OWNER_ID`), uning o'z serverida ishlaydi.

## Ishga tushirish

```bash
pip install -r requirements-dev.txt
pytest                 # testlar (baza kerak emas)
ruff check app/ tests/ --select F,E9,I --ignore E501
```

Botni lokal ishga tushirish uchun `.env` kerak (`.env.example` dan nusxa oling).
`PUBLIC_URL` bo'sh bo'lsa — polling rejimi, aks holda webhook.

## Arxitektura

```
app/
├── bot.py            # ishga tushirish, webhook/polling, migratsiya
├── config.py         # .env sozlamalari (pydantic-settings)
├── handlers/         # aiogram routerlari (bitta ekran = bitta fayl)
├── keyboards/        # inline/reply klaviaturalar
├── middlewares/      # owner (kirish nazorati), menu_reset (FSM tozalash)
├── parsers/          # bank xabarlarini o'qish (uzcard, humo)
├── services/         # baza bilan ishlash (handlerlar SQL yozmaydi)
├── userbot/          # Kurigram/MTProto — bank botlarini avtomatik o'qish
├── utils/            # money (summa), time (vaqt zonasi)
└── webapp/           # Telegram Mini App (aiohttp + bitta index.html)
```

## Muhim qoidalar

**Summa hech qachon to'g'ridan-to'g'ri `Decimal()` ga berilmaydi.** Faqat
`app.utils.money.parse_amount` orqali: `Decimal("100.000")` = 100, ya'ni
foydalanuvchi 100 000 yozib 100 so'm saqlab qo'yardi. Humo botining o'zi
summani `18.483,00` deb yozadi, ya'ni bu format foydalanuvchiga tanish.

**Vaqt bazada naive va MAHALLIY** (`TIMEZONE`). `datetime.utcnow()` va
`datetime.now()` ishlatilmaydi — faqat `app.utils.time.now()`. Ilgari
`created_at` UTC, `transaction_time` mahalliy edi va ular `coalesce()` bilan
aralashardi.

**Callback tugmasida har doim yozuv `id` si bo'ladi** (`pcat:<id>:<kat>`).
Ilgari forward oqimi FSM navbatining boshidagi yozuvni olardi va parallel
kelgan yangilanishlarda kategoriya boshqa tranzaksiyaga yozilib ketardi.

**Hech narsa jimgina yo'qolmaydi.** Userbot parse qilolmagan xabar haqida
egaga xabar beradi; ushlanmagan istisnolar `dp.errors` orqali foydalanuvchiga
ko'rsatiladi; migratsiya yiqilsa bot ishga tushmaydi.

**Davr filtri `sort_column()` bo'yicha**, `created_at` bo'yicha emas — aks
holda eski tranzaksiyani bugun forward qilsangiz u bugungi statistikaga
tushadi.

## Hissa qo'shish

Interfeys matnlari va izohlar o'zbek tilida, emoji bilan. Yangi bank formati
qo'shilsa — `tests/test_parsers.py` ga namuna (shaxsiy ma'lumotsiz) qo'shiladi.
Batafsil: [CONTRIBUTING.md](CONTRIBUTING.md).
