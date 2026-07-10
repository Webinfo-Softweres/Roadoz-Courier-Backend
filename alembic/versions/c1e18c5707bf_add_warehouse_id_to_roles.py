"""add warehouse_id to roles

Revision ID: c1e18c5707bf
Revises: 3aa6b509345d
Create Date: 2026-07-10 18:12:33.866118

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c1e18c5707bf'
down_revision: Union[str, None] = '3aa6b509345d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('roles', sa.Column('warehouse_id', sa.String(length=36), nullable=True))
    op.create_index(op.f('ix_roles_warehouse_id'), 'roles', ['warehouse_id'], unique=False)
    op.create_foreign_key(None, 'roles', 'warehouse_addresses', ['warehouse_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    op.drop_constraint(None, 'roles', type_='foreignkey')
    op.drop_index(op.f('ix_roles_warehouse_id'), table_name='roles')
    op.drop_column('roles', 'warehouse_id')
