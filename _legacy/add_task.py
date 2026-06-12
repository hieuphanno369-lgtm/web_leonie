"""
add_task.py — CLI nhập task mới.
Chạy: python add_task.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from rich.console import Console
from rich.panel import Panel

from modules.deadline import calculate_deadline, get_label
from modules.ollama_client import generate_checklist
from modules.obsidian_client import get_context
from modules.task_manager import add_task
from modules.discord_notifier import send_confirm

console = Console()

CATEGORIES = {"1": "high", "2": "medium", "3": "low", "4": "ad-hoc"}
RECUR_OPTIONS = {"1": None, "2": "monthly", "3": "yearly"}
RECUR_LABELS  = {None: "—", "monthly": "🔄 Hằng tháng", "yearly": "🔁 Hằng năm"}


def ask(prompt: str, required: bool = True) -> str:
    while True:
        val = input(prompt).strip()
        if val or not required:
            return val
        console.print("[red]Cannot be empty.[/red]")


def ask_date(prompt: str) -> str:
    while True:
        val = input(prompt).strip()
        if len(val) == 10 and val[4] == "-" and val[7] == "-":
            return val
        console.print("[red]Format must be YYYY-MM-DD (ví dụ: 2026-04-30)[/red]")


def run() -> None:
    console.print(Panel("📝 [bold cyan]Enter new task[/bold cyan]", expand=False))

    task_name = ask("Task name: ")
    start_date = ask_date("Start-date (YYYY-MM-DD): ")
    end_date = ask_date("End-date (YYYY-MM-DD): ")

    console.print("  [cyan]1[/cyan] 🔴 High    [cyan]2[/cyan] 🟡 Medium    [cyan]3[/cyan] 🟢 Low    [cyan]4[/cyan] ⚡ Ad-hoc")
    while True:
        cat_key = input("Category (1-4): ").strip()
        if cat_key in CATEGORIES:
            category = CATEGORIES[cat_key]
            break
        console.print("[red]Select 1, 2, 3, or 4.[/red]")

    note = ask("Notes (Press Enter to skip): ", required=False) or "(none)"

    console.print("  Lặp lại định kỳ: [cyan]1[/cyan] Không  [cyan]2[/cyan] Hằng tháng  [cyan]3[/cyan] Hằng năm")
    while True:
        recur_key = input("Lặp lại (1-3): ").strip()
        if recur_key in RECUR_OPTIONS:
            recur = RECUR_OPTIONS[recur_key]
            break
        console.print("[red]Chọn 1, 2, hoặc 3.[/red]")

    task = {
        "task_name":      task_name,
        "start_date":     start_date,
        "end_date":       end_date,
        "category_raw":   category,
        "category_label": get_label(category),
        "deadline":       calculate_deadline(end_date, category),
        "note":           note,
        "recur":          recur,
    }

    # Search vault bằng cả tên task + từ khóa trong ghi chú
    console.print("[dim]Reading Obsidian vault...[/dim]")
    search_keywords = task_name.split() + note.split()
    obsidian_context = get_context(search_keywords)

    # Sinh checklist bằng Ollama (bỏ qua nếu Ollama không chạy)
    console.print("[dim]Generating checklist for you...[/dim]")
    checklist = generate_checklist(
        task["task_name"],
        task["category_label"],
        task["deadline"],
        task["note"],
        obsidian_context,
    )
    if not checklist:
        console.print("[yellow]⚠️ Ollama is not running — skipping AI checklist[/yellow]")
    task["checklist"] = checklist

    # Lưu task
    saved = add_task(task)

    recur_display = RECUR_LABELS.get(saved.get("recur"), "—")
    console.print(Panel(
        f"[bold]{saved['task_name']}[/bold]\n"
        f"{saved['category_label']}   Deadline: {saved['deadline']}\n"
        f"Lặp lại: {recur_display}\n"
        f"Ghi chú: {saved['note']}\n\n"
        f"Checklist:\n{checklist}",
        title="✅ Task đã lưu!",
        border_style="green",
    ))

    # Gửi Discord
    console.print("[dim]Sending Discord confirmation...[/dim]")
    ok = send_confirm(saved)
    if ok:
        console.print("[green]✅ Discord message sent.[/green]")
    else:
        console.print("[yellow]⚠️  Failed to send Discord message (check .env).[/yellow]")


if __name__ == "__main__":
    run()
