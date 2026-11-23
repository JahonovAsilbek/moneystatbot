# 🤝 Hissa qo'shish

Yordamingiz uchun rahmat! Eng foydali hissalar:

## 🏦 Bank xabari o'qilmadi

Bot xabarni tushunmasa, [issue oching](../../issues/new?template=bank-format.md)
va xabar namunasini qo'shing. **Avval shaxsiy ma'lumotlarni almashtiring:**

- karta raqami → `***1234`
- balans va summa → istalgan boshqa raqam (formatni saqlang: `1 250 000.00`)
- do'kon nomi qolishi mumkin, xohlasangiz o'zgartiring

Qatorlar soni, emoji va bo'sh joylar **o'zgarmasin** — parser aynan shularga
qaraydi.

## 💻 Kod yozish

1. Fork qiling va alohida branch oching
2. `pip install -r requirements-dev.txt`
3. O'zgartiring va test yozing:
   - yangi bank formati → `tests/test_parsers.py` ga namuna
   - xato tuzatilsa → o'sha xatoni takrorlaydigan test
4. `pytest` va `ruff check app/ tests/ --select F,E9,I --ignore E501` o'tsin
5. Pull request oching

[CLAUDE.md](CLAUDE.md) dagi qoidalarga e'tibor bering — ayniqsa summani
o'qish (`parse_amount`) va vaqt (`app.utils.time.now`) bo'yicha.

Interfeys matnlari o'zbek tilida, emoji bilan.

## 🔒 Xavfsizlik

Zaiflik topsangiz, ochiq issue o'rniga GitHub'dagi
**Security → Report a vulnerability** orqali yozing.
