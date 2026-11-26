-- ============================================================================
-- PLATAFORMA LMS GAMIFICADA MULTIINSTITUCIONAL - ESQUEMA INICIAL POSTGRESQL
-- ============================================================================
BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(320) NOT NULL,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(160) NOT NULL,
    birth_date DATE NULL,
    is_minor BOOLEAN NOT NULL DEFAULT FALSE,
    preferred_ui_profile VARCHAR(20) NOT NULL DEFAULT 'pro'
        CHECK (preferred_ui_profile IN ('kids', 'youth', 'pro')),
    is_super_admin BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL,
    deleted_by UUID NULL REFERENCES users(id)
);

CREATE UNIQUE INDEX uq_users_email_active
    ON users (LOWER(email)) WHERE deleted_at IS NULL;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash CHAR(64) NOT NULL UNIQUE,
    family_id UUID NOT NULL,
    user_agent VARCHAR(512) NULL,
    ip_address INET NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_sessions_user_active
    ON user_sessions (user_id, expires_at) WHERE revoked_at IS NULL;

CREATE TABLE parental_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    minor_user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    guardian_name VARCHAR(160) NOT NULL,
    guardian_email VARCHAR(320) NOT NULL,
    consent_status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (consent_status IN ('pending', 'verified', 'revoked')),
    verification_token_hash CHAR(64) NULL,
    verified_at TIMESTAMPTZ NULL,
    revoked_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_parental_consents_updated_at
    BEFORE UPDATE ON parental_consents FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    sector_type VARCHAR(40) NOT NULL
        CHECK (sector_type IN ('primary_school', 'secondary_school', 'high_school', 'university', 'technical_academy', 'rescue_brigade', 'specialized_training')),
    default_ui_profile VARCHAR(20) NOT NULL DEFAULT 'pro'
        CHECK (default_ui_profile IN ('kids', 'youth', 'pro')),
    settings_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL,
    deleted_by UUID NULL REFERENCES users(id)
);

CREATE UNIQUE INDEX uq_organizations_slug_active
    ON organizations (LOWER(slug)) WHERE deleted_at IS NULL;

CREATE TRIGGER trg_organizations_updated_at
    BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
    code VARCHAR(60) NOT NULL,
    name VARCHAR(120) NOT NULL,
    description TEXT NULL,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX uq_roles_scope_code_active
    ON roles (COALESCE(organization_id, '00000000-0000-0000-0000-000000000000'::uuid), LOWER(code))
    WHERE deleted_at IS NULL;

CREATE TRIGGER trg_roles_updated_at
    BEFORE UPDATE ON roles FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(100) NOT NULL UNIQUE,
    resource VARCHAR(60) NOT NULL,
    action VARCHAR(40) NOT NULL,
    description TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('invited', 'active', 'suspended')),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL,
    deleted_by UUID NULL REFERENCES users(id)
);

CREATE UNIQUE INDEX uq_org_member_role_active
    ON organization_members (organization_id, user_id, role_id) WHERE deleted_at IS NULL;

CREATE INDEX idx_org_members_user_org
    ON organization_members (user_id, organization_id) WHERE deleted_at IS NULL;

CREATE TRIGGER trg_organization_members_updated_at
    BEFORE UPDATE ON organization_members FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE competencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
    code VARCHAR(60) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NULL,
    education_level VARCHAR(40) NOT NULL
        CHECK (education_level IN ('primary', 'secondary', 'high_school', 'university', 'technical', 'specialized', 'rescue')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX uq_competencies_scope_code_active
    ON competencies (COALESCE(organization_id, '00000000-0000-0000-0000-000000000000'::uuid), LOWER(code))
    WHERE deleted_at IS NULL;

CREATE TRIGGER trg_competencies_updated_at
    BEFORE UPDATE ON competencies FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE programs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    code VARCHAR(60) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NULL,
    education_level VARCHAR(40) NOT NULL
        CHECK (education_level IN ('primary', 'secondary', 'high_school', 'university', 'technical', 'specialized', 'rescue')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL,
    deleted_by UUID NULL REFERENCES users(id)
);

CREATE UNIQUE INDEX uq_programs_org_code_active
    ON programs (organization_id, LOWER(code)) WHERE deleted_at IS NULL;

CREATE TRIGGER trg_programs_updated_at
    BEFORE UPDATE ON programs FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE curriculum_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    program_id UUID NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL CHECK (version_number > 0),
    title VARCHAR(200) NOT NULL,
    passing_score NUMERIC(5,2) NOT NULL DEFAULT 70.00 CHECK (passing_score >= 0 AND passing_score <= 100),
    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'published', 'archived')),
    published_at TIMESTAMPTZ NULL,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (program_id, version_number)
);

CREATE INDEX idx_curriculum_versions_org_program
    ON curriculum_versions (organization_id, program_id, status);

CREATE TRIGGER trg_curriculum_versions_updated_at
    BEFORE UPDATE ON curriculum_versions FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE classrooms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    curriculum_version_id UUID NOT NULL REFERENCES curriculum_versions(id) ON DELETE RESTRICT,
    code VARCHAR(60) NOT NULL,
    name VARCHAR(180) NOT NULL,
    starts_at DATE NULL,
    ends_at DATE NULL,
    energy_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    max_energy SMALLINT NOT NULL DEFAULT 5 CHECK (max_energy > 0 AND max_energy <= 20),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('planned', 'active', 'closed', 'archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL,
    deleted_by UUID NULL REFERENCES users(id),
    CHECK (ends_at IS NULL OR starts_at IS NULL OR ends_at >= starts_at)
);

CREATE UNIQUE INDEX uq_classrooms_org_code_active
    ON classrooms (organization_id, LOWER(code)) WHERE deleted_at IS NULL;

CREATE INDEX idx_classrooms_org_status
    ON classrooms (organization_id, status) WHERE deleted_at IS NULL;

CREATE TRIGGER trg_classrooms_updated_at
    BEFORE UPDATE ON classrooms FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE classroom_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    classroom_id UUID NOT NULL REFERENCES classrooms(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    enrollment_status VARCHAR(20) NOT NULL DEFAULT 'enrolled'
        CHECK (enrollment_status IN ('enrolled', 'completed', 'withdrawn')),
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX uq_classroom_members_active
    ON classroom_members (classroom_id, user_id) WHERE deleted_at IS NULL;

CREATE INDEX idx_classroom_members_org_user
    ON classroom_members (organization_id, user_id) WHERE deleted_at IS NULL;

CREATE TRIGGER trg_classroom_members_updated_at
    BEFORE UPDATE ON classroom_members FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE instructor_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    classroom_id UUID NOT NULL REFERENCES classrooms(id) ON DELETE CASCADE,
    instructor_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_lead BOOLEAN NOT NULL DEFAULT FALSE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX uq_instructor_assignment_active
    ON instructor_assignments (classroom_id, instructor_user_id) WHERE deleted_at IS NULL;

CREATE INDEX idx_instructor_assignments_user
    ON instructor_assignments (organization_id, instructor_user_id) WHERE deleted_at IS NULL;

CREATE TABLE courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(120) NOT NULL,
    description TEXT NULL,
    education_level VARCHAR(40) NOT NULL
        CHECK (education_level IN ('primary', 'secondary', 'high_school', 'university', 'technical', 'specialized', 'rescue')),
    ui_profile VARCHAR(20) NOT NULL DEFAULT 'pro'
        CHECK (ui_profile IN ('kids', 'youth', 'pro')),
    visibility VARCHAR(20) NOT NULL DEFAULT 'institutional'
        CHECK (visibility IN ('public', 'institutional', 'private')),
    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'published', 'archived')),
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL,
    deleted_by UUID NULL REFERENCES users(id),
    CHECK (
        (visibility = 'public' AND organization_id IS NULL)
        OR (visibility IN ('institutional', 'private') AND organization_id IS NOT NULL)
    )
);

CREATE UNIQUE INDEX uq_courses_scope_slug_active
    ON courses (COALESCE(organization_id, '00000000-0000-0000-0000-000000000000'::uuid), LOWER(slug))
    WHERE deleted_at IS NULL;

CREATE INDEX idx_courses_public_catalog
    ON courses (visibility, status, education_level) WHERE deleted_at IS NULL;

CREATE TRIGGER trg_courses_updated_at
    BEFORE UPDATE ON courses FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE curriculum_units (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    curriculum_version_id UUID NOT NULL REFERENCES curriculum_versions(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE RESTRICT,
    primary_competency_id UUID NULL REFERENCES competencies(id) ON DELETE SET NULL,
    unit_code VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    order_index INTEGER NOT NULL CHECK (order_index >= 0),
    is_mandatory BOOLEAN NOT NULL DEFAULT TRUE,
    weight NUMERIC(5,2) NOT NULL DEFAULT 1.00 CHECK (weight > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (curriculum_version_id, order_index),
    UNIQUE (curriculum_version_id, unit_code)
);

CREATE TABLE modules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT NULL,
    order_index INTEGER NOT NULL CHECK (order_index >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX uq_modules_course_order_active
    ON modules (course_id, order_index) WHERE deleted_at IS NULL;

CREATE TRIGGER trg_modules_updated_at
    BEFORE UPDATE ON modules FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE lessons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_id UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(120) NOT NULL,
    order_index INTEGER NOT NULL CHECK (order_index >= 0),
    estimated_minutes SMALLINT NOT NULL DEFAULT 5 CHECK (estimated_minutes > 0 AND estimated_minutes <= 120),
    is_safety_critical BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX uq_lessons_module_order_active
    ON lessons (module_id, order_index) WHERE deleted_at IS NULL;

CREATE TRIGGER trg_lessons_updated_at
    BEFORE UPDATE ON lessons FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE lesson_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id UUID NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL CHECK (version_number > 0),
    summary TEXT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'published', 'superseded')),
    requires_revalidation BOOLEAN NOT NULL DEFAULT FALSE,
    published_by UUID NULL REFERENCES users(id),
    published_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (lesson_id, version_number)
);

CREATE INDEX idx_lesson_versions_lesson_status
    ON lesson_versions (lesson_id, status);

CREATE TRIGGER trg_lesson_versions_updated_at
    BEFORE UPDATE ON lesson_versions FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE media_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
    competency_id UUID NULL REFERENCES competencies(id) ON DELETE SET NULL,
    uploaded_by UUID NOT NULL REFERENCES users(id),
    title VARCHAR(200) NOT NULL,
    description TEXT NULL,
    tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    education_level VARCHAR(40) NOT NULL
        CHECK (education_level IN ('primary', 'secondary', 'high_school', 'university', 'technical', 'specialized', 'rescue')),
    visibility VARCHAR(20) NOT NULL DEFAULT 'private'
        CHECK (visibility IN ('public', 'institutional', 'private')),
    media_format VARCHAR(20) NOT NULL
        CHECK (media_format IN ('webp_anim', 'mp4_silent', 'webp', 'png', 'jpg', 'svg', 'pdf')),
    mime_type VARCHAR(100) NOT NULL,
    storage_key TEXT NOT NULL UNIQUE,
    thumbnail_key TEXT NULL,
    byte_size BIGINT NOT NULL CHECK (byte_size > 0),
    duration_seconds NUMERIC(6,2) NULL CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
    processing_status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (processing_status IN ('pending', 'processing', 'ready', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE INDEX idx_media_assets_org_status
    ON media_assets (organization_id, processing_status, visibility) WHERE deleted_at IS NULL;

CREATE TRIGGER trg_media_assets_updated_at
    BEFORE UPDATE ON media_assets FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_version_id UUID NOT NULL REFERENCES lesson_versions(id) ON DELETE CASCADE,
    competency_id UUID NULL REFERENCES competencies(id) ON DELETE SET NULL,
    challenge_type VARCHAR(40) NOT NULL
        CHECK (challenge_type IN ('visual_concept_card', 'matching', 'sequence_ordering', 'interactive_zones', 'decision_simulation', 'fill_in_blanks')),
    schema_version SMALLINT NOT NULL DEFAULT 1 CHECK (schema_version > 0),
    order_index INTEGER NOT NULL CHECK (order_index >= 0),
    prompt TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    answer_key_json JSONB NOT NULL,
    pedagogical_explanation TEXT NOT NULL,
    difficulty SMALLINT NOT NULL DEFAULT 2 CHECK (difficulty BETWEEN 1 AND 5),
    points INTEGER NOT NULL DEFAULT 10 CHECK (points > 0),
    estimated_seconds SMALLINT NOT NULL DEFAULT 45 CHECK (estimated_seconds > 0),
    is_safety_critical BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'published', 'archived')),
    ai_generated BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX uq_challenges_lesson_order_active
    ON challenges (lesson_version_id, order_index) WHERE deleted_at IS NULL;

CREATE INDEX idx_challenges_lesson_status
    ON challenges (lesson_version_id, status) WHERE deleted_at IS NULL;

CREATE TRIGGER trg_challenges_updated_at
    BEFORE UPDATE ON challenges FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE challenge_media_assets (
    challenge_id UUID NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    media_asset_id UUID NOT NULL REFERENCES media_assets(id) ON DELETE RESTRICT,
    role VARCHAR(30) NOT NULL DEFAULT 'primary'
        CHECK (role IN ('primary', 'option', 'diagram', 'explanation')),
    order_index SMALLINT NOT NULL DEFAULT 0,
    PRIMARY KEY (challenge_id, media_asset_id, role)
);

CREATE TABLE challenge_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_attempt_id UUID NULL UNIQUE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
    classroom_id UUID NULL REFERENCES classrooms(id) ON DELETE SET NULL,
    challenge_id UUID NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    submitted_answer_json JSONB NOT NULL,
    is_correct BOOLEAN NOT NULL,
    score_awarded INTEGER NOT NULL DEFAULT 0 CHECK (score_awarded >= 0),
    response_time_ms INTEGER NULL CHECK (response_time_ms IS NULL OR response_time_ms >= 0),
    hints_used SMALLINT NOT NULL DEFAULT 0 CHECK (hints_used >= 0),
    attempt_number INTEGER NOT NULL DEFAULT 1 CHECK (attempt_number > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_attempts_user_challenge_time
    ON challenge_attempts (user_id, challenge_id, created_at DESC);
CREATE INDEX idx_attempts_org_classroom_time
    ON challenge_attempts (organization_id, classroom_id, created_at DESC);

CREATE TABLE lesson_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
    classroom_id UUID NULL REFERENCES classrooms(id) ON DELETE SET NULL,
    lesson_version_id UUID NOT NULL REFERENCES lesson_versions(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress'
        CHECK (status IN ('not_started', 'in_progress', 'completed')),
    best_score_pct NUMERIC(5,2) NOT NULL DEFAULT 0.00 CHECK (best_score_pct >= 0 AND best_score_pct <= 100),
    completed_challenges INTEGER NOT NULL DEFAULT 0 CHECK (completed_challenges >= 0),
    total_challenges INTEGER NOT NULL DEFAULT 0 CHECK (total_challenges >= 0),
    completed_at TIMESTAMPTZ NULL,
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_lesson_progress_context
    ON lesson_progress (user_id, lesson_version_id, COALESCE(classroom_id, '00000000-0000-0000-0000-000000000000'::uuid));

CREATE INDEX idx_lesson_progress_student
    ON lesson_progress (user_id, status, last_activity_at DESC);
CREATE INDEX idx_lesson_progress_classroom
    ON lesson_progress (organization_id, classroom_id, status);

CREATE TRIGGER trg_lesson_progress_updated_at
    BEFORE UPDATE ON lesson_progress FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE student_competencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
    competency_id UUID NOT NULL REFERENCES competencies(id) ON DELETE CASCADE,
    mastery_score NUMERIC(5,2) NOT NULL DEFAULT 0.00 CHECK (mastery_score >= 0 AND mastery_score <= 100),
    evaluated_attempts INTEGER NOT NULL DEFAULT 0 CHECK (evaluated_attempts >= 0),
    mastery_status VARCHAR(20) NOT NULL DEFAULT 'in_progress'
        CHECK (mastery_status IN ('not_started', 'in_progress', 'achieved', 'needs_refresh')),
    last_evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_student_competency_scope
    ON student_competencies (user_id, competency_id, COALESCE(organization_id, '00000000-0000-0000-0000-000000000000'::uuid));

CREATE TRIGGER trg_student_competencies_updated_at
    BEFORE UPDATE ON student_competencies FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE spaced_repetition_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
    challenge_id UUID NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    ease_factor NUMERIC(4,2) NOT NULL DEFAULT 2.50 CHECK (ease_factor >= 1.30 AND ease_factor <= 3.50),
    interval_days INTEGER NOT NULL DEFAULT 1 CHECK (interval_days >= 0),
    repetitions INTEGER NOT NULL DEFAULT 0 CHECK (repetitions >= 0),
    lapses INTEGER NOT NULL DEFAULT 0 CHECK (lapses >= 0),
    last_quality SMALLINT NULL CHECK (last_quality IS NULL OR last_quality BETWEEN 0 AND 5),
    item_state VARCHAR(20) NOT NULL DEFAULT 'learning'
        CHECK (item_state IN ('learning', 'review', 'relearning', 'mastered')),
    last_reviewed_at TIMESTAMPTZ NULL,
    next_review_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, challenge_id)
);

CREATE INDEX idx_sr_items_pending_due
    ON spaced_repetition_items (user_id, next_review_at)
    WHERE item_state <> 'mastered';

CREATE TRIGGER trg_spaced_repetition_items_updated_at
    BEFORE UPDATE ON spaced_repetition_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE review_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
    session_mode VARCHAR(30) NOT NULL DEFAULT 'spaced_repetition'
        CHECK (session_mode IN ('spaced_repetition', 'flash_training', 'energy_recovery')),
    items_planned SMALLINT NOT NULL DEFAULT 0 CHECK (items_planned >= 0),
    items_completed SMALLINT NOT NULL DEFAULT 0 CHECK (items_completed >= 0),
    energy_recovered SMALLINT NOT NULL DEFAULT 0 CHECK (energy_recovered >= 0),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ NULL
);

CREATE TABLE review_session_items (
    review_session_id UUID NOT NULL REFERENCES review_sessions(id) ON DELETE CASCADE,
    spaced_repetition_item_id UUID NOT NULL REFERENCES spaced_repetition_items(id) ON DELETE CASCADE,
    challenge_attempt_id UUID NULL REFERENCES challenge_attempts(id) ON DELETE SET NULL,
    order_index SMALLINT NOT NULL CHECK (order_index >= 0),
    PRIMARY KEY (review_session_id, spaced_repetition_item_id)
);

CREATE TABLE student_library_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    media_asset_id UUID NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    unlocked_from_lesson_version_id UUID NULL REFERENCES lesson_versions(id) ON DELETE SET NULL,
    is_favorite BOOLEAN NOT NULL DEFAULT FALSE,
    flash_reviews_count INTEGER NOT NULL DEFAULT 0 CHECK (flash_reviews_count >= 0),
    unlocked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_reviewed_at TIMESTAMPTZ NULL,
    UNIQUE (user_id, media_asset_id)
);

CREATE TABLE student_gamification_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
    total_xp BIGINT NOT NULL DEFAULT 0 CHECK (total_xp >= 0),
    current_streak_days INTEGER NOT NULL DEFAULT 0 CHECK (current_streak_days >= 0),
    longest_streak_days INTEGER NOT NULL DEFAULT 0 CHECK (longest_streak_days >= 0),
    last_active_date DATE NULL,
    current_energy SMALLINT NOT NULL DEFAULT 5 CHECK (current_energy >= 0),
    max_energy SMALLINT NOT NULL DEFAULT 5 CHECK (max_energy > 0),
    last_energy_refill_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_gamification_profile_scope
    ON student_gamification_profiles (user_id, COALESCE(organization_id, '00000000-0000-0000-0000-000000000000'::uuid));

CREATE TRIGGER trg_gamification_profiles_updated_at
    BEFORE UPDATE ON student_gamification_profiles FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE xp_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
    classroom_id UUID NULL REFERENCES classrooms(id) ON DELETE SET NULL,
    source_type VARCHAR(40) NOT NULL
        CHECK (source_type IN ('challenge', 'lesson_bonus', 'review_session', 'streak_bonus', 'badge')),
    source_id UUID NULL,
    xp_amount INTEGER NOT NULL CHECK (xp_amount > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_xp_transactions_org_classroom
    ON xp_transactions (organization_id, classroom_id, user_id, created_at DESC);

CREATE TABLE badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
    code VARCHAR(80) NOT NULL,
    name VARCHAR(140) NOT NULL,
    description TEXT NOT NULL,
    icon_asset_id UUID NULL REFERENCES media_assets(id) ON DELETE SET NULL,
    criteria_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX uq_badges_scope_code_active
    ON badges (COALESCE(organization_id, '00000000-0000-0000-0000-000000000000'::uuid), LOWER(code))
    WHERE deleted_at IS NULL;

CREATE TABLE student_badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    badge_id UUID NOT NULL REFERENCES badges(id) ON DELETE CASCADE,
    organization_id UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
    awarded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, badge_id)
);

CREATE TABLE certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    curriculum_version_id UUID NOT NULL REFERENCES curriculum_versions(id) ON DELETE RESTRICT,
    classroom_id UUID NULL REFERENCES classrooms(id) ON DELETE SET NULL,
    certificate_number VARCHAR(50) NOT NULL UNIQUE,
    verification_hash CHAR(64) NOT NULL UNIQUE,
    final_grade NUMERIC(5,2) NOT NULL CHECK (final_grade >= 0 AND final_grade <= 100),
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'issued', 'revoked')),
    pdf_storage_key TEXT NULL,
    metadata_snapshot_json JSONB NOT NULL,
    issued_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_certificates_org_user
    ON certificates (organization_id, user_id, status);

CREATE TRIGGER trg_certificates_updated_at
    BEFORE UPDATE ON certificates FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE certificate_signatures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    certificate_id UUID NOT NULL REFERENCES certificates(id) ON DELETE CASCADE,
    signer_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    signer_name VARCHAR(160) NOT NULL,
    signer_title VARCHAR(160) NOT NULL,
    signature_hash CHAR(64) NOT NULL,
    signed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE certificate_revocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    certificate_id UUID NOT NULL UNIQUE REFERENCES certificates(id) ON DELETE RESTRICT,
    revoked_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    reason TEXT NOT NULL,
    revoked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ai_generation_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
    requested_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    job_type VARCHAR(30) NOT NULL
        CHECK (job_type IN ('lesson_generator', 'socratic_tutor')),
    provider VARCHAR(30) NOT NULL,
    model_name VARCHAR(80) NOT NULL,
    target_lesson_version_id UUID NULL REFERENCES lesson_versions(id) ON DELETE SET NULL,
    target_challenge_id UUID NULL REFERENCES challenges(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'completed', 'failed', 'fallback_used')),
    prompt_tokens INTEGER NOT NULL DEFAULT 0 CHECK (prompt_tokens >= 0),
    completion_tokens INTEGER NOT NULL DEFAULT 0 CHECK (completion_tokens >= 0),
    latency_ms INTEGER NULL CHECK (latency_ms IS NULL OR latency_ms >= 0),
    error_code VARCHAR(80) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ NULL
);

CREATE INDEX idx_ai_jobs_org_date
    ON ai_generation_jobs (organization_id, created_at DESC);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NULL REFERENCES organizations(id) ON DELETE SET NULL,
    actor_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(60) NOT NULL,
    resource_id UUID NULL,
    outcome VARCHAR(20) NOT NULL CHECK (outcome IN ('success', 'denied', 'error')),
    ip_address INET NULL,
    details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_org_time
    ON audit_logs (organization_id, created_at DESC);
CREATE INDEX idx_audit_logs_actor_time
    ON audit_logs (actor_user_id, created_at DESC);

COMMIT;
