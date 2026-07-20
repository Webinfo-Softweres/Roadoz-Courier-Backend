"""Change trip_sheets route column to JSON

Revision ID: 49c332a9ff07
Revises: 8ea36cceb61b
Create Date: 2026-07-20 12:48:53.722785

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = '49c332a9ff07'
down_revision: Union[str, None] = '8ea36cceb61b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('trip_sheets', 'route',
               existing_type=sa.String(length=255),
               type_=sa.JSON(),
               existing_nullable=True)


def downgrade() -> None:
    op.alter_column('trip_sheets', 'route',
               existing_type=sa.JSON(),
               type_=sa.String(length=255),
               existing_nullable=True)
