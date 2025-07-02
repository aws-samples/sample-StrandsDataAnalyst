import os

import sqlite3
import pandas as pd
from tqdm import tqdm


def csv_to_sqlite(csv_directory):
    """ 
    Given a directory containing CSV files (one file per table),
    generates a single SQLite DB containing those tables.
    The SQLite file will be named after the directory with a '.sqlite' extension.
    """
    # Generate SQLite DB path from directory name
    db_name = os.path.basename(os.path.normpath(csv_directory)) + ".sqlite"
    sqlite_db_path = os.path.join(csv_directory, db_name)
    if os.path.exists(sqlite_db_path):
        os.remove(sqlite_db_path)

    # Connect to SQLite database (it will be created if it doesn't exist)
    conn = sqlite3.connect(sqlite_db_path)

    # Iterate through each CSV file in the directory
    for filename in os.listdir(csv_directory):
        if filename.endswith(".csv"):
            table_name = os.path.splitext(filename)[0]
            if table_name == "sqlite_sequence":
                continue

            # Read CSV into a DataFrame
            df = pd.read_csv(os.path.join(csv_directory, filename))

            # Write the data into a new table in SQLite
            df.to_sql(table_name, conn, if_exists='replace', index=False)

    # Close connection
    conn.close()


def convert_databases(data_path):
    dirs = []
    for dir_name in os.listdir(data_path):
        dir_path = os.path.join(data_path, dir_name)
        if not os.path.isdir(dir_path):
            continue
        dirs.append(dir_path)
    
    for dir_path in tqdm(dirs):
        try:
            csv_to_sqlite(dir_path)
        except Exception as e:
            print(f"Error processing {dir_path}: {e}")


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--data_path", type=str, default="./data/visEval_dataset/databases")
    args = parser.parse_args()

    convert_databases(args.data_path)
