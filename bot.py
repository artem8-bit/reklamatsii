import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import sqlite3
import datetime
from datetime import date
from dotenv import load_dotenv
import os

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    logger.error("❌ Токен не найден! Установите переменную BOT_TOKEN")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DB_NAME = "modular_stations_complaints.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_1c_number TEXT UNIQUE,
            station_type TEXT,
            station_number TEXT,
            station_name TEXT,
            complaint_date DATE,
            manager_name TEXT,
            tech_engineer TEXT,
            ak_engineer TEXT,
            ov_engineer TEXT,
            os_engineer TEXT,
            complaint_reason TEXT,
            responsible_person TEXT,
            mso_manager TEXT,
            shmr_signed BOOLEAN DEFAULT 0,
            pnr_signed BOOLEAN DEFAULT 0,
            mso_specialist TEXT,
            specialist_on_station BOOLEAN DEFAULT 0,
            last_visit_date DATE,
            supplier_letter_sent BOOLEAN DEFAULT 0,
            customer_letter_sent BOOLEAN DEFAULT 0,
            response_deadline DATE,
            estimated_cost REAL,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# States
class ComplaintForm(StatesGroup):
    waiting_for_1c_number = State()
    waiting_for_station_type = State()
    waiting_for_station_number = State()
    waiting_for_station_name = State()
    waiting_for_manager = State()
    waiting_for_engineers = State()
    waiting_for_reason = State()
    waiting_for_responsible = State()
    waiting_for_mso_manager = State()
    waiting_for_shmr = State()
    waiting_for_pnr = State()
    waiting_for_mso_specialist = State()
    waiting_for_specialist_status = State()
    waiting_for_last_visit = State()
    waiting_for_letters_info = State()
    waiting_for_deadline = State()
    waiting_for_cost = State()

# Клавиатуры
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Новая рекламация"), KeyboardButton(text="📊 Все рекламации")],
            [KeyboardButton(text="👨‍💼 Рекламации по МСО"), KeyboardButton(text="📈 Статистика")],
            [KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True
    )

def get_station_types_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛢️ Блочные насосные станции"), KeyboardButton(text="🔥 Станции пожаротушения")],
            [KeyboardButton(text="⛽ Насосные станции для нефти"), KeyboardButton(text="💨 Газораспределительные установки")],
            [KeyboardButton(text="🌀 Компрессорные станции"), KeyboardButton(text="💧 Модульные станции водоочистки")],
            [KeyboardButton(text="⚡ Трансформаторные станции"), KeyboardButton(text="🌬️ Генераторы азота")],
            [KeyboardButton(text="🎛️ Шкафы управления"), KeyboardButton(text="📦 Блок-боксы под оборудование")],
            [KeyboardButton(text="🏭 Насосные станции большой производительности"), KeyboardButton(text="🔥 Блочно-модульные котельни")],
            [KeyboardButton(text="🏢 Административно-бытовые здания"), KeyboardButton(text="🌫️ Адсорбиционные осушители ОВХР")],
            [KeyboardButton(text="🔧 Оборудование"), KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )

def get_yes_no_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )

def get_specialist_status_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ На станции"), KeyboardButton(text="❌ Не на станции")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )

def get_engineers_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Петров А.И."), KeyboardButton(text="Сидоров В.К.")],
            [KeyboardButton(text="Козлова М.П."), KeyboardButton(text="Николаев С.Д.")],
            [KeyboardButton(text="Другой сотрудник")]
        ],
        resize_keyboard=True
    )

def get_mso_managers_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Волков Д.А."), KeyboardButton(text="Орлова Е.В.")],
            [KeyboardButton(text="Громов М.П."), KeyboardButton(text="Зайцева Т.Н.")],
            [KeyboardButton(text="Другой руководитель")]
        ],
        resize_keyboard=True
    )

def get_mso_specialists_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Белов С.К."), KeyboardButton(text="Морозова А.П.")],
            [KeyboardButton(text="Кузнецов Р.В."), KeyboardButton(text="Павлова И.С.")],
            [KeyboardButton(text="Другой специалист")]
        ],
        resize_keyboard=True
    )

# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🏭 Добро пожаловать в систему учета рекламаций модульных станций!\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
ℹ️ **Руководство по работе с ботом:**

📝 **Новая рекламация** - создание новой рекламации (16 шагов)
📊 **Все рекламации** - просмотр всех рекламаций
👨‍💼 **Рекламации по МСО** - фильтр по руководителю МСО
📈 **Статистика** - статистика по рекламациям

**Процесс создания рекламации:**
1. Номер 1С
2. Тип станции
3. Заводской номер
4. Наименование станции
5. Менеджер проекта
6. Инженеры (ТХ, АК, ОВ, ОС)
7. Причина рекламации
8. Ответственный исполнитель
9. Руководитель МСО
10. ШМР подписаны?
11. ПНР подписаны?
12. Специалист МСО
13. Специалист на станции?
14. Дата последнего визита
15. Письма поставщику/заказчику
16. Срок ответа и стоимость
"""
    await message.answer(help_text)

# Основные обработчики
@dp.message(F.text == "📝 Новая рекламация")
async def start_complaint(message: types.Message, state: FSMContext):
    await state.set_state(ComplaintForm.waiting_for_1c_number)
    await message.answer(
        "🔸 **Шаг 1 из 16**\n"
        "Введите номер рекламации согласно 1С:\n"
        "Например: *РКЛ-2024-001*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(F.text == "⬅️ Назад")
async def go_back(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=get_main_keyboard())

@dp.message(ComplaintForm.waiting_for_1c_number)
async def process_1c_number(message: types.Message, state: FSMContext):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM complaints WHERE complaint_1c_number = ?", (message.text,))
    if cursor.fetchone():
        await message.answer("❌ Рекламация с таким номером 1С уже существует. Введите другой номер:")
        conn.close()
        return
    conn.close()
    
    await state.update_data(complaint_1c_number=message.text)
    await state.set_state(ComplaintForm.waiting_for_station_type)
    await message.answer(
        "🔸 **Шаг 2 из 16**\n"
        "Выберите тип станции:",
        reply_markup=get_station_types_keyboard()
    )

@dp.message(ComplaintForm.waiting_for_station_type)
async def process_station_type(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.set_state(ComplaintForm.waiting_for_1c_number)
        await message.answer("Введите номер рекламации согласно 1С:")
        return
        
    await state.update_data(station_type=message.text)
    await state.set_state(ComplaintForm.waiting_for_station_number)
    await message.answer(
        "🔸 **Шаг 3 из 16**\n"
        "Введите заводской номер станции:",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(ComplaintForm.waiting_for_station_number)
async def process_station_number(message: types.Message, state: FSMContext):
    await state.update_data(station_number=message.text)
    await state.set_state(ComplaintForm.waiting_for_station_name)
    await message.answer(
        "🔸 **Шаг 4 из 16**\n"
        "Введите наименование станции (проектное название):"
    )

@dp.message(ComplaintForm.waiting_for_station_name)
async def process_station_name(message: types.Message, state: FSMContext):
    await state.update_data(station_name=message.text)
    await state.set_state(ComplaintForm.waiting_for_manager)
    await message.answer(
        "🔸 **Шаг 5 из 16**\n"
        "Введите ФИО менеджера проекта:",
        reply_markup=get_engineers_keyboard()
    )

@dp.message(ComplaintForm.waiting_for_manager)
async def process_manager(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.set_state(ComplaintForm.waiting_for_station_name)
        await message.answer("Введите наименование станции (проектное название):")
        return
        
    await state.update_data(manager_name=message.text)
    await state.set_state(ComplaintForm.waiting_for_engineers)
    await message.answer(
        "🔸 **Шаг 6 из 16**\n"
        "Введите ФИО инженера-проектировщика раздела *ТХ*:",
        parse_mode="Markdown",
        reply_markup=get_engineers_keyboard()
    )

@dp.message(ComplaintForm.waiting_for_engineers)
async def process_engineers(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.set_state(ComplaintForm.waiting_for_manager)
        await message.answer("Введите ФИО менеджера проекта:")
        return
        
    data = await state.get_data()
    
    if 'tech_engineer' not in data:
        await state.update_data(tech_engineer=message.text)
        await message.answer(
            "Введите ФИО инженера-проектировщика раздела *АК*:",
            parse_mode="Markdown"
        )
    elif 'ak_engineer' not in data:
        await state.update_data(ak_engineer=message.text)
        await message.answer(
            "Введите ФИО инженера-проектировщика раздела *ОВ*:",
            parse_mode="Markdown"
        )
    elif 'ov_engineer' not in data:
        await state.update_data(ov_engineer=message.text)
        await message.answer(
            "Введите ФИО инженера-проектировщика раздела *ОС*:",
            parse_mode="Markdown"
        )
    elif 'os_engineer' not in data:
        await state.update_data(os_engineer=message.text)
        await state.set_state(ComplaintForm.waiting_for_reason)
        await message.answer(
            "🔸 **Шаг 7 из 16**\n"
            "Опишите причину рекламации подробно:\n\n"
            "• Что произошло?\n"
            "• Когда обнаружено?\n" 
            "• Влияние на работу?\n"
            "• Предварительный анализ:",
            reply_markup=ReplyKeyboardRemove()
        )

@dp.message(ComplaintForm.waiting_for_reason)
async def process_reason(message: types.Message, state: FSMContext):
    await state.update_data(complaint_reason=message.text)
    await state.set_state(ComplaintForm.waiting_for_responsible)
    await message.answer(
        "🔸 **Шаг 8 из 16**\n"
        "Кто занимается вопросом? (ФИО ответственного исполнителя):",
        reply_markup=get_engineers_keyboard()
    )

@dp.message(ComplaintForm.waiting_for_responsible)
async def process_responsible(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.set_state(ComplaintForm.waiting_for_reason)
        await message.answer("Опишите причину рекламации подробно:")
        return
        
    await state.update_data(responsible_person=message.text)
    await state.set_state(ComplaintForm.waiting_for_mso_manager)
    await message.answer(
        "🔸 **Шаг 9 из 16**\n"
        "Введите ответственного руководителя *МСО* по станции:",
        parse_mode="Markdown",
        reply_markup=get_mso_managers_keyboard()
    )

@dp.message(ComplaintForm.waiting_for_mso_manager)
async def process_mso_manager(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.set_state(ComplaintForm.waiting_for_responsible)
        await message.answer("Кто занимается вопросом? (ФИО ответственного исполнителя):")
        return
        
    await state.update_data(mso_manager=message.text)
    await state.set_state(ComplaintForm.waiting_for_shmr)
    await message.answer(
        "🔸 **Шаг 10 из 16**\n"
        "Работы по *ШМР* подписаны?",
        parse_mode="Markdown",
        reply_markup=get_yes_no_keyboard()
    )

@dp.message(ComplaintForm.waiting_for_shmr)
async def process_shmr(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.set_state(ComplaintForm.waiting_for_mso_manager)
        await message.answer("Введите ответственного руководителя МСО по станции:")
        return
        
    shmr_signed = 1 if message.text == "✅ Да" else 0
    await state.update_data(shmr_signed=shmr_signed)
    await state.set_state(ComplaintForm.waiting_for_pnr)
    await message.answer(
        "🔸 **Шаг 11 из 16**\n"
        "Работы по *ПНР* подписаны?",
        parse_mode="Markdown",
        reply_markup=get_yes_no_keyboard()
    )

@dp.message(ComplaintForm.waiting_for_pnr)
async def process_pnr(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.set_state(ComplaintForm.waiting_for_shmr)
        await message.answer("Работы по ШМР подписаны?")
        return
        
    pnr_signed = 1 if message.text == "✅ Да" else 0
    await state.update_data(pnr_signed=pnr_signed)
    await state.set_state(ComplaintForm.waiting_for_mso_specialist)
    await message.answer(
        "🔸 **Шаг 12 из 16**\n"
        "Введите ФИО специалиста *МСО*, который выезжал на станцию:",
        parse_mode="Markdown",
        reply_markup=get_mso_specialists_keyboard()
    )

@dp.message(ComplaintForm.waiting_for_mso_specialist)
async def process_mso_specialist(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.set_state(ComplaintForm.waiting_for_pnr)
        await message.answer("Работы по ПНР подписаны?")
        return
        
    await state.update_data(mso_specialist=message.text)
    await state.set_state(ComplaintForm.waiting_for_specialist_status)
    await message.answer(
        "🔸 **Шаг 13 из 16**\n"
        "Специалист МСО находится на станции сейчас?",
        reply_markup=get_specialist_status_keyboard()
    )

@dp.message(ComplaintForm.waiting_for_specialist_status)
async def process_specialist_status(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.set_state(ComplaintForm.waiting_for_mso_specialist)
        await message.answer("Введите ФИО специалиста МСО, который выезжал на станцию:")
        return
        
    specialist_on_station = 1 if message.text == "✅ На станции" else 0
    await state.update_data(specialist_on_station=specialist_on_station)
    await state.set_state(ComplaintForm.waiting_for_last_visit)
    await message.answer(
        "🔸 **Шаг 14 из 16**\n"
        "Введите дату последнего визита специалиста в формате *дд.мм.гггг*:\n"
        "Например: 15.01.2024",
        parse_mode="Markdown"
    )

@dp.message(ComplaintForm.waiting_for_last_visit)
async def process_last_visit(message: types.Message, state: FSMContext):
    try:
        last_visit = datetime.datetime.strptime(message.text, "%d.%m.%Y").date()
        await state.update_data(last_visit_date=last_visit)
        await state.set_state(ComplaintForm.waiting_for_letters_info)
        await message.answer(
            "🔸 **Шаг 15 из 16**\n"
            "Письмо поставщику отправлено?",
            reply_markup=get_yes_no_keyboard()
        )
    except ValueError:
        await message.answer("❌ Неверный формат даты. Введите в формате *дд.мм.гггг*:", parse_mode="Markdown")

@dp.message(ComplaintForm.waiting_for_letters_info)
async def process_letters_info(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.set_state(ComplaintForm.waiting_for_last_visit)
        await message.answer("Введите дату последнего визита специалиста (дд.мм.гггг):")
        return
        
    data = await state.get_data()
    
    if 'supplier_letter_sent' not in data:
        supplier_sent = 1 if message.text == "✅ Да" else 0
        await state.update_data(supplier_letter_sent=supplier_sent)
        await message.answer("Письмо заказчику отправлено?")
    elif 'customer_letter_sent' not in data:
        customer_sent = 1 if message.text == "✅ Да" else 0
        await state.update_data(customer_letter_sent=customer_sent)
        await state.set_state(ComplaintForm.waiting_for_deadline)
        await message.answer(
            "🔸 **Шаг 16 из 16**\n"
            "Введите срок ответа в формате *дд.мм.гггг*:",
            parse_mode="Markdown"
        )

@dp.message(ComplaintForm.waiting_for_deadline)
async def process_deadline(message: types.Message, state: FSMContext):
    try:
        deadline = datetime.datetime.strptime(message.text, "%d.%m.%Y").date()
        await state.update_data(response_deadline=deadline)
        await state.set_state(ComplaintForm.waiting_for_cost)
        await message.answer("Введите предполагаемую стоимость решения вопроса (руб):")
    except ValueError:
        await message.answer("❌ Неверный формат даты. Введите в формате *дд.мм.гггг*:", parse_mode="Markdown")

@dp.message(ComplaintForm.waiting_for_cost)
async def process_cost(message: types.Message, state: FSMContext):
    try:
        cost = float(message.text)
        await state.update_data(estimated_cost=cost)
        data = await state.get_data()
        await save_complaint(data, message, state)
    except ValueError:
        await message.answer("❌ Введите числовое значение стоимости:")

async def save_complaint(data, message: types.Message, state: FSMContext):
    """Сохранение рекламации в БД"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO complaints (
                complaint_1c_number, station_type, station_number, station_name,
                manager_name, tech_engineer, ak_engineer, ov_engineer, os_engineer,
                complaint_reason, responsible_person, mso_manager, shmr_signed, pnr_signed,
                mso_specialist, specialist_on_station, last_visit_date,
                supplier_letter_sent, customer_letter_sent, response_deadline, 
                estimated_cost, complaint_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['complaint_1c_number'], data['station_type'], data['station_number'],
            data.get('station_name', ''), data['manager_name'], data['tech_engineer'],
            data.get('ak_engineer', ''), data.get('ov_engineer', ''), data.get('os_engineer', ''),
            data['complaint_reason'], data['responsible_person'], data['mso_manager'],
            data.get('shmr_signed', 0), data.get('pnr_signed', 0), data['mso_specialist'],
            data.get('specialist_on_station', 0), data.get('last_visit_date'),
            data.get('supplier_letter_sent', 0), data.get('customer_letter_sent', 0),
            data.get('response_deadline'), data.get('estimated_cost'), date.today()
        ))
        
        conn.commit()
        complaint_id = cursor.lastrowid
        
        summary = f"""✅ **Рекламация #{complaint_id} успешно создана!**

📋 **Основная информация:**
• Номер 1С: {data['complaint_1c_number']}
• Тип станции: {data['station_type']}
• Заводской номер: {data['station_number']}
• Наименование: {data.get('station_name', 'Не указано')}

👨‍💼 **Ответственные:**
• Менеджер: {data['manager_name']}
• ТХ: {data['tech_engineer']}
• АК: {data.get('ak_engineer', 'Не указан')}
• ОВ: {data.get('ov_engineer', 'Не указан')}
• ОС: {data.get('os_engineer', 'Не указан')}
• Исполнитель: {data['responsible_person']}
• Руководитель МСО: {data['mso_manager']}

🏭 **Работы МСО:**
• ШМР подписаны: {'✅' if data.get('shmr_signed') else '❌'}
• ПНР подписаны: {'✅' if data.get('pnr_signed') else '❌'}
• Специалист МСО: {data['mso_specialist']}
• На станции: {'✅' if data.get('specialist_on_station') else '❌'}
• Последний визит: {data.get('last_visit_date', 'Не указан')}

📮 **Коммуникация:**
• Письмо поставщику: {'✅' if data.get('supplier_letter_sent') else '❌'}
• Письмо заказчику: {'✅' if data.get('customer_letter_sent') else '❌'}
• Срок ответа: {data.get('response_deadline', 'Не указан')}

💰 **Финансы:**
• Стоимость решения: {data.get('estimated_cost', 0)} руб.

📝 **Причина:** {data['complaint_reason'][:200]}...

Статус: 🟢 Новая"""
        
        await message.answer(summary, reply_markup=get_main_keyboard())
        logger.info(f"Создана рекламация #{complaint_id}")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при сохранении: {str(e)}")
    finally:
        conn.close()
        await state.clear()

@dp.message(F.text == "📊 Все рекламации")
async def show_all_complaints(message: types.Message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT complaint_1c_number, station_type, station_name, status, mso_manager, created_at 
        FROM complaints ORDER BY created_at DESC LIMIT 10
    ''')
    complaints = cursor.fetchall()
    conn.close()
    
    if not complaints:
        await message.answer("📭 Рекламаций пока нет.")
        return
    
    response = "📊 **Последние рекламации:**\n\n"
    for comp in complaints:
        status_icon = "🟢" if comp[3] == "new" else "🟡" if comp[3] == "in_progress" else "🔴"
        response += f"{status_icon} **{comp[0]}** - {comp[1]}\n"
        response += f"   Станция: {comp[2]}\n"
        response += f"   МСО: {comp[4]}\n"
        response += f"   Дата: {comp[5][:10]}\n\n"
    
    await message.answer(response)

@dp.message(F.text == "👨‍💼 Рекламации по МСО")
async def show_mso_complaints(message: types.Message):
    await message.answer("Выберите руководителя МСО:", reply_markup=get_mso_managers_keyboard())

@dp.message(F.text.in_(["Волков Д.А.", "Орлова Е.В.", "Громов М.П.", "Зайцева Т.Н."]))
async def show_complaints_by_mso(message: types.Message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT complaint_1c_number, station_type, station_name, status, created_at 
        FROM complaints WHERE mso_manager = ? ORDER BY created_at DESC
    ''', (message.text,))
    complaints = cursor.fetchall()
    conn.close()
    
    if not complaints:
        await message.answer(f"📭 Рекламаций по МСО {message.text} не найдено.")
        return
    
    response = f"👨‍💼 **Рекламации по МСО {message.text}:**\n\n"
    for comp in complaints:
        status_icon = "🟢" if comp[3] == "new" else "🟡" if comp[3] == "in_progress" else "🔴"
        response += f"{status_icon} **{comp[0]}** - {comp[1]}\n"
        response += f"   Станция: {comp[2]}\n"
        response += f"   Дата: {comp[4][:10]}\n\n"
    
    await message.answer(response)

@dp.message(F.text == "📈 Статистика")
async def show_statistics(message: types.Message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM complaints")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'new'")
    new = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'in_progress'")
    in_progress = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'resolved'")
    resolved = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT mso_manager, COUNT(*) FROM complaints 
        GROUP BY mso_manager ORDER BY COUNT(*) DESC
    ''')
    mso_stats = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE shmr_signed = 1")
    shmr_signed = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE pnr_signed = 1")
    pnr_signed = cursor.fetchone()[0]
    
    conn.close()
    
    response = f"""📈 **Статистика рекламаций**

📊 **Общее количество:** {total}
🟢 **Новые:** {new}
🟡 **В работе:** {in_progress}
🟠 **Решены:** {resolved}

📋 **Работы:**
• ШМР подписаны: {shmr_signed}
• ПНР подписаны: {pnr_signed}

👨‍💼 **Рейтинг МСО:**
"""
    for mso, count in mso_stats:
        response += f"• {mso}: {count}\n"
    
    await message.answer(response)

@dp.message(F.text == "ℹ️ Помощь")
async def show_help(message: types.Message):
    await cmd_help(message)

async def main():
    init_db()
    logger.info("Бот для учета рекламаций модульных станций запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
