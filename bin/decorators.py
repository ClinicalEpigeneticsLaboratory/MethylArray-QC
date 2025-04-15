import json
from functools import wraps
from pathlib import Path
from typing import Callable

import numpy as np
import plotly.express as px
import plotly.graph_objects as go


def update_and_export_plot(
    json_path: Path | str,
    height: int = 600,
    width: int = 600,
    font_size: int = 22,
    template: str = "ggplot2",
    legend_title: str = "",
    showlegend: bool = True,
) -> Callable:
    """
    Decorator that updates the layout of a Plotly figure and exports it to a JSON file.
    Designed to ensure stable figures layouts.

    Parameters:
        json_path (Path | str): File path to save the JSON.
        height (int): Height of the figure.
        width (int): Width of the figure.
        font_size (int): Font size used in the figure.
        template (str): Plotly template to apply.
        legend_title (str): Title of the legend.
        showlegend (bool): Whether to show the legend.

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

            # Update layout
            fig.update_layout(
                height=height,
                width=width,
                template=template,
                showlegend=showlegend,
                legend={"title": legend_title},
                font=dict(size=font_size),
            )

            # Export to JSON
            fig_json = fig.to_json()
            with open(json_path, "w", encoding="utf-8") as handle:
                json.dump(fig_json, handle, indent=2)

            return fig

        return wrapper

    return decorator
