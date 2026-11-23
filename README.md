# 🍳 RateMyRecipe

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

The Bayesian score pulls each recipe’s average toward the global mean rating. The amount of pull depends on the recipe’s rating count and the confidence threshold derived from the selected rating-count quantile:

```text
Bayesian score = (v × R + m × C) / (v + m)
```

- `R` is the recipe’s average rating.
- `v` is the number of valid positive ratings for the recipe.
- `C` is the global mean of positive ratings.
- `m` is the confidence threshold, calculated from the 90th percentile of recipe rating counts in the app.

The app uses a minimum of **3 ratings** for the Bayesian ranking. With fewer ratings, a recipe can have a high raw average by chance; the Bayesian adjustment balances that average with the overall rating baseline. As the recipe receives more ratings, its own average has more influence on its Bayesian score.

The formula and settings are implemented in [`reciperank/analysis.py`](reciperank/analysis.py). The app displays the global mean and confidence threshold used for the loaded data, so these values depend on the dataset.

## Data and EDA

The app expects two CSV files in the `data/` directory:

- `RAW_recipes.csv` — recipe details, including recipe IDs, names, preparation time, steps, ingredients, and tags.
- `RAW_interactions.csv` — recipe-rating interactions, including recipe IDs and ratings.

The data loader in [`reciperank/data.py`](reciperank/data.py) reads and cleans these files. It keeps interactions linked to known recipe IDs, fills missing review text with an empty string, repairs one recipe record identified during data inspection, and treats non-positive or specifically identified incorrect preparation times as missing.

Rating metrics in [`reciperank/analysis.py`](reciperank/analysis.py) are calculated from positive ratings; zero ratings are excluded from rating averages and dispersion statistics. Interaction counts include all interactions, including zero-rating interactions. The EDA notebook, [`notebooks/ratemyrecipe_eda.ipynb`](notebooks/ratemyrecipe_eda.ipynb), documents the exploratory analysis that informed the data-cleaning and ranking work.

## Libraries

| Library | Used for |
|---------|----------|
| `pandas` | Loading, cleaning, joining, and analyzing the CSV data |
| `numpy` | Numerical operations used by the analysis |
| `matplotlib` | Creating rating charts |
| `seaborn` | Building the scatter plots |
| `streamlit` | The interactive web app |

Exact versions are listed in [`requirements.txt`](requirements.txt). 

## Setup

1. Clone the repository and enter the project folder:

   ```bash
   git clone <repository-url>
   cd RateMyRecipe
   ```

   Replace `<repository-url>` with the URL of your repository.

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # macOS / Linux
   # Windows: .venv\Scripts\activate
   ```

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   pip install streamlit
   ```

4. Place `RAW_recipes.csv` and `RAW_interactions.csv` in the `data/` directory. Both files are required by the app.

## Run the app

From the project root, start Streamlit:

```bash
streamlit run app.py
```

The app loads and analyzes the CSV files from `data/`. To use a different folder, open **Advanced data settings** in the sidebar and enter a folder containing both required CSV files.

## Explore the EDA notebook

The EDA notebook is [`notebooks/ratemyrecipe_eda.ipynb`](notebooks/ratemyrecipe_eda.ipynb). From the project root, start Jupyter and open the notebook:

```bash
jupyter notebook
```

The notebook is for exploratory analysis; the Streamlit app uses the reusable loading, cleaning, metrics, ranking, and plotting functions in the `reciperank` package.

## Project structure

```text
RateMyRecipe/
├── app.py                         # Streamlit entry point and interactive ranking views
├── reciperank/
│   ├── __init__.py                # Package initialization
│   ├── analysis.py                # Rating metrics and naive/Bayesian rankings
│   ├── data.py                    # CSV loading and data cleaning
│   └── plots.py                   # Rating and variability charts
├── data/
│   ├── RAW_interactions.csv       # Recipe-rating interactions (required at runtime)
│   └── RAW_recipes.csv            # Recipe details (required at runtime)
├── notebooks/
│   └── ratemyrecipe_eda.ipynb     # Exploratory data analysis
├── requirements.txt               # Python package requirements
└── README.md
```

The `reciperank` package keeps data preparation and analysis separate from the Streamlit interface. Its functions can be reused in notebooks or other Python code, while `app.py` focuses on presenting the rankings, charts, and filters.