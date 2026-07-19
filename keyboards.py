from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_reply_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Посты"),
             KeyboardButton(text="Управление каналами")],
            [KeyboardButton(text="Стоп/Старт")],
            [KeyboardButton(text="Установить задержку")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_channels_reply_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Список добавленных в рассылку каналов"),
             KeyboardButton(text="Редактировать рассылку канала")],
            [KeyboardButton(text="Удалить канал"), KeyboardButton(text="Добавить канал")],
            [KeyboardButton(text="Назад")]
        ],
        resize_keyboard=True
    )
    return keyboard


def post_keyboard(file_id: int, channel_id: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅", callback_data=f"approve:{file_id}:{channel_id}"),
                InlineKeyboardButton(text="❌", callback_data=f"reject:{file_id}:{channel_id}")
            ]
        ]
    )


def get_posts_reply_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Вкл/Выкл рассылку")],
            [KeyboardButton(text="Ручная/Автоматическая модерация")],
            [KeyboardButton(text="Отбор постов вручную"),
             KeyboardButton(text="Просмотр очереди"),
             KeyboardButton(text="Загрузить посты вручную")],
            [KeyboardButton(text="Удалить все загруженные посты"),
             KeyboardButton(text="Удалить все посты из очереди")],
            [KeyboardButton(text="Назад")]
        ],
        resize_keyboard=True
    )
    return keyboard


def confirm_keyboard(action: str, channel_id: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да",
                    callback_data=f"confirm:{action}:{channel_id}"
                ),
                InlineKeyboardButton(
                    text="Нет",
                    callback_data="cancel"
                )
            ]
        ]
    )


def queue_keyboard(index: int, total: int, file_id: int, channel_id: str):
    buttons = []

    if index > 0:
        buttons.append(InlineKeyboardButton(
            text="⬅️",
            callback_data="queue:prev"
        ))

    if index < total - 1:
        buttons.append(InlineKeyboardButton(
            text="➡️",
            callback_data="queue:next"
        ))

    buttons.append(InlineKeyboardButton(
        text="🗑",
        callback_data=f"queue:delete:{file_id}:{channel_id}"
    ))

    return InlineKeyboardMarkup(inline_keyboard=[buttons])

