# Module 2 - Analytics + Machine Learning

## Files

| File | Purpose |
|---|---|
| `01_eda.ipynb` | Part A: loading, profiling, cleaning, univariate/bivariate/multivariate analysis, standardization check |
| `02_modeling.ipynb` | Part B: stratified split, preprocessing pipeline, three classifiers, imbalance comparison, hyperparameter tuning, regression side-task, final comparison and recommendation |
| `titanic.csv` | Offline fallback of the raw dataset, saved immediately after the one `sns.load_dataset('titanic')` call |
| `requirements.txt` | Libraries needed for this module |
| `best_titanic_pipeline.joblib` | The saved, complete fitted pipeline (preprocessing + tuned Random Forest) |
| `*.png` | Saved chart images referenced in the notebooks |

## How to run

1. Install the libraries: `pip install -r requirements.txt`
2. Run `01_eda.ipynb` top to bottom first. It loads the dataset (once, from the network/cache) and saves `titanic.csv`.
3. Run `02_modeling.ipynb` top to bottom. It reads `titanic.csv` and continues from there — it does not reload the raw dataset again.

## Design decisions and written interpretations

All required written interpretations (missing-value handling, outlier and skewness
analysis, correlation interpretation, the 4-chart data story, the standardization
check, the stratification justification, the imbalance-handling conclusion, the
heteroscedasticity conclusion, and the final model recommendation) are written as
Markdown cells directly in `01_eda.ipynb` and `02_modeling.ipynb`, next to the code
and outputs they explain.

## Summary of results

**Classification models**

| Model | Accuracy | Precision | Recall | F1 | AUC |
|---|---|---|---|---|---|
| Logistic Regression | 0.809 | 0.783 | 0.691 | 0.734 | 0.861 |
| Decision Tree | 0.809 | 0.815 | 0.647 | 0.721 | 0.856 |
| Random Forest | 0.820 | 0.781 | 0.735 | 0.758 | 0.821 |

**Regression model (predicting fare)**

| Model | MAE | RMSE | R2 | Adjusted R2 |
|---|---|---|---|---|
| Linear Regression | 21.14 | 41.75 | 0.347 | 0.324 |

The final recommendation (deploy Random Forest) is written in full in
`02_modeling.ipynb`, alongside the GridSearchCV tuning results (best parameters:
`max_depth=5`, `max_features='sqrt'`, `n_estimators=100`; OOB score 0.809).