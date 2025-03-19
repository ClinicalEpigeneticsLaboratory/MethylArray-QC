import pandas as pd
from sklearn.decomposition import PCA
import plotly.express as px 
import sys
from plotly.subplots import make_subplots

# 3.	Pca dla N cpg z największą wariancją (domyślnie 10%) ale parametr do ustalenia przez usera, kolorowane po fenotypie, array, slide znów do wyboru przez usera domyślnie tylko po fenotypie o ile jest w podany w sample sheet

def main():
    if len(sys.argv) != 3:
        print("Usage: python pca.py <path_to_imputed_mynorm> <path_to_sample_sheet>")
        sys.exit(1)

    path_to_imputed_mynorm = sys.argv[1]
    path_to_sample_sheet = sys.argv[2]

    # Load data
    imputed_mynorm = pd.read_parquet(path_to_imputed_mynorm)
    imputed_mynorm.set_index("CpG", inplace=True)

    sample_sheet = pd.read_csv(path_to_sample_sheet, index_col=0)
    sample_sheet[['Sentrix_ID','Sentrix_Position']] = sample_sheet['Array_Position'].str.split('_',expand=True)



    # Add column Sample_Group to schema
    #X_reduced = PCA(n_components=3).fit_transform(iris.data)

    #pca = PCA(n_components=2)
    #pca.fit(X)

if __name__ == "__main__":
    main()