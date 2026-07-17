#!/usr/local/bin/python

"""
A module responsible for PCA
"""


import math
import sys

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from decorators import update_and_export_plot
from plot_export_utils import export_decorated_fig_with_custom_name
from i18n import t
import pingouin as pg
#from scipy import stats
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Computes Kruskal-Wallis results for a specific column and saves to JSON 
def test_kw_to_json(
    components_data: pd.DataFrame, component_names: list, column: str
) -> None:
    """A function computing Kruskal-Wallis test comparing principal \
        components for currently processed column and exporting the \
        results to JSON file

    Args:
        components_data (pd.DataFrame): Plot data for components, of the following format:

        components_df = pd.DataFrame(
            data=components,  # values
            index=sample_sheet.index.to_list(),  # 1st column as index
            columns=component_col_names,
        )

        where components is a result of calling fit_transform on an object returned by PCA function
        component_names (list):List containing names of principal \
            components (with percentage of explained variance)
        column (str): Currently processed column
    """
    kruskal_pvals = []
    test_method = []
    column_vals = []
    infos = []

    for component in component_names:
        
        df = components_data[[component, column]].dropna()

        grouped_data = [group[component].values for _, group in df.groupby(column)]
        group_sizes = [len(g) for g in grouped_data]
        
        if len(grouped_data) < 2:
            kruskal_pvals.append(float("nan"))
            test_method.append("Kruskal-Wallis test")
            column_vals.append(column)
            infos.append("Too few groups to compare — test skipped")
            continue
        
        all_groups_one_sample = all(size == 1 for size in group_sizes)
        some_too_small = any(size < 2 for size in group_sizes)
        no_within_group_variation = all(np.all(g == g[0]) for g in grouped_data)
        identical_across_groups = np.allclose(
            [np.mean(g) for g in grouped_data], np.mean([v for g in grouped_data for v in g])
        )

        kruskal_res = pg.kruskal(data=df, dv=component, between=column)
        pval = kruskal_res['p-unc'].values[0]  # Extract p-value
        kruskal_pvals.append(pval)
        test_method.append("Kruskal-Wallis test")
        column_vals.append(column)

        info = ""

        if len(grouped_data) < 2:
            info = "Too few groups to compare"
        elif all_groups_one_sample:
            info = "Each group contains only one sample — insufficient data for test"
        elif some_too_small:
            info = "One or more groups have <2 samples — results may be unreliable"
        elif no_within_group_variation:
            info = "No variation across or within groups — test not meaningful"
        elif identical_across_groups:
            info = "Groups have near-identical means — low between-group variation"
        else:
            info = "OK"
        infos.append(info)
    kruskal_col_res = pd.DataFrame(
        data={
            "Column": column_vals,
            "Component": component_names,
            "Method": test_method,
            "p-value": kruskal_pvals, 
            "Info": infos
        },
    )
    kruskal_col_res.to_json(f"PCA_PC_KW_test_{column}.json", orient='records', indent=2)


@update_and_export_plot(
    json_path="PCA_area_plot.json", width=600, height=775, showlegend=False
)
def get_area_plot(
    number_of_pcs: int,
    number_of_cpgs: int,
    perc_of_cpgs: int,
    explained_var_ratio: np.ndarray,
    language: str = "en",
) -> go.Figure:
    """A function generating area plot showing explained variance for principal components

    Args:
        number_of_pcs (int): Number of principal components
        number_of_cpgs (int): Number of CpGs from imputed mynorm used for PCA \
            (computed from perc_of_cpgs)
        perc_of_cpgs (int): Percentage of CpGs from imputed mynorm used for PCA, \
            provided by user
        explained_var_ratio (np.ndarray): Ratio of explained variance \
            for each component
        language (str): report language ("en"/"pl") for the axis/title labels

    Returns:
        go.Figure: area plot
    """
    area_plot_data = {
        "Component": range(1, number_of_pcs + 1, 1),
        "Explained variance (%)": explained_var_ratio * 100,
        "Cumulative explained variance (%)": np.cumsum(explained_var_ratio * 100),
    }

    area_plot_data_df = pd.DataFrame(area_plot_data)

    fig_area = px.area(
        data_frame=area_plot_data_df,
        x="Component",
        y="Cumulative explained variance (%)",
        hover_data=area_plot_data_df.columns.to_list(),
    )

    # fig_area = go.Figure()
    # fig_area.add_trace(go.Scatter(
    #     x=np.arange(1, number_of_pcs + 1),
    #     y=np.cumsum(explained_var_ratio * 100),
    #     fill="tozeroy",
    #     mode="lines",
    #     hoverinfo="x+y",
    # ))

    fig_area.update_xaxes(title=t("plot.pca.principal_component", language))
    fig_area.update_layout(
        title_text=t("plot.pca.area_title", language, p=perc_of_cpgs, n=number_of_cpgs),
        margin={"l": 20, "r": 20, "t": 100, "b": 20},
    )
    return fig_area


def get_scatter_matrix_json(
    components_data: pd.DataFrame,
    component_names: list,
    number_of_cpgs: int,
    perc_of_cpgs: int,
    column: str,
    language: str = "en",
) -> None:
    """A function generating scatter matrix plot

    Args:
        components_data (pd.DataFrame): Plot data for components, of the following format:

        components_df = pd.DataFrame(
            data=components,  # values
            index=sample_sheet.index.to_list(),  # 1st column as index
            columns=component_col_names,
        )

        where components is a result of calling fit_transform on an object returned by PCA function

        component_names (list): List containing names of principal \
            components (with percentage of explained variance)
        number_of_cpgs (int): Number of CpGs from imputed mynorm \
            used for PCA (computed from perc_of_cpgs)
        perc_of_cpgs (int): Percentage of CpGs from imputed mynorm used for PCA, provided by user
        column (str): Currently processed column

    Returns:
        None
    """

    fig_scatter = px.scatter_matrix(
        components_data,
        color=column,
        dimensions=component_names,
        labels=component_names,
    )
    fig_scatter.update_traces(diagonal_visible=False, showupperhalf=False)
    fig_scatter.update_layout(
        title_text=t("plot.pca.scatter_title", language, col=column, p=perc_of_cpgs, n=number_of_cpgs),
        #margin={"l": 20, "r": 20, "t": 175, "b": 20},
        margin={"l": 20, "r": 20, "t": 100, "b": 20},
    )

    if fig_scatter:
        export_decorated_fig_with_custom_name(
            fig=fig_scatter,
            json_path=f"PCA_scatter_matrix_{column}.json",
            #showlegend=False,
            height=len(component_names) * 125 + 100,
            width=len(component_names) * 125,
        )


def main():
    if len(sys.argv) != 8:
        print(
            "Usage: python pca.py <path_to_imputed_mynorm: str> \
                <path_to_sample_sheet: str> <perc_pca_cpgs: int> \
                    <pca_number_of_components: int> <pca_columns: str> \
                        <pca_matrix_pc_count: int> <report_language: en|pl>"
        )
        sys.exit(1)

    path_to_imputed_mynorm = sys.argv[1]
    path_to_sample_sheet = sys.argv[2]
    perc_pca_cpgs = int(sys.argv[3])
    pca_number_of_components = int(sys.argv[4])
    pca_columns = str(sys.argv[5]).split(sep=",")
    pca_matrix_pc_count = int(sys.argv[6])
    language = sys.argv[7]

    imputed_mynorm = pd.read_parquet(path_to_imputed_mynorm)
    imputed_mynorm.set_index("CpG", inplace=True)

    sample_sheet = pd.read_csv(path_to_sample_sheet, index_col=0)
    sample_sheet[["Sentrix_ID", "Sentrix_Position"]] = sample_sheet[
        "Array_Position"
    ].str.split("_", expand=True)

    for i, column in enumerate(pca_columns):
        if column not in sample_sheet.columns:
            raise ValueError(
                f"{column} not provided in sample sheet - PCA cannot be performed!"
            )

        n_cpgs = math.ceil(imputed_mynorm.index.size * (perc_pca_cpgs / 100))

        top_variances = (
            imputed_mynorm.var(axis=1).sort_values(ascending=False).nlargest(n_cpgs)
        )

        transposed_data = imputed_mynorm[
            imputed_mynorm.index.isin(top_variances.index.to_list())
        ].T
        pca_data = transposed_data.reset_index(names="Sample_Name").merge(
            sample_sheet.loc[:, column], on="Sample_Name"
        )

        scaler = StandardScaler().set_output(transform="pandas")
        scaled_pca_data = scaler.fit_transform(
            pca_data.drop(columns=[column, "Sample_Name"])
        )
        pca_res = PCA(n_components=pca_number_of_components, random_state=307)
        components = pca_res.fit_transform(scaled_pca_data)
        component_col_names = [
            f"PC{cnt + 1} {int(var * 100)}%"
            for cnt, var in enumerate(pca_res.explained_variance_ratio_)
        ]

        components_df = pd.DataFrame(
            data=components,  # values
            index=sample_sheet.index.to_list(),  # 1st column as index
            columns=component_col_names,
        )
        components_df = components_df.join(sample_sheet[column])

        get_scatter_matrix_json(
            components_data=components_df,
            column=column,
            component_names=component_col_names[0:pca_matrix_pc_count:1],
            number_of_cpgs=n_cpgs,
            perc_of_cpgs=perc_pca_cpgs,
            language=language,
        )

        if sample_sheet[column].nunique() >= 2:
            test_kw_to_json(
                components_data=components_df,
                column=column,
                component_names=component_col_names,
            )

        if i == 0:
            get_area_plot(
                explained_var_ratio=pca_res.explained_variance_ratio_,
                number_of_cpgs=n_cpgs,
                number_of_pcs=pca_number_of_components,
                perc_of_cpgs=perc_pca_cpgs,
                language=language,
            )


if __name__ == "__main__":
    main()
