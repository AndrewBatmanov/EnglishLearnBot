from bot import bot

if __name__ == '__main__':
    print("Бот запущен!")
    bot.infinity_polling(skip_pending=True)