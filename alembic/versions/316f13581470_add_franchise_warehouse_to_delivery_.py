"""add_franchise_warehouse_to_delivery_assignments

Revision ID: 316f13581470
Revises: ae29fc3306f3
Create Date: 2026-07-29 12:20:54.636176

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '316f13581470'
down_revision: Union[str, None] = 'ae29fc3306f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name, column_name, connection):
    """Helper: check if a column already exists in a table."""
    result = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() "
            "AND table_name = :tbl AND column_name = :col"
        ),
        {"tbl": table_name, "col": column_name}
    )
    return result.scalar() > 0


def upgrade() -> None:
    connection = op.get_bind()

    # 1. Add franchise_id if not already there
    if not column_exists("delivery_assignments", "franchise_id", connection):
        op.add_column(
            "delivery_assignments",
            sa.Column("franchise_id", sa.String(36), sa.ForeignKey("franchises.id", ondelete="SET NULL"), nullable=True, index=True)
        )

    # 2. Add warehouse_id if not already there
    if not column_exists("delivery_assignments", "warehouse_id", connection):
        op.add_column(
            "delivery_assignments",
            sa.Column("warehouse_id", sa.String(36), sa.ForeignKey("warehouse_addresses.id", ondelete="SET NULL"), nullable=True, index=True)
        )


def downgrade() -> None:
    connection = op.get_bind()

    if column_exists("delivery_assignments", "franchise_id", connection):
        op.drop_column("delivery_assignments", "franchise_id")
    if column_exists("delivery_assignments", "warehouse_id", connection):
        op.drop_column("delivery_assignments", "warehouse_id")
