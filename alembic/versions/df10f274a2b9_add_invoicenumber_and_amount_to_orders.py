"""add invoicenumber and amount to orders

Revision ID: df10f274a2b9
Revises: 09dec204a975
Create Date: 2026-06-30 10:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'df10f274a2b9'
down_revision: Union[str, None] = '09dec204a975'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name, column_name):
    bind = op.get_bind()
    insp = inspect(bind)
    columns = [col['name'] for col in insp.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not _column_exists('orders', 'invoicenumber'):
        op.add_column('orders', sa.Column('invoicenumber', sa.Integer(), nullable=True))
    if not _column_exists('orders', 'amount'):
        op.add_column('orders', sa.Column('amount', sa.Integer(), nullable=True))


def downgrade() -> None:
    if _column_exists('orders', 'amount'):
        op.drop_column('orders', 'amount')
    if _column_exists('orders', 'invoicenumber'):
        op.drop_column('orders', 'invoicenumber')
