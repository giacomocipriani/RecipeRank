"""Metrics and recipe rankings."""

import ast

import pandas as pd


def calculate_recipe_metrics(
    recipes: pd.DataFrame,
    interactions: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate rating and interaction metrics for each recipe."""
    required_recipe_columns = {"id"}
    required_interaction_columns = {"recipe_id", "rating"}

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

    # Exclude zero ratings from rating statistics.
    valid_votes = interactions.loc[interactions["rating"] > 0].copy()

    # Calculate rating metrics for each recipe.
    rating_stats = (
        valid_votes.groupby("recipe_id")
        .agg(
            average_rating=("rating", "mean"),
            rating_std=("rating", "std"),
            rating_count=("rating", "count"),
        )
        .reset_index()
    )

    # Count all interactions, including zero-rating interactions.
    engagement_stats = (
        interactions.groupby("recipe_id")
        .agg(total_interactions=("rating", "count"))
        .reset_index()
    )

    # Combine rating statistics with total interaction counts.
    recipe_metrics = rating_stats.merge(
        engagement_stats,
        on="recipe_id",
        how="left",
    )

    # Calculate the number of interactions with a zero rating.
    recipe_metrics["zero_rating_interactions"] = (
        recipe_metrics["total_interactions"] - recipe_metrics["rating_count"]
    )

    # Keep metrics only for recipe IDs present in the recipes dataframe.
    recipe_metrics = recipe_metrics[
        recipe_metrics["recipe_id"].isin(recipes["id"])
    ].copy()

    return recipe_metrics


def merge_recipe_metrics(
    recipes: pd.DataFrame,
    recipe_metrics: pd.DataFrame,
) -> pd.DataFrame:
    """Join recipe details with the calculated metrics."""
    required_recipe_columns = {"id"}
    required_metric_columns = {
        "recipe_id",
        "average_rating",
        "rating_std",
        "rating_count",
        "total_interactions",
        "zero_rating_interactions",
    }

    missing_recipe_columns = required_recipe_columns.difference(recipes.columns)
    missing_metric_columns = required_metric_columns.difference(recipe_metrics.columns)

    if missing_recipe_columns:
        missing = ", ".join(sorted(missing_recipe_columns))
        raise ValueError(f"Required columns missing from recipes data: {missing}")

    if missing_metric_columns:
        missing = ", ".join(sorted(missing_metric_columns))
        raise ValueError(f"Required metric columns missing: {missing}")

    # Join each recipe with the metrics calculated for its ID.
    ranked_recipes = recipes.merge(
        recipe_metrics,
        left_on="id",
        right_on="recipe_id",
        how="inner",
    )

    # Remove the duplicate key introduced by the join.
    ranked_recipes = ranked_recipes.drop(columns="recipe_id")

    return ranked_recipes


def rank_naive(
    ranked_recipes: pd.DataFrame,
    top_n: int | None = None,
) -> pd.DataFrame:
    """Rank recipes by average rating and then by rating count."""
    required_columns = {"average_rating", "rating_count"}
    missing_columns = required_columns.difference(ranked_recipes.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Required ranking columns missing: {missing}")

    # Sort by average rating, using rating count to break ties.
    result = ranked_recipes.sort_values(
        by=["average_rating", "rating_count"],
        ascending=[False, False],
    ).copy()

    if top_n is not None:
        result = result.head(top_n)

    return result


def rank_bayesian(
    ranked_recipes: pd.DataFrame,
    valid_votes: pd.DataFrame,
    min_votes: int = 3,
    confidence_quantile: float = 0.90,
) -> tuple[pd.DataFrame, float, float]:
    """Rank recipes using a Bayesian weighted average."""
    required_recipe_columns = {"average_rating", "rating_count"}
    missing_recipe_columns = required_recipe_columns.difference(ranked_recipes.columns)

    if missing_recipe_columns:
        missing = ", ".join(sorted(missing_recipe_columns))
        raise ValueError(f"Required ranking columns missing: {missing}")

    if "rating" not in valid_votes.columns:
        raise ValueError("Required column 'rating' missing from valid_votes.")

    if not 0 <= confidence_quantile <= 1:
        raise ValueError("confidence_quantile must be between 0 and 1.")

    if min_votes < 1:
        raise ValueError("min_votes must be at least 1.")

    # Calculate the global mean from positive ratings only.
    global_mean = valid_votes.loc[valid_votes["rating"] > 0, "rating"].mean()

    if pd.isna(global_mean):
        raise ValueError("No positive ratings are available for ranking.")

    # Set the confidence threshold using the selected rating-count quantile.
    confidence_threshold = ranked_recipes["rating_count"].quantile(confidence_quantile)

    # Exclude recipes with fewer than the selected minimum number of ratings.
    result = ranked_recipes.loc[ranked_recipes["rating_count"] >= min_votes].copy()

    # Calculate the Bayesian weighted average.
    result["bayesian_score"] = (
        result["rating_count"] * result["average_rating"]
        + confidence_threshold * global_mean
    ) / (result["rating_count"] + confidence_threshold)

    # Sort recipes by Bayesian score in descending order.
    result = result.sort_values(
        by="bayesian_score",
        ascending=False,
    )

    return result, global_mean, confidence_threshold


def rank_by_time(
    bayesian_recipes: pd.DataFrame,
    max_minutes: int = 30,
    top_n: int = 5,
) -> pd.DataFrame:
    """Return the highest-ranked recipes within a preparation-time limit."""
    required_columns = {"minutes", "bayesian_score", "rating_count"}
    missing_columns = required_columns.difference(bayesian_recipes.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Required time-ranking columns missing: {missing}")

    # Keep recipes within the selected preparation-time limit.
    result = bayesian_recipes.loc[bayesian_recipes["minutes"] <= max_minutes].copy()

    # Return the highest Bayesian scores and relevant recipe details.
    result = result.sort_values(
        by="bayesian_score",
        ascending=False,
    ).head(top_n)

    columns = [
        column
        for column in ["name", "bayesian_score", "minutes", "rating_count"]
        if column in result.columns
    ]

    return result[columns]


def rank_by_ingredient_count(
    bayesian_recipes: pd.DataFrame,
    max_ingredients: int = 5,
    top_n: int = 5,
) -> pd.DataFrame:
    """Return the highest-ranked recipes within an ingredient-count limit."""
    required_columns = {
        "n_ingredients",
        "bayesian_score",
        "rating_count",
    }
    missing_columns = required_columns.difference(bayesian_recipes.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Required ingredient-ranking columns missing: {missing}")

    # Keep recipes within the selected ingredient-count limit.
    result = bayesian_recipes.loc[
        bayesian_recipes["n_ingredients"] <= max_ingredients
    ].copy()

    # Return the highest Bayesian scores and relevant recipe details.
    result = result.sort_values(
        by="bayesian_score",
        ascending=False,
    ).head(top_n)

    columns = [
        column
        for column in [
            "name",
            "bayesian_score",
            "n_ingredients",
            "rating_count",
        ]
        if column in result.columns
    ]

    return result[columns]


def rank_by_tag(
    bayesian_recipes: pd.DataFrame,
    tag: str,
    top_n: int = 5,
) -> pd.DataFrame:
    """Return the highest-ranked recipes containing a selected tag."""
    required_columns = {"tags_list", "bayesian_score", "rating_count"}
    missing_columns = required_columns.difference(bayesian_recipes.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Required tag-ranking columns missing: {missing}")

    # Parse string-encoded tag lists when needed.
    def parse_tag_list(value: object) -> list:
        if isinstance(value, list):
            return value

        if isinstance(value, str):
            try:
                parsed = ast.literal_eval(value)
            except (ValueError, SyntaxError):
                return []
            return parsed if isinstance(parsed, list) else []

        return []

    tags = bayesian_recipes["tags_list"].map(parse_tag_list)

    # Keep recipes whose tag list contains the selected tag.
    result = bayesian_recipes.loc[
        tags.map(lambda recipe_tags: tag in recipe_tags)
    ].copy()

    # Return the highest Bayesian scores and relevant rating details.
    result = result.sort_values(
        by="bayesian_score",
        ascending=False,
    ).head(top_n)

    columns = [
        column
        for column in [
            "name",
            "bayesian_score",
            "rating_count",
            "average_rating",
        ]
        if column in result.columns
    ]

    return result[columns]
