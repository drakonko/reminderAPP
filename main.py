import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from reminder_core import (
    init_supabase, add_recurring_payment, add_one_time_reminder,
    get_due_reminders, get_active_reminders, delete_reminder, get_active_one_time
)
from notifier import show_due_popups
from config import setup_logging

logger = setup_logging("main")


GROUP_NAMES = [
    "СОЛУНСКА", "БАНКЯ", "ДОМАКИНСТВО", "АВТОМОБИЛ", "ХРАНЕНЕ",
    "НЕДА", "РАДА", "МИЛА И ГOГО", "КОТКИ", "ЛИЧНИ ГРИЖИ", "РАЗВЛЕЧЕНИЯ"
]

FREQUENCIES = ["daily", "weekly", "monthly", "quarterly", "yearly", "one-time"]


class ReminderApp:
    def __init__(self, master):
        self.master = master
        master.title("Cash Reminder App")
        master.geometry("700x520")

        # Widgets that will be created in setup methods — initialize to None so set_offline_mode can access
        self.add_button = None
        self.check_button = None
        self.refresh_button = None
        self.delete_button = None
        self.status_label = None

        # Try to initialize Supabase; on failure continue in offline mode
        try:
            self.supabase = init_supabase()
            self.online = True
        except Exception as e:
            logger.warning("Supabase init failed at startup: %s", e)
            self.supabase = None
            self.online = False

        self.tabs = ttk.Notebook(master)
        self.tabs.pack(expand=True, fill=tk.BOTH)

        self.setup_add_tab()
        self.setup_active_tab()

        # If offline, set UI accordingly and show a persistent status label
        if not self.online:
            self.set_offline_mode()

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

        self.add_button = ttk.Button(frame, text="Add Reminder", command=self.add_reminder)
        self.add_button.pack(pady=10)

        self.check_button = ttk.Button(
            frame,
            text="Check Due Now",
            command=lambda: show_due_popups(self.supabase) if self.online else messagebox.showwarning("Offline", "No database connection")
        )
        self.check_button.pack(pady=5)

    # -----------------------------
    # Active Reminders Tab
    # -----------------------------
    def setup_active_tab(self):
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text="Active Reminders")

        # Controls: group filter + include one-time checkbox + refresh/delete buttons
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill=tk.X, padx=10, pady=(8, 0))

        ttk.Label(control_frame, text="Group:").pack(side=tk.LEFT, padx=(0, 6))
        self.active_group_var = tk.StringVar(value="All")
        group_values = ["All"] + GROUP_NAMES
        self.active_group_dropdown = ttk.Combobox(control_frame, values=group_values, textvariable=self.active_group_var, state="readonly", width=20)
        self.active_group_dropdown.pack(side=tk.LEFT)

        self.include_one_time_var = tk.BooleanVar(value=True)
        self.include_one_time_cb = ttk.Checkbutton(control_frame, text="Include one-time", variable=self.include_one_time_var)
        self.include_one_time_cb.pack(side=tk.LEFT, padx=10)

        self.refresh_button = ttk.Button(control_frame, text="Refresh", command=self.refresh_active)
        self.refresh_button.pack(side=tk.RIGHT, padx=10)

        self.delete_button = ttk.Button(control_frame, text="Delete Selected", command=self.delete_selected)
        self.delete_button.pack(side=tk.RIGHT)

        # Treeview listing reminders (columns adjusted)
        self.tree = ttk.Treeview(frame, columns=("name", "amount", "frequency", "day", "group"), show="headings")
        self.tree.heading("name", text="Name")
        self.tree.heading("amount", text="Amount")
        self.tree.heading("frequency", text="Frequency")
        self.tree.heading("day", text="Day")
        self.tree.heading("group", text="Group")
        self.tree.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        self.refresh_active()

    # -----------------------------
    # Helpers for offline mode
    # -----------------------------
    def set_offline_mode(self):
        """Adjust UI when database is not available: disable DB actions and show a status label."""
        if self.add_button:
            try:
                self.add_button.state(["disabled"])
            except Exception:
                self.add_button.config(state=tk.DISABLED)
        if self.check_button:
            try:
                self.check_button.state(["disabled"])
            except Exception:
                self.check_button.config(state=tk.DISABLED)
        if self.refresh_button:
            try:
                self.refresh_button.state(["disabled"])
            except Exception:
                self.refresh_button.config(state=tk.DISABLED)
        if self.delete_button:
            try:
                self.delete_button.state(["disabled"])
            except Exception:
                self.delete_button.config(state=tk.DISABLED)

        # Add a persistent status label at the bottom of the main window
        if not self.status_label:
            self.status_label = ttk.Label(self.master, text="Offline: No database connection", foreground="red")
            self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def clear_offline_status(self):
        if self.status_label:
            self.status_label.destroy()
            self.status_label = None

    # -----------------------------
    # Add reminder action
    # -----------------------------
    def add_reminder(self):
        if not self.online or not self.supabase:
            messagebox.showerror("Offline", "Cannot add reminders while offline.")
            return

        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name required.")
            return

        try:
            amount = float(self.amount_entry.get() or 0)
        except ValueError:
            messagebox.showerror("Error", "Amount must be a number.")
            return

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

        if not self.online or not self.supabase:
            # Show a single placeholder row to indicate offline
            self.tree.insert("", tk.END, values=("(offline)", "", "", "", ""))
            return

        group = self.active_group_var.get()
        group_name = None if group == "All" else group

        # recurring reminders
        recurring = get_active_reminders(self.supabase, group_name=group_name) or []
        for r in recurring:
            self.tree.insert("", tk.END, values=(
                r.get("name"),
                r.get("amount", 0),
                r.get("frequency"),
                r.get("day_of_month") or "",
                r.get("group_name") or ""
            ))

        # one-time reminders (if enabled)
        if self.include_one_time_var.get():
            one_time = get_active_one_time(self.supabase, group_name=group_name) or []
            for r in one_time:
                self.tree.insert("", tk.END, values=(
                    r.get("name"),
                    r.get("amount", 0),
                    "one-time",
                    "",
                    r.get("group_name") or ""
                ))

    def delete_selected(self):
        if not self.online or not self.supabase:
            messagebox.showerror("Offline", "Cannot delete reminders while offline.")
            return

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
        if not self.online or not self.supabase:
            return None
        reminders = get_active_reminders(self.supabase)
        for r in reminders:
            if r.get("name") == name:
                return r.get("id")
        # check one-time as well
        one_time = get_active_one_time(self.supabase)
        for r in one_time:
            if r.get("name") == name:
                return r.get("id")
        return None


if __name__ == "__main__":
    root = tk.Tk()
    app = ReminderApp(root)
    root.mainloop()
