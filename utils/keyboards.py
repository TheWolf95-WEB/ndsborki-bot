from telegram import ReplyKeyboardMarkup

def get_main_menu(user_id: int) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([['📋 Сборки Warzone']], resize_keyboard=True)

def build_keyboard_with_main(buttons: list[list[str]]) -> ReplyKeyboardMarkup:
    if not any("🏠 Главное меню" in row for row in buttons):
        buttons.append(["🏠 Главное меню"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)
