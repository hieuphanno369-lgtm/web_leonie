"""
main.py — Menu chính của Task Tracker.
Chạy: python main.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import os
import time
import threading
import schedule
from dotenv import load_dotenv, find_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import date

load_dotenv(find_dotenv(), encoding='utf-8')

from modules.task_manager import (
    load_tasks, get_active_tasks, deactivate_expired,
    update_task, delete_task,
)
from modules.deadline import calculate_deadline
from modules.discord_notifier import send_all_reminders

REMINDER_TIME_1 = os.getenv("REMINDER_TIME_1", "08:40")


def _run_reminders() -> None:
    deactivate_expired()
    tasks = get_active_tasks()
    send_all_reminders(tasks)


def _start_scheduler() -> None:
    schedule.every().day.at(REMINDER_TIME_1).do(_run_reminders)
    while True:
        schedule.run_pending()
        time.sleep(30)

console = Console()

MENU = [
    ("1", "➕",  "Add new task"),
    ("2", "📋",  "View all tasks"),
    ("3", "✏️",  "Edit deadline"),
    ("4", "🗑️",  "Delete task"),
    ("5", "🔔",  "Send reminder now"),
    ("6", "♻️",  "Archive expired tasks"),
    ("0", "❌",  "Exit"),
]


def print_menu() -> None:
    console.print()
    console.print("  [dim]─────────────────────────────────────[/dim]")
    for key, icon, label in MENU:
        console.print(f"  [cyan]{key}[/cyan]   {icon}   {label}")
    console.print("  [dim]─────────────────────────────────────[/dim]")
    console.print()


def ask(prompt: str) -> str:
    return input(prompt).strip()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pick_task(prompt: str = "Select task") -> dict | None:
    tasks = load_tasks()
    if not tasks:
        console.print("[yellow]No tasks found.[/yellow]")
        return None

    today = date.today().isoformat()
    console.print()
    for i, t in enumerate(tasks, 1):
        status = "[green]Active[/green]" if (t.get("active") and t.get("deadline", "") >= today) else "[dim]Archived[/dim]"
        console.print(f"  [cyan]{i}[/cyan]   {t['task_name']:<35} {t['category_label']:<12}  deadline: {t['deadline']}   {status}")
    console.print()

    raw = ask(f"{prompt} (1-{len(tasks)}): ")
    if not raw.isdigit() or not (1 <= int(raw) <= len(tasks)):
        console.print("[red]Invalid number.[/red]")
        return None
    return tasks[int(raw) - 1]


# ── Actions ───────────────────────────────────────────────────────────────────

def show_tasks() -> None:
    tasks = load_tasks()
    if not tasks:
        console.print("[yellow]No tasks found.[/yellow]")
        return

    RECUR_LABELS = {None: "—", "monthly": "🔄 Monthly", "yearly": "🔁 Yearly"}

    today = date.today().isoformat()
    table = Table(title="Task List", show_lines=True, header_style="bold cyan")
    table.add_column("#",        justify="right", style="dim", width=3)
    table.add_column("Task",     style="bold")
    table.add_column("Category", justify="center")
    table.add_column("Start",    justify="center")
    table.add_column("End",      justify="center")
    table.add_column("Deadline", justify="center")
    table.add_column("Recur",    justify="center")
    table.add_column("Status",   justify="center")

    for i, t in enumerate(tasks, 1):
        is_active = t.get("active") and t.get("deadline", "") >= today
        status = "[green]Active[/green]" if is_active else "[dim]Archived[/dim]"
        deadline_str = t["deadline"]
        if is_active and t["deadline"] == today:
            deadline_str = f"[red]{deadline_str} TODAY![/red]"
        recur_display = RECUR_LABELS.get(t.get("recur"), "—")
        table.add_row(
            str(i),
            t["task_name"],
            t["category_label"],
            t.get("start_date", "—"),
            t.get("end_date", "—"),
            deadline_str,
            recur_display,
            status,
        )

    console.print(table)
    console.print(f"[dim]data/tasks.json  •  Total: {len(tasks)} task(s)[/dim]")


def edit_deadline() -> None:
    task = _pick_task("Select task to edit")
    if not task:
        return

    console.print(f"  Current end date : [yellow]{task['end_date']}[/yellow]")
    console.print(f"  Current deadline : [yellow]{task['deadline']}[/yellow]")

    new_end = ask("New end date (YYYY-MM-DD): ")
    if len(new_end) != 10 or new_end[4] != "-" or new_end[7] != "-":
        console.print("[red]Invalid format. Use YYYY-MM-DD.[/red]")
        return

    new_deadline = calculate_deadline(new_end, task["category_raw"])
    update_task(task["task_id"], {"end_date": new_end, "deadline": new_deadline, "active": True})
    console.print(f"[green]Updated:[/green] end_date={new_end}  →  deadline={new_deadline}")


def remove_task() -> None:
    task = _pick_task("Select task to delete")
    if not task:
        return

    confirm = ask(f"Confirm delete '{task['task_name']}'? (y/N): ")
    if confirm.lower() != "y":
        console.print("[dim]Cancelled.[/dim]")
        return

    if delete_task(task["task_id"]):
        console.print(f"[red]Deleted:[/red] {task['task_name']}")
    else:
        console.print("[red]Task not found.[/red]")


# ── Main loop ─────────────────────────────────────────────────────────────────

def run() -> None:
    t = threading.Thread(target=_start_scheduler, daemon=True)
    t.start()

    console.print(Panel(
        "[bold cyan]Task Tracker[/bold cyan]\n"
        "[dim]Discord · Obsidian · Ollama[/dim]\n"
        f"[dim]Reminder: {REMINDER_TIME_1}   •   Storage: data/tasks.json[/dim]",
        expand=False,
    ))

    while True:
        print_menu()
        choice = ask("Select (0-6): ")

        if choice == "0":
            console.print("[dim]Goodbye![/dim]")
            sys.exit(0)

        elif choice == "1":
            import add_task
            add_task.run()

        elif choice == "2":
            show_tasks()

        elif choice == "3":
            edit_deadline()

        elif choice == "4":
            remove_task()

        elif choice == "5":
            tasks = get_active_tasks()
            console.print(f"[cyan]{len(tasks)} active task(s) — sending reminders...[/cyan]")
            send_all_reminders(tasks)

        elif choice == "6":
            archived, renewed = deactivate_expired()
            if archived:
                console.print(f"[green]Archived {archived} expired task(s).[/green]")
            if renewed:
                console.print(f"[cyan]Auto-renewed {renewed} recurring task(s).[/cyan]")
            if not archived and not renewed:
                console.print("[dim]No expired tasks.[/dim]")

        else:
            console.print("[red]Please select 0 to 6.[/red]")


if __name__ == "__main__":
    run()
