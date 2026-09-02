import os

from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS = os.environ["GMAIL_ADDRESS"]
APP_PASSWORD = os.environ["APP_PASSWORD"]
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "5"))
REPLIED_FILE = os.getenv("REPLIED_FILE", "replied_ids.txt")
ESCALATED_FILE = os.getenv("ESCALATED_FILE", "escalated_ids.txt")
CLOSED_FILE = os.getenv("CLOSED_FILE", "closed_threads.txt")
CLOSED_MESSAGE_IDS_FILE = os.getenv("CLOSED_MESSAGE_IDS_FILE", "closed_message_ids.txt")
