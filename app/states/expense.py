from aiogram.fsm.state import State, StatesGroup


class ExpenseFlow(StatesGroup):
    # Faqat parse bo'lmagan forward uchun: summani qo'lda so'raymiz.
    # `waiting_category` olib tashlandi — kategoriya endi FSM navbati orqali
    # emas, saqlangan xarajatning `id` si orqali tanlanadi (app/handlers/expense.py).
    waiting_amount = State()
