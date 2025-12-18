# scripts/db_insert.py

import os
import pandas as pd
from sqlalchemy import create_engine

# SQLite database setup


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "invoice_ai.db")
engine = create_engine(f"sqlite:///{DB_PATH}")


# Insert DataFrame into SQL

def insert_invoices(df, table_name="invoices"):
    """
    Insert invoice DataFrame into SQLite table.
    Creates table if it doesn't exist, appends otherwise.
    """
    try:
        df.to_sql(table_name, engine, if_exists="append", index=False)
        print(f"{len(df)} records inserted into '{table_name}' successfully.")
    except Exception as e:
        print("Error inserting into SQLite database:", e)


if __name__ == "__main__":
    # Load extracted invoices CSV
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "extracted_invoices.csv")
    df = pd.read_csv(csv_path)

   
    insert_invoices(df)
