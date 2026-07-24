"""rename trip sheet route fields

Revision ID: 5ec447f29e9b
Revises: 46173de05605
Create Date: 2026-07-21 11:38:53.082544

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy import inspect


revision: str = '5ec447f29e9b'
down_revision: Union[str, None] = '46173de05605'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name, column_name):
    bind = op.get_bind()
    insp = inspect(bind)
    columns = [col['name'] for col in insp.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Add new columns (idempotent)
    if not _column_exists('trip_sheets', 'route_city'):
        op.add_column('trip_sheets', sa.Column('route_city', sa.JSON(), nullable=True))
    if not _column_exists('trip_sheets', 'destination_city'):
        op.add_column('trip_sheets', sa.Column('destination_city', sa.String(length=255), nullable=True))

    # Drop old columns if they still exist
    if _column_exists('trip_sheets', 'route'):
        op.drop_column('trip_sheets', 'route')
    if _column_exists('trip_sheets', 'destination'):
        op.drop_column('trip_sheets', 'destination')


def downgrade() -> None:
    if not _column_exists('trip_sheets', 'destination'):
        op.add_column('trip_sheets', sa.Column('destination', mysql.VARCHAR(length=255), nullable=True))
    if not _column_exists('trip_sheets', 'route'):
        op.add_column('trip_sheets', sa.Column('route', mysql.JSON(), nullable=True))

    if _column_exists('trip_sheets', 'destination_city'):
        op.drop_column('trip_sheets', 'destination_city')
    if _column_exists('trip_sheets', 'route_city'):
        op.drop_column('trip_sheets', 'route_city')
