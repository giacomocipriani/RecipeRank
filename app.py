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

PODIUM_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


@st.cache_data(show_spinner="Loading and analyzing the CSV files…")
def prepare_rankings(
    data_dir: str,
) -> tuple[pd.DataFrame, pd.DataFrame, float, float]:
    """Load, clean and rank recipes from the selected data directory."""
    recipes, interactions = load_and_clean_data(data_dir)
    metrics = calculate_recipe_metrics(recipes, interactions)
    ranked = merge_recipe_metrics(recipes, metrics)

    naive = rank_naive(ranked)
    bayesian, global_mean, confidence_threshold = rank_bayesian(
        ranked,
        interactions,
        min_votes=3,
        confidence_quantile=0.90,
    )

    return naive, bayesian, global_mean, confidence_threshold


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


def display_columns(data: pd.DataFrame, ranking_type: str) -> pd.DataFrame:
    """Select and label the key columns for a ranking table."""
    result = data.copy()
    labels = {
        "Rank": "Rank",
        "name": "Recipe",
        "average_rating": "Average rating",
        "bayesian_score": "Bayesian score",
        "rating_count": "Ratings",
        "minutes": "Time (min)",
        "n_steps": "Steps",
    }

    if ranking_type == "naive":
        columns = ("Rank", "name", "average_rating", "rating_count")
    elif ranking_type == "final":
        columns = (
            "Rank",
            "name",
            "bayesian_score",
            "average_rating",
            "rating_count",
            "minutes",
            "n_steps",
        )
    else:
        columns = ("Rank", "name", "bayesian_score", "rating_count")

    available = [column for column in columns if column in result.columns]
    return result.loc[:, available].rename(columns=labels)


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
    """Display a compact ranking table with a visible podium."""
    if data.empty:
        st.info("No recipes are available for this ranking.")
        return

    view = data.head(top_n).copy().reset_index(drop=True)
    ranks = list(range(1, len(view) + 1))
    view.insert(
        0,
        "Rank",
        [f"{PODIUM_MEDALS.get(rank, '')} {rank}".strip() for rank in ranks],
    )

    st.dataframe(
        display_columns(view, ranking_type),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Rank": st.column_config.TextColumn("Rank", width="small"),
            "Recipe": st.column_config.TextColumn("Recipe", width="large"),
            "Average rating": st.column_config.NumberColumn(
                "Average rating", format="%.2f", width="small"
            ),
            "Bayesian score": st.column_config.NumberColumn(
                "Bayesian score", format="%.4f", width="small"
            ),
            "Ratings": st.column_config.NumberColumn(
                "Ratings", format="%d", width="small"
            ),
            "Time (min)": st.column_config.NumberColumn(
                "Time (min)", format="%d", width="small"
            ),
            "Steps": st.column_config.NumberColumn(
                "Steps", format="%d", width="small"
            ),
        },
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
            margin-bottom: 1rem;
        }
        div[data-testid="stVerticalBlock"] > div:has(> div > .section-break) {
            margin-top: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("RateMyRecipe")
    st.caption("Explore recipe ratings, compare ranking methods, and find your next dish.")
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
        naive_max_ratings = st.radio(
            "Maximum ratings per recipe in naive ranking",
            options=[1, 5, "No limit"],
            horizontal=True,
            format_func=lambda value: str(value),
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
    st.header("⚖️ 1. Naive vs. Bayesian comparison")
    st.markdown(
        """
        **Naive** orders recipes by their average rating, so a highly rated recipe
        with few reviews can rank near the top. **Bayesian** also considers how
        much rating evidence supports each recipe, reducing sensitivity to very
        small samples.
        """
    )

    st.subheader("Naive ranking")
    st.caption("Ordered by average rating; the selector filters recipes by rating count.")
    if naive_max_ratings != "No limit":
        naive = naive.loc[naive["rating_count"] <= int(naive_max_ratings)]
    render_ranking(naive, ranking_type="naive", top_n=top_n)

    st.subheader("Bayesian ranking")
    st.caption("Ordered by the project’s Bayesian score.")
    render_ranking(bayesian, ranking_type="bayesian", top_n=top_n)
    with st.expander("How to interpret the Bayesian ranking statistics"):
        st.markdown(
            f"""
            - **Global mean rating ({global_mean:.3f})**: overall rating reference.
            - **90th-percentile vote threshold ({confidence_threshold:.0f} ratings)**:
              confidence threshold configured for this ranking.
            - The ranking also applies a minimum of **3 ratings** (`min_votes=3`).
            """
        )

    st.divider()
    st.markdown("<span id='rating-charts'></span>", unsafe_allow_html=True)
    st.header("📈 2. Rating charts")
    st.caption("Use these charts to see how rating quality and review volume relate.")

    figure, _ = plot_rating_vs_review_count(naive)
    figure.set_size_inches(12, 7, forward=True)
    render_chart(figure)

    st.subheader("Rating variability and number of ratings")
    st.caption(
        "Sample standard deviation measures spread, not the average rating. "
        "Recipes with only one positive rating have no defined standard deviation "
        "and are omitted; counts above 100 are not shown."
    )
    figure, _ = plot_rating_std_vs_review_count(naive)
    figure.set_size_inches(12, 7, forward=True)
    render_chart(figure)

    st.divider()
    st.markdown("<span id='final-ranking'></span>", unsafe_allow_html=True)
    st.header("🏆 3. Final ranking")
    st.caption(
        "The final list uses the Bayesian ranking. Time and step limits apply "
        "together; recipes matching at least one selected category are included."
    )

    controls = st.columns([1, 1, 1.5], gap="large", vertical_alignment="top")

    max_steps_value = controls[0].number_input(
        "Maximum number of steps",
        min_value=0,
        value=0,
        step=1,
        help="Set to 0 for no limit.",
    )

    max_minutes_value = controls[1].number_input(
        "Maximum preparation time (minutes)",
        min_value=0,
        value=0,
        step=5,
        help="Set to 0 for no limit.",
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
    ).head(top_n).reset_index(drop=True)

    if final_ranking.empty:
        st.warning("No recipes match the selected filters.")
    else:
        final_ranking.insert(
            0,
            "Rank",
            [
                f"{PODIUM_MEDALS.get(rank, '')} {rank}".strip()
                for rank in range(1, len(final_ranking) + 1)
            ],
        )
        final_table = display_columns(final_ranking, ranking_type="final")
        st.caption(f"Showing {len(final_table)} recipe(s) matching your filters.")
        st.dataframe(
            final_table,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Rank": st.column_config.TextColumn("Rank", width="small"),
                "Recipe": st.column_config.TextColumn("Recipe", width="large"),
                "Bayesian score": st.column_config.NumberColumn(
                    "Bayesian score", format="%.4f", width="small"
                ),
                "Average rating": st.column_config.NumberColumn(
                    "Average rating", format="%.2f", width="small"
                ),
                "Ratings": st.column_config.NumberColumn(
                    "Ratings", format="%d", width="small"
                ),
                "Time (min)": st.column_config.NumberColumn(
                    "Time (min)", format="%d", width="small"
                ),
                "Steps": st.column_config.NumberColumn(
                    "Steps", format="%d", width="small"
                ),
            },
        )
        st.download_button(
            "Download ranking as CSV",
            data=final_table.to_csv(index=False).encode("utf-8-sig"),
            file_name="ratemyrecipe_bayesian_ranking.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
