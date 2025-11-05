# reminder_core.py
import os
import logging
from datetime import date, datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

logger = logging.getLogger("reminder_core")


# -----------------------------
# INIT & CONNECTION
# -----------------------------
def init_supabase() -> Client:
    """Initialize and return a Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Supabase credentials missing in environment (.env).")
    try:
        client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Quick test query
        _ = client.table("recurring_payments").select("id").limit(1).execute()
        return client
    except Exception as e:
        logger.exception("Failed to initialize Supabase client.")
        raise RuntimeError(f"Failed to initialize Supabase client: {e}")


# -----------------------------
# UTILS
# -----------------------------
def parse_iso_date(date_str):
    """Parse ISO string to date object or None."""
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except Exception:
        try:
            return date.fromisoformat(date_str.strip().split("T")[0])
        except Exception:
            logger.warning("Unparseable date string: %s", date_str)
            return None


# -----------------------------
# RECURRING REMINDERS
# -----------------------------
FREQUENCY_DAYS = {
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
    "quarterly": 90,
    "yearly": 365
}


def is_recurring_due(item, today=None):
    """Check if recurring reminder is due."""
    if today is None:
        today = date.today()

    freq = (item.get("frequency") or "").strip().lower()
    if not freq:
        return False
    if item.get("is_active") is False:
        return False

    last_date = parse_iso_date(item.get("last_recorded_date"))

    if freq == "monthly":
        return not last_date or not (last_date.month == today.month and last_date.year == today.year)
    if freq == "quarterly":
        return not last_date or (today - last_date).days >= FREQUENCY_DAYS["quarterly"]
    if freq == "weekly":
        return not last_date or (today - last_date).days >= FREQUENCY_DAYS["weekly"]
    if freq == "daily":
        return not last_date or (today - last_date).days >= FREQUENCY_DAYS["daily"]
    if freq == "yearly":
        return not last_date or last_date.year < today.year
    if freq.isdigit():
        days = int(freq)
        return not last_date or (today - last_date).days >= days
    return False


def add_recurring_payment(supabase, name, amount, frequency, day_of_month=None, group_name="ДОМАКИНСТВО"):
    """Insert a recurring payment."""
    try:
        data = {
            "name": name,
            "amount": amount,
            "frequency": frequency,
            "day_of_month": day_of_month,
            "group_name": group_name
        }
        supabase.table("recurring_payments").insert(data).execute()
        return True
    except Exception:
        logger.exception("Failed to add recurring payment: %s", name)
        return False


def get_active_reminders(supabase, group_name=None):
    """Fetch all active recurring reminders, optionally filtered by group."""
    try:
        query = supabase.table("recurring_payments").select("*")
        if group_name:
            query = query.eq("group_name", group_name)
        resp = query.execute()
        rows = resp.data or []
        active = [r for r in rows if r.get("is_active", True)]
        return active
    except Exception:
        logger.exception("Failed to fetch active reminders.")
        return []


def get_due_reminders(supabase, today=None):
    """Return all reminders (recurring + one-time) due today."""
    if today is None:
        today = date.today()

    due = []

    # recurring
    try:
        rec = supabase.table("recurring_payments").select("*").execute()
        for item in rec.data or []:
            if is_recurring_due(item, today):
                due.append(item)
    except Exception:
        logger.exception("Failed to fetch recurring reminders.")

    # one-time
    try:
        one_time = supabase.table("one_time_reminders")\
            .select("*")\
            .lte("reminder_date", str(today))\
            .eq("is_completed", False)\
            .execute()
        for item in one_time.data or []:
            due.append(item)
    except Exception:
        logger.exception("Failed to fetch one-time reminders.")

    return due


def add_one_time_reminder(supabase, name, amount, reminder_date, group_name="ДОМАКИНСТВО"):
    """Insert a one-time reminder."""
    try:
        data = {
            "name": name,
            "amount": amount,
            "reminder_date": reminder_date.isoformat(),
            "group_name": group_name,
            "is_completed": False
        }
        supabase.table("one_time_reminders").insert(data).execute()
        return True
    except Exception:
        logger.exception("Failed to add one-time reminder: %s", name)
        return False


def mark_one_time_completed(supabase, reminder_id):
    """Mark a one-time reminder as completed."""
    try:
        supabase.table("one_time_reminders").update({"is_completed": True}).eq("id", reminder_id).execute()
        return True
    except Exception:
        logger.exception("Failed to mark one-time reminder complete: %s", reminder_id)
        return False


def record_payment(supabase, reminder_id):
    """Mark recurring reminder as done today."""
    try:
        supabase.table("recurring_payments").update({"last_recorded_date": str(date.today())}).eq("id", reminder_id).execute()
        return True
    except Exception:
        logger.exception("Failed to record recurring reminder: %s", reminder_id)
        return False


def delete_reminder(supabase, reminder_id):
    """Delete reminder (recurring or one-time)."""
    try:
        # try one-time first
        supabase.table("one_time_reminders").delete().eq("id", reminder_id).execute()
        # then recurring
        supabase.table("recurring_payments").delete().eq("id", reminder_id).execute()
        return True
    except Exception:
        logger.exception("Failed to delete reminder: %s", reminder_id)
        return False
