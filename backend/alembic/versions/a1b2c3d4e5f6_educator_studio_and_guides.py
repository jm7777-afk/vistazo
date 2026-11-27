"""educator_studio_and_guides

Revision ID: a1b2c3d4e5f6
Revises: 944057f924e0
Create Date: 2026-11-27 11:05:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a1b2c3d4e5f6'
down_revision = '944057f924e0'
branch_labels = None
depends_on = None


def _json_type() -> sa.types.TypeEngine:
    return sa.JSON().with_variant(postgresql.JSONB(), 'postgresql')


def upgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(
            sa.Column('account_type', sa.String(length=20), nullable=False, server_default='student')
        )
        batch_op.create_check_constraint(
            'ck_users_account_type',
            "account_type IN ('student', 'educator')",
        )

    with op.batch_alter_table('lessons') as batch_op:
        batch_op.add_column(
            sa.Column('lesson_type', sa.String(length=30), nullable=False, server_default='micro_lesson')
        )
        batch_op.add_column(
            sa.Column('passing_score_pct', sa.SmallInteger(), nullable=False, server_default='70')
        )
        batch_op.create_check_constraint(
            'ck_lesson_type',
            "lesson_type IN ('micro_lesson', 'strong_exam', 'study_guide_drill')",
        )
        batch_op.create_check_constraint(
            'ck_lesson_passing_score',
            'passing_score_pct BETWEEN 0 AND 100',
        )

    with op.batch_alter_table('media_assets') as batch_op:
        batch_op.add_column(sa.Column('svg_markup', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('dynamic_spec_json', _json_type(), nullable=True))

    with op.batch_alter_table('ai_generation_jobs') as batch_op:
        batch_op.drop_constraint('ck_ai_job_type', type_='check')
        batch_op.create_check_constraint(
            'ck_ai_job_type',
            "job_type IN ('lesson_generator', 'socratic_tutor', 'blueprint_architect', 'study_guide', 'strong_exam', 'dynamic_visual')",
        )

    op.create_table(
        'study_guides',
        sa.Column('organization_id', sa.Uuid(), nullable=True),
        sa.Column('course_id', sa.Uuid(), nullable=True),
        sa.Column('lesson_id', sa.Uuid(), nullable=True),
        sa.Column('guide_type', sa.String(length=30), nullable=False, server_default='guia_estudio'),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content_markdown', sa.Text(), nullable=False),
        sa.Column('methodology_json', _json_type(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('ai_generated', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_by', sa.Uuid(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by', sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "guide_type IN ('pensum', 'temario', 'guia_estudio', 'metodologia', 'rubrica')",
            name='ck_study_guide_type',
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name='ck_study_guide_status',
        ),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_study_guides_course_status', 'study_guides', ['course_id', 'status'])


def downgrade() -> None:
    op.drop_index('idx_study_guides_course_status', table_name='study_guides')
    op.drop_table('study_guides')

    with op.batch_alter_table('ai_generation_jobs') as batch_op:
        batch_op.drop_constraint('ck_ai_job_type', type_='check')
        batch_op.create_check_constraint(
            'ck_ai_job_type',
            "job_type IN ('lesson_generator', 'socratic_tutor')",
        )

    with op.batch_alter_table('media_assets') as batch_op:
        batch_op.drop_column('dynamic_spec_json')
        batch_op.drop_column('svg_markup')

    with op.batch_alter_table('lessons') as batch_op:
        batch_op.drop_constraint('ck_lesson_passing_score', type_='check')
        batch_op.drop_constraint('ck_lesson_type', type_='check')
        batch_op.drop_column('passing_score_pct')
        batch_op.drop_column('lesson_type')

    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('ck_users_account_type', type_='check')
        batch_op.drop_column('account_type')
