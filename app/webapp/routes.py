"""Mini App API va sahifa marshrutlari (aiohttp)."""
import os
from decimal import Decimal

from aiohttp import web

from app.config import settings
from app.db.base import async_session
from app.db.models import Category, Expense
from app.keyboards.categories import (
    CATEGORY_EMOJI,
    UNCATEGORIZED_EMOJI,
    UNCATEGORIZED_LABEL,
)
from app.services import expense as expense_service
from app.services import stats as stats_service
from app.services.periods import resolve_range
from app.utils.money import format_amount, parse_amount
from app.utils.time import now as local_now
from app.webapp.auth import is_owner

_INDEX_PATH = os.path.join(os.path.dirname(__file__), "index.html")
_VALID_CATEGORIES = {c.value for c in Category}


def _init_data(request: web.Request) -> str:
    # Faqat sarlavhadan. Query-string varianti ham bor edi, lekin Mini App
    # undan foydalanmaydi (index.html X-Init-Data yuboradi), Caddy esa har bir
    # so'rovning to'liq URL'ini access-logga yozadi — ya'ni kirish kaliti
    # diskda ochiq matnda qolib ketardi.
    return request.headers.get("X-Init-Data") or ""


def _require_owner(request: web.Request) -> bool:
    return is_owner(_init_data(request))


def _filters(request: web.Request) -> tuple[dict, web.Response | None]:
    """Query'dan filtr: `period`, yoki `from`/`to` (YYYY-MM-DD, ikkalasi inklyuziv).

    Sana berilsa u tayyor davrdan ustun turadi; faqat bittasi berilsa ikkinchi
    tomon ochiq qoladi.
    """
    try:
        start, end = resolve_range(
            request.query.get("period"),
            request.query.get("from"),
            request.query.get("to"),
        )
    except ValueError:
        return {}, web.json_response(
            {"error": "Sana formati noto'g'ri (YYYY-MM-DD kutilgan)"}, status=400
        )
    return {"start": start, "end": end}, None


def _serialize(e: Expense) -> dict:
    date = e.transaction_time or e.created_at
    return {
        "id": e.id,
        "amount": float(e.amount),
        "original_amount": float(e.original_amount) if e.original_amount is not None else None,
        "merchant": e.merchant,
        "card_type": e.card_type,
        "card_last4": e.card_last4,
        "balance_after": float(e.balance_after) if e.balance_after is not None else None,
        "category": e.category,
        "date": date.strftime("%d.%m.%Y %H:%M") if date else None,
        # Mini App kunlar bo'yicha guruhlash va vaqtni ko'rsatish uchun
        # tayyor matnni emas, tuzilgan qiymatni ishlatadi.
        "ts": date.isoformat(timespec="minutes") if date else None,
    }


async def index(request: web.Request) -> web.Response:
    with open(_INDEX_PATH, encoding="utf-8") as f:
        return web.Response(text=f.read(), content_type="text/html")


async def api_categories(request: web.Request) -> web.Response:
    if not _require_owner(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    data = [
        {"value": c.value, "emoji": CATEGORY_EMOJI.get(c.value, "")}
        for c in Category
    ]
    return web.json_response(data)


async def api_pending(request: web.Request) -> web.Response:
    if not _require_owner(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    async with async_session() as session:
        rows = await expense_service.get_pending(session, settings.OWNER_ID)
    return web.json_response([_serialize(e) for e in rows])


async def api_expenses(request: web.Request) -> web.Response:
    if not _require_owner(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    rng, error = _filters(request)
    if error is not None:
        return error

    # Statistikadan kategoriya ustiga bosilganda shu kategoriya bo'yicha
    # tranzaksiyalar so'raladi. Kategoriyalanmaganlar bazada NULL, shuning
    # uchun ular uchun alohida belgi kerak.
    category = request.query.get("category")
    only_uncategorized = category == UNCATEGORIZED_LABEL

    async with async_session() as session:
        rows = await expense_service.get_expenses(
            session,
            settings.OWNER_ID,
            category=None if only_uncategorized else category,
            only_uncategorized=only_uncategorized,
            **rng,
        )
    return web.json_response([_serialize(e) for e in rows])


async def api_stats(request: web.Request) -> web.Response:
    if not _require_owner(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    rng, error = _filters(request)
    if error is not None:
        return error

    async with async_session() as session:
        rows = await stats_service.get_category_stats(
            session, settings.OWNER_ID, **rng
        )
    total = sum(float(a) for _, a in rows)
    data = [
        {
            "category": cat or UNCATEGORIZED_LABEL,
            "emoji": CATEGORY_EMOJI.get(cat, UNCATEGORIZED_EMOJI),
            "amount": float(amount),
            "pct": (float(amount) / total * 100) if total > 0 else 0,
        }
        for cat, amount in rows
    ]
    return web.json_response({"total": total, "items": data})


async def api_categorize(request: web.Request) -> web.Response:
    if not _require_owner(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    body = await request.json()
    try:
        expense_id = int(body["id"])
    except (KeyError, ValueError, TypeError):
        return web.json_response({"error": "bad id"}, status=400)
    category = body.get("category")
    if category not in _VALID_CATEGORIES:
        return web.json_response({"error": "bad category"}, status=400)
    async with async_session() as session:
        await expense_service.update_expense(session, expense_id, category=category)
    return web.json_response({"ok": True})


async def api_manual(request: web.Request) -> web.Response:
    if not _require_owner(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    body = await request.json()

    category = body.get("category")
    if category not in _VALID_CATEGORIES:
        return web.json_response({"error": "bad category"}, status=400)

    amount = parse_amount(str(body.get("amount", "")))
    if amount is None:
        return web.json_response(
            {"error": "Summani tushunmadim. Masalan: 150000 yoki 150 000"}, status=400
        )

    merchant = (body.get("merchant") or "").strip() or None
    now_local = local_now()

    async with async_session() as session:
        exp = await expense_service.create_expense(
            session,
            user_id=settings.OWNER_ID,
            amount=amount,
            category=category,
            merchant=merchant,
            source="manual",
            transaction_time=now_local,
        )
    return web.json_response({"ok": True, "id": exp.id})


async def api_share(request: web.Request) -> web.Response:
    """Ulush ajratish: {id, amount} yoki bekor qilish: {id, reset: true}."""
    if not _require_owner(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    body = await request.json()
    try:
        expense_id = int(body["id"])
    except (KeyError, ValueError, TypeError):
        return web.json_response({"error": "bad id"}, status=400)

    async with async_session() as session:
        expense = await expense_service.get_expense_by_id(session, expense_id)
        if expense is None:
            return web.json_response({"error": "not found"}, status=404)

        if body.get("reset"):
            expense = await expense_service.reset_share(session, expense_id)
        else:
            total = expense.original_amount or expense.amount
            # Summani o'qish qoidasi bot bilan bir xil: `parse_amount`
            # `100.000` ni 100 emas, 100 000 deb tushunadi.
            share = parse_amount(str(body.get("amount", "")))
            if share is None:
                return web.json_response(
                    {"error": "Summani tushunmadim. Masalan: 100000"}, status=400
                )
            if share > Decimal(total):
                return web.json_response(
                    {"error": f"Ulush jami to'lovdan ({format_amount(total)} UZS) katta bo'lolmaydi"},
                    status=400,
                )
            expense = await expense_service.set_share(session, expense_id, share)

    return web.json_response({"ok": True, **_serialize(expense)})


async def api_delete(request: web.Request) -> web.Response:
    if not _require_owner(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    body = await request.json()
    try:
        expense_id = int(body["id"])
    except (KeyError, ValueError, TypeError):
        return web.json_response({"error": "bad id"}, status=400)
    async with async_session() as session:
        await expense_service.delete_expense(session, expense_id)
    return web.json_response({"ok": True})


def setup_webapp_routes(app: web.Application) -> None:
    app.router.add_get("/app", index)
    app.router.add_get("/api/categories", api_categories)
    app.router.add_get("/api/pending", api_pending)
    app.router.add_get("/api/expenses", api_expenses)
    app.router.add_get("/api/stats", api_stats)
    app.router.add_post("/api/categorize", api_categorize)
    app.router.add_post("/api/manual", api_manual)
    app.router.add_post("/api/share", api_share)
    app.router.add_post("/api/delete", api_delete)
