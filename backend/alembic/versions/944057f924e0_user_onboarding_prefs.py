"""user_onboarding_prefs

Revision ID: 944057f924e0
Revises: 2d35761dfaf7
Create Date: 2026-11-27 00:34:33.165664
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '944057f924e0'
down_revision = '2d35761dfaf7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(
            sa.Column('daily_goal_minutes', sa.SmallInteger(), nullable=False, server_default='5')
        )
        batch_op.add_column(
            sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.create_check_constraint('ck_users_daily_goal', 'daily_goal_minutes BETWEEN 3 AND 120')


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('ck_users_daily_goal', type_='check')
        batch_op.drop_column('onboarding_completed')
        batch_op.drop_column('daily_goal_minutes')
