#!/usr/local/bin/python

import sys

import pandas as pd
import plotly.express as px
from decorators import update_and_export_plot
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler


def ao(
    path_to_imputed_mynorm: str, contamination: str | float
) -> (pd.DataFrame, float):
    imputed_mynorm = pd.read_parquet(path_to_imputed_mynorm)

    if "CpG" in imputed_mynorm.columns:
        imputed_mynorm = imputed_mynorm.set_index("CpG")

    scaled_data = StandardScaler().fit_transform(imputed_mynorm.T)
    samples, cpgs = imputed_mynorm.columns, imputed_mynorm.index
    scaled_data = pd.DataFrame(scaled_data, index=samples, columns=cpgs)

    algorithms = {
        "IsolationForest": IsolationForest(
            random_state=101, contamination=contamination
        ),
    }

    anomaly_results = pd.DataFrame(index=samples)
    anomaly_results.index.name = "sample"

    for name, algorithm_instance in algorithms.items():
        algorithm_instance.fit(scaled_data)

        anomaly_results[f"|scores|"] = list(
            map(abs, algorithm_instance.score_samples(scaled_data))
        )
        anomaly_results[f"classes"] = list(
            map(
                lambda x: {"-1": "Anomaly", "1": "non-Anomaly"}.get(str(x)),
                algorithm_instance.predict(scaled_data),
            )
        )
        anomaly_results[f"threshold"] = [
            abs(algorithm_instance.offset_) for _ in range(len(samples))
        ]

    anomaly_results.to_parquet("ao_results.parquet")
    return anomaly_results, abs(algorithm_instance.offset_)


@update_and_export_plot("ao_plot.json")
def ao_plot(anomaly_results: str, offset: float):
    fig = px.bar(
        anomaly_results,
        y=anomaly_results.index,
        x="|scores|",
        color="classes",
        color_discrete_map={"Anomaly": "red", "non-Anomaly": "blue"},
    )
    fig.add_vline(x=offset, line_width=1, line_dash="dash", line_color="red")
    return fig


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python cli2.py <path_to_imputed_mynorm: str> <contamination: str | float>"
        )
        sys.exit(1)

    path_to_imputed_mynorm, contamination = sys.argv[1:]

    try:
        contamination = float(contamination)
    except ValueError:
        pass

    results, offset = ao(path_to_imputed_mynorm, contamination)
    ao_plot(results, offset)


if __name__ == "__main__":
    main()
