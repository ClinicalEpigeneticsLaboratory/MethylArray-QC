#!/usr/local/bin/python

import math
import pandas as pd
import numpy as np
import plotly.express as px
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import sys

# Computes Kruskal-Wallis results for a specific column and saves to JSON
def testKWToJSON(components_data: pd.DataFrame, component_names: list, column: str) -> None:
    kruskal_pvals = []
    test_method = []

    for component in component_names:
        df = components_data[[component, column]]
        kruskal_res = stats.kruskal(*[group[column].values for name, group in df.groupby(column)])
        kruskal_pvals.append(kruskal_res.pvalue)
        test_method.append("Kruskal-Wallis test")

    kruskal_col_res = pd.DataFrame(
        data = {
            f"{column}_p_value": kruskal_pvals,
            "Method": test_method
        },
        index=component_names
    )
    kruskal_col_res.to_json(f"PCA_PC_KW_test_{column}.json")

def areaPlotToJSON(number_of_pcs: int, number_of_cpgs: int, perc_of_cpgs: int, explained_var_ratio: np.ndarray, col: str) -> None:
    area_plot_data = {
        "Component": range(1, number_of_pcs + 1, 1),
        "Cumulative_explained_variance_%": np.cumsum(explained_var_ratio*100)
    }

    area_plot_data_df = pd.DataFrame(area_plot_data)

    fig_area = px.area(
        data_frame = area_plot_data_df,
        x = "Component",
        y = "Cumulative_explained_variance_%"
    )

    fig_area.update_xaxes(title = "Principal component")
    fig_area.update_yaxes(title = "Cumulative explained variance (%)")
    fig_area.update_layout(width = 600, height = 600, template = "ggplot2", title_text = f"PCA area plot - {col}<br>Top {perc_of_cpgs}% CpGs (n = {number_of_cpgs}) with highest variance", showlegend = False)
    fig_area.write_json(file = "PCA_area.json", pretty = True)

def scatterMatrixToJSON(components_data: pd.DataFrame, component_names: list, number_of_cpgs: int, perc_of_cpgs: int, column: str, scatter_matrix_component_count: int) -> None:
    fig_scatter = px.scatter_matrix(
        components_data,
        color = column,
        dimensions= component_names,
        labels = component_names
    )
    fig_scatter.update_traces(diagonal_visible=False)
    fig_scatter.update_layout(width = 600, height = 600, template = "ggplot2", title_text = f"PCA scatter matrix- {column}<br>Top {perc_of_cpgs}% (n = {number_of_cpgs}) CpGs with highest variance", showlegend = False)
    fig_scatter.write_json(file = f"PCA_scatter_matrix_{column}.json", pretty = True)

#'@ Deprecated
def dot2DToJSON(components_data: pd.DataFrame, component_names: list, number_of_cpgs: int, perc_of_cpgs: int, column: str) -> None:
    fig_dot = px.scatter(components_data, x=component_names[0], y=component_names[1], color = column)
    fig_dot.update_layout(width = 600, height = 600, template = "ggplot2", title_text = f"PCA 2D dot plot- {column}<br>Top {perc_of_cpgs}% (n = {number_of_cpgs}) CpGs with highest variance", showlegend = False)
    fig_dot.write_json(file = f"PCA_2D_dot_{column}.json", pretty = True)

def main():
    if len(sys.argv) != 8:
        print("Usage: python pca.py <path_to_imputed_mynorm> <path_to_sample_sheet> <perc_pca_cpgs> <pca_number_of_components> <column> <draw_area>")
        sys.exit(1)

    path_to_imputed_mynorm = sys.argv[1]
    path_to_sample_sheet = sys.argv[2]
    perc_pca_cpgs = int(sys.argv[3])
    pca_number_of_components = int(sys.argv[4])
    column = str(sys.argv[5])
    draw_area = str(sys.argv[6])
    pca_matrix_PC_count = int(sys.argv[7])

    imputed_mynorm = pd.read_parquet(path_to_imputed_mynorm)
    imputed_mynorm.set_index("CpG", inplace=True)

    sample_sheet = pd.read_csv(path_to_sample_sheet, index_col=0)
    sample_sheet[['Sentrix_ID','Sentrix_Position']] = sample_sheet['Array_Position'].str.split('_',expand=True)

    if column not in sample_sheet.columns:
        raise Exception(f"{column} not provided in sample sheet - PCA cannot be performed!")

    n_cpgs = math.ceil(imputed_mynorm.index.size * (perc_pca_cpgs/100))

    top_variances = imputed_mynorm.var(axis = 1).sort_values(ascending = False).nlargest(n_cpgs)

    transposed_data = imputed_mynorm[imputed_mynorm.index.isin(top_variances.index.to_list())].T
    pca_data = transposed_data.reset_index(names="Sample_Name").merge(sample_sheet.loc[:, column], on= "Sample_Name")

    scaler = StandardScaler().set_output(transform="pandas")
    scaled_PCA_data = scaler.fit_transform(pca_data.drop(columns = [column, "Sample_Name"]))
    pca_res = PCA(n_components=pca_number_of_components, random_state = 307)
    components = pca_res.fit_transform(scaled_PCA_data)
    component_col_names = [
                f"PC{cnt + 1} {int(var * 100)}%"
                for cnt, var in enumerate(pca_res.explained_variance_ratio_)
            ]

    components_df = pd.DataFrame(data=components,    # values
                index=sample_sheet.index.to_list(),    # 1st column as index
                columns=component_col_names)
    components_df = components_df.join(sample_sheet[column])

    scatterMatrixToJSON(
        components_data = components_df, 
        column = column, 
        component_names = component_col_names[0:pca_matrix_PC_count:1], 
        number_of_cpgs = n_cpgs, 
        perc_of_cpgs = perc_pca_cpgs,
        scatter_matrix_component_count = pca_matrix_PC_count
    )

    # dot2DToJSON(
    #     components_data = components_df, 
    #     column = column, 
    #     component_names = component_col_names, 
    #     number_of_cpgs = n_cpgs, 
    #     perc_of_cpgs = perc_pca_cpgs
    # )

    testKWToJSON(
        components_data = components_df, 
        column = column, 
        component_names = component_col_names
    )

    if draw_area == "true":
        areaPlotToJSON(
            col = column, 
            explained_var_ratio = pca_res.explained_variance_ratio_,
            number_of_cpgs = n_cpgs,
            number_of_pcs = pca_number_of_components,
            perc_of_cpgs = perc_pca_cpgs
        )

if __name__ == "__main__":
    main()