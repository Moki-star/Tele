'''
Spotify Premium Shop Bot (aiogram)
=================================
Flow:
 1. /start → Greeting + "Buy Premium" button
 2. "Buy Premium" → Ask 3‑month vs 12‑month (with prices)
 3. Show KPay transfer info → wait screenshot
 4. Screenshot forwarded to admins with Verify/Reject buttons
 5. On Verify → send Spotify account & password to buyer
'''

import os
import uuid
import io
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = set(int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x)

# KPay info
PAY_NAME = "Ko Ko Thar Htet"
PAY_NUMBER = "0927736328823737"

# Plan prices
PLAN_PRICES = {
    "3": 6000,
    "12": 20000
}

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class Form(StatesGroup):
    waiting_product = State()
    waiting_payment = State()

# In‑memory store
ORDERS = {}

# --- Keyboards --------------------------------------------------------------

def kb_buy():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Buy Premium", callback_data="buy"))
    return kb

def kb_plan():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("3‑Months (6000 MMK)", callback_data="plan:3"),
        types.InlineKeyboardButton("12‑Months (20000 MMK)", callback_data="plan:12")
    )
    kb.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel"))
    return kb

def kb_admin(order_id: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Verify", callback_data=f"ok:{order_id}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"no:{order_id}")
    )
    return kb

# --- Handlers ---------------------------------------------------------------
@dp.message_handler(commands=["start"])
async def cmd_start(m: types.Message):
    await m.answer("Spotify shop မှကြိုဆိုပါတယ်ဗျာ 🙌", reply_markup=kb_buy())

@dp.callback_query_handler(lambda c: c.data == "buy")
async def choose_plan(cb: types.CallbackQuery):
    await cb.message.edit_text("သင်ယူလိုတဲ့ Spotify Premium Plan ကို ရွေးပါ:", reply_markup=kb_plan())
    await Form.waiting_product.set()

@dp.callback_query_handler(lambda c: c.data.startswith("plan:"), state=Form.waiting_product)
async def plan_selected(cb: types.CallbackQuery, state):
    months = cb.data.split(":")[1]
    price = PLAN_PRICES.get(months, 0)
    order_id = str(uuid.uuid4())[:8]
    ORDERS[order_id] = {
        "user_id": cb.from_user.id,
        "months": months,
        "price": price,
        "status": "AWAIT_PAY"
    }
    text = (
        f"🧾 Order ID: <code>{order_id}</code>\n"
        f"🎧 Plan: {months}‑Months Spotify Premium\n"
        f"💰 Price: {price:,} MMK\n\n"
        f"➡ KPay ဖြင့် လွှဲရန်\n"
        f"👤 Name: <b>{PAY_NAME}</b>\n"
        f"📱 Number: <code>{PAY_NUMBER}</code>\n\n"
        "ငွေလွှဲပြေစာ (screenshot) ကို ဒီနေရာမှာ upload ပေးပါ။"
    )
    await cb.message.edit_text(text)
    await state.update_data(order_id=order_id)
    await Form.waiting_payment.set()

@dp.message_handler(content_types=[types.ContentType.PHOTO, types.ContentType.DOCUMENT], state=Form.waiting_payment)
async def receive_screenshot(m: types.Message, state):
    data = await state.get_data()
    order_id = data.get("order_id")
    if order_id not in ORDERS:
        await m.answer("Order not found. /start ပြန်လုပ်ပါ")
        return
    ORDERS[order_id]["status"] = "AWAIT_ADMIN"
    await m.answer("✅ ပြေစာလက်ခံပြီးပါပြီ။ Admin အတည်ပြုပြီးပါက premium account ကို ပို့ပေးပါမယ်။")

    # Forward to admins
    for admin in ADMIN_IDS:
        await bot.send_message(admin, f"🔔 New Spotify order #{order_id} ({ORDERS[order_id]['months']}‑M, {ORDERS[order_id]['price']:,} MMK)")
        await bot.forward_message(admin, m.chat.id, m.message_id)
        await bot.send_message(admin, "Approve or Reject this order:", reply_markup=kb_admin(order_id))

# --- Admin buttons ----------------------------------------------------------
@dp.callback_query_handler(lambda c: c.data.startswith("ok:"))
async def admin_verify(cb: types.CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("Not allowed", show_alert=True)
        return
    order_id = cb.data.split(":")[1]
    order = ORDERS.get(order_id)
    if not order:
        await cb.answer("Order missing", show_alert=True)
        return
    order["status"] = "COMPLETED"
    # Dummy credentials ‑ replace with real credential fetch
    cred = f"spotify_user_{order_id}\npassword123"
    await bot.send_message(order["user_id"], f"🎉 သင့် Spotify Premium အကောင့် & စကားဝှက်: \n<code>{cred}</code>\nEnjoy! 🎧")
    await cb.answer("User notified")
    await cb.message.edit_reply_markup()

@dp.callback_query_handler(lambda c: c.data.startswith("no:"))
async def admin_reject(cb: types.CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("Not allowed", show_alert=True)
        return
    order_id = cb.data.split(":")[1]
    order = ORDERS.get(order_id)
    if order:
        order["status"] = "REJECTED"
        await bot.send_message(order["user_id"], "❌ သင့်ငွေလွှဲကို ဗရီဖိုင်မဖြစ်သေးပါ။ ကျေးဇူးပြုပြီး support ကို ဆက်သွယ်ပါ။")
    await cb.answer("Order rejected")
    await cb.message.edit_reply_markup()

# --- Run bot ---------------------------------------------------------------
if __name__ == "__main__":
    print("Spotify bot running...")
    executor.start_polling(dp, skip_updates=True)
