from decorators import update_and_export_plot
from pathlib import Path
import plotly.graph_objects as go

def export_decorated_fig_with_custom_name(
    fig: go.Figure,
    json_path: Path | str,
    height: int = 650,
    width: int = 650,
    font_size: int = 22,
    template: str = "ggplot2",
    legend_title: str = "",
    showlegend: bool = True,
) -> None:
    """
    Wrapper function that applies the update_and_export_plot decorator to a dummy
    function returning the provided Plotly figure.

    This is useful in situations where using a decorator directly is not ergonomic,
    such as in dynamic or looped contexts.

    Parameters:
        fig (go.Figure): The Plotly figure to update and export.
        json_path (Path | str): File path to save the JSON.
        height (int): Height of the figure.
        width (int): Width of the figure.
        font_size (int): Font size used in the figure.
        template (str): Plotly template to apply.
        legend_title (str): Title of the legend.
        showlegend (bool): Whether to show the legend.
    """

    @update_and_export_plot(
        json_path=json_path,
        height=height,
        width=width,
        font_size=font_size,
        template=template,
        legend_title=legend_title,
        showlegend=showlegend,
    )
    def _export():
        return fig

    _export()