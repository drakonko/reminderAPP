# config.py
import os
import sys
import logging

APP_NAME = "Cash Reminder App"
ICON_PATH = os.path.join(os.path.dirname(__file__), "icon.ico")
SPREADSHEET_URL = os.getenv("SPREADSHEET_URL", "https://docs.google.com/spreadsheets/d/1IHH_aGtVvaJqtxQjvnGncM55gTrhCmo9HLv9-hWu-ME/edit?gid=1688809850#gid=1688809850")
LOG_FILE = os.path.join(os.path.dirname(__file__), "reminder_log.txt")


def setup_logging(name="reminder"):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(name)
