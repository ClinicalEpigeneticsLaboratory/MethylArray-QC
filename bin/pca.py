#!/usr/local/bin/python

import math
import pandas as pd
import plotly.express as px
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import sys

def main():
    if len(sys.argv) != 5:
        print("Usage: python pca.py <path_to_imputed_mynorm> <path_to_sample_sheet> <perc_pca_cpgs> <column>")
        sys.exit(1)

    path_to_imputed_mynorm = sys.argv[1]
    path_to_sample_sheet = sys.argv[2]
    perc_pca_cpgs= int(sys.argv[3])
    column = str(sys.argv[4])

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
    pca_res = PCA(n_components=2, random_state = 307)
    components = pca_res.fit_transform(scaled_PCA_data)
    component_col_names = [
                f"PC{cnt + 1} {int(var * 100)}%"
                for cnt, var in enumerate(pca_res.explained_variance_ratio_)
            ]

    components_df = pd.DataFrame(data=components,    # values
                index=sample_sheet.index.to_list(),    # 1st column as index
                columns=component_col_names)
    components_df = components_df.join(sample_sheet[column])

    fig = px.scatter(components_df, x=component_col_names[0], y=component_col_names[1], color = column, title = f"PCA - {column}<br>Top {perc_pca_cpgs}% CpGs with highest variance")
    fig.update_layout(showlegend = False)
    fig.write_json(file = f"PCA_{column}.json", pretty = True)

if __name__ == "__main__":
    main()