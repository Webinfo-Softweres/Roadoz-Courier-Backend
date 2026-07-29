"""pickup_assignment_drop_pickup_address_id_add_franchise_warehouse

Revision ID: d7abde4b970c
Revises: a3e47cf55d05
Create Date: 2026-07-29

Changes:
- Drop pickup_address_id column from pickup_assignments
- Add franchise_id column (FK → franchises.id)
- Add warehouse_id column (FK → warehouse_addresses.id)
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'd7abde4b970c'
down_revision = 'a3e47cf55d05'
branch_labels = None
depends_on = None


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


def upgrade():
    connection = op.get_bind()

    # 1. Add franchise_id if not already there
    if not column_exists("pickup_assignments", "franchise_id", connection):
        op.add_column(
            "pickup_assignments",
            sa.Column("franchise_id", sa.String(36), sa.ForeignKey("franchises.id", ondelete="SET NULL"), nullable=True, index=True)
        )

    # 2. Add warehouse_id if not already there
    if not column_exists("pickup_assignments", "warehouse_id", connection):
        op.add_column(
            "pickup_assignments",
            sa.Column("warehouse_id", sa.String(36), sa.ForeignKey("warehouse_addresses.id", ondelete="SET NULL"), nullable=True, index=True)
        )

    # 3. Drop pickup_address_id if it still exists
    if column_exists("pickup_assignments", "pickup_address_id", connection):
        # Drop FK constraint first (MySQL requires this)
        # Get the constraint name
        fk_result = connection.execute(
            sa.text(
                "SELECT constraint_name FROM information_schema.key_column_usage "
                "WHERE table_schema = DATABASE() "
                "AND table_name = 'pickup_assignments' "
                "AND column_name = 'pickup_address_id' "
                "AND referenced_table_name IS NOT NULL"
            )
        )
        for row in fk_result:
            op.drop_constraint(row[0], "pickup_assignments", type_="foreignkey")

        op.drop_column("pickup_assignments", "pickup_address_id")


def downgrade():
    connection = op.get_bind()

    # Re-add pickup_address_id
    if not column_exists("pickup_assignments", "pickup_address_id", connection):
        op.add_column(
            "pickup_assignments",
            sa.Column("pickup_address_id", sa.String(36), sa.ForeignKey("pickup_addresses.id", ondelete="RESTRICT"), nullable=True)
        )

    # Remove franchise_id and warehouse_id
    if column_exists("pickup_assignments", "franchise_id", connection):
        op.drop_column("pickup_assignments", "franchise_id")
    if column_exists("pickup_assignments", "warehouse_id", connection):
        op.drop_column("pickup_assignments", "warehouse_id")
