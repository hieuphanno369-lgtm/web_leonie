# ◉ Pipeline Monitor

> View scheduler status, manually trigger Discord notifications, check system health.

## Scheduled jobs

| Job                | Run time   | What it does                                       |
|--------------------|------------|----------------------------------------------------|
| Morning reminder   | 09:00      | Sends today's task list to Discord                 |
| Afternoon reminder | 13:30      | Reminds about unfinished tasks + overdue tasks     |

## Features in this tab

- **Manual trigger**: click the button to send a Discord notification immediately (no waiting for schedule)
- **Health check**: verify that the Discord webhook is working
- **Job status**: see when the last job ran and whether it had errors

## Notes

- Scheduler runs via `scheduler.py` — this file must be running in the background
- Requires `DISCORD_WEBHOOK_URL` in `.env`
- If Discord webhook fails → check the URL in `.env` first
