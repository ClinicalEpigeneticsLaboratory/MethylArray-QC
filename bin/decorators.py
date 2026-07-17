"""
A module containing helper decorators used by Python modules
"""

from functools import wraps
from pathlib import Path
from typing import Callable

import plotly.graph_objects as go


def update_and_export_plot(
    json_path: Path | str,
    height: int = 625,
    width: int = 625,
    font_size: int = 16,
    title_font_size: int = 16,
    template: str = "ggplot2",
    legend_title: str = "",
    showlegend: bool = True,
    height_per_item: int | None = None,
) -> Callable:
    """
    Decorator that updates the layout of a Plotly figure and exports it to a JSON file.
    Designed to ensure stable figures layouts.

    Parameters:
        json_path (Path | str): File path to save the JSON.
        height (int): Height of the figure (used as minimum when height_per_item is set).
        width (int): Width of the figure.
        font_size (int): Font size used in the figure.
        title_font_size (int): Title font size used in the figure.
        template (str): Plotly template to apply.
        legend_title (str): Title of the legend.
        showlegend (bool): Whether to show the legend.
        height_per_item (int | None): If set, height is computed as
            max(height, n_items * height_per_item) where n_items is the
            number of y-axis categories across all traces. Useful for
            horizontal bar charts where all labels must remain visible.

    Returns:
        Callable: Decorated function that returns a Plotly Figure.

    Example:
    @update_and_export_plot(json_path="my_plot_1.json")
    def create_scatter(x, y) -> go.Figure:
        return px.scatter(x=x, y=y)

    """

    def decorator(func: Callable) -> Callable:

        @wraps(func)
        def wrapper(*args, **kwargs) -> go.Figure:
            fig = func(*args, **kwargs)

            if not isinstance(fig, go.Figure):
                raise TypeError(
                    "The decorated function must return a Plotly Figure object."
                )
            
            if height_per_item is not None and fig.data:
                # Union across all traces: px.bar with color= splits data into
                # one trace per category, so max(lengths) would undercount.
                # n_items == 0 when all traces have empty y; falls back to height.
                all_y_values = set()
                for trace in fig.data:
                    if hasattr(trace, "y") and trace.y is not None:
                        all_y_values.update(trace.y)
                n_items = len(all_y_values)
                computed_height = max(height, n_items * height_per_item)
            else:
                computed_height = height    

            # Update layout
            fig.update_layout(
                height=computed_height,
                width=width,
                template=template,
                showlegend=showlegend,
                legend={"title": legend_title},
                font={"size": font_size},
                title={"font":{"size": title_font_size}}
            )

            # Export to JSON
            fig_json = fig.to_json()
            with open(json_path, "w", encoding="utf-8") as handle:
                handle.write(fig_json)

            return fig

        return wrapper

    return decorator
