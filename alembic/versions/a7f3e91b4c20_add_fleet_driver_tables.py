"""add fleet driver tables

Revision ID: a7f3e91b4c20
Revises: 46173de05605
Create Date: 2026-07-16 06:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine.reflection import Inspector

revision: str = "a7f3e91b4c20"
down_revision: Union[str, None] = "46173de05605"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()

    if "vehicles" not in tables:
        op.create_table(
            "vehicles",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("franchise_id", sa.String(length=36), nullable=True),
            sa.Column("type", sa.String(length=50), nullable=False),
            sa.Column("plate_number", sa.String(length=50), nullable=False),
            sa.Column("make", sa.String(length=100), nullable=False),
            sa.Column("model", sa.String(length=100), nullable=False),
            sa.Column("year", sa.String(length=10), nullable=False),
            sa.Column("color", sa.String(length=50), nullable=True),
            sa.Column("status", sa.String(length=30), server_default=sa.text("'draft'"), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["franchise_id"], ["franchises.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_vehicles_franchise_id"), "vehicles", ["franchise_id"], unique=False)

    if "drivers" not in tables:
        op.create_table(
            "drivers",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("franchise_id", sa.String(length=36), nullable=True),
            sa.Column("vehicle_id", sa.String(length=36), nullable=True),
            sa.Column("first_name", sa.String(length=100), nullable=False),
            sa.Column("last_name", sa.String(length=100), nullable=False),
            sa.Column("phone", sa.String(length=30), nullable=True),
            sa.Column("dob", sa.Date(), nullable=True),
            sa.Column("onboarding_status", sa.String(length=30), server_default=sa.text("'incomplete'"), nullable=False),
            sa.Column("status", sa.String(length=30), server_default=sa.text("'draft'"), nullable=False),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("rejection_reason", sa.String(length=500), nullable=True),
            sa.Column("online", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["franchise_id"], ["franchises.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id"),
        )
        op.create_index(op.f("ix_drivers_franchise_id"), "drivers", ["franchise_id"], unique=False)
        op.create_index(op.f("ix_drivers_user_id"), "drivers", ["user_id"], unique=True)
        op.create_index(op.f("ix_drivers_vehicle_id"), "drivers", ["vehicle_id"], unique=False)

    if "fleet_files" not in tables:
        op.create_table(
            "fleet_files",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("subject_type", sa.String(length=50), nullable=False),
            sa.Column("subject_id", sa.String(length=36), nullable=False),
            sa.Column("document_type", sa.String(length=50), nullable=False),
            sa.Column("path", sa.String(length=500), nullable=False),
            sa.Column("content_type", sa.String(length=100), nullable=True),
            sa.Column("file_size", sa.Integer(), nullable=True),
            sa.Column("original_filename", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("subject_id", "document_type", name="uq_fleet_file_subject_doc"),
        )
        op.create_index(op.f("ix_fleet_files_subject_id"), "fleet_files", ["subject_id"], unique=False)
        op.create_index(op.f("ix_fleet_files_subject_type"), "fleet_files", ["subject_type"], unique=False)

    if "driver_payout_accounts" not in tables:
        op.create_table(
            "driver_payout_accounts",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("driver_id", sa.String(length=36), nullable=False),
            sa.Column("account_holder_name", sa.String(length=200), nullable=False),
            sa.Column("bank_name", sa.String(length=200), nullable=False),
            sa.Column("account_number", sa.String(length=50), nullable=False),
            sa.Column("ifsc_or_routing_code", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("driver_id"),
        )
        op.create_index(op.f("ix_driver_payout_accounts_driver_id"), "driver_payout_accounts", ["driver_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_driver_payout_accounts_driver_id"), table_name="driver_payout_accounts")
    op.drop_table("driver_payout_accounts")
    op.drop_index(op.f("ix_fleet_files_subject_type"), table_name="fleet_files")
    op.drop_index(op.f("ix_fleet_files_subject_id"), table_name="fleet_files")
    op.drop_table("fleet_files")
    op.drop_index(op.f("ix_drivers_vehicle_id"), table_name="drivers")
    op.drop_index(op.f("ix_drivers_user_id"), table_name="drivers")
    op.drop_index(op.f("ix_drivers_franchise_id"), table_name="drivers")
    op.drop_table("drivers")
    op.drop_index(op.f("ix_vehicles_franchise_id"), table_name="vehicles")
    op.drop_table("vehicles")
