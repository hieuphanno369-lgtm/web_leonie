# ⬢ Data Explorer

> Upload a file → the app automatically analyses and shows you everything you need to know before doing anything else.

## What is it for?

When you have a new data file and don't know what's inside — Data Explorer is the first place to visit.

## Supported file formats

| Format  | Extension        |
|---------|------------------|
| CSV     | `.csv`           |
| Excel   | `.xlsx`, `.xls`  |
| Parquet | `.parquet`       |

## 5 tabs generated automatically after upload

| Tab         | What it shows                                              |
|-------------|-----------------------------------------------------------|
| HEAD        | First 5 rows of the data                                  |
| DTYPES      | Data type of each column (int, float, string, datetime…)  |
| MISSING     | % missing per column, visual bar chart                    |
| STATS       | Min, max, mean, median, std for numeric columns           |
| CORRELATION | Correlation heatmap between numeric columns               |

## Tips

- Check **MISSING** first: columns with > 30% missing should usually be dropped before ML
- **CORRELATION** > 0.9 between 2 columns → keep only one (multicollinearity)
- Once you understand the data → move to **ML Studio** for deeper analysis
