from telegram import ReplyKeyboardMarkup

def get_main_menu(user_id: int) -> ReplyKeyboardMarkup:
    # Здесь вы можете добавить больше кнопок, если нужно
    buttons = [["📋 Сборки Warzone"]]
    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def build_keyboard_with_main(buttons: list[list[str]]) -> ReplyKeyboardMarkup:
    if not any("🏠 Главное меню" in cell for row in buttons for cell in row):
        buttons.append(["🏠 Главное меню"])
    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )
