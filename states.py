from aiogram.fsm.state import State, StatesGroup


class TransactionForm(StatesGroup):
    choosing_category = State()
    entering_amount = State()
    entering_note = State()


class LimitForm(StatesGroup):
    entering_limit = State()


class DeleteForm(StatesGroup):
    confirming = State()
