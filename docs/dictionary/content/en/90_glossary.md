# 📚 Glossary — Common Terms

> Short explanations, no padding. If you see an unfamiliar term in ML Studio → look here.

## Model evaluation metrics

| Term                   | Simple meaning                                                                  | Good when            |
|------------------------|---------------------------------------------------------------------------------|----------------------|
| **MAPE**               | How many % off the prediction is vs actual (Mean Absolute Percentage Error)    | Lower is better      |
| **RMSE**               | Average error in the original unit (Root Mean Squared Error)                   | Lower is better      |
| **R²**                 | What % of the data's variance the model explains (0→1)                         | Closer to 1 is better|
| **Accuracy**           | Ratio of correct predictions to total predictions (for classification)          | Higher is better     |
| **F1 Score**           | Balance between Precision and Recall — use when data is imbalanced             | Closer to 1 is better|
| **Silhouette Score**   | How clearly separated the KMeans clusters are (-1→1)                           | Closer to 1 is better|
| **AIC / BIC**          | SARIMAX evaluation score — which model fits better with fewer parameters       | Lower is better      |

## ML Concepts

| Term                   | Simple meaning                                                                   |
|------------------------|----------------------------------------------------------------------------------|
| **Overfitting**        | Model memorises old data but predicts new data poorly — like rote learning       |
| **Feature Importance** | Which column affects the prediction result the most                              |
| **Confidence Interval**| Forecast band — actual values will fall here with ~95% probability               |
| **Seasonality**        | Recurring cycles by season/month/week — e.g. December is always higher           |
| **Exogenous variable** | External variable added to help the forecast — e.g. promotion dates             |
| **Imputation**         | Automatically filling null values instead of deleting the entire row             |
| **Cross-validation**   | Testing the model by splitting data into multiple parts and testing each part     |

## Data formats

| Term           | Meaning                                                             |
|----------------|---------------------------------------------------------------------|
| **CSV**        | Text file, values separated by commas                               |
| **Parquet**    | Compressed binary file — loads much faster than CSV for large data  |
| **Long format**| Each row is 1 observation (date × product) — ML Studio needs this  |
| **Wide format**| Each product is a column — needs pivoting before use               |
