"""Change lat lng columns from Float to Double

Revision ID: 738e6eb6606c
Revises: c5fabedcc295
Create Date: 2026-07-16 21:24:58.211173

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = '738e6eb6606c'
down_revision: Union[str, None] = 'c5fabedcc295'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # consignees
    op.alter_column('consignees', 'latitude',
               existing_type=mysql.FLOAT(),
               type_=sa.Double(),
               existing_nullable=True)
    op.alter_column('consignees', 'longitude',
               existing_type=mysql.FLOAT(),
               type_=sa.Double(),
               existing_nullable=True)
    
    # franchises
    op.alter_column('franchises', 'latitude',
               existing_type=mysql.FLOAT(),
               type_=sa.Double(),
               existing_nullable=True)
    op.alter_column('franchises', 'longitude',
               existing_type=mysql.FLOAT(),
               type_=sa.Double(),
               existing_nullable=True)
               
    # pickup_addresses
    op.alter_column('pickup_addresses', 'latitude',
               existing_type=mysql.FLOAT(),
               type_=sa.Double(),
               existing_nullable=True)
    op.alter_column('pickup_addresses', 'longitude',
               existing_type=mysql.FLOAT(),
               type_=sa.Double(),
               existing_nullable=True)
               
    # warehouse_addresses
    op.alter_column('warehouse_addresses', 'latitude',
               existing_type=mysql.FLOAT(),
               type_=sa.Double(),
               existing_nullable=True)
    op.alter_column('warehouse_addresses', 'longitude',
               existing_type=mysql.FLOAT(),
               type_=sa.Double(),
               existing_nullable=True)


def downgrade() -> None:
    # warehouse_addresses
    op.alter_column('warehouse_addresses', 'longitude',
               existing_type=sa.Double(),
               type_=mysql.FLOAT(),
               existing_nullable=True)
    op.alter_column('warehouse_addresses', 'latitude',
               existing_type=sa.Double(),
               type_=mysql.FLOAT(),
               existing_nullable=True)
               
    # pickup_addresses
    op.alter_column('pickup_addresses', 'longitude',
               existing_type=sa.Double(),
               type_=mysql.FLOAT(),
               existing_nullable=True)
    op.alter_column('pickup_addresses', 'latitude',
               existing_type=sa.Double(),
               type_=mysql.FLOAT(),
               existing_nullable=True)
               
    # franchises
    op.alter_column('franchises', 'longitude',
               existing_type=sa.Double(),
               type_=mysql.FLOAT(),
               existing_nullable=True)
    op.alter_column('franchises', 'latitude',
               existing_type=sa.Double(),
               type_=mysql.FLOAT(),
               existing_nullable=True)
               
    # consignees
    op.alter_column('consignees', 'longitude',
               existing_type=sa.Double(),
               type_=mysql.FLOAT(),
               existing_nullable=True)
    op.alter_column('consignees', 'latitude',
               existing_type=sa.Double(),
               type_=mysql.FLOAT(),
               existing_nullable=True)

