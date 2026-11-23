"""Loading and cleaning functions for the Food.com datasets."""

from pathlib import Path

import pandas as pd

# Resolve the project directory from this module's location.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Recipe IDs whose preparation times were manually identified as incorrect.
TIME_ERROR_IDS = {
    261647,
    95215,
    372282,
    142936,
    251194,
    447963,
}

# Replacement values for the recipe with missing name and description.
REPAIRED_RECIPE_ID = 368257
REPAIRED_RECIPE_NAME = "Honey Lemon Mustard Cup Dressing"
REPAIRED_RECIPE_DESCRIPTION = "Honey lemon mustard cup dressing"


def load_data(
    data_dir: Path | str = DATA_DIR,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the recipes and interactions CSV files.

    Parameters
    ----------
    data_dir:
        Directory containing RAW_recipes.csv and RAW_interactions.csv.
        Defaults to the project's data directory.

    Returns
    -------
    tuple[pandas.DataFrame, pandas.DataFrame]
        The recipes dataframe and the interactions dataframe.
    """
    data_path = Path(data_dir)

    recipes_path = data_path / "RAW_recipes.csv"
    interactions_path = data_path / "RAW_interactions.csv"

    # Collect missing filenames before attempting to read either dataset.
    missing_files = [
        path.name for path in (recipes_path, interactions_path) if not path.is_file()
    ]

    if missing_files:
        missing = ", ".join(missing_files)
        raise FileNotFoundError(f"CSV files not found in '{data_path}': {missing}")

    recipes = pd.read_csv(recipes_path)
    interactions = pd.read_csv(interactions_path)

    return recipes, interactions


def clean_data(
    recipes: pd.DataFrame,
    interactions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply the cleaning steps used in the analysis notebook."""
    recipes = recipes.copy()
    interactions = interactions.copy()

    # Check for columns required by the cleaning operations.
    required_recipe_columns = {"id", "name", "description", "minutes"}
    required_interaction_columns = {"recipe_id", "review"}

    missing_recipe_columns = required_recipe_columns.difference(recipes.columns)
    missing_interaction_columns = required_interaction_columns.difference(
        interactions.columns
    )

    if missing_recipe_columns:
        missing = ", ".join(sorted(missing_recipe_columns))
        raise ValueError(f"Required columns missing from recipes data: {missing}")

    if missing_interaction_columns:
        missing = ", ".join(sorted(missing_interaction_columns))
        raise ValueError(f"Required columns missing from interactions data: {missing}")

    # Keep interactions linked to recipe IDs present in the recipes dataframe.
    interactions = interactions[interactions["recipe_id"].isin(recipes["id"])].copy()

    # Replace missing review text with an empty string.
    interactions["review"] = interactions["review"].fillna("")

    # Replace the missing name and description identified during data inspection.
    recipe_to_repair = recipes["id"] == REPAIRED_RECIPE_ID
    recipes.loc[recipe_to_repair, "name"] = REPAIRED_RECIPE_NAME
    recipes.loc[recipe_to_repair, "description"] = REPAIRED_RECIPE_DESCRIPTION

    # Treat non-positive preparation times and manually identified errors as missing.
    invalid_minutes = recipes["minutes"].le(0) | recipes["id"].isin(TIME_ERROR_IDS)

    # Use pandas' nullable integer dtype to preserve integer values alongside missing data.
    recipes["minutes"] = recipes["minutes"].astype("Int64")
    recipes.loc[invalid_minutes, "minutes"] = pd.NA

    return recipes, interactions


def load_and_clean_data(
    data_dir: Path | str = DATA_DIR,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load both datasets and apply the notebook's cleaning steps."""
    recipes, interactions = load_data(data_dir)
    return clean_data(recipes, interactions)
