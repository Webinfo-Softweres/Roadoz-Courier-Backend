"""Add parcel_tripsheet_orders table

Revision ID: f605020f3ef5
Revises: ac4a2d6f413f
Create Date: 2026-08-06 16:52:05.872629

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'f605020f3ef5'
down_revision: Union[str, None] = 'ac4a2d6f413f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'parcel_tripsheet_orders',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('trip_sheet_id', sa.String(36), sa.ForeignKey('parcel_tripsheets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parcel_order_id', sa.String(36), sa.ForeignKey('parcel_orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_parcel_tripsheet_orders_trip_sheet_id', 'parcel_tripsheet_orders', ['trip_sheet_id'])
    op.create_index('ix_parcel_tripsheet_orders_parcel_order_id', 'parcel_tripsheet_orders', ['parcel_order_id'])


def downgrade() -> None:
    op.drop_index('ix_parcel_tripsheet_orders_parcel_order_id', table_name='parcel_tripsheet_orders')
    op.drop_index('ix_parcel_tripsheet_orders_trip_sheet_id', table_name='parcel_tripsheet_orders')
    op.drop_table('parcel_tripsheet_orders')
