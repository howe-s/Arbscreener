from sqlalchemy import create_engine, text

engine = create_engine('sqlite:///users.db')

with engine.connect() as conn:
    conn.execute(text('ALTER TABLE contracts ADD COLUMN price_usd FLOAT;'))
    conn.commit()
print("Column 'price_usd' added successfully.")