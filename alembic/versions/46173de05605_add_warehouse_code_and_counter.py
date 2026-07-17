"""add warehouse code and counter

Revision ID: 46173de05605
Revises: 85a39ba778fc
Create Date: 2026-07-11 05:19:35.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy.engine.reflection import Inspector

revision: str = '46173de05605'
down_revision: Union[str, None] = '85a39ba778fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()
    
    if 'warehouse_code_counter' not in tables:
        op.create_table('warehouse_code_counter',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('last_sequence', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('year')
        )
        
    columns = [c['name'] for c in inspector.get_columns('warehouse_addresses')]
    if 'warehouse_code' not in columns:
        op.add_column('warehouse_addresses', sa.Column('warehouse_code', sa.String(length=50), nullable=True))
        op.create_index(op.f('ix_warehouse_addresses_warehouse_code'), 'warehouse_addresses', ['warehouse_code'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_warehouse_addresses_warehouse_code'), table_name='warehouse_addresses')
    op.drop_column('warehouse_addresses', 'warehouse_code')
    op.drop_table('warehouse_code_counter')
