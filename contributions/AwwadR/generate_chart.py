import os
import subprocess
from io import StringIO

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns


CONTAINER_NAME = "postgres-m3-int"
DB_NAME = "amman_market"
DB_USER = "postgres"


def read_table_via_docker(table_name):
    query = f"COPY (SELECT * FROM {table_name}) TO STDOUT WITH CSV HEADER"

    cmd = [
        "docker",
        "exec",
        "-i",
        CONTAINER_NAME,
        "psql",
        "-U",
        DB_USER,
        "-d",
        DB_NAME,
        "-c",
        query,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to read table '{table_name}' via docker.\n{result.stderr}"
        )

    return pd.read_csv(StringIO(result.stdout))


def main():
    os.makedirs("contributions/AwwadR", exist_ok=True)

    sns.set_theme(style="whitegrid")
    sns.set_palette("colorblind")

    customers = read_table_via_docker("customers")
    products = read_table_via_docker("products")
    orders = read_table_via_docker("orders")
    order_items = read_table_via_docker("order_items")

    # cleaning
    orders = orders[orders["status"] != "cancelled"].copy()
    order_items = order_items[order_items["quantity"] <= 100].copy()
    customers["city"] = customers["city"].fillna("Unknown")

    # merge
    df = order_items.merge(orders, on="order_id", how="inner")
    df = df.merge(products, on="product_id", how="inner")
    df = df.merge(customers, on="customer_id", how="inner")

    # feature engineering
    df["line_revenue"] = df["quantity"] * df["unit_price"]

    order_category_values = (
        df.groupby(["order_id", "category"], as_index=False)["line_revenue"]
        .sum()
        .rename(columns={"line_revenue": "category_order_value"})
    )

    category_order = [
        "Clothing",
        "Electronics",
        "Food & Beverage",
        "Books",
        "Sports",
        "Home & Garden",
    ]

    plt.figure(figsize=(10, 6))
    ax = sns.boxplot(
        data=order_category_values,
        x="category",
        y="category_order_value",
        order=["Clothing", "Electronics", "Food & Beverage", "Books", "Sports", "Home & Garden"]
    )

    ax.set_title("Books Show Higher Typical Order Values Than Most Categories")
    ax.set_xlabel("Product Category")
    ax.set_ylabel("Order Value per Order (JOD)")
    plt.xticks(rotation=45)

    ax.annotate(
        "Highest median",
        xy=(3, 62),
        xytext=(3.15, 90),
        arrowprops=dict(arrowstyle="->")
    )

    plt.tight_layout()
    plt.savefig("contributions/AwwadR/chart.png", dpi=150, bbox_inches="tight")
    plt.close()

    print("chart.png created")


if __name__ == "__main__":
    main()