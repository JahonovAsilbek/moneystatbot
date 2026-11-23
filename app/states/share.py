from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


class ShareFlow(StatesGroup):
    waiting_share = State()


async def clear_share_state(state: FSMContext) -> None:
    """Ulush kutish holatidan chiqadi.

    Boshqa oqimlarning holati/ma'lumotlariga tegmaydi (forward navbati saqlanadi).
    """
    if await state.get_state() == ShareFlow.waiting_share.state:
        await state.set_state(None)
