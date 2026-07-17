import asyncio
import random
from os import getenv

from aiogram import Bot, Dispatcher, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, \
    InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from dotenv import load_dotenv
import aiosqlite
from aiogram.methods import GetChat
from aiogram import F
from aiogram.fsm.context import FSMContext

import keyboards
from db import requests_db, functions_db
from db.init_db import DB_NAME, init_db
from db.requests_db import get_delay, get_next_channel, get_next_post, get_channels
from forms.channel import AddForm, EditTags, PostActionChoose, AddDelay
from http_client import create_session, close_session

load_dotenv()
TOKEN = getenv("BOT_TOKEN")
CAPTION = getenv("CAPTION")

ALLOWED_IDS = [
    int(x) for x in getenv("ALLOWED_IDS", "").split(",")
]

dp = Dispatcher()
router = Router()
dp.include_router(router)

loading_lock = asyncio.Lock()

sender_task = None
bot_session = Bot(token=TOKEN)

async def hourly_sender(bot_session):
    while True:
        delay = await get_delay()
        sec_delay = delay * 60

        await asyncio.sleep(sec_delay + random.randint(0, sec_delay // 4))

        status = await requests_db.get_bot_status()
        if not status:
            continue

        channels = await requests_db.get_channels()

        if channels:
            for channel_name, channel_id in channels:
                try:
                    posts = await requests_db.get_all_query_posts(channel_id)
                    if not posts:
                        if await requests_db.is_channel_auto(channel_id):
                            try:
                                await auto_refill_query(bot_session, channel_id)
                                posts = await requests_db.get_all_query_posts(channel_id)
                            except Exception as e:
                                print(e)
                    if not posts:
                        continue

                    file_id, file, _, artist_name = posts[0]

                    if await requests_db.is_channel_active(channel_id):
                        try:
                            await send_message(bot_session, channel_id, file_id, file, artist_name)
                        except Exception as e:
                            print(e)

                except Exception as e:
                    print(f"Ошибка отправки в канале {channel_id}: {e}")


async def send_message(bot_session, channel_id, file_id, file, artist_name):

    caption = (
        "🌙 <b>The Way | New Post</b> ✨️\n"
        "━━━━━━━━━━━━━━\n"
        f"✦ <b>Artist:</b> {artist_name}\n"
        f'✦ <b>Source:</b> <a href="https://e621.net/posts/{file_id}">e621 Post</a>\n'
        "━━━━━━━━━━━━━━\n"
        f'<a href="{CAPTION}">Follow The Way 🖤</a>'
    )

    await bot_session.send_photo(chat_id=channel_id, photo=file, caption=caption, parse_mode="HTML")

    sleep_delay = random.randint(10, 30)

    await asyncio.sleep(sleep_delay)

    try:
        await requests_db.delete_query_post(file_id)

    except Exception as e:
        print(f"Ошибка удаления арта из БД: {e}")

async def get_next_global_post(current_channel_id):
    start = current_channel_id

    while True:
        current_channel_id = await get_next_channel(current_channel_id)

        post = await get_next_post(current_channel_id)
        if post:
            return post

        if current_channel_id == start:
            return None


async def auto_refill_query(bot_session, channel_id):
    try:
        loaded_count = await functions_db.fetch_and_save_posts(channel_id)

        if loaded_count == 0:
            await bot_session.send_message(channel_id, "По этим тегам ничего не найдено")
            return

        print("Успешная загрузка данных")


    except Exception as e:
        await bot_session.send_message(channel_id, "Возникла ошибка при загрузке данных. Возможно, не заданы тэги?")
        print(e)
        return

    try:
        posts = await requests_db.get_posts(channel_id)
        print(posts)
        for file_id in posts:
            await requests_db.query_approve_post(file_id, channel_id)

    except Exception as e:
        print("Ошибка автоматического добавления в очередь", e)


def tags_to_query(tags) -> str:
    return " ".join(tags.split())


@router.message(F.text.lower() == "стоп/старт")
async def command_pause_handler(message: Message) -> None:
    if message.from_user.id not in ALLOWED_IDS:
        return
    status = await requests_db.get_bot_status()

    if not status:
        try:
            await requests_db.set_bot_status_on()
            await message.answer("Рассылка включена")

        except Exception as e:
            print(e)

    if status:
        try:
            await requests_db.set_bot_status_off()
            await message.answer("Рассылка выключена")

        except Exception as e:
            print(e)

@router.message(PostActionChoose.choosing_action,
                F.text.lower() == "вкл/выкл рассылку")
async def command_active_handler(message: Message, state: FSMContext) -> None:
    if message.from_user.id not in ALLOWED_IDS:
        return
    data = await state.get_data()
    channel_id = data.get("channel_id")
    status_active = await requests_db.is_channel_active(channel_id)

    if not status_active:
        try:
            await requests_db.set_channel_active(channel_id, True)
            await message.answer("Рассылка для этого канала включена")

        except Exception as e:
            print(e)

    if status_active:
        try:
            await requests_db.set_channel_active(channel_id, False)
            await message.answer("Рассылка для этого канала выключена")

        except Exception as e:
            print(e)

@router.message(PostActionChoose.choosing_action,
                F.text.lower() == "ручная/автоматическая модерация")
async def command_auto_handler(message: Message, state: FSMContext) -> None:
    if message.from_user.id not in ALLOWED_IDS:
        return
    data = await state.get_data()
    channel_id = data.get("channel_id")
    status_auto = await requests_db.is_channel_auto(channel_id)

    if not status_auto:
        try:
            await requests_db.set_channel_auto(channel_id, True)
            await message.answer("Авто-модерация включена")

        except Exception as e:
            print(e)

    if status_auto:
        try:
            await requests_db.set_channel_auto(channel_id, False)
            await message.answer("Авто-модерация выключена")

        except Exception as e:
            print(e)


@router.message(Command("start"))
async def command_start_handler(message: Message) -> None:
    if message.from_user.id not in ALLOWED_IDS:
        return
    await message.answer("Тыкай кнопки",
                         reply_markup=keyboards.get_main_reply_keyboard())


@router.message(F.text.lower() == "управление каналами")
async def command_manipulatechannels_handler(message: Message) -> None:
    if message.from_user.id not in ALLOWED_IDS:
        return
    await message.answer("Выберите действие с каналами", reply_markup=keyboards.get_channels_reply_keyboard())


@router.message(F.text.lower() == "посты")
async def command_posts_handler(message: Message) -> None:
    if message.from_user.id not in ALLOWED_IDS:
        return
    channels = await requests_db.get_channels()

    if not channels:
        await message.answer("Нет добавленных каналов")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=channel_name,
                    callback_data=f"postschannel:{channel_id}"
                )
            ]
            for channel_name, channel_id in channels
        ]
    )

    await message.answer("Выберите канал:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("postschannel:"))
async def posts_channel(callback: CallbackQuery, state: FSMContext):
    channel_id = callback.data.split(":")[1]

    await state.update_data(channel_id=channel_id)

    await state.set_state(PostActionChoose.choosing_action)

    await callback.message.answer(f"Выберите действие:", reply_markup=keyboards.get_posts_reply_keyboard())

    await callback.answer()


@router.message(PostActionChoose.choosing_action,
                F.text.lower() == "загрузить посты вручную")
async def handle_posts_downloading_nonfilter(message: Message, state: FSMContext):
    if message.from_user.id not in ALLOWED_IDS:
        return
    data = await state.get_data()
    channel_id = data.get("channel_id")

    try:
        loaded_count = await functions_db.fetch_and_save_posts(channel_id)

        if loaded_count == 0:
            await message.answer("По этим тегам ничего не найдено")
            return

        posts_count = await requests_db.get_posts_count(channel_id)
        await message.answer(f"Успешная загрузка данных в {channel_id}. Кол-во нефильтрованных постов: {posts_count}")

    except Exception as e:
        await message.answer("Возникла ошибка при загрузке данных. Возможно, не заданы тэги?")
        print(e)
        return

@router.message(PostActionChoose.choosing_action,
                F.text.lower() == "отбор постов вручную")
async def handle_moderate_posts(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id not in ALLOWED_IDS:
        return
    data = await state.get_data()
    start_channel_id = data.get("channel_id")
    chat = await bot.get_chat(start_channel_id)
    post = await get_next_global_post(start_channel_id)
    channel_name = chat.title

    if not post:

        await message.answer("Очередь закончилась. Загрузка...")

        channels = await get_channels()
        results = []

        for c_n, c_id in channels:

            try:
                await functions_db.fetch_and_save_posts(c_id)

                posts_count = await requests_db.get_posts_count(c_id)

                results.append(
                    f"• {c_n}: всего в очереди {posts_count}"
                )

            except Exception as e:
                await message.answer("Возникла ошибка при загрузке данных. Возможно, не заданы тэги?")
                print(e)
                return

        await message.answer(
            "Загрузка завершена.\n\n" + "\n".join(results))

        post = await get_next_global_post(start_channel_id)

    if post is None:
        await message.answer("Ошибка: невозможно получить следующий пост")
        return

    file_id, file, tags, post_channel_id = post

    post_chat = await bot.get_chat(post_channel_id)
    post_channel_name = post_chat.title

    await message.answer_photo(
        photo=file,
        caption=f"Канал: {post_channel_name}",
        reply_markup=keyboards.post_keyboard(file_id, post_channel_id)
    )


@router.message(PostActionChoose.choosing_action,
                F.text.lower() == "удалить все загруженные посты")
async def handle_delete_nonfilter_posts(message: Message, state: FSMContext):
    if message.from_user.id not in ALLOWED_IDS:
        return
    data = await state.get_data()
    channel_id = data.get("channel_id")

    await message.answer(
        "Вы уверены, что хотите удалить ВСЕ загруженные посты?",
        reply_markup=keyboards.confirm_keyboard("nonfilter", channel_id)
    )


@router.message(
    PostActionChoose.choosing_action,
    F.text.lower().strip() == "удалить все посты из очереди"
)
async def handle_delete_query_posts(message: Message, state: FSMContext):
    if message.from_user.id not in ALLOWED_IDS:
        return
    data = await state.get_data()
    channel_id = data.get("channel_id")

    await message.answer(
        "Вы уверены, что хотите удалить ВСЕ посты из очереди?",
        reply_markup=keyboards.confirm_keyboard("query", channel_id)

    )


@router.callback_query(F.data == "cancel")
async def handle_cancel(callback: CallbackQuery):
    await callback.message.edit_text("Удаление отменено")
    await callback.answer()


@router.callback_query(F.data.startswith("confirm:"))
async def handle_confirm(callback: CallbackQuery):
    _, action, channel_id = callback.data.split(":")

    try:
        if action == "nonfilter":
            await requests_db.delete_nonfilter_posts(channel_id)
            text = "Загруженные посты удалены"

        elif action == "query":
            await requests_db.delete_query_posts(channel_id)
            text = "Посты из очереди удалены"

        else:
            text = "Неизвестное действие"

    except Exception as e:
        print(e)
        text = "Ошибка при удалении"

    await callback.message.edit_text(text)
    await callback.answer()


@router.message(PostActionChoose.choosing_action,
                F.text.lower() == "просмотр очереди")
async def start_queue_view(message: Message, state: FSMContext):
    if message.from_user.id not in ALLOWED_IDS:
        return
    data = await state.get_data()
    channel_id = data.get("channel_id")
    posts = await requests_db.get_all_query_posts(channel_id)

    if not posts:
        await message.answer("Очередь пуста")
        return

    try:
        await state.update_data(
            queue=posts,
            index=0
        )
        await show_queue_post(message, state)

    except Exception as e:
        print(e)


async def show_queue_post(message: Message, state: FSMContext):
    data = await state.get_data()

    posts = data.get("queue")
    index = data.get("index", 0)

    if not posts:
        await message.answer("Очередь пуста")
        return

    file_id, file, tags, artist_name = posts[index]

    caption = tags or ""
    if len(caption) > 1010:
        caption = caption[:1000] + "..."

    try:
        await message.answer_photo(
            photo=file,
            caption=f"{index + 1}/{len(posts)}\n\n{caption}",
            reply_markup=keyboards.queue_keyboard(index, len(posts), file_id)
        )
    except Exception as e:
        print(e)


@router.callback_query(F.data.in_(["queue:next", "queue:prev"]))
async def navigate_queue(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    posts = data.get("queue")
    index = data.get("index", 0)

    if callback.data == "queue:next":
        index += 1
    else:
        index -= 1

    index = max(0, min(index, len(posts) - 1))

    await state.update_data(index=index)

    file_id, file, tags, artist_name = posts[index]

    caption = tags or ""
    if len(caption) > 1010:
        caption = caption[:1000] + "..."

    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=file,
                caption=f"{index + 1}/{len(posts)}\n\n{caption}"
            ),
            reply_markup=keyboards.queue_keyboard(index, len(posts), file_id)
        )
    except TelegramBadRequest:
        pass

    await callback.answer()


@router.callback_query(F.data.startswith("queue:delete:"))
async def delete_from_queue(callback: CallbackQuery, state: FSMContext):
    file_id = callback.data.split(":")[2]

    try:
        await requests_db.delete_query_post(file_id)
        await callback.answer("Пост успешно удален из очереди")

    except Exception as e:
        print(e)
        await callback.message.answer("Ошибка удаления арта из очереди в БД")

    data = await state.get_data()
    posts = data.get("queue")

    posts = [p for p in posts if p[0] != int(file_id)]

    if not posts:
        await callback.message.edit_caption("Очередь пуста")
        await state.clear()
        await callback.answer("Удалено")
        return

    await callback.message.bot.delete_message(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id
    )
    await start_queue_view(callback.message, state)


@router.callback_query(F.data.startswith(("approve:", "reject:")))
async def handle_moderation(callback: CallbackQuery, bot: Bot):
    action, file_id, start_channel_id = callback.data.split(":")

    if action == "approve":
        try:
            await requests_db.query_approve_post(file_id, start_channel_id)

        except Exception as e:
            await callback.answer("Ошибка при занесении арта в очередь в БД")
            print(e)

    if action == "reject":
        try:
            await requests_db.query_reject_post(file_id, start_channel_id)

        except Exception as e:
            await callback.answer("Ошибка при изменении статуса арта в  БД")
            print(e)

    post = await get_next_global_post(start_channel_id)

    if not post:

        async with loading_lock:

            post = await get_next_global_post(start_channel_id)

            if not post:

                await callback.answer("Очередь закончилась. Загрузка...")

                channels = await get_channels()

                for channel_name, channel_id in channels:

                    try:
                        loaded_count = await functions_db.fetch_and_save_posts(channel_id)

                        if loaded_count == 0:
                            await callback.answer("По этим тегам ничего не найдено")
                            return

                        await callback.answer(
                            f"Успешная загрузка данных")


                    except Exception as e:
                        await callback.answer("Возникла ошибка при загрузке данных. Возможно, не заданы тэги?")
                        print(e)
                        return

                post = await get_next_global_post(start_channel_id)

        if not post:
            await callback.answer("Во всех каналах новых постов нет")
            return

    new_query_id, file, tags, post_channel_id = post

    chat = await bot.get_chat(post_channel_id)
    title = chat.title

    caption = tags or ""

    if len(caption) >= 1010:
        caption = caption[:1000 - 3] + "..."

    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=file,
                caption=f"Канал: {title}"
            ),
            reply_markup=keyboards.post_keyboard(new_query_id, post_channel_id)
        )

    except TelegramBadRequest:
        pass

    await callback.answer()


@router.message(F.text.lower() == "назад")
async def command_back_handler(message: Message, state: FSMContext) -> None:
    if message.from_user.id not in ALLOWED_IDS:
        return
    await state.clear()
    await message.answer("С чем работаем?", reply_markup=keyboards.get_main_reply_keyboard())


@router.message(Command("channels"))
@router.message(F.text.lower() == "список добавленных в рассылку каналов")
async def command_channels_handler(message: Message):
    if message.from_user.id not in ALLOWED_IDS:
        return
    channels = await requests_db.get_channels()
    if not channels:
        await message.answer("Каналы не найдены")
        return

    text = "Каналы, которые я могу администрировать:\n"
    for channel_name, channel_id in channels:
        text += f"{channel_name} ({channel_id})\n"

    await message.answer(text)


@router.message(Command("editchannel"))
@router.message(F.text.lower() == "редактировать рассылку канала")
async def command_editchannel_handler(message: Message):
    if message.from_user.id not in ALLOWED_IDS:
        return
    channels = await requests_db.get_channels()

    if not channels:
        await message.answer("Нет добавленных каналов")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=channel_name,
                    callback_data=f"editchannel:{channel_id}"
                )
            ]
            for channel_name, channel_id in channels
        ]
    )

    await message.answer("Выберите канал:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("editchannel:"))
async def channel_selected(callback: CallbackQuery):
    chat_id = callback.data.split(":")[1]
    chat_tags = await requests_db.get_channel_tags(chat_id)

    if chat_tags:
        tags = chat_tags
    else:
        tags = None

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Удалить тэги", callback_data=f"deletetags:{chat_id}")],
            [InlineKeyboardButton(text="Редактировать тэги", callback_data=f"edittags:{chat_id}")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_channels")]
        ]
    )

    await callback.message.edit_text(
        f"Выбран канал:\n{chat_id}\nСписок тэгов для канала:\n{tags}",
        reply_markup=keyboard
    )

    await callback.answer()


@router.callback_query(F.data.startswith("deletetags:"))
async def delete_tags_start(callback: CallbackQuery):
    chat_id = callback.data.split(":")[1]
    await requests_db.delete_channel_tags(chat_id)
    await requests_db.update_last_post_id(None, chat_id)

    await callback.message.edit_text(
        f"Тэги для канала {chat_id}\n удалены"
    )

    await callback.answer()


@router.callback_query(F.data.startswith("edittags:"))
async def edit_tags_start(callback: CallbackQuery, state: FSMContext):
    chat_id = callback.data.split(":")[1]
    chat_tags = await requests_db.get_channel_tags(chat_id)

    if chat_tags:
        tags = chat_tags
    else:
        tags = None

    await state.update_data(chat_id=chat_id)

    await callback.message.edit_text(
        f"Введите новые тэги для канала {chat_id}\n({tags})"
    )

    await state.set_state(EditTags.waiting_for_tag)
    await callback.answer()


@router.message(EditTags.waiting_for_tag, F.text)
async def process_new_tag(message: Message, state: FSMContext):
    if message.from_user.id not in ALLOWED_IDS:
        return
    tags = message.text

    data = await state.get_data()
    chat_id = data.get("chat_id")

    if not tags.isascii():
        await message.answer("Ошибка. Введите тэги на английском языке")
        await state.clear()
        return

    if not chat_id:
        await message.answer("Ошибка. Попробуйте заново")
        await state.clear()
        return

    try:
        await requests_db.insert_channel_tags(tags, chat_id)
        await requests_db.update_last_post_id(None, chat_id)

        await message.answer(f"Для канала '{chat_id}' теперь используются тэги: \n'{tags}'")

    except Exception as e:
        print("ERROR:", e)
        await message.answer("Ошибка при добавлении тэга")

    finally:
        await state.clear()


@router.callback_query(F.data == "back_to_channels")
async def back_to_channels(callback: CallbackQuery):
    channels = await requests_db.get_channels()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=channel_name,
                    callback_data=f"editchannel:{channel_id}"
                )
            ]
            for channel_name, channel_id in channels
        ]
    )

    await callback.message.edit_text("Выберите канал:", reply_markup=keyboard)
    await callback.answer()


@router.message(Command("addchannel"))
@router.message(F.text.lower() == "добавить канал")
async def command_addchannel_handler(message: Message, state: FSMContext):
    if message.from_user.id not in ALLOWED_IDS:
        return
    await message.answer("Введите id канала для добавления:")
    await state.set_state(AddForm.channel_id)


@router.message(AddForm.channel_id, F.text)
async def process_addchannel(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id not in ALLOWED_IDS:
        return
    parts = message.text.strip().split()

    if len(parts) != 1 or not parts[0].isascii():
        await message.answer("Введите id вида @channelname")
        return

    await state.update_data(channel_id=parts[0])
    data = await state.get_data()

    try:
        chat = await GetChat(chat_id=parts[0]).as_(bot)

    except Exception:
        await message.answer("Канал не найден. Проверь ID (@channelname)")
        return

    chat_id = data["channel_id"]

    try:
        bot_member = await bot.get_chat_member(parts[0], bot.id)

        if bot_member.status not in ["administrator", "creator"]:
            await message.answer("Бот не является администратором канала")
            return

    except Exception:
        await message.answer("Бот не добавлен в канал")
        return

    try:
        await requests_db.add_channels(chat.title, chat_id)
        await message.answer(f"Добавлен канал: {chat.title}. Что делаем теперь?")
        await state.clear()

    except Exception as e:
        await message.answer("Ошибка при добавлении канала")

@router.message(F.text.lower() == "установить задержку")
async def command_setdelay_handler(message: Message, state: FSMContext):
    if message.from_user.id not in ALLOWED_IDS:
        return
    await message.answer("Введите время задержки (в минутах):")
    await state.set_state(AddDelay.channel_id)


@router.message(AddDelay.channel_id, F.text)
async def process_setdelay(message: Message, state: FSMContext, bot: Bot):
    global sender_task, bot_session

    if message.from_user.id not in ALLOWED_IDS:
        return

    if not message.text.isdigit():
        await message.answer("Введите число (в минутах).")
        return

    delay = int(message.text)

    try:
        await requests_db.set_delay(delay)

        if sender_task:
            sender_task.cancel()

            try:
                await sender_task
            except asyncio.CancelledError:
                pass

        sender_task = asyncio.create_task(hourly_sender(bot_session))

        await message.answer("Задержка успешно изменена")
    except Exception as e:
        await message.answer("Ошибка при изменении задержки")

    await state.clear()

@router.message(Command("removechannel"))
@router.message(F.text.lower() == "удалить канал")
async def command_removechannel_handler(message: Message):
    if message.from_user.id not in ALLOWED_IDS:
        return
    channels = await requests_db.get_channels()

    if not channels:
        await message.answer("Нет добавленных каналов")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=channel_name,
                    callback_data=f"removechannel:{channel_id}"
                )
            ]
            for channel_name, channel_id in channels
        ]
    )

    await message.answer("Выберите канал:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("removechannel:"))
async def remove_channel_selected(callback: CallbackQuery):
    channel_id = callback.data.split(":")[1]

    try:
        await requests_db.remove_channels(channel_id)
        await callback.message.edit_text("Канал удалён")

    except Exception as e:
        await callback.message.edit_text("Ошибка при удалении")
        print("Ошибка при удалении канала:", e)

# Run the bot
async def main() -> None:
    global sender_task, bot_session
    await init_db()
    sender_task = asyncio.create_task(hourly_sender(bot_session))
    await create_session()

    try:
        await dp.start_polling(bot_session)
    finally:
        await bot_session.session.close()
        await close_session()


if __name__ == "__main__":
    asyncio.run(main())
