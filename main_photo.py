import os
import random
from aiogram import Bot
from aiogram import Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium_stealth import stealth
from selenium.webdriver.common.by import By
import time
import sqlite3
from pyqiwip2p import QiwiP2P
import datetime
import requests
from webdriver_manager.chrome import ChromeDriverManager


storage = MemoryStorage()

options = webdriver.ChromeOptions()
# options.add_argument('headless')
options.add_argument("start-maximized")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36")
extension_path = "extension_1_3_0_0.crx"
options.add_extension(extension_path)
# extension_path = "extension_2_2_2_0.crx"
# options.add_extension(extension_path)


# Токен бота
TOKEN = ""
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=storage)

# ////////////////////////////////////////////////////////////////////////////////////////////////////////////////
# https://qiwi.com/api
api_access_token = ''
# Номер телефона кивиса
my_login = ''
rows_num = "30"
# https://qiwi.com/p2p-admin/transfers/api
SECRET_KEY = ''
p2p = QiwiP2P(auth_key=SECRET_KEY)
# /////////////////////////////////////////////////////////////////////////////////////////////////////////////////

# Пароль и почта от сайта РЭШ
email = ""
password = ""

# Абсолютный путь до chromedriver.exe
path = ""
# Цена за подписку
price = 300

def payment_history_last(my_login, api_access_token, rows_num):
    s = requests.Session()
    s.headers['authorization'] = 'Bearer ' + api_access_token
    parameters = {'rows': rows_num}
    h = s.get('https://edge.qiwi.com/payment-history/v2/persons/' + my_login + '/payments', params = parameters)
    return h.json()


def updateEgeAnswers(user_id):
    cur.execute(f"UPDATE ids SET ege_data='0' WHERE id={user_id}")
    conn.commit()


def writeEgeData(user_id, data):
    cur.execute(f"UPDATE ids SET ege_data='{data}' WHERE id={user_id}")
    conn.commit()


def createPayForPerson(user_id, sum, comment):
    cur.execute(f"INSERT INTO payment_query (user_id, sum, comment) VALUES({user_id}, {sum}, {comment})")
    conn.commit()


def update_previous(user_id, sum, comment):
    cur.execute(f"UPDATE payment_query SET sum={sum} WHERE user_id={user_id}")
    cur.execute(f"UPDATE payment_query SET comment={comment} WHERE user_id={user_id}")
    conn.commit()


def take_price_and_comment(user_id):
    count = cur.execute(f"SELECT * FROM payment_query WHERE user_id={int(user_id)}").fetchone()
    return count


def giveSubscribe(user_id, date):
    date = str(date)[:10]
    cur.execute(f"UPDATE ids SET date_subscribe='{date}' WHERE id={user_id}")
    conn.commit()


def getDateSubscribe(user_id):
    date_subscribe = cur.execute(f"SELECT date_subscribe FROM ids WHERE id={int(user_id)}").fetchone()[0]
    return date_subscribe


def takeDataForEge():
    count = cur.execute(f"SELECT * FROM ids WHERE ege_data!='0'").fetchall()
    return count


b1 = KeyboardButton('Решить тест')
b2 = KeyboardButton('Отмена')
b3 = KeyboardButton("Рассылка")
b4 = KeyboardButton("Оплатить подписку")
b5 = KeyboardButton("Проверить оплату")
b6 = KeyboardButton("Отменить оплату")
b7 = KeyboardButton("Решить ЕГЭ")
b8 = KeyboardButton("Просмотреть запросы на ЕГЭ")
b9 = KeyboardButton("Отправить ответы")
b10 = KeyboardButton("Авторешение ЕГЭ")

kb_client = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(b1).add(b4).row(b7, b10)
kb_client_cancel = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(b2)
kb_admin = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(b1).add(b3).add(b8).add(b9)
kb_client_pay = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(b5).add(b6)

# wallet = QiwiWrapper(
#     phone_number="+79373010140",
#     api_access_token="",
#     secret_p2p=""
# )

async def on_startup(_):
    print("Bot is online!")
    global conn, cur
    conn = sqlite3.connect('data_base.db')
    cur = conn.cursor()

# IDS = [1355326155, 2006765935]
IDS = [1355326155]

class FSMAnswers(StatesGroup):
    link = State()


class FSMSpam(StatesGroup):
    text = State()


class FSMAnswersEge(StatesGroup):
    link = State()


class FSMSendAnswers(StatesGroup):
    id = State()
    document = State()


async def cm_start_answers(message: types.Message):
    if message.from_user.id in IDS:
        await FSMSendAnswers.id.set()
        await bot.send_message(message.from_user.id, "Напишите id человека, которому хотите отправить ответы.", reply_markup=kb_client_cancel)


async def cm_middle_answers(message: types.Message, state: FSMContext):
    result = cur.execute('''SELECT id FROM ids WHERE ege_data!="0"''').fetchall()
    q = []
    for i in result:
        q.append(i[0])
    try:
        if int(message.text) in q:
            async with state.proxy() as data:
                data['id'] = message.text
            await FSMSendAnswers.next()
            await bot.send_message(message.from_user.id, "Отправьте фото с ответами", reply_markup=kb_client_cancel)
        else:
            await bot.send_message(message.from_user.id, "У этого пользователя нет запросов!", reply_markup=kb_admin)
            await state.finish()
    except Exception as E:
        await bot.send_message(message.from_user.id, "У этого пользователя нет запросов!", reply_markup=kb_admin)
        await state.finish()


@dp.message_handler(content_types=['photo', "text"], state=FSMSendAnswers.document)
async def load_file_answers(message: types.Message, state: FSMContext):
    try:
        if message.content_type == "photo":
            async with state.proxy() as data:
                await bot.send_photo(int(data['id']), message.photo[-1].file_id, caption=message.caption, reply_markup=kb_client)
                updateEgeAnswers(int(data['id']))
                for i in IDS:
                    await bot.send_message(i, "Успешно", reply_markup=kb_admin)
                await state.finish()
        else:
            async with state.proxy() as data:
                await bot.send_message(int(data['id']), message.text, reply_markup=kb_client)
                for i in IDS:
                    await bot.send_message(i, "Успешно", reply_markup=kb_admin)
                await state.finish()
    except Exception as E:
        for i in IDS:
            await bot.send_message(i, "Что-то пошло не по плану...", reply_markup=kb_admin)



async def send_requests(message: types.Message):
    if message.from_user.id in IDS:
        try:
            result = takeDataForEge()
            if len(result) == 0:
                await bot.send_message(message.from_user.id, "Нет никаких запросов!")
            elif len(result) == 5:
                await bot.send_message(message.from_user.id, f"У человека с id {result[0]} появился запрос:\n{result[-1]}")
            else:
                for item in result:
                    await bot.send_message(message.from_user.id, f"У человека с id {item[0]} появился запрос:\n{item[-1]}")
        except Exception as E:
            await bot.send_message(message.from_user.id, "Нет никаких запросов!")


async def cm_start_ege(message: types.Message):
    if message.from_user.id in IDS:
        await FSMAnswersEge.link.set()
        await message.reply('Напишите:\n1. Ссылка на вариант\n2. Класс\n3. Школа\n4. Место проживания', reply_markup=kb_client_cancel)
    elif getDateSubscribe(message.from_user.id) != "0":
        data_sub = getDateSubscribe(message.from_user.id).split("-")
        data_sub = datetime.datetime(year=int(data_sub[0]), month=int(data_sub[1]), day=int(data_sub[2]))
        if data_sub > datetime.datetime.now() - datetime.timedelta(days=30):
            await FSMAnswersEge.link.set()
            await message.reply('Напишите:\n1. Ссылка на вариант\n2. Класс\n3. Школа\n4. Место проживания', reply_markup=kb_client_cancel)
        else:
            await message.reply('Продлите доступ к ответам!', reply_markup=kb_client)
    else:
        await message.reply('Купите доступ к ответам!', reply_markup=kb_client)


async def cm_start_auto_ege(message: types.Message):
    if message.from_user.id in IDS:
        await FSMAnswersEge.link.set()
        await message.reply('Напишите:\n1. Ссылка на тест\n2. Логин\n3. Пароль\n4. Время решения(через сколько тест отправится учителю)\n5. Кол-во ошибок', reply_markup=kb_client_cancel)
    elif getDateSubscribe(message.from_user.id) != "0":
        data_sub = getDateSubscribe(message.from_user.id).split("-")
        data_sub = datetime.datetime(year=int(data_sub[0]), month=int(data_sub[1]), day=int(data_sub[2]))
        if data_sub > datetime.datetime.now() - datetime.timedelta(days=30):
            await FSMAnswersEge.link.set()
            await message.reply('Напишите:\n1. Ссылка на тест\n2. Логин\n3. Пароль\n4. Время решения(через сколько тест отправится учителю)\n5. Кол-во ошибок', reply_markup=kb_client_cancel)
        else:
            await message.reply('Продлите доступ к ответам!', reply_markup=kb_client)
    else:
        await message.reply('Купите доступ к ответам!', reply_markup=kb_client)


async def cm_start_test(message: types.Message):
    if message.from_user.id in IDS:
        await FSMAnswers.link.set()
        await message.reply('Впишите ссылку на тест', reply_markup=kb_client_cancel)
    elif getDateSubscribe(message.from_user.id) != "0":
        data_sub = getDateSubscribe(message.from_user.id).split("-")
        data_sub = datetime.datetime(year=int(data_sub[0]), month=int(data_sub[1]), day=int(data_sub[2]))
        if data_sub > datetime.datetime.now() - datetime.timedelta(days=30):
            await FSMAnswers.link.set()
            await message.reply('Впишите ссылку на тест', reply_markup=kb_client_cancel)
        else:
            await message.reply('Продлите доступ к ответам!', reply_markup=kb_client)
    else:
        await message.reply('Купите доступ к ответам!', reply_markup=kb_client)


async def cm_start_spam(message: types.Message):
    if message.from_user.id in IDS:
        await FSMSpam.text.set()
        await message.reply('Что вы хотите всем отослать?', reply_markup=kb_client_cancel)


async def cm_start_subscribe(message: types.Message):
    await message.reply(f'Цена подписки на 1 месяц - {price} рубей. Оплата киви.')
    user_id = message.from_user.id
    lifetime = 60  # Время действия ссылки
    comment = random.randint(99999, 99999999999999)  # Комментарий к платежу, может быть абсолютно любым
    new_check = p2p.bill(amount=price, lifetime=lifetime, comment=comment)  # Создаем счет
    if take_price_and_comment(message.from_user.id) is None:
        createPayForPerson(user_id, price, comment)
    else:
        update_previous(user_id, price, comment)
    await bot.send_message(message.from_user.id,
                     f'К оплате {price}. Оплатите по этой ссылке, в комментарии оставьте {comment}\n{new_check.pay_url}',
                     reply_markup=kb_client_pay)


async def check_subscribe(message: types.Message):
    profile = payment_history_last(my_login, api_access_token, rows_num)
    pay = False

    # giveSubscribe(message.from_user.id, message.date)
    # await bot.send_message(message.from_user.id, f'Вы получили доступ к ответам!', reply_markup=kb_client)

    try:
        for i in range(20):
            if profile['data'][i]['sum']['amount'] == take_price_and_comment(message.from_user.id)[3] and int(
                    profile['data'][i]['comment']) == int(take_price_and_comment(message.from_user.id)[4]):
                # тут получение или обновление доступа
                giveSubscribe(message.from_user.id, message.date)
                await bot.send_message(message.from_user.id, f'Вы получили доступ к ответам!',
                                 reply_markup=kb_client)
                pay = True
                break
        if not pay:
            await bot.send_message(message.from_user.id,
                             'Вы ещё не оплатили или нажмите проверить платеж через пару секунд!',
                             reply_markup=kb_client_pay)
    except Exception as e:
        await bot.send_message(message.from_user.id, 'Вы ещё не оплатили или нажмите проверить платеж через пару секунд!',
                         reply_markup=kb_client_pay)



async def load_spam(message: types.Message, state: FSMContext):
    result = cur.execute('''SELECT id FROM ids''').fetchall()
    q = []
    for i in result:
        q.append(i[0])

    if message.content_type == "photo":
        for user in q:
            try:
                if user not in IDS:
                    await bot.send_photo(user, message.photo[-1].file_id, caption=message.caption, reply_markup=kb_client)
            except Exception as E:
                pass
    else:
        for user in q:
            try:
                if user not in IDS:
                    await bot.send_message(user, message.text, reply_markup=kb_client)
            except Exception as E:
                pass
    await bot.send_message(message.from_user.id, "Отослал!", reply_markup=kb_admin)
    await state.finish()


async def load_text_ege(message: types.Message, state: FSMContext):
    try:
        data = message.text
        writeEgeData(message.from_user.id, data)
        await bot.send_message(message.from_user.id, "Мы приняли ваши данные. Ответы будут высланы в скором времени.", reply_markup=kb_client)
    except Exception as E:
        await bot.send_message(message.from_user.id, "Повторите попытку!", reply_markup=kb_client)
    await state.finish()




async def load_text_en(message: types.Message, state: FSMContext):
    try:
        # os.environ.get("CHROMEDRIVER_PATH")
        data = message.text
        driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
        stealth(driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
                )


        driver.get(data)



        # driver.execute_script("window.postMessage('clicked_browser_action', '*')")
        time.sleep(2)
        await bot.send_message(message.from_user.id, "Начинаем обработку.", reply_markup=ReplyKeyboardRemove())

        button_ok = driver.find_element(By.CLASS_NAME, "swal2-confirm").click()

        login = driver.find_element(By.CLASS_NAME, "header__login").find_element(By.TAG_NAME, "a").click()
        email_input = driver.find_elements(By.CLASS_NAME, "menu-slide__form-row")[0].find_element(By.CLASS_NAME, "menu-slide__input-text")
        email_input.clear()
        email_input.send_keys(email)
        password_input = driver.find_elements(By.CLASS_NAME, "menu-slide__form-row")[1].find_element(By.CLASS_NAME, "menu-slide__input-text")
        password_input.clear()
        password_input.send_keys(password)

        button_submit = driver.find_element(By.CLASS_NAME, "form-submit").click()

        time.sleep(1.5)
        tasks_to_delete = []
        count_of_tasks = int(driver.find_element(By.XPATH, "/html/body/div[2]/div/main/div[1]/div[3]/div/div[2]/div/div/ul").find_elements(By.TAG_NAME, "li")[-1].find_element(By.TAG_NAME, "b").text)
        # driver.execute_script("document.body.style.zoom='80%'")
        # Скрыть интерфейс
        # driver.find_element(By.XPATH, '//*[@id="reshAnswers__block1"]/div/a[3]').click()
        for task in range(int(data.split('/')[-2].replace("/", "").replace("#", '')), int(data.split('/')[-2].replace("/", "").replace("#", '')) + count_of_tasks):
            # driver.get(data[:int(data.index("#"))] + str(task))
            time.sleep(1)
            block = driver.find_element(By.CLASS_NAME, 'test__buttons-line').find_elements(By.TAG_NAME, "a")[-1].click()
            time.sleep(1)
            screenshot = driver.save_screenshot(f'task_number_{task}.png')
            time.sleep(1)
            tasks_to_delete.append(f'task_number_{task}.png')
            if int(data.split('/')[-2].replace("/", "").replace("#", '')) + count_of_tasks != task + 1:
                driver.find_element(By.CLASS_NAME, 'js-go-to-next-test-btn').click()
            await bot.send_photo(message.from_user.id, open(f'task_number_{task}.png', 'rb'), reply_markup=ReplyKeyboardRemove())
        await bot.send_message(message.from_user.id, "Готово!", reply_markup=kb_client)
        for task in tasks_to_delete:
            os.remove(task)
        driver.quit()
    except Exception as E:
        await bot.send_message(message.from_user.id, "Что-то пошло не по плану :(", reply_markup=kb_client)
    await state.finish()


async def command_start(message: types.Message):
    result = cur.execute('''SELECT id FROM ids''').fetchall()
    q = []
    for i in result:
        q.append(i[0])
    if message.from_user.id not in q:
        cur.execute("INSERT INTO ids (id, date) VALUES(?, ?)", (int(message.from_user.id), message.date))
        conn.commit()

    if message.from_user.id not in IDS:
        await bot.send_message(message.from_user.id, "Добро Пожаловать", reply_markup=kb_client)
    else:
        await bot.send_message(message.from_user.id, "Добро Пожаловать Командир!", reply_markup=kb_admin)
    await message.delete()


async def cancel_handler(message: types.Message, state: FSMContext):
    try:
        current_state = await state.get_state()
        if current_state is None:
            return
        await state.finish()
        if message.from_user.id in IDS:
            await message.reply('OK', reply_markup=kb_admin)
        else:
            await message.reply('OK', reply_markup=kb_client)
    except Exception as E:
        await message.reply('OK', reply_markup=kb_client)


async def cancel_payment(message: types.Message):
    await message.reply('OK', reply_markup=kb_client)

def register_handlers_admin(dp: Dispatcher):
    dp.register_message_handler(command_start, commands=["start", "help"])
    dp.register_message_handler(cancel_handler, Text(equals='Отмена', ignore_case=True), state="*")
    dp.register_message_handler(cm_start_test, Text(equals='Решить тест', ignore_case=True), state=None)
    dp.register_message_handler(cm_start_ege, Text(equals='Решить ЕГЭ', ignore_case=True), state=None)
    dp.register_message_handler(cm_start_auto_ege, Text(equals='Авторешение ЕГЭ', ignore_case=True), state=None)
    dp.register_message_handler(cm_start_spam, Text(equals='Рассылка', ignore_case=True), state=None)
    dp.register_message_handler(cm_start_subscribe, Text(equals='Оплатить подписку', ignore_case=True))
    dp.register_message_handler(check_subscribe, Text(equals='Проверить оплату', ignore_case=True))
    dp.register_message_handler(cancel_payment, Text(equals='Отменить оплату', ignore_case=True))
    dp.register_message_handler(send_requests, Text(equals='Просмотреть запросы на ЕГЭ', ignore_case=True))
    dp.register_message_handler(cm_start_answers, Text(equals='Отправить ответы', ignore_case=True), state=None)
    # dp.register_message_handler(load_file_answers, content_types=['file'], state=FSMSendAnswers.document)
    dp.register_message_handler(cm_middle_answers, state=FSMSendAnswers.id)
    dp.register_message_handler(load_text_en, state=FSMAnswers.link)
    dp.register_message_handler(load_spam, content_types=['photo', "text", "video"], state=FSMSpam.text)
    dp.register_message_handler(load_text_ege, state=FSMAnswersEge.link)


register_handlers_admin(dp)
executor.start_polling(dp, skip_updates=True, on_startup=on_startup)