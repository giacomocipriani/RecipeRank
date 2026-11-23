"""Recipe ranking - Streamlit entry point."""

from __future__ import annotations

import ast
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from reciperank.analysis import (
    calculate_recipe_metrics,
    merge_recipe_metrics,
    rank_bayesian,
    rank_naive,
)
from reciperank.data import load_and_clean_data
from reciperank.plots import (
    plot_rating_std_vs_review_count,
    plot_rating_vs_review_count,
)

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"

CATEGORY_TAGS = {
    "Main dish": "main-dish",
    "Vegetarian": "vegetarian",
    "Meat": "meat",
    "Dietary": "dietary",
    "Dessert": "desserts",
}

CATEGORY_STICKERS = {
    "Main dish": "🍽️",
    "Vegetarian": "🥬",
    "Meat": "🥩",
    "Dietary": "🌿",
    "Dessert": "🍰",
}


@st.cache_data(show_spinner="Loading and analyzing the CSV files…")
def prepare_rankings(
    data_dir: str,
) -> tuple[pd.DataFrame, pd.DataFrame, float, float]:
    """Load, clean and rank recipes from the selected data directory."""
    recipes, interactions = load_and_clean_data(data_dir)
    metrics = calculate_recipe_metrics(recipes, interactions)
    ranked = merge_recipe_metrics(recipes, metrics)

    # Recipes with one valid rating have an undefined standard deviation.
    if "rating_std" in ranked.columns:
        ranked["rating_std"] = ranked["rating_std"].fillna(0)

    naive = rank_naive(ranked)
    bayesian = rank_bayesian(
        ranked,
        interactions,
        min_votes=3,
        confidence_quantile=0.90,
    )

    return (
        naive,
        bayesian,
        float(bayesian.attrs["global_mean"]),
        float(bayesian.attrs["confidence_threshold"]),
    )


def parse_tags(value: object) -> list[str]:
    """Parse string-encoded recipe tags."""
    if isinstance(value, list):
        return [str(tag) for tag in value]

    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return []
        return [str(tag) for tag in parsed] if isinstance(parsed, list) else []

    return []


def display_columns(data: pd.DataFrame) -> pd.DataFrame:
    """Select and label useful recipe columns present in a ranking."""
    result = data.copy()

    if "tags" in result.columns:
        result["tags"] = result["tags"].map(lambda value: ", ".join(parse_tags(value)))
    elif "tags_list" in result.columns:
        result["tags"] = result["tags_list"].map(
            lambda value: ", ".join(parse_tags(value))
        )

    labels = {
        "name": "Recipe",
        "average_rating": "Average rating",
        "bayesian_score": "Bayesian score",
        "rating_count": "Ratings",
        "minutes": "Preparation time (min)",
        "n_steps": "Steps",
        "n_ingredients": "Ingredients",
        "tags": "Tags",
    }

    columns = [
        column
        for column in (
            "name",
            "average_rating",
            "bayesian_score",
            "rating_count",
            "minutes",
            "n_steps",
            "n_ingredients",
            "tags",
        )
        if column in result.columns
    ]

    return result.loc[:, columns].rename(columns=labels)


def filter_recipes(
    recipes: pd.DataFrame,
    max_steps: int | None,
    max_minutes: int | None,
    selected_categories: list[str],
) -> pd.DataFrame:
    """Apply the selected time, step and category filters together."""
    result = recipes.copy()

    if max_steps is not None:
        result = result.loc[
            pd.to_numeric(result["n_steps"], errors="coerce") <= max_steps
        ]

    if max_minutes is not None:
        result = result.loc[
            pd.to_numeric(result["minutes"], errors="coerce") <= max_minutes
        ]

    if selected_categories:
        if "tags_list" in result.columns:
            tags = result["tags_list"].map(parse_tags)
        elif "tags" in result.columns:
            tags = result["tags"].map(parse_tags)
        else:
            return result.iloc[0:0]

        wanted_tags = {CATEGORY_TAGS[category] for category in selected_categories}
        result = result.loc[
            tags.map(
                lambda recipe_tags: bool(
                    wanted_tags.intersection(
                        {tag.strip().lower() for tag in recipe_tags}
                    )
                )
            )
        ]

    return result


def render_chart(figure: plt.Figure) -> None:
    """Render a Matplotlib figure and release it afterwards."""
    st.pyplot(figure, use_container_width=True)
    plt.close(figure)


def render_ranking(
    data: pd.DataFrame,
    ranking_type: str,
    top_n: int,
) -> None:
    """Display a ranking table with a visible rank number."""
    if data.empty:
        st.info("No recipes are available for this ranking.")
        return

    view = data.head(top_n).copy().reset_index(drop=True)
    view.insert(0, "Rank", [f"#{index}" for index in range(1, len(view) + 1)])

    if ranking_type == "naive" and "average_rating" in view.columns:
        view["average_rating"] = view["average_rating"].map(
            lambda value: f"{value:.2f}" if pd.notna(value) else "—"
        )

    if "bayesian_score" in view.columns:
        view["bayesian_score"] = view["bayesian_score"].map(
            lambda value: f"{value:.4f}" if pd.notna(value) else "—"
        )

    st.dataframe(
        display_columns(view),
        hide_index=True,
        use_container_width=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="RateMyRecipe",
        page_icon="🍳",
        layout="wide",
    )

    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1450px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        div[data-testid="stDataFrame"] {
            border-radius: 12px;
            overflow: hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("RateMyRecipe")
    st.markdown(
        "**On this page:** "
        "[Naive vs. Bayesian comparison](#ranking-comparison) · "
        "[Rating charts](#rating-charts) · "
        "[Final ranking](#final-ranking)"
    )

    with st.sidebar:
        st.header("Display")
        top_n = st.radio(
            "Recipes shown in the comparison",
            options=[5, 10],
            horizontal=True,
        )

        with st.expander("Advanced data settings"):
            data_dir = st.text_input(
                "CSV folder",
                value=str(DATA_DIR),
                help="The folder must contain RAW_recipes.csv and RAW_interactions.csv.",
            )

    try:
        naive, bayesian, global_mean, confidence_threshold = prepare_rankings(data_dir)
    except FileNotFoundError as error:
        st.error(f"Could not find the CSV files. {error}")
        st.info(
            "Check that app.py is in the project folder and that both CSV files "
            "are in its data subfolder."
        )
        st.stop()
    except (ValueError, KeyError) as error:
        st.error(f"Could not prepare the rankings: {error}")
        st.stop()

    st.markdown("<span id='ranking-comparison'></span>", unsafe_allow_html=True)
    st.header("1. Naive vs. Bayesian comparison")

    st.markdown(
        """
        The **Naive ranking** sorts recipes by their average rating. A recipe
        with only a few ratings can therefore rise to the top based on a small
        sample.

        The **Bayesian ranking** uses the recipe’s rating information together
        with its number of ratings, according to the project’s ranking function.
        This takes into account how much evidence supports each recipe’s rating
        and makes the ranking less sensitive to very small samples.
        """
    )

    st.subheader("Naive ranking")
    st.caption(
        "Recipes are ordered by average rating. The ratings column shows how "
        "many ratings contribute to each recipe’s result."
    )
    render_ranking(naive, ranking_type="naive", top_n=top_n)

    st.subheader("Bayesian ranking")
    with st.expander("How to interpret the Bayesian ranking statistics"):
        st.markdown(
            f"""
            - **Global mean rating ({global_mean:.3f})**: the overall rating
              reference exposed by the Bayesian ranking function.
            - **90th-percentile vote threshold ({confidence_threshold:.0f} ratings)**:
              the confidence threshold exposed by that function, as configured
              in the project.
            - The ranking also applies a minimum of **3 ratings**
              (`min_votes=3`).
            """
        )

    st.caption(
        "Recipes are ordered by the Bayesian score computed by the project. "
        "The minimum-vote and confidence settings are controlled by the existing "
        "ranking function."
    )
    render_ranking(bayesian, ranking_type="bayesian", top_n=top_n)

    st.markdown("<span id='rating-charts'></span>", unsafe_allow_html=True)
    st.header("2. Rating charts")

    st.subheader("Average rating and number of ratings")
    st.markdown(
        """
        Each point represents a recipe. This chart compares its average rating
        with the number of ratings behind it. It provides context for the naive
        ranking: similar average ratings can be supported by very different
        numbers of reviews. The chart complements the rankings; it does not
        replace them.
        """
    )
    figure, _ = plot_rating_vs_review_count(naive)
    render_chart(figure)

    st.subheader("Rating variability and number of ratings")
    st.markdown(
        """
        This chart compares each recipe’s rating variability with its number of
        ratings. Standard deviation describes how spread out the ratings are
        around their average; it is not a measure of whether the average is high
        or low. It can add context about reviewer agreement and the amount of
        data supporting that estimate.
        """
    )
    figure, _ = plot_rating_std_vs_review_count(naive)
    render_chart(figure)

    st.markdown("<span id='final-ranking'></span>", unsafe_allow_html=True)
    st.header("3. Final ranking")

    st.markdown(
        """
        This definitive list uses the **Bayesian ranking only**. The time and
        step limits are applied together. If you choose more than one category,
        a recipe is included when it matches **at least one** selected category.
        """
    )

    controls = st.columns([1, 1, 1.5])

    max_steps_value = controls[0].number_input(
        "Maximum number of steps (0 = no limit)",
        min_value=0,
        value=0,
        step=1,
    )

    max_minutes_value = controls[1].number_input(
        "Maximum preparation time in minutes (0 = no limit)",
        min_value=0,
        value=0,
        step=5,
    )

    selected_categories = controls[2].multiselect(
        "Recipe categories",
        options=list(CATEGORY_TAGS),
        format_func=lambda category: f"{CATEGORY_STICKERS[category]} {category}",
    )

    final_ranking = filter_recipes(
        bayesian,
        max_steps=int(max_steps_value) or None,
        max_minutes=int(max_minutes_value) or None,
        selected_categories=selected_categories,
    )

    final_ranking = final_ranking.sort_values(
        "bayesian_score",
        ascending=False,
    ).head(top_n)

    if final_ranking.empty:
        st.warning("No recipes match the selected filters.")
    else:
        final_table = display_columns(final_ranking)
        st.dataframe(
            final_table,
            hide_index=True,
            use_container_width=True,
        )
        st.download_button(
            "Download filtered Bayesian ranking as CSV",
            data=final_table.to_csv(index=False).encode("utf-8-sig"),
            file_name="ratemyrecipe_bayesian_ranking.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
