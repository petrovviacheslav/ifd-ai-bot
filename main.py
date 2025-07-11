import os
import re
import random

from telegram import Update, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    CallbackContext
)

# Конфигурация
BOT_TOKEN = os.getenv('TOKEN')
KANDINSKY_BOT_USERNAME = "kandinsky21_bot"
ARR_BAN_WORD = [
    ['конь', 'кони', 'коня', 'коней', 'богатырь', 'богатыри', 'богатырей', 'кольчуга', 'кольчуги', 'кольчуг', 'поле',
     'поля', 'полей'], ['том', 'тома', 'джери', 'мышь', 'мыши', 'кот', 'кота', 'красный', 'красного'],
    ['мужчина', 'мужчин', 'мужчины', 'мужчину', 'яблоко', 'яблок', 'море', 'морей', 'моря', 'шляпа', 'шляп', 'шляпы'],
    ['синий', 'синего', 'девушка', 'девушек', 'девушки', 'остров', 'острова', 'фильм', 'фильмы', 'фильма', 'аватар']]

BASE_DATA_DIR = "user_data"
os.makedirs(BASE_DATA_DIR, exist_ok=True)

# Глобальная переменная для текущего номера голосования
current_vote_number = 1

ADMIN_ID = int(os.getenv('ADMIN_ID'))


def get_pattern(vote_num):
    """Возвращает регулярку с запрещёнными словами"""
    current_bans = ARR_BAN_WORD[vote_num - 1]
    pattern = r'(' + '|'.join(current_bans) + ')'
    return pattern


def get_vote_dir(vote_num):
    """Возвращает путь к папке голосования"""
    return os.path.join(BASE_DATA_DIR, f"vote_{vote_num}")


# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id

    vote_dir = get_vote_dir(current_vote_number)
    os.makedirs(vote_dir, exist_ok=True)

    sub_file = os.path.join(vote_dir, "subscriptions.txt")

    with open(sub_file, "a+") as f:
        f.seek(0)
        subscribers = f.read().splitlines()
        if str(user_id) not in subscribers:
            f.write(f"{user_id}\n")

    await update.message.reply_text(
        "Добро пожаловать в захватывающее состязание талантов! Здесь вы сможете проявить свои навыки в создании промптов для генерации изображений. Ваша задача — максимально точно воспроизвести известную картину или афишу, используя бот @kandinsky21_bot.\n\n🚫 Запрещённые слова\nВнимательно изучите список запрещённых слов и их однокоренных форм. Их использование в промптах недопустимо и ваше изображение будет не принято в Битву промтов.\n\nКоманды:\n- /get_task - получить текущее задание\n- /start - основная информация")


# Обработчик команды /decrement_vote
async def decrement_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Непонятная команда!")
        return
    global current_vote_number
    if current_vote_number > 1:
        current_vote_number -= 1
        await update.message.reply_text("Голосование откачено к предыдущему!")


# Обработчик команды /get_id
async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("Ваш id: " + str(user_id))


# Обработчик команды /get_task
async def get_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    original_media = [InputMediaPhoto(
        media=open(os.path.join(BASE_DATA_DIR, "original_" + str(current_vote_number) + ".jpg"), "rb"))]
    await context.bot.send_media_group(chat_id=user_id, media=original_media)
    await context.bot.send_message(
        chat_id=user_id,
        text="Повторите данное фото через @kandinsky21_bot, не используя данные запрещённые слова: " + str(
            ', '.join(ARR_BAN_WORD[current_vote_number - 1])))


def calc_votes(vote_dir: str) -> {}:
    vote_file = os.path.join(vote_dir, "votes.txt")
    with open(vote_file, "r") as f:
        votes = f.read().splitlines()
        count_vote_each_id = {}
        for vote in votes:
            member_id, vote_id = vote.split(',')
            if vote_id in count_vote_each_id:
                count_vote_each_id[vote_id] += 1
            else:
                count_vote_each_id[vote_id] = 1
    return count_vote_each_id


# Обработчик команды /info
async def about_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /info"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Непонятная команда!")
        return

    for i in range(1, current_vote_number):
        vote_dir = get_vote_dir(i)
        count_vote_each_id = calc_votes(vote_dir)

        await context.bot.send_message(
            chat_id=user_id,
            text="Голосование #" + str(i) + ": " + str(count_vote_each_id)
        )


# Обработчик команды /set_winner
async def set_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_user_id = update.effective_user.id
    if admin_user_id != ADMIN_ID:
        await update.message.reply_text("❌ Непонятная команда!")
        return

    vote_dir = get_vote_dir(current_vote_number - 1)
    count_vote_each_id = calc_votes(vote_dir)

    nums_choose = 3
    max_vote_ID = [0] * nums_choose
    max_vote = [0] * nums_choose
    for member_id in count_vote_each_id:
        current_vote = count_vote_each_id[member_id]
        for i in range(nums_choose):
            if max_vote[i] < current_vote:
                for j in range(nums_choose - 1, i, -1):
                    max_vote_ID[j] = max_vote_ID[j - 1]
                    max_vote[j] = max_vote[j - 1]
                max_vote_ID[i] = member_id
                max_vote[i] = count_vote_each_id[member_id]

                break

    choose_text = ""
    for i in range(nums_choose):
        prompt_dir = get_vote_dir(current_vote_number - 1)
        prompt_file = os.path.join(prompt_dir, str(max_vote_ID[i]) + "_text.txt")
        with open(prompt_file, "r") as f:
            prompt = f.read()

        choose_text += "place: " + str(i) + ", id: " + str(max_vote_ID[i]) + ", count: " + str(
            max_vote[i]) + "\n" + prompt + "\n\n"

    buttons = [
        InlineKeyboardButton(f"id_{i}",
                             callback_data=f"winner_{current_vote_number - 1}_{i}")
        for i in max_vote_ID
    ]
    keyboard = InlineKeyboardMarkup([buttons])

    await context.bot.send_message(
        chat_id=admin_user_id,
        text=choose_text,
        reply_markup=keyboard
    )


async def newsletter_winner(update: Update, context: CallbackContext):
    """Обработка личного назначения победителя"""
    query = update.callback_query
    await query.answer()

    # user_id = query.from_user.id
    _, vote_num, winner_id = query.data.split("_")

    vote_dir = get_vote_dir(int(vote_num))

    # Рассылаем персонализированные голосования
    with open(os.path.join(vote_dir, "subscriptions.txt"), "r") as f:
        subscribers = f.read().splitlines()
    for user_id in subscribers:
        try:
            media = [InputMediaPhoto(media=open(os.path.join(vote_dir, str(winner_id) + "_photo.jpg"), "rb"))]

            await context.bot.send_media_group(chat_id=user_id, media=media)
            await context.bot.send_message(
                chat_id=user_id,
                text=f"В {vote_num} этапе победила данная картинка. Автора просим подойти к нашей зоне для получения приза."
            )

        except Exception as e:
            print(f"Ошибка отправки пользователю {user_id}: {e}")

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text="Сообщения разосланы. В голосовании #" + vote_num + " победил " + str(winner_id)
    )


# Обработчик всех сообщений
async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_vote_number
    message = update.message
    user_id = message.from_user.id

    if current_vote_number >= 5:
        await message.reply_text(
            "Игры на сегодня закончились! Рады были вас видеть на Itmo Family Day!")
        return

    # Проверка 1: Является ли сообщение пересланным и от нужного бота
    if 'forward_from' not in message.api_kwargs:
        await message.reply_text("❌ Упс, это не пересланное сообщение!")
        return

    if message.api_kwargs.get('forward_from').get('username') != KANDINSKY_BOT_USERNAME:
        await message.reply_text("❌ Упс, сообщение переслано не от @kandinsky21_bot!")
        return

    # Проверка 2: Есть ли картинка
    if not (message.photo or (message.document and message.document.mime_type.startswith('image/'))):
        await message.reply_text("❌ Упс, вышла ошибка, попробуйте снова. В сообщении нет изображения.")
        return

    # Проверка 3: Соответствует ли текст регулярке
    text = update.message.text or update.message.caption or ""

    if re.search(get_pattern(current_vote_number), text) or not ("Запрос:" in text):
        await update.message.reply_text("❌ Сообщение содержит запрещённые слова или не содержат текст вообще!")
        return

    vote_dir = get_vote_dir(current_vote_number)
    os.makedirs(vote_dir, exist_ok=True)
    # Удаляем предыдущие файлы пользователя
    for filename in os.listdir(vote_dir):
        if filename.startswith(f"{user_id}_"):
            try:
                os.remove(os.path.join(vote_dir, filename))
            except Exception as e:
                print(f"Ошибка удаления файла {filename}: {e}")

    # Сохранение новых данных
    try:
        # Сохраняем изображение
        if message.photo:
            photo_file = await message.photo[-1].get_file()
        else:
            photo_file = await message.document.get_file()

        # Сохраняем с фиксированным именем пользователя
        photo_path = os.path.join(vote_dir, f"{user_id}_photo.jpg")
        await photo_file.download_to_drive(photo_path)

        # Сохраняем текст, если есть
        if text:
            text_path = os.path.join(vote_dir, f"{user_id}_text.txt")
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text)

        await message.reply_text(
            "👾Изображение принято. Когда все работы будут собраны, вам будет отправлено голосование. Здесь вы сможете оценить работы других участников и выбрать наиболее похожие шедевры.")
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
        await message.reply_text("❌ Ошибка при сохранении файла")


async def start_voting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск нового голосования"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Непонятная команда!")
        return

    global current_vote_number

    vote_dir = get_vote_dir(current_vote_number)

    # Получаем все фото для текущего голосования
    all_photos = [f for f in os.listdir(vote_dir) if f.endswith("_photo.jpg")]

    if len(all_photos) < 6:
        await update.message.reply_text("Недостаточно фото для голосования (нужно минимум 5 от разных пользователей)!")
        return

    # Рассылаем персонализированные голосования
    with open(os.path.join(vote_dir, "subscriptions.txt"), "r") as f:
        subscribers = f.read().splitlines()

    original_media = [InputMediaPhoto(
        media=open(os.path.join(BASE_DATA_DIR, "original_" + str(current_vote_number) + ".jpg"), "rb"))]
    for user_id in subscribers:
        try:
            available_photos = [p for p in all_photos if p.split("_")[0] != user_id]
            selected_photos = random.sample(available_photos, min(5, len(available_photos)))

            media = [InputMediaPhoto(media=open(os.path.join(vote_dir, photo), "rb"))
                     for photo in selected_photos]

            buttons = [
                InlineKeyboardButton(f"Фото {i + 1}",
                                     callback_data=f"vote_{current_vote_number}_{selected_photos[i].split('_')[0]}")
                for i in range(len(selected_photos))
            ]
            keyboard = InlineKeyboardMarkup([buttons])

            await context.bot.send_media_group(chat_id=user_id, media=original_media)
            await context.bot.send_message(
                chat_id=user_id,
                text=f"Оригинальное фото"
            )
            await context.bot.send_media_group(chat_id=user_id, media=media)
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🗳️ Голосование #{current_vote_number} «Битва Промтов»\n\nВремя выбрать лучшего мастера промтов!\n- ознакомьтесь с работами участников\n- выберите изображение, которое максимально похоже на оригинал\n\nГолосование доступно 30 минут\n\nКаждый голос имеет значение\n- Голосование открыто для всех участников бота\n- Результаты будут объявлены после закрытия голосования",
                reply_markup=keyboard
            )

        except Exception as e:
            print(f"Ошибка отправки пользователю {user_id}: {e}")

    await update.message.reply_text(
        f"✅ Голосование #{current_vote_number} запущено!\n"
        f"Участников: {len(subscribers)}\n"
        f"Фото для выбора: {len(all_photos)}"
    )

    # Увеличиваем номер голосования
    current_vote_number += 1
    if current_vote_number < 5:
        vote_dir = get_vote_dir(current_vote_number)
        os.makedirs(vote_dir, exist_ok=True)

        # Копируем подписки из предыдущего голосования (если есть)
        prev_sub_file = os.path.join(get_vote_dir(current_vote_number - 1), "subscriptions.txt")
        if os.path.exists(prev_sub_file):
            with open(prev_sub_file, "r") as f:
                subscribers = f.read().splitlines()
            with open(os.path.join(vote_dir, "subscriptions.txt"), "w") as f:
                f.write("\n".join(subscribers))


async def handle_vote(update: Update, context: CallbackContext):
    """Обработка выбора пользователя"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    _, vote_num, chosen_user_id = query.data.split("_")
    vote_dir = get_vote_dir(int(vote_num))

    # Записываем голос
    with open(os.path.join(vote_dir, "votes.txt"), "a") as f:
        f.write(f"{user_id},{chosen_user_id}\n")

    # Убираем кнопки и подтверждаем
    await query.edit_message_text("✅ Ваш голос учтен!")


if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()

    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("get_id", get_id))
    app.add_handler(CommandHandler("get_task", get_task))
    app.add_handler(CommandHandler("start_voting", start_voting))
    app.add_handler(CommandHandler("set_winner", set_winner))
    app.add_handler(CommandHandler("info", about_members))
    app.add_handler(CommandHandler("decrement_vote", decrement_count))
    app.add_handler(MessageHandler(filters.TEXT | filters.CAPTION | filters.PHOTO, check_message))
    app.add_handler(CallbackQueryHandler(handle_vote, pattern="^vote_"))
    app.add_handler(CallbackQueryHandler(newsletter_winner, pattern="^winner_"))

    print("Бот запущен...")
    app.run_polling()
