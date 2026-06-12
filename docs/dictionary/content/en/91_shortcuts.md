# ⌨ Shortcuts & Tips

> Useful tips to work faster in Leonie.

## Tips by tab

### ◈ ML Studio
- You can **return to any step** without re-uploading — click the step button on the progress bar
- Sessions are **saved automatically** — close and reopen the app and it's still there
- If the model gives wrong results → redo step 4 (Clean) — data quality beats algorithm choice

### ⬡ Tasks
- The search bar supports **tag filtering**: type `#sf` to see only Salesforce tasks
- **Click directly** on a task name to edit — no need to open a separate form
- Recurring tasks: after marking done → a new task is automatically created for the next period

### ⬡ SQL → Obsidian
- **Ctrl+Enter** in the SQL text box to trigger analysis quickly
- After analysis, **title and tags** can be edited before saving
- File saves to `D:\ai_brain\SQL Queries\` → automatically indexed by Obsidian

### ⬢ Data Explorer
- **Drag multiple files** at once to compare structures
- **CORRELATION** tab → value > 0.9 between 2 columns = consider dropping one before ML
- **MISSING** tab → columns with > 30% null should usually be dropped rather than imputed

### ◉ Email
- Email digest sends to Discord **immediately** if you click Manual trigger in the Pipeline tab
- To **skip an email** without sending → click Skip (saved to history, won't prompt again)

## Streamlit keyboard shortcuts (while app is open)

| Key           | Action                                              |
|---------------|-----------------------------------------------------|
| `R`           | Reload the app (hard refresh)                       |
| `Ctrl + Enter`| Re-run current widget (text area, code box)         |
| `Esc`         | Close open dropdown / dialog                        |

## When the app has an error

```
1. Try Ctrl+C → streamlit run app.py  (restart app)
2. If import error → .venv\Scripts\python.exe -m pip install -r requirements.txt
3. If AI doesn't respond → check ANTHROPIC_API_KEY in .env
4. If Discord doesn't send → check DISCORD_WEBHOOK_URL in .env
```
