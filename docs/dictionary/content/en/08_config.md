# ⊛ Config

> View environment variables currently loaded from the `.env` file. Read-only — do not edit here.

## Key variables

| Variable               | Used for                                       |
|------------------------|------------------------------------------------|
| `ANTHROPIC_API_KEY`    | All AI features (ML insight, email, SQL)       |
| `OLLAMA_BASE_URL`      | Fallback when Claude API is unavailable        |
| `DISCORD_WEBHOOK_URL`  | Sending reminders and digests to Discord       |
| `OBSIDIAN_VAULT_PATH`  | Obsidian vault path for saving SQL notes       |

## How to change config

```
1. Open the .env file at the project root
2. Edit the value you want to change
3. Restart the app: Ctrl+C → streamlit run app.py
```

## Security notes

- Do not commit the `.env` file to git (already in `.gitignore`)
- If an API key is leaked → revoke it immediately at console.anthropic.com
- See `.env.example` for the required format
