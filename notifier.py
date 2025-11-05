# notifier.py
import os
import webbrowser
import locale
import tkinter as tk
from tkinter import messagebox, Toplevel, Label, Button
from datetime import date
from plyer import notification
from config import APP_NAME, ICON_PATH, SPREADSHEET_URL, setup_logging
from reminder_core import (
    record_payment,
    mark_one_time_completed,
    get_due_reminders,
    delete_reminder
)

logger = setup_logging("notifier")


def format_currency(amount):
    try:
        locale.setlocale(locale.LC_ALL, "")
        return locale.currency(amount, grouping=True)
    except Exception:
        return f"${float(amount):.2f}"


def send_native_notification(title, message):
    try:
        notification.notify(
            title=title,
            message=message,
            app_name=APP_NAME,
            app_icon=ICON_PATH if os.path.exists(ICON_PATH) else None,
            timeout=10
        )
        return True
    except Exception:
        logger.exception("Notification failed.")
        return False


class ReminderPopup:
    AUTO_CLOSE_MS = 60_000  # 1 minute

    def __init__(self, master, item, supabase, one_time=False):
        self.master = master
        self.item = item
        self.supabase = supabase
        self.one_time = one_time

        master.title("Reminder Due")
        master.geometry("400x200")
        master.resizable(False, False)
        master.grab_set()

        Label(master, text=f"Reminder: {item.get('name')}", font=("Arial", 14, "bold")).pack(pady=(10,5))
        Label(master, text=f"Amount: {format_currency(item.get('amount', 0))}", font=("Arial", 12)).pack()

        btn_frame = tk.Frame(master)
        btn_frame.pack(pady=20)
        Button(btn_frame, text="Mark Done", bg="green", fg="white", command=self.mark_done).pack(side=tk.LEFT, padx=8)
        Button(btn_frame, text="Open Sheet", bg="blue", fg="white", command=self.open_sheet).pack(side=tk.LEFT, padx=8)

        if ReminderPopup.AUTO_CLOSE_MS:
            master.after(ReminderPopup.AUTO_CLOSE_MS, master.destroy)

    def mark_done(self):
        if self.one_time:
            mark_one_time_completed(self.supabase, self.item.get("id"))
        else:
            record_payment(self.supabase, self.item.get("id"))
        messagebox.showinfo("Marked", "Reminder marked done.")
        self.master.destroy()

    def open_sheet(self):
        webbrowser.open(SPREADSHEET_URL)


def show_due_popups(supabase):
    today = date.today()
    due_recurring = get_due_recurring(supabase, today)
    due_one_time = get_due_one_time(supabase, today)
    all_due = due_recurring + due_one_time

    if not all_due:
        logger.info("No reminders due today.")
        return

    # Show native notification with summary
    names = [d['name'] for d in all_due[:3]]
    send_native_notification(f"{len(all_due)} reminders due today", ", ".join(names))

    # Tkinter popups
    root = tk.Tk()
    root.withdraw()
    for item in due_recurring:
        win = Toplevel(root)
        ReminderPopup(win, item, supabase, one_time=False)
    for item in due_one_time:
        win = Toplevel(root)
        ReminderPopup(win, item, supabase, one_time=True)
    root.mainloop()
