/**
 * Mini App'ning DOM darajasidagi testlari.
 *
 * `app/webapp/index.html` o'zgartirilmasdan yuklanadi; faqat `window.Telegram`
 * va `fetch` almashtiriladi. Ya'ni tekshirilayotgan narsa — ishlab chiqarishga
 * ketadigan haqiqiy kod.
 */
import { JSDOM } from "jsdom";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const INDEX = path.join(HERE, "..", "..", "app", "webapp", "index.html");

const CATS = [
  ["Oziq-ovqat","🍽"],["Transport","🚗"],["Kommunal","🏠"],["Kiyim","👕"],
  ["Sog'liqni saqlash","💊"],["Ta'lim","📚"],["Ko'ngilochar","🎮"],
  ["Uy-ro'zg'or","🛒"],["Telefon","📱"],["Qarz berish","🤝"],
  ["Naqdlashtirish","💵"],["Boshqa","📦"],
];

const iso = (back) => {
  const d = new Date(); d.setDate(d.getDate() - back);
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
};

// Ataylab 11 xil kategoriya: palitrada 8 slot bor, ya'ni "Boshqalar" ga
// yig'ilish yo'li ham sinaladi.
const RAW = [
  [0,"09:12","KORZINKA","Oziq-ovqat",87000,null],
  [0,"13:40","YANDEX GO","Transport",24000,null],
  [0,"19:05","CHAYXONA","Ko'ngilochar",120000,360000],
  [1,"08:31","PAYME UZ",null,45000,null],
  [1,"12:00","MAKRO","Oziq-ovqat",213500,null],
  [1,"21:14","UZMOBILE","Telefon",30000,null],
  [2,"09:30","TOSHKENT SUV","Kommunal",88000,null],
  [3,"10:02","APTEKA","Sog'liqni saqlash",56000,null],
  [3,"15:22","KORZINKA","Oziq-ovqat",142000,null],
  [5,"14:10","ZARA","Kiyim",340000,null],
  [6,"18:00","KINOTEATR","Ko'ngilochar",60000,null],
  [7,"11:20","IELTS KURS","Ta'lim",700000,null],
  [9,"11:45","TEXNOMART","Uy-ro'zg'or",890000,null],
  [12,"16:30","QARZ","Qarz berish",200000,null],
];
const EXPENSES = RAW.map(([day,t,m,c,a,o],i)=>({
  id:i+1, amount:a, original_amount:o, merchant:m, card_type:"uzcard",
  card_last4:"4321", balance_after:1250000, category:c,
  date:`${iso(day)} ${t}`, ts:`${iso(day)}T${t}`,
}));

const agg = {};
for (const e of EXPENSES) agg[e.category] = (agg[e.category] || 0) + e.amount;
const TOTAL = Object.values(agg).reduce((a,b)=>a+b,0);
const EMOJI = Object.fromEntries(CATS);
const ITEMS = Object.entries(agg).sort((a,b)=>b[1]-a[1]).map(([c,v])=>({
  category: c === "null" ? "Kategoriyalanmagan" : c,
  emoji: EMOJI[c] || "❓", amount: v, pct: v / TOTAL * 100,
}));

const FX = {
  categories: CATS.map(([value,emoji])=>({value,emoji})),
  pending: EXPENSES.filter(e=>!e.category),
  expenses: EXPENSES,
  stats: {total: TOTAL, items: ITEMS},
};

function buildDom(scheme) {
  let html = fs.readFileSync(INDEX, "utf8");
  const stub = `<script>
    window.Telegram = {WebApp:{ready(){},expand(){},colorScheme:${JSON.stringify(scheme)},
      HapticFeedback:{impactOccurred(){}},onEvent(){},initData:"stub",showAlert(){}}};
    const FX = ${JSON.stringify(FX)};
    window.fetch = async (url)=>{
      const u = new URL(url, location.origin);
      let data;
      if(u.pathname==="/api/categories") data = FX.categories;
      else if(u.pathname==="/api/pending") data = FX.pending;
      else if(u.pathname==="/api/stats") data = FX.stats;
      else if(u.pathname==="/api/expenses"){
        const c = u.searchParams.get("category");
        data = c ? FX.expenses.filter(e=>(e.category||"Kategoriyalanmagan")===c) : FX.expenses;
      } else data = {ok:true};
      return {ok:true, status:200, json: async()=>data};
    };
  </script>\n`;
  html = html.replace("<script>\nconst tg = window.Telegram.WebApp;",
                      stub + "<script>\nconst tg = window.Telegram.WebApp;");
  if (scheme === "dark") html = html.replace("<body>", '<body data-scheme="dark">');
  return new JSDOM(html, {runScripts:"dangerously", pretendToBeVisual:true, url:"https://test.local/app"});
}

let failures = 0;
const ok = (cond, name, extra="") => {
  console.log((cond ? "  OK   " : "  XATO ") + name + (extra ? `  <- ${extra}` : ""));
  if (!cond) failures++;
};
const sleep = (ms)=>new Promise(r=>setTimeout(r, ms));

async function run(scheme) {
  console.log(`\n===== ${scheme} =====`);
  const {window} = buildDom(scheme);
  const $  = (s)=>window.document.querySelector(s);
  const $$ = (s)=>[...window.document.querySelectorAll(s)];
  await sleep(400);

  $('.tab[data-tab="stats"]').onclick();
  await sleep(300);

  ok($$(".donutwrap .slice").length === 8,
     "diagramma 8 bo'lakdan oshmaydi (palitrada 8 slot)", `${$$(".donutwrap .slice").length}`);
  ok(!/NaN|undefined/.test($(".donutwrap").innerHTML), "SVG'da NaN/undefined yo'q");
  ok($(".dcenter .dval").textContent.trim().length > 0, "markazda jami summa");

  const rows = $$(".srow");
  ok(rows.length === ITEMS.length, "ro'yxatda BARCHA kategoriyalar", `${rows.length}/${ITEMS.length}`);
  const sw = rows.map(r=>r.style.getPropertyValue("--sw"));
  ok(sw.every(v=>/^var\(--s[1-8]\)$/.test(v)), "har bir qatorda 1..8 slotdan rang chiziqchasi");
  ok(sw.slice(7).every(v=>v === "var(--s8)"), "8-dan keyingilar 'Boshqalar' rangini ulashadi");
  ok(rows.every(r=>r.querySelector(".nmt").textContent.trim()), "rang hech qachon yolg'iz emas — nom ham bor");

  // Nom ko'rsatish: SVG'ning tug'ma <title> tooltipi telefonda chiqmaydi,
  // shuning uchun nom halqa atrofidagi emoji va markazdagi matn orqali beriladi.
  const labels = $$(".donutwrap .dlabel");
  ok(labels.length > 0, "halqa atrofida emoji yorliqlari bor", `${labels.length} ta`);
  ok(labels.every(l=>l.textContent.trim()), "yorliqlar bo'sh emas");
  ok(labels.every(l=>l.dataset.i), "yorliqlar ham bosiladigan (data-i bor)");

  const norm = (el)=>el.textContent.replace(/\s+/g," ").trim();
  const totalText = norm($(".dcenter"));
  $$(".donutwrap .slice")[0].onpointerenter();
  const hoverText = norm($(".dcenter"));
  ok(hoverText !== totalText, "bo'lak ustiga kelganda markaz o'zgaradi");
  ok(hoverText.includes(ITEMS[0].category), "markazda kategoriya NOMI chiqadi", hoverText);
  ok(/%/.test(hoverText), "foizi ham ko'rsatiladi");
  $(".donutwrap").onpointerleave();
  ok(norm($(".dcenter")) === totalText, "sichqoncha ketgach jami qaytadi", norm($(".dcenter")));

  $$(".donutwrap .slice")[1].onpointerdown();
  ok(norm($(".dcenter")).includes(ITEMS[1].category),
     "telefonda bosganda ham nom chiqadi (pointerdown)");
  $(".donutwrap").onpointerleave();

  ok($$(".donutwrap .slice title").length === $$(".donutwrap .slice").length,
     "har bir bo'lakda <title> ham qoldi (skrinrider/desktop uchun)");

  // Diagramma bo'lagi -> kategoriya ekrani
  $$(".donutwrap .slice")[0].onclick();
  await sleep(300);
  ok(!!$(".dhead"), "bo'lak bosilganda kategoriya ekrani ochiladi");
  ok(($(".dtitle")?.textContent || "").includes(ITEMS[0].category),
     "eng katta bo'lak -> eng katta kategoriya", $(".dtitle")?.textContent.trim());
  ok($$("#drillrows .lrow").length > 0, "tranzaksiyalar chiqdi");
  $(".backbtn").onclick(); await sleep(300);
  ok(!!$(".donutwrap"), "orqaga -> diagramma qaytadi");

  $$(".donutwrap .dlabel")[0].onclick();
  await sleep(300);
  ok(!!$(".dhead"), "emoji yorlig'i bosilganda ham kategoriya ochiladi");
  $(".backbtn").onclick(); await sleep(250);

  // Ro'yxat qatori -> xuddi shu ekran
  $$(".srow")[1].onclick(); await sleep(300);
  ok(!!$(".dhead"), "ro'yxat qatori bosilganda ham ochiladi");
  $(".backbtn").onclick(); await sleep(250);

  // Filtr
  $("#stats .rangebtn").onclick();
  ok($("#stats .datebox").classList.contains("open"), "sana paneli ochiladi");
  $("#stats .dapply").onclick();
  ok($("#stats .derr").classList.contains("show"), "bo'sh sana -> xato ko'rsatiladi");
  $('#stats .dinp[data-k="from"]').value = "2026-08-01";
  $("#stats .dapply").onclick(); await sleep(300);
  ok($("#stats .rangebtn").classList.contains("active"), "sana qo'llangach tugma faollashadi");

  // Ro'yxat
  $('.tab[data-tab="list"]').onclick(); await sleep(300);
  ok($$("#list .lrow").length === EXPENSES.length, "barcha yozuvlar", `${$$("#list .lrow").length}`);
  ok($$("#list .dayhead").length >= 3, "kunlar bo'yicha guruhlangan");
  ok(/UZS/.test($("#list .dayhead").textContent), "kun sarlavhasida o'sha kunning jami summasi");
  ok($$("#list .lrow.uncat").length === 1, "kategoriyalanmagan yozuv ajratilgan");
  ok($$("#list .lamt").every(e=>e.textContent.trim()), "har bir qatorda summa ko'rinadi");

  // Mavzu. jsdom maxsus xossalarni `:root` dan `body` ga meros qilmaydi,
  // shuning uchun ikkala elementdan ham o'qiymiz: qorong'i qiymat `body`
  // dagi `[data-scheme]` qoidasidan, yorug'i esa `:root` dan keladi.
  const readVar = (name) =>
    [window.document.body, window.document.documentElement]
      .map(el => window.getComputedStyle(el).getPropertyValue(name).trim())
      .find(Boolean) || "";
  const s1 = readVar("--s1");
  ok(scheme === "dark" ? s1 === "#3987e5" : s1 === "#2a78d6",
     "palitra mavzuga mos", `--s1 = ${s1 || "(o'qilmadi)"}`);
}

await run("light");
await run("dark");

console.log(failures ? `\n>>> ${failures} ta XATO` : "\n>>> MINI APP: HAMMASI O'TDI");
process.exit(failures ? 1 : 0);
