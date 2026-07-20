import asyncio
from app.core.database import Base, engine
# Import explicitly to populate Base.metadata
from app.models.trip_sheet import TripSheet, TripSheetOrder

async def drop():
    async with engine.begin() as conn:
        print("Dropping tables...")
        await conn.run_sync(Base.metadata.drop_all, tables=[
            Base.metadata.tables['trip_sheet_orders'],
            Base.metadata.tables['trip_sheets']
        ])
        print("Done.")

asyncio.run(drop())
