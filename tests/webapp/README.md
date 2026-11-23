# Mini App testlari

Python testlaridan alohida, chunki bu yerda brauzer DOM'i kerak. CI'da
(`.github/workflows/tests.yml`) avtomatik ishlaydi, lokal ishga tushirish:

```bash
cd tests/webapp
npm install     # jsdom
npm test
```

Nimani tekshiradi: `app/webapp/index.html` haqiqiy DOM'ga yuklanadi, API
javoblari o'rniga namunaviy ma'lumot beriladi va ekranlar bosib ko'riladi —
diagramma bo'laklari, kategoriya bo'yicha ochish, sana filtri, kunlar bo'yicha
guruhlash. Server umuman ishtirok etmaydi.
