from sqlalchemy import create_engine
from sqlalchemy.sql import text

engine = create_engine('sqlite:///users.db')

try:
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS _alembic_tmp_contracts;"))
        conn.commit()
    print("Temporary table dropped successfully.")
except Exception as e:
    print(f"An error occurred: {e}")