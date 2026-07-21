"""add package_index to order_packages

Revision ID: 23ce2c56d92c
Revises: a3e47cf55d05
Create Date: 2026-07-03 19:18:24.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = '23ce2c56d92c'
down_revision: Union[str, None] = 'a3e47cf55d05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name, column_name):
    bind = op.get_bind()
    insp = inspect(bind)
    columns = [col['name'] for col in insp.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not _column_exists('order_packages', 'package_index'):
        op.add_column('order_packages', sa.Column('package_index', sa.Integer(), nullable=True))


def downgrade() -> None:
    if _column_exists('order_packages', 'package_index'):
        op.drop_column('order_packages', 'package_index')
