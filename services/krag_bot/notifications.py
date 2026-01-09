import requests
import os
import logging
import datetime, time
# Configure logging for this module
logger = logging.getLogger(__name__)

# Load Telegram Bot Token and Chat ID from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_message(message: str, chat_id: str = None) -> bool:
    """
    Sends a message to a specified Telegram chat.
    If chat_id is not provided, it uses the TELEGRAM_CHAT_ID from environment variables.
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set in environment variables. Cannot send Telegram message.")
        return False
    
    target_chat_id = chat_id if chat_id else TELEGRAM_CHAT_ID
    if not target_chat_id:
        logger.error("TELEGRAM_CHAT_ID is not set in environment variables or provided. Cannot send Telegram message.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": target_chat_id,
        "text": message,
        "parse_mode": "HTML" # Use HTML for basic formatting (bold, italics, links)
    }

    try:
        response = requests.post(url, json=payload, timeout=5) # Set a timeout
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        response_json = response.json()
        
        if response_json.get("ok"):
            logger.info(f"Telegram message sent successfully to chat_id {target_chat_id}: {message[:50]}...")
            return True
        else:
            logger.error(f"Failed to send Telegram message to chat_id {target_chat_id}. Response: {response_json}")
            return False
    except requests.exceptions.Timeout:
        logger.error(f"Telegram message request timed out for chat_id {target_chat_id}.")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending Telegram message to chat_id {target_chat_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending Telegram message to chat_id {target_chat_id}: {e}")
        return False

def send_heartbeat_message(bot_name: str = "Trading Bot") -> None:
    """
    Sends a periodic heartbeat message to confirm the bot is running.
    """
    message = f"🤖 {bot_name} is alive! Last heartbeat at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    send_telegram_message(message)

# Example usage (for testing this module directly)
if __name__ == "__main__":
    # To test this, you need to set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
    # as environment variables in your terminal BEFORE running this script:
    # export TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"
    # export TELEGRAM_CHAT_ID="YOUR_CHAT_ID"
    # python -m modules.notifications

    logging.getLogger().setLevel(logging.DEBUG) # Set root logger to DEBUG for more output

    logger.info("Testing notifications module...")
    test_message_success = send_telegram_message("<b>Test Message:</b> Your bot's notifications module is working! 💪")
    if test_message_success:
        logger.info("First test message sent successfully.")
    else:
        logger.error("First test message failed.")

    time.sleep(2) # Avoid rate limits if testing rapidly

    test_heartbeat = send_heartbeat_message()
    logger.info("Heartbeat message attempt completed.")

    # Example of a failure (e.g., incorrect chat ID or token)
    # logger.warning("Attempting to send message with an invalid chat ID (expecting failure)...")
    # send_telegram_message("This message should fail.", chat_id="12345")