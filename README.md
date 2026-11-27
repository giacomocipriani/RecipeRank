# 🍲 RateMyRecipe

RateMyRecipe explores how recipes can be ranked more fairly when recipes have very different numbers of ratings. It combines exploratory data analysis (EDA), rating metrics, a Bayesian ranking, and an interactive Streamlit app built around recipe and user-interaction data.

![Streamlit app](https://img.shields.io/badge/built%20with-Streamlit-ff4b4b)

## What the app does

The Streamlit app presents the ranking analysis in three sections:

| Section | What you can do |
|---------|-----------------|
| **Naive vs. Bayesian comparison** | Compare recipes sorted by average rating with recipes sorted by the Bayesian score. Choose whether to show the top 5 or top 10. |
| **Rating charts** | Explore the relationship between a recipe’s average rating and number of ratings, and between rating variability (standard deviation) and number of ratings. |
| **Final ranking** | Browse the Bayesian ranking with optional maximum preparation-time and step limits, and category filters for main dish, vegetarian, meat, dietary, and dessert recipes. Download the filtered results as CSV. |

Category stickers appear in the selector; recipe names in the ranking table are shown without stickers. The dessert filter uses the `desserts` tag.

## How the ranking works

### Naive ranking

The naive ranking sorts recipes by their average positive rating, using rating count as a tie-breaker. It is easy to interpret, but an average based on only a few ratings can be less stable than one supported by many ratings.

### Bayesian ranking

The Bayesian score pulls each recipe’s average toward the global mean rating. The amount of pull depends on the recipe’s positive-rating count and on a smoothing weight (`m`):

```text
Bayesian score = (v × R + m × C) / (v + m)
```

- `R` is the recipe’s average positive rating.
- `v` is the number of positive ratings for the recipe.
- `C` is the global mean of positive ratings.
- `m` is the confidence threshold, calculated as the selected quantile (90th percentile by default) of recipe positive-rating counts.

Here, “confidence threshold” does **not** mean the minimum number of ratings required for a recipe to enter the ranking. It sets the strength of the smoothing: mathematically, the score is a weighted average of `R` and `C`, with weights `v` and `m`. A larger `m` gives the global mean more influence; as `v` grows relative to `m`, the recipe’s own average has more influence and the score moves closer to `R`. When `v` is small, the score is pulled more strongly toward `C`.

Eligibility is controlled separately by `min_votes`, which defaults to **3**: recipes with fewer than 3 positive ratings are excluded from the Bayesian ranking. The 90th percentile determines `m`; it is not that eligibility cutoff. Both the percentile setting and minimum-rating setting are parameters in `rank_bayesian` in [`reciperank/analysis.py`](reciperank/analysis.py). The app displays the global mean and confidence threshold calculated for the loaded data, so their values depend on the dataset.

## Data and EDA

The app requires both CSV files in the `data/` directory:

- `RAW_recipes.csv` — recipe details, including recipe IDs, names, preparation time, steps, ingredients, and tags.
- `RAW_interactions.csv` — recipe-rating interactions, including recipe IDs and ratings.

The data loader in [`reciperank/data.py`](reciperank/data.py) reads and cleans these files. It keeps interactions linked to known recipe IDs, fills missing review text with an empty string, repairs one recipe record identified during data inspection, and treats non-positive or specifically identified incorrect preparation times as missing.

Rating metrics in [`reciperank/analysis.py`](reciperank/analysis.py) are calculated from positive ratings; zero ratings are excluded from rating averages and dispersion statistics. Interaction counts include all interactions, including zero-rating interactions. The EDA notebook, [`notebooks/ratemyrecipe_eda.ipynb`](notebooks/ratemyrecipe_eda.ipynb), documents the exploratory analysis that informed the data-cleaning and ranking work.

The dataset CSVs are excluded from Git and are not included in new commits after they are removed from Git tracking. They are still required locally for the app and notebook: keep or place both actual CSV files in `data/`. Anyone cloning the repository can download the datasets from [Kaggle](https://www.kaggle.com/datasets/shuyangli94/food-com-recipes-and-user-interactions).

## Libraries

| Library | Used for |
|---------|----------|
| `pandas` | Loading, cleaning, joining, and analyzing the CSV data |
| `numpy` | Numerical operations used by the EDA notebook |
| `matplotlib` | Creating rating charts |
| `seaborn` | Building the scatter plots |
| `streamlit` | The interactive web app |
| `TextBlob` | Sentiment analysis in the EDA notebook |
| `Jupyter` | Running the EDA notebook interactively |

The dependencies for the app and EDA notebook are listed in [`requirements.txt`](requirements.txt).

## Setup

1. Clone the repository and enter the project folder:

   ```bash
   git clone https://github.com/giacomocipriani/RecipeRank.git
   cd RecipeRank
   ```

2. Download the datasets from [Kaggle](https://www.kaggle.com/datasets/shuyangli94/food-com-recipes-and-user-interactions) and place the actual CSV files at `data/RAW_recipes.csv` and `data/RAW_interactions.csv`. Both are required to run the app and notebook.

3. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # macOS / Linux
   # PowerShell: .\.venv\Scripts\Activate.ps1
   ```

4. Install the project dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

## Run the Streamlit app

From the project root, start Streamlit:

```bash
streamlit run app.py
```

The app loads and analyzes the CSV files from `data/`. To use a different folder, open **Advanced data settings** in the sidebar and enter a folder containing both required CSV files. Streamlit is already installed by `pip install -r requirements.txt`; there is no need to install it a second time.

## Explore the EDA notebook

The notebook is [`notebooks/ratemyrecipe_eda.ipynb`](notebooks/ratemyrecipe_eda.ipynb). From the project root, start Jupyter:

```bash
jupyter notebook
```

Then open `notebooks/ratemyrecipe_eda.ipynb` in the browser. Run the notebook with `notebooks/` as the working directory; its relative CSV paths should use `../data/...` to reach the project-root `data/` directory. The notebook imports TextBlob. Make sure the Jupyter kernel uses the same Python environment where `requirements.txt` was installed. The notebook is for exploratory analysis; the Streamlit app uses the reusable loading, cleaning, metrics, ranking, and plotting functions in the `reciperank` package.

## Project structure

```text
RecipeRank/
├── app.py                         # Streamlit entry point and interactive ranking views
├── reciperank/
│   ├── __init__.py                # Package initialization
│   ├── analysis.py                # Rating metrics and naive/Bayesian rankings
│   ├── data.py                    # CSV loading and data cleaning
│   └── plots.py                   # Rating and variability charts
├── notebooks/
│   └── ratemyrecipe_eda.ipynb     # Exploratory data analysis
├── data/
│   ├── RAW_interactions.csv       # Recipe-rating interactions (required at runtime; obtain separately)
│   └── RAW_recipes.csv            # Recipe details (required at runtime; obtain separately)
├── requirements.txt               # App and EDA Python package requirements
└── README.md
```

The `reciperank` package keeps data preparation and analysis separate from the Streamlit interface. Its functions can be reused in notebooks or other Python code, while `app.py` focuses on presenting the rankings, charts, and filters.
