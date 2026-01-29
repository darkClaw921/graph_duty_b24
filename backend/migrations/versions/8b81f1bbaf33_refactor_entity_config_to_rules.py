"""refactor_entity_config_to_rules

Revision ID: 8b81f1bbaf33
Revises: 19e6c33f26e2
Create Date: 2026-01-23 21:35:33.715858

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b81f1bbaf33'
down_revision: Union[str, None] = '19e6c33f26e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Получаем список существующих таблиц
    existing_tables = inspector.get_table_names()
    
    # Получаем список существующих колонок в update_rules
    existing_columns = []
    if 'update_rules' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('update_rules')]
    
    # 1. Создаем таблицу update_rule_users (если не существует)
    if 'update_rule_users' not in existing_tables:
        op.create_table(
            'update_rule_users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('update_rule_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.ForeignKeyConstraint(['update_rule_id'], ['update_rules.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('update_rule_id', 'user_id', name='uq_update_rule_user')
        )
        op.create_index(op.f('ix_update_rule_users_id'), 'update_rule_users', ['id'], unique=False)
    
    # 2. Добавляем колонки в update_rules (если их еще нет)
    if 'entity_type' not in existing_columns:
        op.add_column('update_rules', sa.Column('entity_type', sa.String(), nullable=True))
    if 'entity_name' not in existing_columns:
        op.add_column('update_rules', sa.Column('entity_name', sa.String(), nullable=True))
    if 'update_time' not in existing_columns:
        op.add_column('update_rules', sa.Column('update_time', sa.Time(), nullable=True))
    if 'update_days' not in existing_columns:
        op.add_column('update_rules', sa.Column('update_days', sa.Text(), nullable=True))
    if 'distribution_percentage' not in existing_columns:
        op.add_column('update_rules', sa.Column('distribution_percentage', sa.Integer(), nullable=True, server_default='100'))
    
    # 3. Переносим данные из entity_configs в update_rules (если таблица существует)
    if 'entity_configs' in existing_tables and 'entity_config_id' in existing_columns:
        # Для каждого EntityConfig создаем правило с его правилами
        entity_configs = connection.execute(sa.text("SELECT id, entity_type, entity_name, enabled, update_time, update_days, distribution_percentage FROM entity_configs"))
        
        for ec in entity_configs:
            ec_id, entity_type, entity_name, enabled, update_time, update_days, distribution_percentage = ec
            
            # Получаем правила для этого EntityConfig
            rules = connection.execute(
                sa.text("SELECT id, rule_type, condition_config, priority, enabled FROM update_rules WHERE entity_config_id = :ec_id"),
                {"ec_id": ec_id}
            )
            
            # Если есть правила, обновляем их данными из EntityConfig
            for rule in rules:
                rule_id = rule[0]
                connection.execute(
                    sa.text("""
                        UPDATE update_rules 
                        SET entity_type = :entity_type,
                            entity_name = :entity_name,
                            update_time = :update_time,
                            update_days = :update_days,
                            distribution_percentage = :distribution_percentage,
                            enabled = :enabled
                        WHERE id = :rule_id
                    """),
                    {
                        "entity_type": entity_type,
                        "entity_name": entity_name,
                        "update_time": update_time,
                        "update_days": update_days,
                        "distribution_percentage": distribution_percentage or 100,
                        "enabled": enabled,
                        "rule_id": rule_id
                    }
                )
            
            # Если правил нет, создаем одно правило по умолчанию
            if not list(rules):
                connection.execute(
                    sa.text("""
                        INSERT INTO update_rules (entity_type, entity_name, rule_type, condition_config, priority, enabled, update_time, update_days, distribution_percentage)
                        VALUES (:entity_type, :entity_name, 'assigned_by_condition', '{}', 0, :enabled, :update_time, :update_days, :distribution_percentage)
                    """),
                    {
                        "entity_type": entity_type,
                        "entity_name": entity_name,
                        "enabled": enabled,
                        "update_time": update_time,
                        "update_days": update_days,
                        "distribution_percentage": distribution_percentage or 100
                    }
                )
    
    # 4. Заполняем NULL значения в новых колонках (если они существуют)
    if 'entity_type' in existing_columns:
        connection.execute(sa.text("UPDATE update_rules SET entity_type = 'unknown' WHERE entity_type IS NULL"))
    if 'entity_name' in existing_columns:
        connection.execute(sa.text("UPDATE update_rules SET entity_name = 'Unknown' WHERE entity_name IS NULL"))
    if 'update_time' in existing_columns:
        connection.execute(sa.text("UPDATE update_rules SET update_time = '09:00:00' WHERE update_time IS NULL"))
    
    # 5. Создаем индекс для entity_type (если еще не существует)
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('update_rules')] if 'update_rules' in existing_tables else []
    if 'ix_update_rules_entity_type' not in existing_indexes:
        op.create_index(op.f('ix_update_rules_entity_type'), 'update_rules', ['entity_type'], unique=False)
    
    # 6. Пересоздаем таблицу если нужно удалить entity_config_id или сделать колонки обязательными
    needs_recreate = False
    if 'entity_config_id' in existing_columns:
        needs_recreate = True
    
    # Проверяем, нужно ли сделать колонки обязательными
    # Если колонки только что добавлены, они nullable=True, но нам нужно сделать их обязательными
    if 'entity_type' not in existing_columns or 'entity_name' not in existing_columns or 'update_time' not in existing_columns:
        needs_recreate = True
    elif 'entity_type' in existing_columns or 'entity_name' in existing_columns or 'update_time' in existing_columns:
        # Проверяем, есть ли NULL значения (если есть, нужно пересоздать таблицу)
        result = connection.execute(sa.text("SELECT COUNT(*) FROM update_rules WHERE entity_type IS NULL OR entity_name IS NULL OR update_time IS NULL")).scalar()
        if result > 0:
            needs_recreate = True
    
    if needs_recreate:
        # Сначала удаляем foreign key constraint (если существует)
        try:
            op.drop_constraint('update_rules_entity_config_id_fkey', 'update_rules', type_='foreignkey')
        except Exception:
            pass  # Может не существовать
        
        # Удаляем индексы перед пересозданием таблицы
        existing_indexes_before = [idx['name'] for idx in inspector.get_indexes('update_rules')] if 'update_rules' in existing_tables else []
        if 'ix_update_rules_id' in existing_indexes_before:
            op.drop_index('ix_update_rules_id', table_name='update_rules')
        if 'ix_update_rules_entity_type' in existing_indexes_before:
            op.drop_index('ix_update_rules_entity_type', table_name='update_rules')
        
        # Создаем временную таблицу с правильной структурой (без entity_config_id, с обязательными колонками)
        op.create_table(
            'update_rules_new',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('entity_type', sa.String(), nullable=False),
            sa.Column('entity_name', sa.String(), nullable=False),
            sa.Column('rule_type', sa.String(), nullable=False),
            sa.Column('condition_config', sa.Text(), nullable=False),
            sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('enabled', sa.Boolean(), nullable=True, server_default='1'),
            sa.Column('update_time', sa.Time(), nullable=False),
            sa.Column('update_days', sa.Text(), nullable=True),
            sa.Column('distribution_percentage', sa.Integer(), nullable=True, server_default='100'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Копируем данные (используем COALESCE для NULL значений)
        connection.execute(sa.text("""
            INSERT INTO update_rules_new 
            (id, entity_type, entity_name, rule_type, condition_config, priority, enabled, update_time, update_days, distribution_percentage, created_at, updated_at)
            SELECT 
                id, 
                COALESCE(entity_type, 'unknown') as entity_type,
                COALESCE(entity_name, 'Unknown') as entity_name,
                rule_type, 
                condition_config, 
                priority, 
                enabled, 
                COALESCE(update_time, '09:00:00') as update_time,
                update_days, 
                COALESCE(distribution_percentage, 100) as distribution_percentage,
                created_at, 
                updated_at
            FROM update_rules
        """))
        
        # Удаляем старую таблицу
        op.drop_table('update_rules')
        
        # Переименовываем новую таблицу
        op.rename_table('update_rules_new', 'update_rules')
        
        # Создаем индексы
        op.create_index(op.f('ix_update_rules_id'), 'update_rules', ['id'], unique=False)
        op.create_index(op.f('ix_update_rules_entity_type'), 'update_rules', ['entity_type'], unique=False)
    
    # 7. Удаляем таблицу entity_configs (если она существует)
    if 'entity_configs' in existing_tables:
        try:
            op.drop_index('ix_entity_configs_entity_type', table_name='entity_configs')
        except Exception:
            pass
        try:
            op.drop_index('ix_entity_configs_id', table_name='entity_configs')
        except Exception:
            pass
        op.drop_table('entity_configs')


def downgrade() -> None:
    connection = op.get_bind()
    
    # Восстанавливаем таблицу entity_configs
    op.create_table(
        'entity_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_name', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('update_time', sa.Time(), nullable=False),
        sa.Column('update_days', sa.Text(), nullable=True),
        sa.Column('distribution_percentage', sa.Integer(), nullable=True, server_default='100'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_entity_configs_entity_type'), 'entity_configs', ['entity_type'], unique=False)
    op.create_index(op.f('ix_entity_configs_id'), 'entity_configs', ['id'], unique=False)
    
    # Восстанавливаем entity_config_id в update_rules
    op.add_column('update_rules', sa.Column('entity_config_id', sa.Integer(), nullable=True))
    
    # Группируем правила по entity_type и создаем EntityConfig для каждой группы
    entity_types = connection.execute(sa.text("SELECT DISTINCT entity_type FROM update_rules"))
    
    for row in entity_types:
        entity_type = row[0]
        # Берем первое правило для получения данных
        first_rule = connection.execute(
            sa.text("SELECT entity_name, update_time, update_days, distribution_percentage, enabled FROM update_rules WHERE entity_type = :entity_type LIMIT 1"),
            {"entity_type": entity_type}
        ).fetchone()
        
        if first_rule:
            entity_name, update_time, update_days, distribution_percentage, enabled = first_rule
            
            # Создаем EntityConfig
            result = connection.execute(
                sa.text("""
                    INSERT INTO entity_configs (entity_type, entity_name, enabled, update_time, update_days, distribution_percentage)
                    VALUES (:entity_type, :entity_name, :enabled, :update_time, :update_days, :distribution_percentage)
                """),
                {
                    "entity_type": entity_type,
                    "entity_name": entity_name,
                    "enabled": enabled,
                    "update_time": update_time,
                    "update_days": update_days,
                    "distribution_percentage": distribution_percentage or 100
                }
            )
            ec_id = result.lastrowid
            
            # Обновляем правила с entity_config_id
            connection.execute(
                sa.text("UPDATE update_rules SET entity_config_id = :ec_id WHERE entity_type = :entity_type"),
                {"ec_id": ec_id, "entity_type": entity_type}
            )
    
    op.alter_column('update_rules', 'entity_config_id', nullable=False)
    op.create_foreign_key('update_rules_entity_config_id_fkey', 'update_rules', 'entity_configs', ['entity_config_id'], ['id'])
    
    # Удаляем колонки из update_rules
    op.drop_index('ix_update_rules_entity_type', table_name='update_rules')
    op.drop_column('update_rules', 'distribution_percentage')
    op.drop_column('update_rules', 'update_days')
    op.drop_column('update_rules', 'update_time')
    op.drop_column('update_rules', 'entity_name')
    op.drop_column('update_rules', 'entity_type')
    
    # Удаляем таблицу update_rule_users
    op.drop_index('ix_update_rule_users_id', table_name='update_rule_users')
    op.drop_table('update_rule_users')
