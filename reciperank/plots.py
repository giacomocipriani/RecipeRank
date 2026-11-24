"""Plotting functions for recipe rating analysis."""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


RATING_COUNT_XLIM = (0, 100)
RATING_COUNT_XTICKS = (0, 20, 40, 60, 80, 100)


def _validate_columns(data: pd.DataFrame, required_columns: set[str]) -> None:
    """Raise a clear error when required columns are missing."""
    missing_columns = required_columns.difference(data.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Required plotting columns missing: {missing}")


def _set_rating_count_axis(axes: plt.Axes) -> None:
    """Set and label the rating-count range shown in the charts."""
    axes.set_xlim(*RATING_COUNT_XLIM)
    axes.set_xticks(RATING_COUNT_XTICKS)
    axes.set_xlabel("Numero di valutazioni (visualizzate fino a 100)", fontsize=12)


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
        "Valutazione media e numero di valutazioni: dettaglio fino a 100",
        fontsize=14,
    )
    _set_rating_count_axis(axes)
    axes.set_ylabel("Valutazione media", fontsize=12)
    axes.set_ylim(0.5, 5.5)
    axes.grid(True, linestyle="--", alpha=0.5)

    figure.tight_layout()
    return figure, axes


def plot_rating_std_vs_review_count(
    recipes: pd.DataFrame,
) -> tuple[plt.Figure, plt.Axes]:
    """Plot defined rating standard deviations against rating counts."""
    _validate_columns(recipes, {"rating_count", "rating_std"})

    # A missing standard deviation is not zero; omit unestimable points.
    plot_data = recipes.loc[recipes["rating_std"].notna()]

    figure, axes = plt.subplots(figsize=(10, 6))
    sns.scatterplot(
        data=plot_data,
        x="rating_count",
        y="rating_std",
        alpha=0.3,
        color="teal",
        ax=axes,
    )

    axes.set_title(
        "Dispersione delle valutazioni per volume: dettaglio fino a 100",
        fontsize=14,
    )
    _set_rating_count_axis(axes)
    axes.set_ylabel("Deviazione standard campionaria", fontsize=12)
    axes.grid(True, linestyle="--", alpha=0.5)
    if plot_data.empty:
        axes.text(
            0.5,
            0.5,
            "Nessuna ricetta con deviazione standard definita",
            ha="center",
            va="center",
            transform=axes.transAxes,
        )
    else:
        axes.text(
            0.01,
            0.99,
            "Ricette con una sola valutazione positiva: deviazione non definita, non mostrate.",
            ha="left",
            va="top",
            transform=axes.transAxes,
            fontsize=9,
            wrap=True,
        )

    figure.tight_layout()
    return figure, axes
