import json
import csv
import argparse
import os
import pandas as pd

from OpenOrchestrator.database import db_util


def process_csv(filepath):
    # Pandas håndterer både .xlsx, .xls og .csv automatisk
    if filepath.endswith('.xlsx') or filepath.endswith('.xls'):
        df = pd.read_excel(filepath, dtype=str)
    else:
        df = pd.read_csv(filepath, delimiter=";", dtype=str)

    queue = {}

    for _, row in df.iterrows():
        cpr = str(row.iloc[1])  # Column index 1
        aftale = str(row.iloc[3]).lstrip("0")  # Column index 3

        if cpr not in queue:
            queue[cpr] = []

        queue[cpr].append(aftale)

    return queue


def main():
    parser = argparse.ArgumentParser(description="Process kontrolafgifter CSV and create queue elements")
    parser.add_argument("filepath", help="Path to CSV file")
    parser.add_argument("--conn-string", help="OpenOrchestrator connection string (defaults to env var)")

    args = parser.parse_args()

    conn_string = args.conn_string or os.getenv("OpenOrchestratorConnString")

    if not conn_string:
        parser.error("Connection string must be provided via --conn-string or OpenOrchestratorConnString env var")

    queue = process_csv(args.filepath)

    db_util.connect(conn_string)

    for cpr, aftaler in queue.items():
        db_util.create_queue_element(
            queue_name="Kontrolafgifter i bus",
            data=json.dumps({"cpr": cpr, "aftaler": aftaler})
        )

    print(f"Processed {len(queue)} CPR numbers")


if __name__ == "__main__":
    main()
