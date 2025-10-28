import random
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from database import Database
from parameters import BOT_TOKEN

if not BOT_TOKEN:
    print("❌ ОШИБКА: Токен бота не найден!")
    exit(1)

db = Database()
bot = TeleBot(BOT_TOKEN, state_storage=StateMemoryStorage())

buttons = []


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    adding_word = State()
    deleting_word = State()


@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    cid = message.chat.id

    try:
        user_id = db.get_or_create_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name
        )

        word_data = db.get_random_word(user_id)
        if not word_data:
            bot.send_message(cid, "В базе данных нет слов для изучения.")
            return

        word_id, russian_word, english_word, source = word_data

        wrong_options = db.get_wrong_options(english_word, 3)
        all_options = wrong_options + [english_word]
        random.shuffle(all_options)

        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        global buttons
        buttons = []

        for option in all_options:
            buttons.append(types.KeyboardButton(option))

        buttons.extend([
            types.KeyboardButton(Command.NEXT),
            types.KeyboardButton(Command.ADD_WORD),
            types.KeyboardButton(Command.DELETE_WORD)
        ])

        markup.add(*buttons)

        bot.send_message(
            message.chat.id,
            f"Выберите правильный перевод слова:\n🇷🇺 {russian_word}",
            reply_markup=markup
        )

        bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['target_word'] = english_word
            data['translate_word'] = russian_word

    except Exception as e:
        print(f"Ошибка: {e}")
        bot.send_message(cid, "Неправильно:( Попробуйте снова!")


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    bot.send_message(
        message.chat.id,
        "Введите слово в формате: русское - английское\nНапример: машина - car",
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.set_state(message.from_user.id, MyStates.adding_word, message.chat.id)


@bot.message_handler(state=MyStates.adding_word)
def process_add_word(message):
    user_id = db.get_or_create_user(message.from_user.id)

    if message.text.lower() == 'отмена':
        bot.delete_state(message.from_user.id, message.chat.id)
        create_cards(message)
        return

    try:
        if ' - ' in message.text:
            russian_word, english_word = message.text.split(' - ', 1)
            russian_word = russian_word.strip()
            english_word = english_word.strip()

            if russian_word and english_word:
                word_id = db.add_user_word(user_id, russian_word, english_word)
                if word_id:
                    bot.send_message(message.chat.id, f"✅ Слово '{russian_word} - {english_word}' добавлено!")
                else:
                    bot.send_message(message.chat.id, "❌ Ошибка при добавлении слова")
        else:
            bot.send_message(message.chat.id, "Используйте формат: русское - английское")

    except Exception as e:
        bot.send_message(message.chat.id, "❌ Ошибка при обработке")

    bot.delete_state(message.from_user.id, message.chat.id)
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    user_id = db.get_or_create_user(message.from_user.id)
    user_words = db.get_user_words(user_id)

    if not user_words:
        bot.send_message(message.chat.id, "У вас пока нет пользовательских слов для удаления.")
        return

    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for word_id, russian, english in user_words:
        markup.add(types.KeyboardButton(f"{russian} - {english}"))
    markup.add(types.KeyboardButton("Отмена"))

    bot.send_message(message.chat.id, "Выберите слово для удаления:", reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.deleting_word, message.chat.id)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['user_words'] = user_words


@bot.message_handler(state=MyStates.deleting_word)
def process_delete_word(message):
    user_id = db.get_or_create_user(message.from_user.id)

    if message.text == "Отмена":
        bot.delete_state(message.from_user.id, message.chat.id)
        create_cards(message)
        return

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        user_words = data.get('user_words', [])

    # Ищем слово для удаления
    for word_id, russian, english in user_words:
        if f"{russian} - {english}" == message.text:
            if db.delete_user_word(user_id, word_id):
                bot.send_message(message.chat.id, f"✅ Слово удалено!")
            else:
                bot.send_message(message.chat.id, "❌ Ошибка при удалении")
            break
    else:
        bot.send_message(message.chat.id, "❌ Слово не найдено")

    bot.delete_state(message.from_user.id, message.chat.id)
    create_cards(message)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text

    if text in [Command.NEXT, Command.ADD_WORD, Command.DELETE_WORD]:
        return

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if 'target_word' not in data:
            create_cards(message)
            return

        target_word = data['target_word']
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

        if text == target_word:
            hint = f"✅ Правильно!\n{data['target_word']} -> {data['translate_word']}"

            global buttons
            new_buttons = []
            for btn in buttons:
                if btn.text == text:
                    new_buttons.append(types.KeyboardButton(btn.text + ' ✅'))
                elif btn.text not in [Command.NEXT, Command.ADD_WORD, Command.DELETE_WORD]:
                    new_buttons.append(btn)

            new_buttons.extend([
                types.KeyboardButton(Command.NEXT),
                types.KeyboardButton(Command.ADD_WORD),
                types.KeyboardButton(Command.DELETE_WORD)
            ])
            buttons = new_buttons

        else:
            hint = f"❌ Ошибка!\nПопробуйте ещё раз: 🇷🇺{data['translate_word']}"

            # Обновляем кнопки
            new_buttons = []
            for btn in buttons:
                if btn.text == text:
                    new_buttons.append(types.KeyboardButton(btn.text + ' ❌'))
                elif btn.text not in [Command.NEXT, Command.ADD_WORD, Command.DELETE_WORD]:
                    new_buttons.append(btn)

            new_buttons.extend([
                types.KeyboardButton(Command.NEXT),
                types.KeyboardButton(Command.ADD_WORD),
                types.KeyboardButton(Command.DELETE_WORD)
            ])
            buttons = new_buttons

    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)


@bot.message_handler(func=lambda message: True)
def handle_any_message(message):
    """Обрабатывает любые сообщения и предлагает начать"""
    if message.text and message.text.startswith('/'):
        return

    if message.text in [Command.NEXT, Command.ADD_WORD, Command.DELETE_WORD]:
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    start_btn = types.KeyboardButton('/start')
    markup.add(start_btn)

    bot.send_message(
        message.chat.id,
        "👋 Привет! Я бот для изучения английских слов.\n\n"
        "Нажмите кнопку ниже, чтобы начать обучение!",
        reply_markup=markup
    )


bot.add_custom_filter(custom_filters.StateFilter(bot))

if __name__ == '__main__':
    print("✅ Бот запущен! Отправьте /start")
    bot.infinity_polling(skip_pending=True)