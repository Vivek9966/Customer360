import sqlite3

conn = sqlite3.connect("project_memory.db")
cursor = conn.cursor()

# Create sample tables
cursor.execute("""
CREATE TABLE crm_db (
  cust_id INTEGER,
  dob DATE,
  city TEXT,
  gender TEXT
)
""")

cursor.execute("""
CREATE TABLE banking_db (
  customer_id INTEGER,
  avg_balance_12m FLOAT,
  txn_count INTEGER
)
""")

cursor.execute("""
CREATE TABLE credit_db (
  customer_id INTEGER,
  credit_rating FLOAT,
  total_loans INTEGER
)
""")

cursor.execute("""
CREATE TABLE investment_db (
  customer_id INTEGER,
  asset_value FLOAT,
  invested_products TEXT
)
""")

conn.commit()
conn.close()
