#!/usr/local/bin/python

import math
import pandas as pd
import plotly.express as px
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import sys

def main():
    if len(sys.argv) != 6:
        print("Usage: python pca.py <path_to_imputed_mynorm> <path_to_sample_sheet> <perc_pca_cpgs> <pca_number_of_components> <column>")
        sys.exit(1)

    path_to_imputed_mynorm = sys.argv[1]
    path_to_sample_sheet = sys.argv[2]
    perc_pca_cpgs = int(sys.argv[3])
    pca_number_of_components = int(sys.argv[4])
    column = str(sys.argv[5])

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

    fig_dot = px.scatter(components_df, x=component_col_names[0], y=component_col_names[1], color = column)
    fig_dot.update_layout(width = 600, height = 600, template = "ggplot2", title_text = f"PCA 2D dot plot- {column}<br>Top {perc_pca_cpgs}% CpGs with highest variance", showlegend = False)
    fig_dot.write_json(file = f"PCA_2D_dot_{column}.json", pretty = True)

    scree_plot_data = {
        "Component": range(1, pca_number_of_components + 1, 1),
        "Explained_variance_%": pca_res.explained_variance_ratio_*100
    }

    scree_plot_data_df = pd.DataFrame(scree_plot_data)

    fig_scree = px.line(scree_plot_data_df, x = "Component", y = "Explained_variance_%")
    fig_scree.update_xaxes(title = "Principal component")
    fig_scree.update_yaxes(title = "Cumulative explained variance (%)")
    fig_scree.update_layout(width = 600, height = 600, template = "ggplot2", title_text = f"PCA scree plot - {column}<br>Top {perc_pca_cpgs}% CpGs with highest variance", showlegend = False)
    fig_scree.write_json(file = f"PCA_scree_{column}.json", pretty = True)

if __name__ == "__main__":
    main()