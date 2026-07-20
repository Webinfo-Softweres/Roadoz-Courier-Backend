"""merge heads

Revision ID: 4ff9a0de5aa1
Revises: 3003ccf654d8, b8c4f02a5d31
Create Date: 2026-07-19 16:06:13.948447

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '4ff9a0de5aa1'
down_revision: Union[str, None] = ('3003ccf654d8', 'b8c4f02a5d31')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
