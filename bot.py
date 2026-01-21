# bot.py
import os
import logging
import json
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === НАСТРОЙКИ ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPERATOR_CHAT_ID = os.getenv("OPERATOR_CHAT_ID")  # Ваш Telegram ID
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

logging.basicConfig(level=logging.INFO)

# === GOOGLE SHEETS ===
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("DVSferra_Заявки").sheet1
    return sheet

# === КНОПКИ ===
MAIN_MENU = [
    ["🔍 Найти услугу", "💼 Стать исполнителем"],
    ["🎟️ Афиша Приморья", "📞 Поддержка"]
]

CATEGORIES_PAGE_1 = [
    ["👶 Детские услуги", "💻 Для Бизнеса/IT"],
    ["🍔 Еда/Продукты", "🐾 Животные"],
    ["🧼 Клининг/Химчистка", "🛋️ Мебель"],
    ["🩺 Медицина/Врачи", "🎓 Обучение/Курсы"],
    ["➡️ 2/4", "➕ Нет нужного? - Добавьте"]
]

CATEGORIES_PAGE_2 = [
    ["🚗 Авто/мото услуги", "🚌 Автобусы/Область"],
    ["⚖️ Адвокаты/Юристы", "🔑 Аренда/Прокат"],
    ["✂️ Ателье/Швея", "🔧 Быт.услуги/Ремонт"],
    ["🛍️ Бьюти Сфера", "🚚 Грузоперевозки"],
    ["⬅️ 1/4", "➡️ 3/4"],
    ["➕ Нет нужного? - Добавьте"]
]

PET_SUBCATEGORIES = [
    ["🏥 Ветеринары", "🛁 Груминг"],
    ["🐶 Зооняни", "🐱 Кинологи"],
    ["📦 Передержка", "➕ Добавить услугу"],
    ["⬅️ Назад", "🏠 Главное меню"]
]

CITIES = ["Владивосток", "Находка", "Артём", "Уссурийск", "Другой город Приморья"]

# === СОСТОЯНИЯ ===
user_state = {}

# === ОБРАБОТЧИКИ ===
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Привет! Я бот *PrimorService* — ваш агент по услугам во Владивостоке и Приморье!\n\n"
        "Выберите действие:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)
    )

def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text

    if text == "🔍 Найти услугу":
        show_categories_page_1(update, context)
        user_state[user_id] = "choosing_service"

    elif text == "💼 Стать исполнителем":
        buttons = [[city] for city in CITIES]
        update.message.reply_text(
            "Выберите ваш город:",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        user_state[user_id] = "choosing_city"

    elif text == "📞 Поддержка":
        update.message.reply_text("Напишите нам: @dvsferra_support")

    elif text == "🎟️ Афиша Приморья":
        update.message.reply_text(
            "🎉 *Афиша Приморья*\n\n"
            "🔥 Горячие предложения:\n"
            "• Эвакуатор — от 1 500 ₽ (Владивосток)\n"
            "• Мини-экскаватор — 2 000 ₽/час\n"
            "• Доставка авто из Японии — скидка 5% при заказе через бота\n\n"
            "Следите за обновлениями в @jpcn_auto!",
            parse_mode="Markdown"
        )

    elif text == "➡️ 2/4":
        show_categories_page_2(update, context)
    elif text == "⬅️ 1/4":
        show_categories_page_1(update, context)
    elif text == "➡️ 3/4":
        update.message.reply_text("📌 Пока доступны только 2 страницы. Добавлю больше в следующем обновлении!")
    elif text == "⬅️ 2/4":
        show_categories_page_1(update, context)

    elif text == "➕ Нет нужного? - Добавьте":
        update.message.reply_text("📩 Укажите, какую услугу вы хотите добавить — мы рассмотрим её и включим в список!")
        user_state[user_id] = "adding_service"

    elif text == "🐾 Животные":
        update.message.reply_text(
            "Выберите конкретную услугу для животных:",
            reply_markup=ReplyKeyboardMarkup(PET_SUBCATEGORIES, resize_keyboard=True)
        )
        user_state[user_id] = "choosing_pet_service"

    elif user_state.get(user_id) == "choosing_pet_service" and any(text in cat for cat in PET_SUBCATEGORIES):
        service = text
        context.user_data["service"] = service
        has_providers = False
        if not has_providers:
            message = (
                "❌ К сожалению, в данный момент нет доступных исполнителей для выбранной услуги в вашем городе.\n\n"
                "💡 Попробуйте посмотреть в соседних городах — возможно, они есть там!\n\n"
                "🤝 Давайте сделаем сервис лучше! Если вы знаете человека, который выполняет эту услугу, отправьте ему ссылку на бота (нажмите на имя бота вверху — ссылка скопируется).\n\n"
                "🛠️ Если вы сами оказываете данную услугу, нажмите 'Стать исполнителем' в Главном Меню."
            )
            update.message.reply_text(
                message,
                reply_markup=ReplyKeyboardMarkup([["⬅️ Назад", "🏠 Главное меню"]], resize_keyboard=True)
            )
        else:
            update.message.reply_text(f"Вы выбрали: *{service}*\n\nНапишите подробности (адрес, дата, пожелания):", parse_mode="Markdown")
            user_state[user_id] = "entering_details"

    elif text == "⬅️ Назад" and user_state.get(user_id) == "choosing_pet_service":
        show_categories_page_1(update, context)
        user_state[user_id] = "choosing_service"

    elif user_state.get(user_id) == "choosing_city" and text in CITIES:
        context.user_data["city"] = text
        update.message.reply_text(f"Город: *{text}*\n\nВведите ваше имя или название компании:", parse_mode="Markdown")
        user_state[user_id] = "entering_name"

    elif user_state.get(user_id) == "entering_name":
        context.user_data["name"] = text
        update.message.reply_text(
            f"✅ Спасибо, {text}! Вы зарегистрированы как исполнитель в городе {context.user_data['city']}.\n\n"
            "Ваш профиль добавлен в DVSфера. Мы свяжемся с вами для подтверждения.",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)
        )
        try:
            sheet = get_sheet()
            sheet.append_row(["Исполнитель", context.user_data["name"], context.user_data["city"], "", user_id, str(update.effective_user)])
        except Exception as e:
            logging.error(f"Ошибка записи в таблицу: {e}")
        if OPERATOR_CHAT_ID:
            context.bot.send_message(
                chat_id=OPERATOR_CHAT_ID,
                text=f"🆕 Новый исполнитель!\nИмя: {text}\nГород: {context.user_data['city']}\nID: {user_id}"
            )
        user_state.pop(user_id, None)

    elif user_state.get(user_id) == "entering_details":
        details = text
        service = context.user_data.get("service", "Не указано")
        user = update.effective_user
        try:
            sheet = get_sheet()
            sheet.append_row(["Заявка", service, details, "", user_id, f"@{user.username}" if user.username else user.full_name])
        except Exception as e:
            logging.error(f"Ошибка записи в таблицу: {e}")
        if OPERATOR_CHAT_ID:
            context.bot.send_message(
                chat_id=OPERATOR_CHAT_ID,
                text=f"📥 Новая заявка!\nУслуга: {service}\nДетали: {details}\nКлиент: @{user.username or '—'} (ID: {user_id})"
            )
        update.message.reply_text(
            "✅ Ваша заявка принята! Мы свяжемся с вами в ближайшее время.",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)
        )
        user_state.pop(user_id, None)

    elif user_state.get(user_id) == "adding_service":
        new_service = text
        if OPERATOR_CHAT_ID:
            context.bot.send_message(
                chat_id=OPERATOR_CHAT_ID,
                text=f"📌 Запрос на добавление услуги:\n{new_service}\nОт пользователя: @{update.effective_user.username or '—'} (ID: {user_id})"
            )
        update.message.reply_text(
            "✅ Ваш запрос передан оператору. Если услуга будет добавлена — вы получите уведомление!",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)
        )
        user_state.pop(user_id, None)

    else:
        update.message.reply_text("Пожалуйста, используйте кнопки меню.")

def show_categories_page_1(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Выберите категорию услуг (1/4):",
        reply_markup=ReplyKeyboardMarkup(CATEGORIES_PAGE_1, resize_keyboard=True)
    )

def show_categories_page_2(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Выберите категорию услуг (2/4):",
        reply_markup=ReplyKeyboardMarkup(CATEGORIES_PAGE_2, resize_keyboard=True)
    )

# === ЗАПУСК ===
def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    port = int(os.environ.get("PORT", 10000))
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TELEGRAM_BOT_TOKEN}"

    updater.start_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TELEGRAM_BOT_TOKEN,
        webhook_url=webhook_url
    )
    updater.idle()

if __name__ == "__main__":
    main()
