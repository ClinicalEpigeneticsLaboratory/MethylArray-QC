import pandas as pd
from sklearn.decomposition import PCA
import plotly.express as px 
from plotly.subplots import make_subplots
from sklearn.preprocessing import StandardScaler
import sys

# 3.	Pca dla N cpg z największą wariancją (domyślnie 10%) ale parametr do ustalenia przez usera, kolorowane po fenotypie, array, slide znów do wyboru przez usera domyślnie tylko po fenotypie o ile jest w podany w sample sheet
# TODO: add a visualisation with coloring by columns specified by the user

def preparePCAData(path_to_imputed_mynorm: str, n_cpgs: int):
    imputed_mynorm = pd.read_parquet(path_to_imputed_mynorm)
    imputed_mynorm.set_index("CpG", inplace=True)

    # Getting top variances
    top_variances = imputed_mynorm.var(axis = 1).sort_values(ascending = False).head(n_cpgs)

    # Filtering mynorm
    pca_data = imputed_mynorm[imputed_mynorm.index.isin(top_variances.index.to_list())].T

    return pca_data

def performPCA(pca_data: pd.DataFrame):
    
    # Data scaling
    scaler = StandardScaler().set_output(transform="pandas")
    scaled_PCA_data = scaler.fit_transform(pca_data)

    # Performing PCA
    PCA_res = PCA(n_components=2, random_state = 307).fit(scaled_PCA_data)
    return PCA_res

def main():
    if len(sys.argv) != 4:
        print("Usage: python pca.py <path_to_imputed_mynorm> <path_to_sample_sheet> <n_cpgs>")
        sys.exit(1)

    path_to_imputed_mynorm = sys.argv[1]
    path_to_sample_sheet = sys.argv[2]
    n_cpgs = sys.argv[3]

    # Provide additional parameter PCA_cols to plot PCA  for selected columns
    # funs: getFigHtml, performPCA - and do it on each column provided (allowed: Sample_Group - default, Sentrix_ID, Sentrix_Position)

    sample_sheet = pd.read_csv(path_to_sample_sheet, index_col=0)
    
    # Split only if in PCA_cols Sentrix_ID and/or Sentrix_Position is provided
    sample_sheet[['Sentrix_ID','Sentrix_Position']] = sample_sheet['Array_Position'].str.split('_',expand=True)

    pca_data = preparePCAData(path_to_imputed_mynorm, n_cpgs)
    PCA_res = performPCA(pca_data)

if __name__ == "__main__":
    main()