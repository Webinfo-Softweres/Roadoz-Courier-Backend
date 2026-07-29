"""merge_trip_sheet_and_pickup_assignment

Revision ID: ae29fc3306f3
Revises: a1b2c3d4e5f6, d7abde4b970c
Create Date: 2026-07-29 11:26:05.678542

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'ae29fc3306f3'
down_revision: Union[str, None] = ('a1b2c3d4e5f6', 'd7abde4b970c')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
