# ⚗ ML Studio

> Let the app analyse your data — no coding knowledge, no ML knowledge required.

---

## What is ML Studio?

Imagine you have two years of sales figures.

**ML Studio is like a smart friend** — you hand it the file, it asks itself *"What question is this data trying to answer?"*, then picks the right analysis method and explains the results in plain language.

You don't need to know what SARIMAX is. You just need to know: *"I want to forecast next month's revenue."*

---

## 8-Step Pipeline

```
[1] Upload  →  [2] Detect Header  →  [3] EDA  →  [4] Clean
     ↓
[5] Feature Select  →  [6] AI Recommend  →  [7] Train  →  [8] Result + Insight
```

| Step | Name              | You do                           | App does                                           |
|------|-------------------|----------------------------------|----------------------------------------------------|
| 1    | Upload            | Drag in a CSV/Excel file         | Reads file, detects encoding, loads into memory    |
| 2    | Detect Header     | Confirm column names             | Auto-detects header row, asks if file is complex   |
| 3    | EDA               | Review data overview             | Stats, % missing, correlation, distribution        |
| 4    | Clean             | Choose how to handle null values | Drop rows/columns, fill mean/median, or impute     |
| 5    | Feature Select    | See which columns matter most    | Calculates feature importance, suggests removals   |
| 6    | AI Recommend      | Confirm problem + algorithm      | Claude AI suggests the best algorithm + reasoning  |
| 7    | Train             | Click Train                      | Runs the model, computes metrics, saves results    |
| 8    | Result + Insight  | Read the output                  | Draws charts + writes commentary in plain language |

**Important:** You can return to any step without re-uploading the file. Sessions are saved at `data/ml_sessions/`.

---

## Available Algorithms

### XGBoost — Classification & Regression

> **Analogy:** Ask 500 different friends for their opinion. Each one looks at the data from a different angle, then the group votes on the answer. Friends who are often wrong get less say next time — so the group gets smarter over time.

| | |
|-|-|
| **Use when** | Predicting a number (revenue, conversion rate) or classifying (yes/no, group A/B/C) |
| **Input needed** | A table with a clear **target column** (the column you want to predict) |
| **Output** | Predicted values + Feature Importance chart (which columns matter most) |
| **Strengths** | High accuracy, handles missing values well, fast |
| **Weaknesses** | Hard to explain *why* for each individual prediction |

---

### Random Forest — Classification & Regression

> **Analogy:** Like XGBoost but those 500 friends learn **completely independently** — no one knows what the others are learning. More diverse results, less prone to memorising the training data.

| | |
|-|-|
| **Use when** | Similar to XGBoost; especially good when data is small or has many outliers |
| **Input needed** | Table with a target column |
| **Output** | Predicted values + Feature Importance |
| **vs XGBoost** | More stable, less overfitting, slightly slower |

---

### SARIMAX — Time Series Forecasting

> **Analogy:** You have 24 months of sales data. SARIMAX looks at it and learns 3 things: (1) the long-term upward/downward trend, (2) recurring seasonal cycles (December is always higher), (3) external factors you provide like promotions or holidays. Then it says: *"Next month you'll sell around X, ±Y margin of error"*.

| | |
|-|-|
| **Use when** | Data is a time series by day/week/month **and** has clear seasonality |
| **Minimum needed** | 24 data points (24 months, or 24 weeks…) |
| **Input needed** | Date column + value column; optionally: exogenous variable columns |
| **Output** | Forecast line (orange) + confidence interval band (shaded area) |
| **Strengths** | Handles seasonality well, can incorporate external variables |
| **Weaknesses** | Needs at least 24 points; gaps in data cause problems |

**Reading the SARIMAX chart:**
- **Blue line** = actual historical data
- **Orange line** = forecast
- **Shaded band** = confidence interval — actual values will fall here with ~95% probability

---

### Prophet — Time Series Forecasting

> **Analogy:** Like SARIMAX but much more relaxed — it automatically handles holidays, no need to tune complex parameters. Best when data has gaps or unusual days.

| | |
|-|-|
| **Use when** | Time series with holiday effects, irregular data, or you want a quick setup |
| **Input needed** | Date column (named `ds`) + value column (named `y`) |
| **Output** | Forecast line + uncertainty band + decomposition (trend, seasonality, holidays) |
| **vs SARIMAX** | Easier to use, less control; good for short-to-medium-term forecasts |

---

### KMeans — Clustering

> **Analogy:** You have 1,000 customers and don't know how many groups to split them into. KMeans tries many different groupings, scores each one, then tells you which grouping is the most natural — without you needing to specify how many groups upfront.

| | |
|-|-|
| **Use when** | Segmenting customers, SKUs, regions — no labels available |
| **Input needed** | A table **without a target column** (unsupervised) |
| **Output** | Scatter plot with colour-coded clusters + table of each cluster's characteristics |
| **Strengths** | No labelled data required |
| **Weaknesses** | Results depend on the choice of K (number of clusters) |

---

## Which algorithm should I use?

| Your question                                         | Suggested algorithm          |
|-------------------------------------------------------|------------------------------|
| How much will I sell next month?                      | SARIMAX or Prophet           |
| Will this customer buy again?                         | XGBoost or Random Forest     |
| Which factors affect revenue most?                    | XGBoost (Feature Importance) |
| How should I segment my customers?                    | KMeans                       |
| Data has gaps and complex holiday patterns?           | Prophet                      |
| Small data (<500 rows), many outliers?                | Random Forest                |

---

## Reading results — Evaluation metrics

See detailed explanations in: **📚 Glossary**

| Metric           | Algorithm                    | Short meaning                              |
|------------------|------------------------------|--------------------------------------------|
| MAPE             | SARIMAX, Prophet             | How many % off vs actual                   |
| RMSE             | XGBoost, RF, SARIMAX         | Average error in original units            |
| Silhouette Score | KMeans                       | How well-separated are the clusters?       |
| R²               | XGBoost, RF                  | What % of variance does the model explain? |
| Accuracy / F1    | XGBoost, RF (classification) | What % of predictions are correct?         |
