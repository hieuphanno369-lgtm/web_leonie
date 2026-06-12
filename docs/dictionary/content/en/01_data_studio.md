# ◈ Data Studio

> Your data analysis room. 4 tools in one place — from exploration to prediction.

## 4 Sub-views

| Sub-view        | When to use                                      | Output                          |
|-----------------|--------------------------------------------------|---------------------------------|
| Data Explorer   | Upload a file → need to understand the structure | Stats, missing%, correlation    |
| SQL → Obsidian  | Have a SQL query → want to analyse + save a note | .md file in Obsidian vault      |
| ⚗ ML Studio    | Have data → want to forecast or cluster          | Model + chart + AI insight      |
| Snippets        | Have a reusable SQL query → want to store it     | Personal SQL library            |

## Typical flow

```
1. Upload CSV/Excel/Parquet into Data Explorer
   → Check columns, missing values, distribution

2. If you need SQL to filter/aggregate:
   → Go to SQL → Obsidian → paste SQL → analyse → save note

3. Once you understand the data:
   → Go to ML Studio → upload the clean file → run the 8-step pipeline

4. Save frequently used SQL:
   → Go to Snippets → add snippet → assign tag
```

## Notes

- Data Explorer and ML Studio **are not directly connected** — you need to export/save the file then re-upload
- SQL → Obsidian writes `.md` files to `D:\ai_brain\SQL Queries\` — the Obsidian vault must be mounted
- ML Studio saves sessions at `data/ml_sessions/` — you can continue from any step
