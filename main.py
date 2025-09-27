import requests
from bs4 import BeautifulSoup
import time
from telegram import Bot
import asyncio # For async functions with python-telegram-bot v20+

# --- Telegram Bot Configuration ---
TELEGRAM_BOT_TOKEN = "8494708391:AAH6lK7QSzpvk6BoyIV4zp_yICeIf_Am60Y"
TELEGRAM_CHAT_ID = "-1002933775039" # Where the notifications should go

# --- Orange Carrier Website Configuration ---
LOGIN_URL = "https://www.orangecarrier.com/login" # Replace with actual login URL
DASHBOARD_URL = "https://www.orangecarrier.com/client/activecalls" # Replace with actual active calls URL
USERNAME = "4139037418" # e.g., "4139037418"
PASSWORD = "Raju123@#"

# Store previously seen active calls to detect new ones
previous_active_calls = set() # Store unique identifiers for calls (e.g., DID + CLI)

async def send_telegram_message(message_text):
    """Sends a message to the configured Telegram chat."""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message_text, parse_mode='HTML')

def login_and_get_page(session):
    """Logs into the Orange Carrier system and returns the Active Calls page HTML."""
    print("Attempting to log in...")
    # Step 1: Get the login page to retrieve any CSRF tokens if necessary
    login_page_response = session.get(LOGIN_URL)
    login_page_soup = BeautifulSoup(login_page_response.text, 'html.parser')

    # Find hidden input fields for CSRF tokens if they exist (common in forms)
    # Example: csrf_token = login_page_soup.find('input', {'name': 'csrf_token'})['value'] if csrf_token else ''

    login_data = {
        'username': USERNAME,
        'password': PASSWORD,
        # Add any other required form fields like csrf_token
        # 'csrf_token': csrf_token
    }

    # Step 2: Post login credentials
    post_login_response = session.post(LOGIN_URL, data=login_data, allow_redirects=True)
    post_login_response.raise_for_status() # Raise an exception for bad status codes

    # You might want to check if login was successful by looking for a specific element
    if "logout" not in post_login_response.text.lower() and "dashboard" not in post_login_response.text.lower():
         print("Login failed! Check credentials or form fields.")
         # You might want to handle specific error messages from the page
         return None

    print("Login successful. Fetching dashboard page...")
    # Step 3: Navigate to the Active Calls dashboard
    dashboard_response = session.get(DASHBOARD_URL)
    dashboard_response.raise_for_status()
    return dashboard_response.text

def parse_active_calls(html_content):
    """Parses the HTML to extract active call details."""
    soup = BeautifulSoup(html_content, 'html.parser')
    active_calls_data = []

    # --- THIS IS THE CRITICAL PART YOU NEED TO ADJUST ---
    # You'll need to inspect the HTML of the Orange Carrier dashboard
    # to find the specific table or div that contains the "Active Calls"
    # For example, if it's a table with id="activeCallsTable":
    table = soup.find('table', {'id': 'activeCallsTable'})
    if not table:
        print("Could not find the active calls table. Check HTML structure.")
        return active_calls_data

    rows = table.find('tbody').find_all('tr') # Assuming data is in tbody rows

    for row in rows:
        cols = row.find_all('td') # Or 'th' for headers, 'td' for data
        if len(cols) >= 4: # Assuming at least DID, CLI, Duration, Revenue
            did = cols[0].text.strip()
            full_cli = cols[1].text.strip()
            cli_last_6 = full_cli[-6:] if len(full_cli) >= 6 else full_cli # Get last 6 digits
            duration = cols[2].text.strip()
            revenue = cols[3].text.strip()

            active_calls_data.append({
                'did': did,
                'cli_full': full_cli,
                'cli_last_6': cli_last_6,
                'duration': duration,
                'revenue': revenue
            })
    # --- END OF CRITICAL ADJUSTMENT PART ---

    return active_calls_data

async def monitor_calls():
    global previous_active_calls
    session = requests.Session()

    while True:
        try:
            html = login_and_get_page(session)
            if html:
                current_active_calls = parse_active_calls(html)
                current_call_identifiers = set()

                for call in current_active_calls:
                    # Create a unique identifier for each call (e.g., DID + CLI)
                    call_id = f"{call['did']}-{call['cli_full']}"
                    current_call_identifiers.add(call_id)

                    if call_id not in previous_active_calls:
                        # New call detected!
                        notification_message = (
                            f"🔥 <b>NEW CALL RECEIVED</b> ✨\n\n"
                            f"<b>DID:</b> {call['did']}\n"
                            f"<b>CLI (last 6):</b> {call['cli_last_6']}\n"
                            f"<b>Duration:</b> {call['duration']}\n"
                            f"<b>Revenue:</b> {call['revenue']}\n\n"
                            f"<i>(Full CLI: {call['cli_full']})</i>"
                        )
                        await send_telegram_message(notification_message)
                        print(f"Sent notification for new call: {call_id}")

                # Update previous_active_calls with the current set
                previous_active_calls = current_call_identifiers
            else:
                print("Failed to get HTML content after login.")

        except requests.exceptions.RequestException as e:
            print(f"Network or request error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        time.sleep(60) # Check every 60 seconds

if __name__ == '__main__':
    # Initialize the bot in the main thread if needed for other commands,
    # but the monitoring loop runs asynchronously.
    # For `python-telegram-bot` v20+, you'd usually run handlers like this:
    # application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    # application.add_handler(...)
    # application.run_polling()
    # For a simple monitoring script, we can just run the async function directly.

    print("Starting call monitor...")
    asyncio.run(monitor_calls())