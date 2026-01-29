"""add_distribution_percentage_to_update_rule_users

Revision ID: 20658eee69cb
Revises: 8b81f1bbaf33
Create Date: 2026-01-23 21:53:36.848960

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20658eee69cb'
down_revision: Union[str, None] = '8b81f1bbaf33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем колонку distribution_percentage в таблицу update_rule_users
    op.add_column('update_rule_users', sa.Column('distribution_percentage', sa.Integer(), nullable=True, server_default='100'))


def downgrade() -> None:
    # Удаляем колонку distribution_percentage из таблицы update_rule_users
    op.drop_column('update_rule_users', 'distribution_percentage')
