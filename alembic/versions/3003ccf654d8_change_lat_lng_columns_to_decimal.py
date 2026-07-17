"""Change lat lng columns to DECIMAL

Revision ID: 3003ccf654d8
Revises: 738e6eb6606c
Create Date: 2026-07-16 21:30:15.060690

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = '3003ccf654d8'
down_revision: Union[str, None] = '738e6eb6606c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # consignees
    op.alter_column('consignees', 'latitude',
               existing_type=mysql.DOUBLE(asdecimal=True),
               type_=sa.DECIMAL(precision=18, scale=8),
               existing_nullable=True)
    op.alter_column('consignees', 'longitude',
               existing_type=mysql.DOUBLE(asdecimal=True),
               type_=sa.DECIMAL(precision=18, scale=8),
               existing_nullable=True)
    
    # franchises
    op.alter_column('franchises', 'latitude',
               existing_type=mysql.DOUBLE(asdecimal=True),
               type_=sa.DECIMAL(precision=18, scale=8),
               existing_nullable=True)
    op.alter_column('franchises', 'longitude',
               existing_type=mysql.DOUBLE(asdecimal=True),
               type_=sa.DECIMAL(precision=18, scale=8),
               existing_nullable=True)
               
    # pickup_addresses
    op.alter_column('pickup_addresses', 'latitude',
               existing_type=mysql.DOUBLE(asdecimal=True),
               type_=sa.DECIMAL(precision=18, scale=8),
               existing_nullable=True)
    op.alter_column('pickup_addresses', 'longitude',
               existing_type=mysql.DOUBLE(asdecimal=True),
               type_=sa.DECIMAL(precision=18, scale=8),
               existing_nullable=True)
               
    # warehouse_addresses
    op.alter_column('warehouse_addresses', 'latitude',
               existing_type=mysql.DOUBLE(asdecimal=True),
               type_=sa.DECIMAL(precision=18, scale=8),
               existing_nullable=True)
    op.alter_column('warehouse_addresses', 'longitude',
               existing_type=mysql.DOUBLE(asdecimal=True),
               type_=sa.DECIMAL(precision=18, scale=8),
               existing_nullable=True)


def downgrade() -> None:
    # warehouse_addresses
    op.alter_column('warehouse_addresses', 'longitude',
               existing_type=sa.DECIMAL(precision=18, scale=8),
               type_=mysql.DOUBLE(asdecimal=True),
               existing_nullable=True)
    op.alter_column('warehouse_addresses', 'latitude',
               existing_type=sa.DECIMAL(precision=18, scale=8),
               type_=mysql.DOUBLE(asdecimal=True),
               existing_nullable=True)
               
    # pickup_addresses
    op.alter_column('pickup_addresses', 'longitude',
               existing_type=sa.DECIMAL(precision=18, scale=8),
               type_=mysql.DOUBLE(asdecimal=True),
               existing_nullable=True)
    op.alter_column('pickup_addresses', 'latitude',
               existing_type=sa.DECIMAL(precision=18, scale=8),
               type_=mysql.DOUBLE(asdecimal=True),
               existing_nullable=True)
               
    # franchises
    op.alter_column('franchises', 'longitude',
               existing_type=sa.DECIMAL(precision=18, scale=8),
               type_=mysql.DOUBLE(asdecimal=True),
               existing_nullable=True)
    op.alter_column('franchises', 'latitude',
               existing_type=sa.DECIMAL(precision=18, scale=8),
               type_=mysql.DOUBLE(asdecimal=True),
               existing_nullable=True)
               
    # consignees
    op.alter_column('consignees', 'longitude',
               existing_type=sa.DECIMAL(precision=18, scale=8),
               type_=mysql.DOUBLE(asdecimal=True),
               existing_nullable=True)
    op.alter_column('consignees', 'latitude',
               existing_type=sa.DECIMAL(precision=18, scale=8),
               type_=mysql.DOUBLE(asdecimal=True),
               existing_nullable=True)

