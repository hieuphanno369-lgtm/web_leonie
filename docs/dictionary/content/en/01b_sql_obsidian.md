# ⬡ SQL → Obsidian

> Paste a SQL query → the app analyses the business intent → optimises → saves as a `.md` note in your Obsidian vault.

## What is it for?

When you write SQL to answer a business question, you want to:
- Know **what the query is asking** (not the syntax — the meaning)
- Have an **optimised** version that runs faster if possible
- **Save it** in a searchable way in Obsidian for future reference

## How to use

```
1. Paste the SQL query into the text box
2. Click Analyse → the app sends it to Claude AI for analysis
3. Review results: business intent, optimisation suggestions, tags
4. Adjust the title / tags if needed
5. Click Save → the .md file is written to D:\ai_brain\SQL Queries\
```

## What does the output .md file contain?

- Title and business question
- Original SQL query
- Optimised SQL query (if improvements were found)
- Tags for future search
- Tables used in the query
- Date saved

## Notes

- Requires `ANTHROPIC_API_KEY` in `.env` for AI analysis
- If no API key → falls back to local Ollama
- Files are saved at `D:\ai_brain\SQL Queries\` — this path must exist
