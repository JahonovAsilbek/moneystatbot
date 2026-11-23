# 💰 MoneyStatBot

UzCard va Humo kartalaringizdagi xarajatlarni avtomatik kuzatadigan shaxsiy
Telegram bot. Bank botlaridan kelgan xabarlarni o'qiydi, xarajatlarni
kategoriyalarga ajratadi va statistika ko'rsatadi.

> 🏠 **Self-hosted:** har kim botni o'z serverida, o'z bot tokeni bilan
> ishga tushiradi. Ma'lumotlaringiz faqat sizning bazangizda turadi.

## ✨ Imkoniyatlar

- 📲 **Bank xabarini o'qish** — UzCard (@CardXabarBot) va Humo (@HUMOcardbot)
  xabarlarini forward qilsangiz, summa, do'kon, karta va balans o'zi ajratiladi
- 🤖 **Avtomatik rejim** (ixtiyoriy) — forward ham shart emas: bot bank
  xabarlarini o'zi o'qib, kategoriyalashni kutayotganlar ro'yxatiga qo'shadi
- 🏷 **12 ta kategoriya** — bitta tugma bilan belgilash
- 🔔 **Eslatma** — kuniga 4 marta kategoriyalanmagan xarajatlar haqida
- 📊 **Statistika** — kun, hafta, oy yoki ixtiyoriy sana oralig'i bo'yicha
- 🤝 **Ulush ajratish** — do'stlar bilan bo'lingan to'lovda faqat o'z
  ulushingiz hisoblanadi (`/3`, `40%` yoki summa)
- 📥 **PDF hisobot** yuklab olish
- 📱 **Mini App** (ixtiyoriy) — grafiklar, ro'yxat, tahrirlash, qo'lda kiritish
- 🔁 **Dublikatdan himoya** — bir xabarni ikki marta forward qilsangiz ham
  bir marta saqlanadi

## 🚀 Ishga tushirish

Kerak bo'ladi: Docker o'rnatilgan kompyuter yoki server (VPS). Eng arzon VPS
ham yetadi.

**1. Bot yarating.** Telegram'da [@BotFather](https://t.me/BotFather) ga
`/newbot` yozing va bergan tokenni saqlang.

**2. Telegram ID'ingizni bilib oling.** [@userinfobot](https://t.me/userinfobot)
ga `/start` yozing.

**3. Loyihani yuklab oling va sozlang:**

```bash
git clone https://github.com/JahonovAsilbek/moneystatbot.git
cd moneystatbot
cp .env.example .env
nano .env          # BOT_TOKEN, OWNER_ID, POSTGRES_PASSWORD ni to'ldiring
```

**4. Ishga tushiring:**

```bash
docker compose up -d --build
```

Tayyor! Botingizga `/start` yozing. Loglarni ko'rish:
`docker compose logs -f bot`

## 🤖 Avtomatik o'qish (ixtiyoriy)

Busiz ham bot to'liq ishlaydi — bank xabarlarini qo'lda forward qilasiz.
Avtomatik rejimda esa bot sizning Telegram akkauntingiz nomidan bank
botlaridagi xabarlarni **faqat o'qiydi**.

1. [my.telegram.org](https://my.telegram.org) → *API development tools* →
   `API_ID` va `API_HASH` ni oling va `.env` ga yozing
2. Sessiya yarating (telefon raqam va Telegram kodini so'raydi):
   ```bash
   docker compose run --rm bot python scripts/gen_session.py
   ```
3. Chiqqan satrni `.env` dagi `SESSION_STRING=` ga qo'ying
4. `docker compose up -d` — ⚙️ Sozlamalar ekranida 🟢 ko'rinadi

> ⚠️ **`SESSION_STRING` — akkauntingizga TO'LIQ kirish kaliti.** Uni hech
> kimga bermang, git'ga qo'ymang, ishonmagan serverga joylamang. Shu sababli
> bu bot "hammaga bitta" xizmat sifatida emas, self-hosted ko'rinishda
> tarqatiladi.

## 📱 Mini App (ixtiyoriy)

Grafikli panel uchun HTTPS kerak, ya'ni domen (masalan `bot.example.com`)
serveringiz IP manziliga yo'naltirilgan bo'lishi lozim.

1. `.env` ga yozing:
   ```
   DOMAIN=bot.example.com
   PUBLIC_URL=https://bot.example.com
   ```
2. HTTPS bilan ishga tushiring (sertifikatni Caddy o'zi oladi):
   ```bash
   docker compose --profile https up -d --build
   ```

Bot chatida **📊 Panel** tugmasi paydo bo'ladi. `PUBLIC_URL` bo'lsa bot
webhook rejimiga o'tadi.

## 🔄 Yangilash va zaxira

```bash
git pull && docker compose up -d --build          # yangilash (migratsiya o'zi ishlaydi)
docker compose exec postgres pg_dump -U moneystat moneystat > backup.sql   # zaxira
```

## 🏦 Qo'llab-quvvatlanadigan banklar

| Karta | Bot | Holat |
|---|---|---|
| UzCard | @CardXabarBot | ✅ |
| Humo | @HUMOcardbot | ✅ |

Kirim (➕) tranzaksiyalari hisobga olinmaydi — faqat xarajatlar.
Boshqa bank yoki format kerakmi? [CONTRIBUTING.md](CONTRIBUTING.md) ga qarang.

## 🛠 Dasturchilar uchun

```bash
pip install -r requirements-dev.txt
pytest
ruff check app/ tests/ --select F,E9,I --ignore E501
```

Arxitektura va muhim qoidalar: [CLAUDE.md](CLAUDE.md).
Stek: Python 3.12, aiogram 3, SQLAlchemy (async) + PostgreSQL, Alembic,
Kurigram (MTProto), aiohttp.

## 📄 Litsenziya

[MIT](LICENSE). PDF hisobotdagi DejaVu shriftlari o'z
[bepul litsenziyasi](https://dejavu-fonts.github.io/License.html) ostida.
