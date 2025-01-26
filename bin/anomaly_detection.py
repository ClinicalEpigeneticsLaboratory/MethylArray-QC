#!/bin/Python

import sys
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.neighbors import LocalOutlierFactor


def main():
    if len(sys.argv) != 2:
        print("Usage: python cli2.py <path_to_imputed_mynorm>")
        sys.exit(1)

    path_to_imputed_mynorm = sys.argv[1]

    # Load data
    imputed_mynorm = pd.read_parquet(path_to_imputed_mynorm)

    # Anomaly detection
    algorithms = {
        "LOF": LocalOutlierFactor(novelty=True),
        "IsolationForest": IsolationForest(random_state=101),
        "OneClassSVM": OneClassSVM()
    }

    anomaly_results = pd.DataFrame(index=imputed_mynorm.columns)
    for name, algorithm in algorithms.items():
        if hasattr(algorithm, "fit_predict"):
            algorithm.fit(imputed_mynorm.T)
            anomaly_results[f"{name}_scores"] = algorithm.decision_function(imputed_mynorm.T)
            anomaly_results[f"{name}_classes"] = algorithm.predict(imputed_mynorm.T)

    # Save the results
    anomaly_results.to_csv("anomaly_results.csv")
    print("Anomaly detection results saved as 'anomaly_results.csv'.")


if __name__ == "__main__":
    main()
