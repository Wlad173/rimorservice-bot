# bot.py — DVSфера Telegram Bot (финальная версия)
import os
import logging
import json
from telegram import Update, ReplyKeyboardMarkup
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
OPERATOR_CHAT_ID = os.getenv("OPERATOR_CHAT_ID")
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

# === ГОРОДА ПРИМОРЬЯ ===
CITIES = [
    "Владивосток", "Уссурийск", "Находка", "Арсеньев", "Дальнереченск",
    "Дальнегорск", "Лесозаводск", "Славянка", "Артём"
]

def paginate(items, page_size=6):
    return [items[i:i + page_size] for i in range(0, len(items), page_size)]

CITY_PAGES = paginate(CITIES)

# === ОСНОВНЫЕ КАТЕГОРИИ (все на одном экране) ===
MAIN_CATEGORIES = [
    ["👶 Детские услуги", "💻 Для Бизнеса/IT"],
    ["🍔 Еда/Продукты", "🐾 Животные"],
    ["🧼 Клининг/Химчистка", "🛋️ Мебель"],
    ["🩺 Медицина/Врачи", "🎓 Обучение/Курсы"],
    ["🚗 Авто/мото услуги", "🚌 Автобусы/Область"],
    ["⚖️ Адвокаты/Юристы", "🔑 Аренда/Прокат"],
    ["✂️ Ателье/Швея", "🔧 Быт.услуги/Ремонт"],
    ["🛍️ Бьюти Сфера", "🚚 Грузоперевозки"],
    ["⬅️ Назад", "🏠 Главное меню"]
]

MAIN_MENU = [
    ["🔍 Найти услугу", "💼 Стать исполнителем"],
    ["🎟️ Афиша Приморья", "📞 Поддержка"]
]

# === ОБРАБОТЧИКИ ===
def start(update: Update, context: CallbackContext):
    context.user_data.clear()
    update.message.reply_text(
        "👋 Привет! Я бот *DVSфера* — ваш агент по услугам в Приморье!\n\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)
    )

def show_city_page(update: Update, context: CallbackContext, page=0, for_search=True):
    cities = CITY_PAGES[page]
    buttons = [[city] for city in cities]
    
    nav = []
    if page > 0:
        nav.append("⬅️ Назад")
    if page < len(CITY_PAGES) - 1:
        nav.append("➡️ Вперёд")
    if nav:
        buttons.append(nav)
    
    buttons.append(["🏠 Главное меню"])
    
    action = "поиска" if for_search else "регистрации"
    update.message.reply_text(
        f"Выберите город для {action} (стр. {page + 1}/{len(CITY_PAGES)}):",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    context.user_data["city_page"] = page
    context.user_data["for_search"] = for_search

def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text
    state = context.user_data.get("state", "main")

    # === Главное меню ===
    if text == "🔍 Найти услугу":
        show_city_page(update, context, page=0, for_search=True)
        context.user_data["state"] = "choosing_city_for_search"

    elif text == "💼 Стать исполнителем":
        show_city_page(update, context, page=0, for_search=False)
        context.user_data["state"] = "choosing_city_for_reg"

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

    elif text == "🏠 Главное меню":
        start(update, context)
        return

    # === Навигация по городам ===
    elif state in ("choosing_city_for_search", "choosing_city_for_reg"):
        page = context.user_data.get("city_page", 0)
        for_search = context.user_data.get("for_search", True)

        if text == "⬅️ Назад":
            if page > 0:
                show_city_page(update, context, page - 1, for_search)
        elif text == "➡️ Вперёд":
            if page < len(CITY_PAGES) - 1:
                show_city_page(update, context, page + 1, for_search)
        elif text in CITIES:
            context.user_data["selected_city"] = text
            if for_search:
                update.message.reply_text(
                    f"Город: *{text}*\nВыберите категорию:",
                    parse_mode="Markdown",
                    reply_markup=ReplyKeyboardMarkup(MAIN_CATEGORIES, resize_keyboard=True)
                )
                context.user_data["state"] = "choosing_category"
            else:
                update.message.reply_text(
                    f"Город: *{text}*\nВведите ваше имя или название компании:",
                    parse_mode="Markdown"
                )
                context.user_data["state"] = "entering_name"

    # === Выбор категории ===
    elif state == "choosing_category":
        if text == "⬅️ Назад":
            show_city_page(update, context, context.user_data.get("city_page", 0), for_search=True)
            context.user_data["state"] = "choosing_city_for_search"
        elif text == "🏠 Главное меню":
            start(update, context)
        else:
            update.message.reply_text(
                f"❌ В городе {context.user_data['selected_city']} пока нет исполнителей в категории:\n*{text}*",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup([["⬅️ Назад", "🏠 Главное меню"]], resize_keyboard=True)
            )

    # === Регистрация имени ===
    elif state == "entering_name":
        name = text
        city = context.user_data["selected_city"]
        try:
            sheet = get_sheet()
            sheet.append_row(["Исполнитель", name, city, "", user_id, str(update.effective_user)])
        except Exception as e:
            logging.error(f"Ошибка записи в таблицу: {e}")
        if OPERATOR_CHAT_ID:
            context.bot.send_message(
                chat_id=OPERATOR_CHAT_ID,
                text=f"🆕 Новый исполнитель!\nИмя: {name}\nГород: {city}\nID: {user_id}"
            )
        update.message.reply_text(
            f"✅ Спасибо, {name}! Вы зарегистрированы в городе {city}.",
            reply_markup=ReplyKeyboardMarkup([["🏠 Главное меню"]], resize_keyboard=True)
        )
        context.user_data.clear()

    # === Запрос на добавление услуги ===
    elif text == "➕ Нет нужного? - Добавьте":
        update.message.reply_text("📩 Укажите, какую услугу вы хотите добавить — мы рассмотрим её и включим в список!")
        context.user_data["state"] = "adding_service"

    elif state == "adding_service":
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
        context.user_data.clear()

    else:
        update.message.reply_text("Пожалуйста, используйте кнопки меню.")

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
