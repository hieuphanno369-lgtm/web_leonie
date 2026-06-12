# ◉ Email

> Read Outlook emails, AI classifies by priority, summarises, suggests replies.

## Email Pipeline

```
Outlook → Read emails → Classify priority → Summarise → Suggest reply → Send Discord digest
```

## Steps

| Step             | What the app does                                         |
|------------------|-----------------------------------------------------------|
| Read Outlook     | Uses win32com to read inbox (requires Outlook desktop)    |
| Classify         | Rule-based + AI → assigns priority: Urgent / Normal / FYI|
| Summarise        | Claude AI summarises the main content in 2-3 sentences    |
| Suggest reply    | 3 reply options from brief to detailed                    |
| Discord digest   | Compiles important emails → sends to Discord channel      |

## Notes

- Requires **Outlook desktop** open and logged in
- Requires `ANTHROPIC_API_KEY` for AI summary/reply
- Processed emails are saved to `data/email_history.json` to avoid duplicates
- Learns from your past emails to suggest replies that match your writing style
