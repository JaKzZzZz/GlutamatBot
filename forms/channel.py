from aiogram.fsm.state import StatesGroup, State
class AddForm(StatesGroup):
    channel_id = State()

class EditForm(StatesGroup):
    channel_id = State()

class EditTags(StatesGroup):
    waiting_for_tag = State()

class PostActionChoose(StatesGroup):
    choosing_action = State()
    waiting_confirmation = State()
