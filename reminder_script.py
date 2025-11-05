# reminder_script.py
"""
Compatibility wrapper for scripts or scheduled tasks that previously called
reminder_script.py directly. This delegates to the new modular code.
"""
import sys
from reminder_core import init_supabase
from notifier import run_interactive, run_check_only
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reminder_script_wrapper")

def main(argv=None):
    argv = argv or sys.argv[1:]
    only_day_of_month_match = True
    if "--all" in argv:
        only_day_of_month_match = False

    try:
        supabase_client = init_supabase()
    except Exception:
        logger.exception("Supabase init failed.")
        sys.exit(2)

    if "check" in argv or "--check" in argv:
        found = run_check_only(supabase_client, only_day_of_month_match=only_day_of_month_match)
        sys.exit(1 if found else 0)

    try:
        run_interactive(supabase_client, only_day_of_month_match=only_day_of_month_match)
    except Exception:
        logger.exception("Interactive run failed.")
        print("Interactive run failed; see logs.")

if __name__ == "__main__":
    main()
