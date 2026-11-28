"""phase8_full_suite

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-27 20:05:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def _json_type() -> sa.types.TypeEngine:
    return sa.JSON().with_variant(postgresql.JSONB(), 'postgresql')


def upgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(
            sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.false())
        )

    with op.batch_alter_table('classrooms') as batch_op:
        batch_op.add_column(sa.Column('invite_code', sa.String(length=24), nullable=True))
        batch_op.add_column(
            sa.Column('invite_enabled', sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.create_unique_constraint('uq_classrooms_invite_code', ['invite_code'])

    with op.batch_alter_table('ai_generation_jobs') as batch_op:
        batch_op.drop_constraint('ck_ai_job_type', type_='check')
        batch_op.create_check_constraint(
            'ck_ai_job_type',
            "job_type IN ('lesson_generator', 'socratic_tutor', 'blueprint_architect', 'study_guide', 'strong_exam', 'dynamic_visual', 'adaptive_remediation')",
        )

    op.create_table(
        'password_reset_tokens',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )

    op.create_table(
        'email_verification_tokens',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )

    op.create_table(
        'live_quiz_sessions',
        sa.Column('organization_id', sa.Uuid(), nullable=True),
        sa.Column('classroom_id', sa.Uuid(), nullable=True),
        sa.Column('lesson_version_id', sa.Uuid(), nullable=False),
        sa.Column('host_user_id', sa.Uuid(), nullable=False),
        sa.Column('room_code', sa.String(length=16), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='waiting'),
        sa.Column('current_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.CheckConstraint("status IN ('waiting', 'active', 'finished')", name='ck_live_quiz_status'),
        sa.CheckConstraint('current_index >= 0', name='ck_live_quiz_index'),
        sa.ForeignKeyConstraint(['classroom_id'], ['classrooms.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['host_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lesson_version_id'], ['lesson_versions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('room_code'),
    )

    op.create_table(
        'live_quiz_participants',
        sa.Column('session_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('display_name', sa.String(length=120), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('answered_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('correct_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_answered_index', sa.Integer(), nullable=False, server_default='-1'),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['live_quiz_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'push_subscriptions',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('endpoint', sa.Text(), nullable=False),
        sa.Column('subscription_json', _json_type(), nullable=False),
        sa.Column('device_label', sa.String(length=120), nullable=False, server_default='Web PWA'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('push_subscriptions')
    op.drop_table('live_quiz_participants')
    op.drop_table('live_quiz_sessions')
    op.drop_table('email_verification_tokens')
    op.drop_table('password_reset_tokens')

    with op.batch_alter_table('ai_generation_jobs') as batch_op:
        batch_op.drop_constraint('ck_ai_job_type', type_='check')
        batch_op.create_check_constraint(
            'ck_ai_job_type',
            "job_type IN ('lesson_generator', 'socratic_tutor', 'blueprint_architect', 'study_guide', 'strong_exam', 'dynamic_visual')",
        )

    with op.batch_alter_table('classrooms') as batch_op:
        batch_op.drop_constraint('uq_classrooms_invite_code', type_='unique')
        batch_op.drop_column('invite_enabled')
        batch_op.drop_column('invite_code')

    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('email_verified')
