"""add_country_remove_lat_lng_parcel_sender_receiver

Revision ID: 15fd41c6b185
Revises: 0c5230776947
Create Date: 2026-08-07 14:01:44.120587

Also creates parcel_senders / parcel_receivers when missing.
0c5230776947 added FKs to those tables but never created them, which
blocked staging alembic upgrade head with MISSING_TABLE.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql

revision: str = "15fd41c6b185"
down_revision: Union[str, None] = "0c5230776947"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_party_table(inspector, table_name: str) -> None:
    if table_name in inspector.get_table_names():
        return
    op.create_table(
        table_name,
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=True),
        sa.Column("mobile", sa.String(length=20), nullable=True),
        sa.Column("alternate_mobile", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address_line_1", sa.String(length=500), nullable=True),
        sa.Column("address_line_2", sa.String(length=500), nullable=True),
        sa.Column("pincode", sa.String(length=10), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("franchise_id", sa.String(length=36), nullable=True),
        sa.Column("warehouse_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["franchise_id"], ["franchises.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["warehouse_id"], ["warehouse_addresses.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(f"ix_{table_name}_created_by", table_name, ["created_by"])
    op.create_index(f"ix_{table_name}_franchise_id", table_name, ["franchise_id"])
    op.create_index(f"ix_{table_name}_warehouse_id", table_name, ["warehouse_id"])


def _ensure_column(inspector, table_name: str, column_name: str, column) -> None:
    cols = {c["name"] for c in inspector.get_columns(table_name)}
    if column_name not in cols:
        op.add_column(table_name, column)


def _drop_column_if_exists(inspector, table_name: str, column_name: str) -> None:
    cols = {c["name"] for c in inspector.get_columns(table_name)}
    if column_name in cols:
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    _ensure_party_table(inspector, "parcel_senders")
    _ensure_party_table(inspector, "parcel_receivers")

    # Refresh inspector after possible creates
    inspector = inspect(bind)

    _ensure_column(
        inspector,
        "parcel_receivers",
        "country",
        sa.Column("country", sa.String(length=100), nullable=True),
    )
    _ensure_column(
        inspector,
        "parcel_senders",
        "country",
        sa.Column("country", sa.String(length=100), nullable=True),
    )

    inspector = inspect(bind)
    _drop_column_if_exists(inspector, "parcel_senders", "lat")
    _drop_column_if_exists(inspector, "parcel_senders", "lng")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "parcel_senders" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("parcel_senders")}
        if "lng" not in cols:
            op.add_column("parcel_senders", sa.Column("lng", mysql.FLOAT(), nullable=True))
        if "lat" not in cols:
            op.add_column("parcel_senders", sa.Column("lat", mysql.FLOAT(), nullable=True))
        if "country" in cols:
            op.drop_column("parcel_senders", "country")
    if "parcel_receivers" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("parcel_receivers")}
        if "country" in cols:
            op.drop_column("parcel_receivers", "country")
