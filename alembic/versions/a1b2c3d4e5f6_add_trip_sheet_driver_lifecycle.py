"""Add trip sheet driver lifecycle columns and driver payment collections

Revision ID: a1b2c3d4e5f6
Revises: 777d33343dcb
Create Date: 2026-07-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "777d33343dcb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("trip_sheets", sa.Column("driver_status", sa.String(length=30), nullable=True))
    op.add_column("trip_sheets", sa.Column("accepted_at", sa.DateTime(), nullable=True))
    op.add_column("trip_sheets", sa.Column("started_at", sa.DateTime(), nullable=True))
    op.add_column("trip_sheets", sa.Column("completed_at", sa.DateTime(), nullable=True))
    op.add_column("trip_sheets", sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
    op.create_index("ix_trip_sheets_driver_status", "trip_sheets", ["driver_id", "driver_status"], unique=False)

    op.create_table(
        "driver_payment_collections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("driver_id", sa.String(length=36), nullable=False),
        sa.Column("trip_sheet_id", sa.String(length=36), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("payment_method", sa.String(length=30), nullable=False),
        sa.Column("payment_reference", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("transaction_id", sa.String(length=100), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trip_sheet_id"], ["trip_sheets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_reference"),
    )
    op.create_index("ix_driver_payment_collections_order_id", "driver_payment_collections", ["order_id"])
    op.create_index("ix_driver_payment_collections_driver_id", "driver_payment_collections", ["driver_id"])


def downgrade() -> None:
    op.drop_index("ix_driver_payment_collections_driver_id", table_name="driver_payment_collections")
    op.drop_index("ix_driver_payment_collections_order_id", table_name="driver_payment_collections")
    op.drop_table("driver_payment_collections")
    op.drop_index("ix_trip_sheets_driver_status", table_name="trip_sheets")
    op.drop_column("trip_sheets", "updated_at")
    op.drop_column("trip_sheets", "completed_at")
    op.drop_column("trip_sheets", "started_at")
    op.drop_column("trip_sheets", "accepted_at")
    op.drop_column("trip_sheets", "driver_status")
