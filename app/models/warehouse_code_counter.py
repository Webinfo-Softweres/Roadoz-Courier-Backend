import uuid
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class WarehouseCodeCounter(Base):
    __tablename__ = "warehouse_code_counter"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    year: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    last_sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
