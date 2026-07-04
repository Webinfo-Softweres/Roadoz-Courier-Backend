"""add_weight_unit_to_order_packages

Revision ID: 826da0476dd9
Revises: 23ce2c56d92c
Create Date: 2026-07-04 21:14:49.451490

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '826da0476dd9'
down_revision: Union[str, None] = '23ce2c56d92c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'order_packages',
        sa.Column('weight_unit', sa.String(5), nullable=False, server_default='kg')
    )


def downgrade() -> None:
    op.drop_column('order_packages', 'weight_unit')
