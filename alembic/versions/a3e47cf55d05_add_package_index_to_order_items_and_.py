"""add package_index to order_items and prepaid_amount to orders

Revision ID: a3e47cf55d05
Revises: df10f274a2b9
Create Date: 2026-07-03 19:01:05.812541

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = 'a3e47cf55d05'
down_revision: Union[str, None] = 'df10f274a2b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name, column_name):
    bind = op.get_bind()
    insp = inspect(bind)
    columns = [col['name'] for col in insp.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not _column_exists('order_items', 'package_index'):
        op.add_column('order_items', sa.Column('package_index', sa.Integer(), nullable=True))
    if not _column_exists('orders', 'prepaid_amount'):
        op.add_column('orders', sa.Column('prepaid_amount', sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    if _column_exists('order_items', 'package_index'):
        op.drop_column('order_items', 'package_index')
    if _column_exists('orders', 'prepaid_amount'):
        op.drop_column('orders', 'prepaid_amount')
