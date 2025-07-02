# bot.py
# Telegram Game Top-up Bot (aiogram based)

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv
import os, uuid, io

load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher(bot)

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.answer("🎮 Welcome to Game Shop!\nType /order to begin.")

if __name__ == "__main__":
    executor.start_polling(dp)
