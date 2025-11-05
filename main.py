# main.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from reminder_core import (
    init_supabase, add_recurring_payment, add_one_time_reminder,
    get_due_reminders, get_active_reminders, delete_reminder
)
from notifier import show_due_popups
from config import setup_logging

logger = setup_logging("main")


GROUP_NAMES = [
    "СОЛУНСКА", "БАНКЯ", "ДОМАКИНСТВО", "АВТОМОБИЛ", "ХРАНЕНЕ",
    "НЕДА", "РАДА", "МИЛА И ГОГО", "КОТКИ", "ЛИЧНИ ГРИЖИ", "РАЗВЛЕЧЕНИЯ"
]

FREQUENCIES = ["daily", "weekly", "monthly", "quarterly", "yearly", "one-time"]


class ReminderApp:
    def __init__(self, master):
        self.master = master
        master.title("Cash Reminder App")
        master.geometry("600x500")

        self.supabase = init_supabase()

        self.tabs = ttk.Notebook(master)
        self.tabs.pack(expand=True, fill=tk.BOTH)

        self.setup_add_tab()
        self.setup_active_tab()

    # -----------------------------
    # Add Reminder Tab
    # -----------------------------
    def setup_add_tab(self):
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text="Add Reminder")

        ttk.Label(frame, text="Name:").pack(pady=3)
        self.name_entry = ttk.Entry(frame)
        self.name_entry.pack(fill=tk.X, padx=10)

        ttk.Label(frame, text="Amount:").pack(pady=3)
        self.amount_entry = ttk.Entry(frame)
        self.amount_entry.pack(fill=tk.X, padx=10)

        ttk.Label(frame, text="Frequency:").pack(pady=3)
        self.freq_var = tk.StringVar(value="monthly")
        self.freq_dropdown = ttk.Combobox(frame, values=FREQUENCIES, textvariable=self.freq_var, state="readonly")
        self.freq_dropdown.pack(fill=tk.X, padx=10)

        ttk.Label(frame, text="Day of month (if recurring):").pack(pady=3)
        self.day_entry = ttk.Entry(frame)
        self.day_entry.pack(fill=tk.X, padx=10)

        ttk.Label(frame, text="One-time date (YYYY-MM-DD):").pack(pady=3)
        self.date_entry = ttk.Entry(frame)
        self.date_entry.pack(fill=tk.X, padx=10)

        ttk.Label(frame, text="Group:").pack(pady=3)
        self.group_var = tk.StringVar(value="ДОМАКИНСТВО")
        self.group_dropdown = ttk.Combobox(frame, values=GROUP_NAMES, textvariable=self.group_var, state="readonly")
        self.group_dropdown.pack(fill=tk.X, padx=10)

        ttk.Button(frame, text="Add Reminder", command=self.add_reminder).pack(pady=10)
        ttk.Button(frame, text="Check Due Now", command=lambda: show_due_popups(self.supabase)).pack(pady=5)

    # -----------------------------
    # Active Reminders Tab
    # -----------------------------
    def setup_active_tab(self):
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text="Active Reminders")

        self.tree = ttk.Treeview(frame, columns=("name", "amount", "frequency", "day", "date", "group"), show="headings")
        self.tree.heading("name", text="Name")
        self.tree.heading("amount", text="Amount")
        self.tree.heading("frequency", text="Frequency")
        self.tree.heading("day", text="Day")
        self.tree.heading("date", text="One-time Date")
        self.tree.heading("group", text="Group")
        self.tree.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        ttk.Button(frame, text="Refresh", command=self.refresh_active).pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Button(frame, text="Delete Selected", command=self.delete_selected).pack(side=tk.LEFT, padx=10, pady=5)

        self.refresh_active()

    # -----------------------------
    # Add reminder action
    # -----------------------------
    def add_reminder(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name required.")
            return

        amount = float(self.amount_entry.get() or 0)
        freq = self.freq_var.get().strip().lower()
        day = int(self.day_entry.get() or 0) or None
        date_str = self.date_entry.get().strip() or None
        group = self.group_var.get().strip()

        success = False
        if freq == "one-time":
            if not date_str:
                messagebox.showerror("Error", "Date required for one-time reminder.")
                return
            try:
                dt = datetime.fromisoformat(date_str).date()
            except Exception:
                messagebox.showerror("Error", "Invalid date format.")
                return
            success = add_one_time_reminder(self.supabase, name, amount, dt, group)
        else:
            success = add_recurring_payment(self.supabase, name, amount, freq, day, group)

        if success:
            messagebox.showinfo("Success", "Reminder added!")
            self.refresh_active()
        else:
            messagebox.showerror("Error", "Failed to add reminder.")

    # -----------------------------
    # Active reminders actions
    # -----------------------------
    def refresh_active(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        reminders = get_active_reminders(self.supabase)
        for r in reminders:
            self.tree.insert("", tk.END, values=(
                r.get("name"),
                r.get("amount", 0),
                r.get("frequency"),
                r.get("day_of_month") or "",
                r.get("reminder_date") or "",
                r.get("group_name") or ""
            ))

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        confirm = messagebox.askyesno("Confirm", "Delete selected reminder(s)?")
        if not confirm:
            return
        for item_id in selected:
            values = self.tree.item(item_id)["values"]
            name = values[0]
            reminder_id = self.get_reminder_id_by_name(name)
            if reminder_id:
                delete_reminder(self.supabase, reminder_id)
        self.refresh_active()

    def get_reminder_id_by_name(self, name):
        reminders = get_active_reminders(self.supabase)
        for r in reminders:
            if r.get("name") == name:
                return r.get("id")
        return None


if __name__ == "__main__":
    root = tk.Tk()
    app = ReminderApp(root)
    root.mainloop()
