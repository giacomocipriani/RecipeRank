"""Plotting functions for recipe rating analysis."""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def _validate_columns(data: pd.DataFrame, required_columns: set[str]) -> None:
    """Raise a clear error when required columns are missing."""
    missing_columns = required_columns.difference(data.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Required plotting columns missing: {missing}")


def plot_rating_vs_review_count(
    recipes: pd.DataFrame,
) -> tuple[plt.Figure, plt.Axes]:
    """Plot average recipe rating against the number of ratings."""
    _validate_columns(recipes, {"rating_count", "average_rating"})

    figure, axes = plt.subplots(figsize=(10, 6))
    sns.scatterplot(
        data=recipes,
        x="rating_count",
        y="average_rating",
        alpha=0.3,
        color="teal",
        ax=axes,
    )

    axes.set_title(
        "Limitations of Naive Ranking: Variance in Small Samples",
        fontsize=14,
    )
    axes.set_xlabel("Number of Reviews (Rating Count)", fontsize=12)
    axes.set_ylabel("Average Rating", fontsize=12)
    axes.set_xlim(0, 100)
    axes.set_ylim(0.5, 5.5)
    axes.grid(True, linestyle="--", alpha=0.5)

    figure.tight_layout()
    return figure, axes


def plot_rating_std_vs_review_count(
    recipes: pd.DataFrame,
) -> tuple[plt.Figure, plt.Axes]:
    """Plot rating standard deviation against the number of ratings."""
    _validate_columns(recipes, {"rating_count", "rating_std"})

    figure, axes = plt.subplots(figsize=(10, 6))
    sns.scatterplot(
        data=recipes,
        x="rating_count",
        y="rating_std",
        alpha=0.3,
        color="teal",
        ax=axes,
    )

    axes.set_title("Rating Dispersion versus Review Volume", fontsize=14)
    axes.set_xlabel("Number of Reviews (Rating Count)", fontsize=12)
    axes.set_ylabel("Rating Standard Deviation", fontsize=12)
    axes.set_xlim(0, 100)
    axes.grid(True, linestyle="--", alpha=0.5)

    figure.tight_layout()
    return figure, axes
