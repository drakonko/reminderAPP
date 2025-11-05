# crud.py
import sys
from reminder_core import init_supabase
from notifier import show_due_popups
from config import setup_logging

logger = setup_logging("crud")

def main(argv=None):
    supabase = init_supabase()
    show_due_popups(supabase)

if __name__ == "__main__":
    main()
