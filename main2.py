import requests
from bs4 import BeautifulSoup
import asyncio
from telegram import Bot

# --- Telegram Bot Configuration ---
TELEGRAM_BOT_TOKEN = "8494708391:AAH6lK7QSzpvk6BoyIV4zp_yICeIf_Am60Y"
TELEGRAM_CHAT_ID = "-1002933775039"

# --- Orange Carrier Website Configuration ---
LOGIN_URL = "https://www.orangecarrier.com/login"
DASHBOARD_URL = "https://www.orangecarrier.com/live/calls"
USERNAME = "4139037418"
PASSWORD = "Raju123@#"

# Store previously seen active calls
previous_active_calls = set()

# --- Telegram Notification ---
async def send_telegram_message(message_text):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message_text, parse_mode='HTML')

# --- Extract all hidden inputs + add credentials ---
def get_login_data(session):
    r = session.get(LOGIN_URL)
    soup = BeautifulSoup(r.text, 'html.parser')
    login_data = {}

    # Automatically extract all hidden inputs
    for input_tag in soup.find_all('input', type='hidden'):
        name = input_tag.get('name')
        value = input_tag.get('value', '')
        if name:
            login_data[name] = value

    # Add username & password
    login_data['username'] = USERNAME
    login_data['password'] = PASSWORD

    return login_data

# --- Login and fetch dashboard ---
def login_and_get_page(session):
    try:
        print("Attempting to log in...")

        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': LOGIN_URL
        }

        login_data = get_login_data(session)
        post_login_response = session.post(LOGIN_URL, data=login_data, headers=headers, allow_redirects=True)
        post_login_response.raise_for_status()

        if "logout" not in post_login_response.text.lower() and "dashboard" not in post_login_response.text.lower():
            print("Login failed! Check credentials or hidden tokens.")
            return None

        print("Login successful. Fetching live calls page...")
        dashboard_response = session.get(DASHBOARD_URL, headers=headers)
        dashboard_response.raise_for_status()
        return dashboard_response.text

    except requests.exceptions.RequestException as e:
        print(f"Network error during login: {e}")
        return None

# --- Parse Active Calls Table ---
def parse_active_calls(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    active_calls_data = []

    # Adjust table id/class according to actual dashboard HTML
    table = soup.find('table', {'id': 'activeCallsTable'})
    if not table:
        print("Could not find the active calls table. Check HTML structure.")
        return active_calls_data

    rows = table.find('tbody').find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 4:
            did = cols[0].text.strip()
            full_cli = cols[1].text.strip()
            cli_last_6 = full_cli[-6:] if len(full_cli) >= 6 else full_cli
            duration = cols[2].text.strip()
            revenue = cols[3].text.strip()

            active_calls_data.append({
                'did': did,
                'cli_full': full_cli,
                'cli_last_6': cli_last_6,
                'duration': duration,
                'revenue': revenue
            })

    return active_calls_data

# --- Monitor Active Calls ---
async def monitor_calls():
    global previous_active_calls
    session = requests.Session()

    while True:
        try:
            html = await asyncio.to_thread(login_and_get_page, session)
            if html:
                current_active_calls = parse_active_calls(html)
                current_call_identifiers = set()

                for call in current_active_calls:
                    call_id = f"{call['did']}-{call['cli_full']}"
                    current_call_identifiers.add(call_id)

                    if call_id not in previous_active_calls:
                        message = (
                            f"🔥 <b>NEW CALL RECEIVED</b> ✨\n\n"
                            f"<b>DID:</b> {call['did']}\n"
                            f"<b>CLI (last 6):</b> {call['cli_last_6']}\n"
                            f"<b>Duration:</b> {call['duration']}\n"
                            f"<b>Revenue:</b> {call['revenue']}\n\n"
                            f"<i>(Full CLI: {call['cli_full']})</i>"
                        )
                        await send_telegram_message(message)
                        print(f"Sent notification for new call: {call_id}")

                previous_active_calls = current_call_identifiers
            else:
                print("Failed to fetch live calls HTML.")

        except Exception as e:
            print(f"Unexpected error: {e}")

        await asyncio.sleep(5)  # Fast check every 5 seconds

# --- Main ---
if __name__ == '__main__':
    print("Starting Orange Carrier live call monitor...")
    asyncio.run(monitor_calls())