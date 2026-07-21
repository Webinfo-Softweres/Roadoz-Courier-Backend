"""remove unique constraint from role name

Revision ID: 85a39ba778fc
Revises: c1e18c5707bf
Create Date: 2026-07-10 17:02:15.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = '85a39ba778fc'
down_revision: Union[str, None] = 'c1e18c5707bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('ix_roles_name', table_name='roles')
    op.create_index(op.f('ix_roles_name'), 'roles', ['name'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_roles_name'), table_name='roles')
    op.create_index('ix_roles_name', 'roles', ['name'], unique=True)
