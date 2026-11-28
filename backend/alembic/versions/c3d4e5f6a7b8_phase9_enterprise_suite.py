"""phase9_enterprise_suite

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-27 20:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def _json_type() -> sa.types.TypeEngine:
    return sa.JSON().with_variant(postgresql.JSONB(), 'postgresql')


def upgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('family_access_code', sa.String(length=24), nullable=True))
        batch_op.create_unique_constraint('uq_users_family_access_code', ['family_access_code'])

    with op.batch_alter_table('lessons') as batch_op:
        batch_op.add_column(
            sa.Column('randomize_order', sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column('sample_size', sa.SmallInteger(), nullable=True))
        batch_op.create_check_constraint(
            'ck_lesson_sample_size',
            'sample_size IS NULL OR (sample_size >= 1 AND sample_size <= 50)',
        )

    with op.batch_alter_table('challenges') as batch_op:
        batch_op.drop_constraint('ck_challenge_type', type_='check')
        batch_op.create_check_constraint(
            'ck_challenge_type',
            "challenge_type IN ('visual_concept_card', 'matching', 'sequence_ordering', 'interactive_zones', 'decision_simulation', 'fill_in_blanks', 'open_response')",
        )

    with op.batch_alter_table('media_assets') as batch_op:
        batch_op.drop_constraint('ck_media_format', type_='check')
        batch_op.create_check_constraint(
            'ck_media_format',
            "media_format IN ('webp_anim', 'mp4_silent', 'webp', 'png', 'jpg', 'svg', 'pdf', 'audio_clip')",
        )

    op.create_table(
        'question_bank_items',
        sa.Column('organization_id', sa.Uuid(), nullable=True),
        sa.Column('competency_id', sa.Uuid(), nullable=True),
        sa.Column('topic_tag', sa.String(length=80), nullable=False, server_default='general'),
        sa.Column('challenge_type', sa.String(length=40), nullable=False),
        sa.Column('schema_version', sa.SmallInteger(), nullable=False, server_default='1'),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('payload_json', _json_type(), nullable=False),
        sa.Column('answer_key_json', _json_type(), nullable=False),
        sa.Column('pedagogical_explanation', sa.Text(), nullable=False),
        sa.Column('difficulty', sa.SmallInteger(), nullable=False, server_default='2'),
        sa.Column('points', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('estimated_seconds', sa.SmallInteger(), nullable=False, server_default='45'),
        sa.Column('is_safety_critical', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_by', sa.Uuid(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "challenge_type IN ('visual_concept_card', 'matching', 'sequence_ordering', 'interactive_zones', 'decision_simulation', 'fill_in_blanks', 'open_response')",
            name='ck_qbank_type',
        ),
        sa.CheckConstraint('difficulty BETWEEN 1 AND 5', name='ck_qbank_difficulty'),
        sa.CheckConstraint('points > 0', name='ck_qbank_points'),
        sa.ForeignKeyConstraint(['competency_id'], ['competencies.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'open_submissions',
        sa.Column('organization_id', sa.Uuid(), nullable=True),
        sa.Column('challenge_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=False),
        sa.Column('attachment_note', sa.Text(), nullable=True),
        sa.Column('max_points', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('ai_suggested_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ai_feedback', sa.Text(), nullable=True),
        sa.Column('final_score', sa.Integer(), nullable=True),
        sa.Column('teacher_feedback', sa.Text(), nullable=True),
        sa.Column('graded_by', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending_review'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('graded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.CheckConstraint("status IN ('pending_review', 'graded')", name='ck_open_sub_status'),
        sa.ForeignKeyConstraint(['challenge_id'], ['challenges.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['graded_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'async_task_records',
        sa.Column('organization_id', sa.Uuid(), nullable=True),
        sa.Column('requested_by', sa.Uuid(), nullable=False),
        sa.Column('task_type', sa.String(length=40), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='queued'),
        sa.Column('result_json', _json_type(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')", name='ck_async_task_status'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'student_notes',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('course_id', sa.Uuid(), nullable=True),
        sa.Column('lesson_id', sa.Uuid(), nullable=True),
        sa.Column('study_guide_id', sa.Uuid(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('highlight_quote', sa.Text(), nullable=True),
        sa.Column('is_flashcard', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['study_guide_id'], ['study_guides.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'organization_subscriptions',
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('owner_user_id', sa.Uuid(), nullable=False),
        sa.Column('plan_code', sa.String(length=30), nullable=False, server_default='free'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('max_students', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('monthly_ai_limit', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('external_customer_id', sa.String(length=120), nullable=True),
        sa.Column('external_subscription_id', sa.String(length=120), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("plan_code IN ('free', 'educator_pro', 'institution')", name='ck_sub_plan_code'),
        sa.CheckConstraint("status IN ('active', 'trialing', 'past_due', 'canceled')", name='ck_sub_status'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id'),
    )


def downgrade() -> None:
    op.drop_table('organization_subscriptions')
    op.drop_table('student_notes')
    op.drop_table('async_task_records')
    op.drop_table('open_submissions')
    op.drop_table('question_bank_items')

    with op.batch_alter_table('media_assets') as batch_op:
        batch_op.drop_constraint('ck_media_format', type_='check')
        batch_op.create_check_constraint(
            'ck_media_format',
            "media_format IN ('webp_anim', 'mp4_silent', 'webp', 'png', 'jpg', 'svg', 'pdf')",
        )

    with op.batch_alter_table('challenges') as batch_op:
        batch_op.drop_constraint('ck_challenge_type', type_='check')
        batch_op.create_check_constraint(
            'ck_challenge_type',
            "challenge_type IN ('visual_concept_card', 'matching', 'sequence_ordering', 'interactive_zones', 'decision_simulation', 'fill_in_blanks')",
        )

    with op.batch_alter_table('lessons') as batch_op:
        batch_op.drop_constraint('ck_lesson_sample_size', type_='check')
        batch_op.drop_column('sample_size')
        batch_op.drop_column('randomize_order')

    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('uq_users_family_access_code', type_='unique')
        batch_op.drop_column('family_access_code')
