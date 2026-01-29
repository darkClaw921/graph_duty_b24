"""add_update_related_contacts_companies_to_update_rules

Revision ID: 189756f3db4e
Revises: 20658eee69cb
Create Date: 2026-01-23 23:33:28.585041

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '189756f3db4e'
down_revision: Union[str, None] = '20658eee69cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем колонку update_related_contacts_companies в таблицу update_rules
    op.add_column('update_rules', sa.Column('update_related_contacts_companies', sa.Boolean(), nullable=True, server_default='0'))


def downgrade() -> None:
    # Удаляем колонку update_related_contacts_companies из таблицы update_rules
    op.drop_column('update_rules', 'update_related_contacts_companies')
