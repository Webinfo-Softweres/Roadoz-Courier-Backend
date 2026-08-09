"""
Safe DB Fix Script
==================
Run this directly on the server to add ALL missing columns to the `orders`
table without breaking existing data or failing if columns already exist.

Usage:
    python fix_missing_order_columns.py
"""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Columns to add: (column_name, sql_type, default)
COLUMNS_TO_ADD = [
    ("payment_status",      "VARCHAR(50)",   "'Payment_pending'"),
    ("razorpay_qr_id",      "VARCHAR(100)",  "NULL"),
    ("razorpay_qr_url",     "VARCHAR(255)",  "NULL"),
    ("razorpay_qr_upi_uri", "VARCHAR(255)",  "NULL"),
    ("cancellation_reason", "VARCHAR(500)",  "NULL"),
    ("cancellation_phase",  "VARCHAR(50)",   "NULL"),
    ("cancelled_at",        "DATETIME",      "NULL"),
]


async def add_missing_columns():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        for col_name, col_type, default in COLUMNS_TO_ADD:
            try:
                if default == "NULL":
                    sql = f"ALTER TABLE orders ADD COLUMN IF NOT EXISTS `{col_name}` {col_type} DEFAULT NULL"
                else:
                    sql = f"ALTER TABLE orders ADD COLUMN IF NOT EXISTS `{col_name}` {col_type} DEFAULT {default}"
                await conn.execute(text(sql))
                print(f"✅ Column '{col_name}' ensured.")
            except Exception as e:
                print(f"⚠️  Column '{col_name}' skipped: {e}")

    await engine.dispose()
    print("\n✅ All columns processed. Restart your server now.")


if __name__ == "__main__":
    asyncio.run(add_missing_columns())
