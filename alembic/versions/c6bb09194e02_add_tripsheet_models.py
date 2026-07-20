"""Add TripSheet models

Revision ID: c6bb09194e02
Revises: 4ff9a0de5aa1
Create Date: 2026-07-19 16:10:26.286364

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = 'c6bb09194e02'
down_revision: Union[str, None] = '4ff9a0de5aa1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('trip_sheets',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('franchise_id', sa.String(length=36), nullable=True),
    sa.Column('warehouse_id', sa.String(length=36), nullable=True),
    sa.Column('destination_franchise_id', sa.String(length=36), nullable=True),
    sa.Column('route_franchise_ids', sa.JSON(), nullable=True),
    sa.Column('driver_id', sa.String(length=36), nullable=True),
    sa.Column('vehicle_id', sa.String(length=36), nullable=True),
    sa.Column('topay_freight', sa.Numeric(precision=12, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('topay_packages', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('credit_freight', sa.Numeric(precision=12, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('credit_packages', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cod_freight', sa.Numeric(precision=12, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('cod_packages', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('prepaid_freight', sa.Numeric(precision=12, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('prepaid_packages', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('total_freight', sa.Numeric(precision=12, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('total_packages', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('created_by', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['destination_franchise_id'], ['franchises.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['franchise_id'], ['franchises.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouse_addresses.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trip_sheets_created_by'), 'trip_sheets', ['created_by'], unique=False)
    op.create_index(op.f('ix_trip_sheets_destination_franchise_id'), 'trip_sheets', ['destination_franchise_id'], unique=False)
    op.create_index(op.f('ix_trip_sheets_driver_id'), 'trip_sheets', ['driver_id'], unique=False)
    op.create_index(op.f('ix_trip_sheets_franchise_id'), 'trip_sheets', ['franchise_id'], unique=False)
    op.create_index(op.f('ix_trip_sheets_vehicle_id'), 'trip_sheets', ['vehicle_id'], unique=False)
    op.create_index(op.f('ix_trip_sheets_warehouse_id'), 'trip_sheets', ['warehouse_id'], unique=False)

    op.create_table('trip_sheet_orders',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('trip_sheet_id', sa.String(length=36), nullable=False),
    sa.Column('order_id', sa.String(length=36), nullable=False),
    sa.Column('sl_no', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['trip_sheet_id'], ['trip_sheets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trip_sheet_orders_order_id'), 'trip_sheet_orders', ['order_id'], unique=False)
    op.create_index(op.f('ix_trip_sheet_orders_trip_sheet_id'), 'trip_sheet_orders', ['trip_sheet_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_trip_sheet_orders_trip_sheet_id'), table_name='trip_sheet_orders')
    op.drop_index(op.f('ix_trip_sheet_orders_order_id'), table_name='trip_sheet_orders')
    op.drop_table('trip_sheet_orders')
    
    op.drop_index(op.f('ix_trip_sheets_warehouse_id'), table_name='trip_sheets')
    op.drop_index(op.f('ix_trip_sheets_vehicle_id'), table_name='trip_sheets')
    op.drop_index(op.f('ix_trip_sheets_franchise_id'), table_name='trip_sheets')
    op.drop_index(op.f('ix_trip_sheets_driver_id'), table_name='trip_sheets')
    op.drop_index(op.f('ix_trip_sheets_destination_franchise_id'), table_name='trip_sheets')
    op.drop_index(op.f('ix_trip_sheets_created_by'), table_name='trip_sheets')
    op.drop_table('trip_sheets')
