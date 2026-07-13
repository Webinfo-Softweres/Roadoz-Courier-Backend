import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine('mysql+aiomysql://root:@localhost:3306/roadoz_courier')
    async with engine.begin() as conn:
        try:
            await conn.execute(text('DROP TABLE warehouse_code_counter'))
        except Exception as e:
            print("Drop table failed:", e)
        
        try:
            await conn.execute(text('ALTER TABLE warehouse_addresses DROP COLUMN warehouse_code'))
        except Exception as e:
            print("Drop column failed:", e)

if __name__ == "__main__":
    asyncio.run(main())
