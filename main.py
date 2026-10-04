import asyncio
from email.mime import message
from dotenv import load_dotenv
from aiogram import Dispatcher, Router, Bot , F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command, CommandObject
from connection import create_table
from service import *
import os
from aiogram.types import ReplyKeyboardMarkup , KeyboardButton , InlineKeyboardMarkup , InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

load_dotenv()

bot = Bot(os.getenv("tg_token"))
dp = Dispatcher()
dish_callback_router = Router()

@dp.message(CommandStart())
async def start(message: Message):
    if await is_admin(message.from_user.id):
        await message.answer("""
👋 Welcome, Admin! 🛠️

🍽️ You can manage the menu, view orders, and control the shop using these commands:

━━━━━━━━━━━━━━━━━━

🚀 Basic Commands

▶️ /start — Start the bot
➕ /add_dish — Add a new dish to the menu
🍽️ /dish — Show a dish card
🛒 /show_cart — View your cart
📊 /cart_stats — View total portions and different dishes
🗑️ /clear_cart — Clear your cart
➕ /add_to_cart — Add a dish to your cart
❌ /cancel — Cancel the current operation

━━━━━━━━━━━━━━━━━━

✨ Manage your menu and keep everything organized with ease! 📦

        """)
    else:
        await message.answer("""
👋 Welcome to the Online Shop! 🛍️

🍽️ Choose your favorite dishes and manage your cart using these commands:

━━━━━━━━━━━━━━━━━━

🚀 Available Commands

▶️ /start — Start the bot
🍽️ /dish — Show a dish card
🛒 /show_cart — View your cart
📊 /cart_stats — View total portions and different dishes
🗑️ /clear_cart — Clear your cart
➕ /add_to_cart — Add a dish to your cart
❌ /cancel — Cancel the current operation

━━━━━━━━━━━━━━━━━━

✨ Enjoy your shopping! 🛒🍴

        """)

@dp.message(Command("cancel"))
async def cancel_fsm(message: Message, state: FSMContext):
    cancelled = await clear_current_fsm(state)
    if cancelled:
        await message.answer("Current operation cancelled.")
    else:
        await message.answer("There is no active operation to cancel.")


class AddDishToMenu(StatesGroup):
    title = State()
    price = State()
    description = State()
    photo_file_id = State()


@dp.message(Command("add_dish"))
async def add_dish(message: Message , state: FSMContext):
    if await is_admin(message.from_user.id):
        await message.answer("Please enter the title of the dish:")
        await state.set_state(AddDishToMenu.title)

@dp.message(AddDishToMenu.title)
async def add_dish_title(message: Message , state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Please enter the price of the dish:")
    await state.set_state(AddDishToMenu.price)

@dp.message(AddDishToMenu.price)
async def add_dish_price(message: Message , state: FSMContext):
    await state.update_data(price=int(message.text))
    await message.answer("Please enter the description of the dish:")
    await state.set_state(AddDishToMenu.description)

@dp.message(AddDishToMenu.description)
async def add_dish_description(message: Message , state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Please send the photo of the dish:")
    await state.set_state(AddDishToMenu.photo_file_id)

@dp.message(AddDishToMenu.photo_file_id, F.photo)
async def add_dish_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photo_file_id = message.photo[-1].file_id
    await add_dish_to_menu(await is_admin(message.from_user.id), message.from_user.id, data["title"], data["price"], data["description"], photo_file_id)
    await message.answer("Dish added to menu!")
    await state.clear()

class AddDishToCart(StatesGroup):
    dish_id = State()
    quantity = State()

@dp.message(Command("add_to_cart"))
async def add_to_cart(message: Message , state: FSMContext):
    await message.answer("Please enter the dish ID you want to add to your cart:")
    await state.set_state(AddDishToCart.dish_id)

@dp.message(AddDishToCart.dish_id)
async def add_to_cart_dish_id(message: Message , state: FSMContext):
    await state.update_data(dish_id=int(message.text))
    await message.answer("Please enter the quantity:")
    await state.set_state(AddDishToCart.quantity)

@dp.message(AddDishToCart.quantity)
async def add_to_cart_quantity(message: Message , state: FSMContext):
    data = await state.get_data()
    await add_dish_to_cart(message.from_user.id, data["dish_id"], int(message.text))
    await message.answer("Dish added to cart!")
    await state.clear()

@dp.message(Command("show_dishes"))
async def show_dishes(message: Message):
    dishes = await show_all_dishes()
    if not dishes:
        await message.answer("No dishes available.")
        return

    await message.answer("Our menu:")
    for i in dishes:
        text = f"""
Dish ID: {i['dish_id']}
Title: {i['title']}
Price: {i['price']}
Description: {i['description']}
        """
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="Подробнее",
                callback_data=f"dish:show:{i['dish_id']}"
            )
        ]])
        photot_file_id = i['photo_file_id']
        if not photot_file_id or len(photot_file_id) < 20:
            await message.answer(f"""
{text}
This dish has no valid Telegram photo""")
            continue
        try:
            await message.answer_photo(photo=photot_file_id, caption=text, reply_markup=keyboard)
        except Exception as error:
            await message.answer(f"{text} cold not send the photo: {error}")

@dp.message(Command("dish"))
async def show_dish_command(message: Message, command: CommandObject):
    if not command.args:
        dishes = await show_all_dishes()
        if not dishes:
            await message.answer("The menu is empty.")
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{dish['title']} — {dish['price']}",
                callback_data=f"dish:show:{dish['dish_id']}"
            )]
            for dish in dishes
        ])
        await message.answer("Choose a dish to see its photo and details:", reply_markup=keyboard)
        return

    try:
        dish_id = int(command.args.strip())
        if dish_id <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Dish ID must be a positive number. Example: /dish 2")
        return

    await send_dish_card(message, dish_id)

async def send_dish_card(message: Message, dish_id: int, user_id: int = None):
    dish = await get_dish(dish_id)
    if dish is None:
        await message.answer("Dish not found.")
        return

    quantity = await get_cart_quantity(user_id or message.from_user.id, dish_id)
    if quantity is None:
        await message.answer("Couldn't load this dish's cart quantity. Please try again.")
        return
    caption = format_dish_caption(dish, quantity)
    keyboard = build_dish_keyboard(dish_id)

    photo_file_id = dish["photo_file_id"]
    if photo_file_id:
        try:
            await message.answer_photo(photo=photo_file_id, caption=caption, reply_markup=keyboard)
            return
        except Exception:
            pass
    await message.answer(f"{caption}\n\nPhoto is unavailable.", reply_markup=keyboard)

def format_dish_caption(dish, quantity: int):
    return (
        f"Title: {dish['title']}\n"
        f"Price: {dish['price']}\n"
        f"{dish['description']}\n"
        f"In your cart: {quantity}"
    )

def build_dish_keyboard(dish_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➖",
                callback_data=f"dish:cart:minus:{dish_id}"
            ),
            InlineKeyboardButton(
                text="➕",
                callback_data=f"dish:cart:plus:{dish_id}"
            ),
        ],
        [InlineKeyboardButton(
            text="🗑 Remove from cart",
            callback_data=f"dish:cart:remove:{dish_id}"
        )],
    ])

@dish_callback_router.callback_query(F.data.startswith("dish:show:"))
async def dish_details_callback(callback: CallbackQuery):
    try:
        _, _, dish_id_text = callback.data.split(":")
        dish_id = int(dish_id_text)
        if dish_id <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        await callback.answer("Invalid dish button.", show_alert=True)
        return

    await callback.answer()
    await send_dish_card(callback.message, dish_id, callback.from_user.id)

@dish_callback_router.callback_query(F.data.startswith("cart:add:"))
async def add_dish_callback(callback: CallbackQuery):
    try:
        parts = callback.data.split(":")
        if len(parts) not in {3, 4}:
            raise ValueError
        dish_id_text = parts[2]
        dish_id = int(dish_id_text)
        if dish_id <= 0:
            raise ValueError
        quantity = int(parts[3]) if len(parts) == 4 else 1
        if not 1 <= quantity <= 99:
            raise ValueError
    except (ValueError, AttributeError):
        await callback.answer("Invalid dish button.", show_alert=True)
        return

    dish = await get_dish(dish_id)
    if dish is None:
        await callback.answer("This dish is no longer available.", show_alert=True)
        return

    added = await add_dish_to_cart(callback.from_user.id, dish_id, quantity)
    if added:
        await refresh_dish_card(callback, dish_id)
        await callback.answer(f"Added {quantity} portion(s) to your cart.")
    else:
        await callback.answer("Couldn't add this dish. Please try again.", show_alert=True)

async def refresh_dish_card(callback: CallbackQuery, dish_id: int):
    dish = await get_dish(dish_id)
    quantity = await get_cart_quantity(callback.from_user.id, dish_id)
    if dish is None or quantity is None:
        return

    caption = format_dish_caption(dish, quantity)
    keyboard = build_dish_keyboard(dish_id)
    if callback.message.photo:
        await callback.message.edit_caption(caption=caption, reply_markup=keyboard)
    else:
        await callback.message.edit_text(text=caption, reply_markup=keyboard)

@dish_callback_router.callback_query(F.data.startswith("dish:cart:"))
async def change_dish_cart_quantity(callback: CallbackQuery):
    try:
        _, _, action, dish_id_text = callback.data.split(":")
        dish_id = int(dish_id_text)
        if dish_id <= 0 or action not in {"minus", "plus", "remove"}:
            raise ValueError
    except (ValueError, AttributeError):
        await callback.answer("Invalid cart button.", show_alert=True)
        return

    if action == "plus":
        succeeded = await add_dish_to_cart(callback.from_user.id, dish_id, 1)
        if not succeeded:
            await callback.answer("Couldn't update your cart. Please try again.", show_alert=True)
            return
    elif action == "minus":
        current_quantity = await get_cart_quantity(callback.from_user.id, dish_id)
        if current_quantity is None:
            await callback.answer("Couldn't load your cart. Please try again.", show_alert=True)
            return
        if current_quantity == 0:
            await callback.answer("This dish is not in your cart yet.", show_alert=True)
            return
        if current_quantity == 1:
            await callback.answer("Quantity is 1. Use Remove from cart to remove it.", show_alert=True)
            return
        new_quantity = await decrease_dish_in_cart(callback.from_user.id, dish_id)
        if new_quantity is None:
            await callback.answer("Couldn't update your cart. Please try again.", show_alert=True)
            return
    else:
        removed = await remove_dish_from_cart(callback.from_user.id, dish_id)
        if not removed:
            await callback.answer("This dish is not in your cart.", show_alert=True)
            return

    await refresh_dish_card(callback, dish_id)
    await callback.answer("Cart updated.")

@dish_callback_router.callback_query(F.data.startswith("dish:quantity:"))
async def outdated_quantity_button(callback: CallbackQuery):
    try:
        _, _, action, dish_id_text, _ = callback.data.split(":")
        dish_id = int(dish_id_text)
        if dish_id <= 0 or action not in {"minus", "plus", "show"}:
            raise ValueError
    except (ValueError, AttributeError):
        await callback.answer("Invalid cart button.", show_alert=True)
        return

    if action == "plus":
        if not await add_dish_to_cart(callback.from_user.id, dish_id, 1):
            await callback.answer("Couldn't update your cart. Please try again.", show_alert=True)
            return
    elif action == "minus":
        quantity = await get_cart_quantity(callback.from_user.id, dish_id)
        if quantity is None:
            await callback.answer("Couldn't load your cart. Please try again.", show_alert=True)
            return
        if quantity <= 1:
            await callback.answer(
                "Quantity is 1 or this dish is not in your cart. Use Remove from cart to remove it.",
                show_alert=True,
            )
            return
        if await decrease_dish_in_cart(callback.from_user.id, dish_id) is None:
            await callback.answer("Couldn't update your cart. Please try again.", show_alert=True)
            return

    await refresh_dish_card(callback, dish_id)
    if action == "show":
        quantity = await get_cart_quantity(callback.from_user.id, dish_id)
        await callback.answer(f"In your cart: {quantity}")
    else:
        await callback.answer("Cart updated.")

dp.include_router(dish_callback_router)

@dp.message(Command("show_cart"))
async def show_cart_command(message: Message):
    cart = await show_cart(message.from_user.id)
    
    if not cart:
        await message.answer("Your cart is empty.")
        return
    
    text = "Your cart:\n"
    
    for item in cart:
        text += f"""
Title: {item['title']}
Price: {item['price']}
Quantity: {item['quantity']}
Total price: {item['total_price']}
        """
    await message.answer(f"{text}")

@dp.message(Command("cart_stats"))
async def cart_stats_command(message: Message):
    stats = await get_cart_stats(message.from_user.id)
    if stats is None:
        await message.answer("Couldn't get your cart statistics. Please try again.")
        return

    await message.answer(f"""
Cart statistics:\n
Total portions: {stats['total_portions']}\n
Different dishes: {stats['different_dishes']}
    """
    )

@dp.message(Command("clear_cart"))
async def clear_user_cart(message: Message):
    await clear_cart(message.from_user.id)
    await message.answer("Your cart has been cleared.")

@dp.message(Command("help"))
async def help(message: Message):
    if await is_admin(message.from_user.id):
        await message.answer("""
👋 Hey Admin! 🛠️ Here’s what you can do with this bot:

━━━━━━━━━━━━━━━━━━

⚙️ Admin & Shop Commands

▶️ /start — Start the bot
➕ /add_dish — Add a new dish to the menu
🍽️ /show_dishes — View all dishes in the menu
🔎 /dish <id> — View a dish card
🛒 /show_cart — View your cart
📊 /cart_stats — View cart portions and different dishes
🗑️ /clear_cart — Clear your cart
➕ /add_to_cart — Add a dish to your cart
❌ /cancel — Cancel the current operation

━━━━━━━━━━━━━━━━━━

✨ Manage your menu and keep your shop organized! 📋🍽️

    """)
    else:
        await message.answer("""
👋 Hey! Here’s what you can do with this bot:

━━━━━━━━━━━━━━━━━━

🚀 Available Commands

▶️ /start — Start the bot
🍽️ /show_dishes — View all dishes in the menu
🔎 /dish <id> — View a dish card
🛒 /show_cart — View your cart
📊 /cart_stats — View cart portions and different dishes
🗑️ /clear_cart — Clear your cart
➕ /add_to_cart — Add a dish to your cart
❌ /cancel — Cancel the current operation

━━━━━━━━━━━━━━━━━━

✨ Enjoy your shopping! 🛍️🍴

    """)

@dp.message()
async def unknown_command(message: Message):
    await message.answer("Unknown command. Please use /help to see the list of available commands.")

async def main():
    print("Bot started")
    await create_table()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
