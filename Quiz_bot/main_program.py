import asyncio
import logging
import nest_asyncio
import aiosqlite
import quiz_data_generator
import json

from aiogram import F
from aiogram.filters.command import Command
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command

nest_asyncio.apply()

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# считываем токен
#with open('config.json', 'r') as json_file:
API_TOKEN = ""#json.load(json_file).get("API_TOKEN")

# Объект бота
bot = Bot(token=API_TOKEN)
# Диспетчер
dp = Dispatcher()

DB_NAME = 'quiz_bot.db'

# получаем данные опроса
quiz_data_generator = quiz_data_generator.quiz_data_generator()
quiz_data = quiz_data_generator.quiz_data


# Запуск процесса поллинга новых апдейтов
async def main():
    await create_table()
    await dp.start_polling(bot)


# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Создаем сборщика клавиатур типа Reply
    builder = ReplyKeyboardBuilder()
    # Добавляем в сборщик одну кнопку
    builder.add(types.KeyboardButton(text="Начать игру"))
    # Прикрепляем кнопки к сообщению
    await message.answer("Добро пожаловать в квиз!", reply_markup=builder.as_markup(resize_keyboard=True))


# Хэндлер на команды /quiz
@dp.message(F.text=="Начать игру")
@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message):
    if quiz_data == None:
        await message.answer(f"Сегодня не поиграем")
    else:
        # Отправляем новое сообщение без кнопок
        await message.answer(f"Давайте начнем квиз!")
        # Запускаем новый квиз
        await new_quiz(message)


valid_callbacks = ["0", "1", "2", "3"]

@dp.callback_query(lambda callback_query: callback_query.data in valid_callbacks)
async def handle_callback_query(callback: types.CallbackQuery):
    await answer(callback)

async def answer(callback):
    current_question_index = await get_quiz_index(callback.from_user.id)
    correct_option = quiz_data[current_question_index]['correct_option']

    if callback.data == str(correct_option):
        await right_answer(callback, current_question_index, correct_option)
    else:
        await wrong_answer(callback, current_question_index, correct_option)

async def right_answer(callback, current_question_index, correct_option):
    await next_question_action(callback, True, current_question_index, correct_option)

async def wrong_answer(callback, current_question_index, correct_option):
    await next_question_action(callback, False, current_question_index, correct_option)



async def next_question_action(callback: types.CallbackQuery, is_right_question, current_question_index, correct_option):
    
    answer = quiz_data[current_question_index]['options'][int(callback.data)]
    await bot.send_message(chat_id=callback.from_user.id, text=answer)
    await remove_buttons(callback)
    await print_answer_message(callback, is_right_question, current_question_index)
    await next_step_in_questionary(callback, current_question_index, is_right_question)

async def remove_buttons(callback: types.CallbackQuery):
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )

async def print_answer_message(callback: types.CallbackQuery, is_right_question, current_question_index):
    if is_right_question:
        await callback.message.answer("Верно!")
    else:
        correct_option = quiz_data[current_question_index]['correct_option']
        await callback.message.answer(f"Неправильно. Правильный ответ: {quiz_data[current_question_index]['options'][correct_option]}")

async def next_step_in_questionary(callback: types.CallbackQuery, current_question_index, is_right_question):
    current_question_index += 1
    
    right_answers_count = await get_right_answers_count(callback.from_user.id)
    if is_right_question:
        right_answers_count += 1

    await update_quiz_progress(callback.from_user.id, current_question_index, right_answers_count)

    if current_question_index < len(quiz_data):
        # Следующий вопрос
        await get_question(callback.message, callback.from_user.id)
    else:
        # Уведомление об окончании квиза
        await callback.message.answer("Это был последний вопрос. Квиз завершен!")
        await callback.message.answer("Ваш результат " + str(right_answers_count))







async def create_table():
    # Создаем соединение с базой данных (если она не существует, то она будет создана)
    async with aiosqlite.connect('quiz_bot.db') as db:
        # Выполняем SQL-запрос к базе данных
        
        #await db.execute('''DROP TABLE IF EXISTS quiz_state''')
        #await db.execute('''ALTER TABLE quiz_state ADD right_answers_count INTEGER''')
        #await db.execute("SHOW COLUMNS FROM quiz_state")
        await db.execute('''CREATE TABLE IF NOT EXISTS quiz_state (user_id INTEGER PRIMARY KEY, question_index INTEGER, right_answers_count INTEGER)''')
        # Сохраняем изменения
        await db.commit()

async def update_quiz_progress(user_id, index, right_answers_count):
    # Создаем соединение с базой данных (если она не существует, она будет создана)
    async with aiosqlite.connect(DB_NAME) as db:
        # Вставляем новую запись или заменяем ее, если с данным user_id уже существует
        await db.execute('INSERT OR REPLACE INTO quiz_state (user_id, question_index, right_answers_count) VALUES (?, ?, ?)', (user_id, index, right_answers_count))
        # Сохраняем изменения
        await db.commit()

async def get_quiz_index(user_id):
     # Подключаемся к базе данных
     async with aiosqlite.connect(DB_NAME) as db:
        # Получаем запись для заданного пользователя
        async with db.execute('SELECT question_index FROM quiz_state WHERE user_id = (?)', (user_id, )) as cursor:
            # Возвращаем результат
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0
            
async def get_right_answers_count(user_id):
     # Подключаемся к базе данных
     async with aiosqlite.connect(DB_NAME) as db:
        # Получаем запись для заданного пользователя
        async with db.execute('SELECT right_answers_count FROM quiz_state WHERE user_id = (?)', (user_id, )) as cursor:
            # Возвращаем результат
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0





async def new_quiz(message):
    # получаем id пользователя, отправившего сообщение
    user_id = message.from_user.id
    # сбрасываем значение текущего индекса вопроса квиза в 0

    current_question_index = await get_quiz_index(user_id)
    right_answers_count = await get_right_answers_count(user_id)

    if current_question_index >= len(quiz_data):
        current_question_index = 0
        right_answers_count = 0

    await update_quiz_progress(user_id, current_question_index, right_answers_count)

    # запрашиваем новый вопрос для квиза
    await get_question(message, user_id)

async def get_question(message, user_id):

    # Запрашиваем из базы текущий индекс для вопроса
    current_question_index = await get_quiz_index(user_id)
    # Получаем индекс правильного ответа для текущего вопроса

    correct_index = quiz_data[current_question_index]['correct_option']
    # Получаем список вариантов ответа для текущего вопроса
    opts = quiz_data[current_question_index]['options']

    # Функция генерации кнопок для текущего вопроса квиза
    # В качестве аргументов передаем варианты ответов и значение правильного ответа
    kb = generate_options_keyboard(opts, correct_index)
    # Отправляем в чат сообщение с вопросом, прикрепляем сгенерированные кнопки
    await message.answer(f"{quiz_data[current_question_index]['question']}", reply_markup=kb)


def generate_options_keyboard(answer_options, correct_index):
  # Создаем сборщика клавиатур типа Inline
    builder = InlineKeyboardBuilder()

    # В цикле создаем 4 Inline кнопки, а точнее Callback-кнопки
    for option in answer_options:
        builder.add(types.InlineKeyboardButton(
            # Текст на кнопках соответствует вариантам ответов
            text=option,
            
            callback_data=str(answer_options.index(option)))
            
        ) 

    builder.adjust(1)
    return builder.as_markup()


if __name__ == "__main__":
    asyncio.run(main())
