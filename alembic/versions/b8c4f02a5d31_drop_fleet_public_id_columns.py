"""drop fleet public_id columns

Revision ID: b8c4f02a5d31
Revises: a7f3e91b4c20
Create Date: 2026-07-16 07:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.engine.reflection import Inspector

revision: str = "b8c4f02a5d31"
down_revision: Union[str, None] = "a7f3e91b4c20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_public_id(table: str) -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = {col["name"] for col in inspector.get_columns(table)}
    if "public_id" not in columns:
        return
    indexes = {idx["name"] for idx in inspector.get_indexes(table)}
    index_name = op.f(f"ix_{table}_public_id")
    if index_name in indexes:
        op.drop_index(index_name, table_name=table)
    op.drop_column(table, "public_id")


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = set(inspector.get_table_names())
    if "drivers" in tables:
        _drop_public_id("drivers")
    if "vehicles" in tables:
        _drop_public_id("vehicles")


def downgrade() -> None:
    pass
