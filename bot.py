# bot.py — DVSфера Telegram Bot (финальная версия с афишей)
import os
import logging
import json
import datetime
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
def get_sheet(name="DVSferra_Заявки"):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(name).sheet1
    return sheet

# === ГОРОДА ПРИМОРЬЯ ===
CITIES = [
    "Владивосток", "Уссурийск", "Находка", "Арсеньев", "Дальнереченск",
    "Дальнегорск", "Лесозаводск", "Славянка", "Артём"
]

def paginate(items, page_size=6):
    return [items[i:i + page_size] for i in range(0, len(items), page_size)]

CITY_PAGES = paginate(CITIES)

# === КНОПКИ ===
MAIN_MENU = [
    ["🔍 Найти услугу", "💼 Стать исполнителем"],
    ["🎟️ Афиша Приморья", "📞 Поддержка"]
]

SERVICE_CATEGORIES = [
    ["👶 Детские услуги", "💻 Для Бизнеса/IT"],
    ["🍔 Еда/Продукты", "🐾 Животные"],
    ["🧼 Клининг/Химчистка", "🛋️ Мебель"],
    ["🩺 Медицина/Врачи", "🎓 Обучение/Курсы"],
    ["🚗 Авто/мото услуги", "🚌 Автобусы/Область"],
    ["⚖️ Адвокаты/Юристы", "🔑 Аренда/Прокат"],
    ["✂️ Ателье/Швея", "🔧 Быт.услуги/Ремонт"],
    ["🛍️ Бьюти Сфера", "🚚 Грузоперевозки"],
    ["➕ Другое", "🏠 Главное меню"]
]

AFISHA_MENU = [
    ["🗓️ Выбрать дату", "⭐ На 2 недели"],
    ["🎭 Театр/Кино", "🎵 Концерты"],
    ["🖼️ Выставки", "🎲 Игры/Конкурсы"],
    ["🎉 Фестивали", "👶 Для детей"],
    ["🧑‍🏫 Мастер-классы", "🏃 Активный отдых"],
    ["💃 Вечеринки", "😊 Другое"],
    ["➕ Добавить событие", "🏠 Главное меню"]
]

# === ФУНКЦИИ ===
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

def show_events(update: Update, events):
    if not events:
        update.message.reply_text("❌ Пока нет событий.")
        return
    
    message = "📅 *Ближайшие мероприятия:*\n\n"
    for event in events[:5]:
        message += f"📍 {event.get('Место', '—')}\n"
        message += f"🗓️ {event.get('Дата', '—')}\n"
        message += f"🎫 {event.get('Название', '—')}\n"
        link = event.get('Ссылка', '')
        if link:
            message += f"🔗 {link}\n"
        desc = event.get('Описание', '')
        if desc:
            message += f"📝 {desc}\n"
        message += "\n"
    
    update.message.reply_text(
        message,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["⬅️ Назад", "🏠 Главное меню"]], resize_keyboard=True)
    )

# === ОБРАБОТЧИКИ ===
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
            "📌 Здесь мы собираем самые яркие и значимые события Приморья. "
            "Афиша поможет вам планировать отдых и выходные!\n\n"
            "🔎 Поиск удобно распределен: по календарю, по ближайшим 2 неделям, по типам событий. "
            "Будьте в курсе событий всего за 3 клика!\n\n"
            "💡 Кроме того, вы сами можете добавить любое событие через кнопку в меню «Добавить событие»!",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(AFISHA_MENU, resize_keyboard=True)
        )
        context.user_data["state"] = "choosing_afisha_category"

    elif text == "🏠 Главное меню":
        start(update, context)
        return

    # === АФИША ===
    elif state == "choosing_afisha_category":
        if text == "➕ Добавить событие":
            update.message.reply_text("📝 Укажите название события:")
            context.user_data["state"] = "entering_event_name"

        elif text == "🗓️ Выбрать дату":
            update.message.reply_text("📅 Укажите дату (формат: ГГГГ-ММ-ДД):")
            context.user_data["state"] = "entering_event_date_filter"

        elif text == "⭐ На 2 недели":
            try:
                events = get_sheet("DVSferra_Афиша").get_all_records()
                today = datetime.date.today()
                two_weeks = today + datetime.timedelta(days=14)
                filtered = [
                    e for e in events
                    if e.get("Дата") and today <= datetime.datetime.strptime(e["Дата"], "%Y-%m-%d").date() <= two_weeks
                ]
                show_events(update, filtered)
            except Exception as e:
                logging.error(f"Ошибка загрузки афиши: {e}")
                update.message.reply_text("❌ Не удалось загрузить афишу.")

        else:
            # Фильтр по категории
            try:
                events = get_sheet("DVSferra_Афиша").get_all_records()
                filtered = [e for e in events if e.get("Категория") == text]
                show_events(update, filtered)
            except Exception as e:
                logging.error(f"Ошибка загрузки афиши: {e}")
                update.message.reply_text("❌ Не удалось загрузить афишу.")

    # === ФИЛЬТР ПО ДАТЕ ===
    elif state == "entering_event_date_filter":
        try:
            target_date = datetime.datetime.strptime(text, "%Y-%m-%d").date()
            events = get_sheet("DVSferra_Афиша").get_all_records()
            filtered = [e for e in events if e.get("Дата") == str(target_date)]
            show_events(update, filtered)
        except ValueError:
            update.message.reply_text("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД.")
        context.user_data["state"] = "afisha_browsing"

    # === ДОБАВЛЕНИЕ СОБЫТИЯ ===
    elif state == "entering_event_name":
        context.user_data["event_name"] = text
        update.message.reply_text("📅 Укажите дату (формат: ГГГГ-ММ-ДД):")
        context.user_data["state"] = "entering_event_date"

    elif state == "entering_event_date":
        context.user_data["event_date"] = text
        update.message.reply_text("📍 Укажите место проведения:")
        context.user_data["state"] = "entering_event_place"

    elif state == "entering_event_place":
        context.user_data["event_place"] = text
        update.message.reply_text("📝 Укажите описание события:")
        context.user_data["state"] = "entering_event_description"

    elif state == "entering_event_description":
        context.user_data["event_description"] = text
        update.message.reply_text("🔗 Укажите ссылку на событие:")
        context.user_data["state"] = "entering_event_link"

    elif state == "entering_event_link":
        context.user_data["event_link"] = text
        update.message.reply_text("🏷️ Укажите категорию (например: Концерты, Театр/Кино и т.д.):")
        context.user_data["state"] = "entering_event_category"

    elif state == "entering_event_category":
        category = text
        name = context.user_data["event_name"]
        date = context.user_data["event_date"]
        place = context.user_data["event_place"]
        desc = context.user_data["event_description"]
        link = context.user_data["event_link"]

        try:
            sheet = get_sheet("DVSferra_Афиша")
            sheet.append_row([name, date, place, desc, link, category])
        except Exception as e:
            logging.error(f"Ошибка записи события: {e}")
            update.message.reply_text("❌ Ошибка при сохранении события. Попробуйте позже.")
            return

        if OPERATOR_CHAT_ID:
            context.bot.send_message(
                chat_id=OPERATOR_CHAT_ID,
                text=f"🆕 Новое событие добавлено!\nНазвание: {name}\nДата: {date}\nМесто: {place}\nКатегория: {category}\nСсылка: {link}"
            )

        update.message.reply_text(
            "✅ Событие успешно добавлено! Оператор проверит его и опубликует.",
            reply_markup=ReplyKeyboardMarkup([["🏠 Главное меню"]], resize_keyboard=True)
        )
        context.user_data.clear()

    # === РЕГИСТРАЦИЯ ИСПОЛНИТЕЛЯ ===
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
                    reply_markup=ReplyKeyboardMarkup(SERVICE_CATEGORIES, resize_keyboard=True)
                )
                context.user_data["state"] = "choosing_service"
            else:
                update.message.reply_text(
                    f"Город: *{text}*\nВыберите сферу услуг:",
                    parse_mode="Markdown",
                    reply_markup=ReplyKeyboardMarkup(SERVICE_CATEGORIES, resize_keyboard=True)
                )
                context.user_data["state"] = "choosing_service"

    elif state == "choosing_service":
        if text == "➕ Другое":
            update.message.reply_text("Укажите сферу услуг:")
            context.user_data["state"] = "entering_custom_service"
        elif text in [cat for row in SERVICE_CATEGORIES for cat in row]:
            context.user_data["service"] = text
            update.message.reply_text("Введите название компании или ваше имя:")
            context.user_data["state"] = "entering_name"

    elif state == "entering_custom_service":
        context.user_data["service"] = text
        update.message.reply_text("Введите название компании или ваше имя:")
        context.user_data["state"] = "entering_name"

    elif state == "entering_name":
        context.user_data["name"] = text
        update.message.reply_text("Введите контактные данные (телефон, Telegram, email):")
        context.user_data["state"] = "entering_contact"

    elif state == "entering_contact":
        contact = text
        city = context.user_data["selected_city"]
        service = context.user_data["service"]
        name = context.user_data["name"]
        try:
            sheet = get_sheet("DVSferra_Заявки")
            sheet.append_row([
                "Исполнитель",
                name,
                city,
                service,
                user_id,
                str(update.effective_user),
                contact
            ])
        except Exception as e:
            logging.error(f"Ошибка записи в таблицу: {e}")
        if OPERATOR_CHAT_ID:
            context.bot.send_message(
                chat_id=OPERATOR_CHAT_ID,
                text=f"🆕 Новый исполнитель!\nИмя: {name}\nГород: {city}\nСфера: {service}\nКонтакты: {contact}\nID: {user_id}"
            )
        update.message.reply_text(
            f"✅ Спасибо, {name}! Вы зарегистрированы в городе {city}.",
            reply_markup=ReplyKeyboardMarkup([["🏠 Главное меню"]], resize_keyboard=True)
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
