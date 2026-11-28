export type UIProfile = 'kids' | 'youth' | 'pro';
export type AccountType = 'student' | 'educator';
export type LessonType = 'micro_lesson' | 'strong_exam' | 'study_guide_drill';
export type GuideType = 'pensum' | 'temario' | 'guia_estudio' | 'metodologia' | 'rubrica';
export type PedagogyStyle = 'active_recall' | 'problem_based' | 'flipped_mastery' | 'spaced_microlearning';
export type DiagramKind = 'auto' | 'cycle' | 'flowchart' | 'hierarchy' | 'comparison' | 'layers';

export interface MembershipSummary {
  organization_id: string;
  organization_name: string;
  organization_slug: string;
  sector_type: string;
  default_ui_profile: UIProfile;
  role_code: string;
  role_name: string;
}

export interface UserSummary {
  id: string;
  email: string;
  full_name: string;
  account_type?: AccountType;
  is_minor: boolean;
  preferred_ui_profile: UIProfile;
  daily_goal_minutes?: number;
  onboarding_completed?: boolean;
  email_verified?: boolean;
  is_super_admin: boolean;
  created_at: string;
  memberships: MembershipSummary[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in_seconds: number;
  csrf_token: string;
  user: UserSummary;
}

export interface CourseSummary {
  id: string;
  organization_id: string | null;
  title: string;
  slug: string;
  description: string | null;
  education_level: string;
  ui_profile: UIProfile;
  visibility: string;
  status: string;
}

export interface LessonOut {
  id: string;
  title: string;
  slug: string;
  order_index: number;
  estimated_minutes: number;
  lesson_type?: LessonType;
  passing_score_pct?: number;
  is_safety_critical: boolean;
  active_lesson_version_id: string | null;
  active_version_number: number | null;
}

export interface StudyGuideOut {
  id: string;
  organization_id: string | null;
  course_id: string | null;
  lesson_id: string | null;
  guide_type: GuideType;
  title: string;
  content_markdown: string;
  methodology_json: Record<string, unknown>;
  status: 'draft' | 'published' | 'archived';
  ai_generated: boolean;
  created_at: string;
  updated_at: string;
}

export interface MediaAssetOut {
  id: string;
  organization_id: string | null;
  title: string;
  description: string | null;
  tags: string[];
  education_level: string;
  visibility: string;
  media_format: string;
  mime_type: string;
  byte_size: number;
  processing_status: string;
  signed_url: string | null;
  dynamic_spec_json?: Record<string, unknown> | null;
  has_svg_markup?: boolean;
}

export interface GenerateBlueprintResponse {
  job_id: string;
  provider: string;
  model_name: string;
  status: string;
  used_fallback: boolean;
  blueprint: {
    course_title: string;
    course_description: string;
    methodology: Record<string, unknown>;
    study_guide_markdown: string;
    modules: {
      title: string;
      description: string;
      lessons: {
        title: string;
        lesson_type: LessonType;
        estimated_minutes: number;
        passing_score_pct: number;
        is_safety_critical: boolean;
        key_concepts: string[];
      }[];
    }[];
  };
  created_course_id: string | null;
  created_guide_id: string | null;
}

export interface GenerateStudyGuideResponse {
  job_id: string;
  provider: string;
  model_name: string;
  status: string;
  used_fallback: boolean;
  title: string;
  content_markdown: string;
  methodology_json: Record<string, unknown>;
  saved_guide_id: string | null;
}

export interface GenerateDynamicVisualResponse {
  job_id: string;
  provider: string;
  model_name: string;
  status: string;
  used_fallback: boolean;
  media_asset_id: string;
  signed_url: string;
  title: string;
  template: string;
  zones: Record<string, unknown>[];
  created_challenge_id: string | null;
}

export interface ProgramOut {
  id: string;
  organization_id: string;
  code: string;
  title: string;
  description: string | null;
  education_level: string;
  is_active: boolean;
}

export interface CurriculumUnitOut {
  id: string;
  course_id: string;
  primary_competency_id: string | null;
  unit_code: string;
  title: string;
  order_index: number;
  is_mandatory: boolean;
  weight: string;
}

export interface CurriculumVersionOut {
  id: string;
  program_id: string;
  version_number: number;
  title: string;
  passing_score: string;
  status: 'draft' | 'published' | 'archived';
  published_at: string | null;
  units: CurriculumUnitOut[];
}

export interface CompetencyOut {
  id: string;
  organization_id: string | null;
  code: string;
  title: string;
  description: string | null;
  education_level: string;
}

export interface ModuleOut {
  id: string;
  title: string;
  description: string | null;
  order_index: number;
  lessons: LessonOut[];
}

export interface CourseDetail extends CourseSummary {
  modules: ModuleOut[];
}

export type ChallengeType =
  | 'visual_concept_card'
  | 'matching'
  | 'sequence_ordering'
  | 'interactive_zones'
  | 'decision_simulation'
  | 'fill_in_blanks';

export interface ChallengePublic {
  id: string;
  lesson_version_id: string;
  competency_id: string | null;
  challenge_type: ChallengeType;
  schema_version: number;
  order_index: number;
  prompt: string;
  payload_json: Record<string, unknown>;
  difficulty: number;
  points: number;
  estimated_seconds: number;
  is_safety_critical: boolean;
  status: string;
}

export interface AttemptResult {
  attempt_id: string;
  challenge_id: string;
  is_correct: boolean;
  score_awarded: number;
  max_points: number;
  pedagogical_explanation: string;
  detail: Record<string, unknown>;
  lesson_status: string;
  lesson_score_pct: string;
  completed_challenges: number;
  total_challenges: number;
  xp_awarded?: number;
  next_review_at?: string | null;
  unlocked_library_items?: number;
}

export interface DueReviewItem {
  sr_item_id: string;
  challenge_id: string;
  challenge_type: ChallengeType;
  prompt: string;
  payload_json: Record<string, unknown>;
  points: number;
  estimated_seconds: number;
  is_safety_critical: boolean;
  item_state: string;
  interval_days: number;
  lapses: number;
  next_review_at: string;
}

export interface ReviewSessionOut {
  session_id: string;
  session_mode: 'spaced_repetition' | 'flash_training' | 'energy_recovery';
  items_planned: number;
  items_completed: number;
  energy_recovered: number;
  items: DueReviewItem[];
}

export interface LibraryItem {
  library_item_id: string;
  asset_id: string;
  title: string;
  description: string | null;
  tags: string[];
  media_format: string;
  is_favorite: boolean;
  flash_reviews_count: number;
  signed_url: string;
  unlocked_at: string;
}

export interface BadgeOut {
  code: string;
  name: string;
  description: string;
  awarded_at: string;
}

export interface GamificationProfile {
  total_xp: number;
  current_streak_days: number;
  longest_streak_days: number;
  current_energy: number;
  max_energy: number;
  badges: BadgeOut[];
}

export interface LeaderboardEntry {
  rank: number;
  display_name: string;
  xp_in_classroom: number;
  is_me: boolean;
}

export interface HardChallengeStat {
  challenge_id: string;
  prompt: string;
  challenge_type: string;
  total_attempts: number;
  error_rate_pct: number;
}

export interface ClassroomAnalytics {
  classroom_id: string;
  classroom_name: string;
  enrolled_students: number;
  completed_lesson_records: number;
  avg_lesson_score_pct: number;
  total_challenge_attempts: number;
  overall_accuracy_pct: number;
  hardest_challenges: HardChallengeStat[];
}

export interface SocraticHintResponse {
  job_id: string;
  hint: string;
  provider: string;
  model_name: string;
  used_fallback: boolean;
  failed_attempts: number;
  safety_reminder: boolean;
}

export interface GenerateLessonDraftResponse {
  job_id: string;
  provider: string;
  model_name: string;
  status: string;
  used_fallback: boolean;
  lesson_summary: string;
  challenges_created: number;
  challenge_ids: string[];
}

export interface AIJobOut {
  id: string;
  job_type: string;
  provider: string;
  model_name: string;
  status: string;
  prompt_tokens: number;
  completion_tokens: number;
  latency_ms: number | null;
  created_at: string;
}

export interface AIProviderConfigOut {
  id: string;
  provider: 'gemini' | 'groq' | 'fallback';
  model_name: string;
  is_active: boolean;
  max_tokens: number;
  daily_org_job_limit: number;
  has_api_key_configured: boolean;
}

export interface CertificateOut {
  id: string;
  organization_id: string;
  user_id: string;
  curriculum_version_id: string;
  classroom_id: string | null;
  certificate_number: string;
  verification_hash: string;
  final_grade: string;
  status: 'pending' | 'issued' | 'revoked';
  issued_at: string | null;
  verification_url: string;
  has_pdf: boolean;
}

export interface PublicCertificateVerification {
  valid: boolean;
  status: string;
  certificate_number: string;
  organization_name: string;
  program_title: string;
  curriculum_title: string;
  recipient_initials: string;
  final_grade: string;
  issued_at: string | null;
  signer_name: string;
  signer_title: string;
  revoked_at: string | null;
  revocation_reason: string | null;
}

export interface CohortComparisonItem {
  classroom_id: string;
  classroom_code: string;
  classroom_name: string;
  enrolled_students: number;
  completed_lessons: number;
  avg_score_pct: number;
}

export interface OrgAnalyticsOverview {
  organization_id: string;
  total_classrooms: number;
  total_enrolled_students: number;
  issued_certificates: number;
  revoked_certificates: number;
  ai_jobs_count: number;
  cohorts: CohortComparisonItem[];
}

export interface LessonVersionOut {
  id: string;
  lesson_id: string;
  version_number: number;
  summary: string | null;
  status: 'draft' | 'published' | 'superseded';
  requires_revalidation: boolean;
  published_at: string | null;
}

export interface ChallengeAuthorOut extends ChallengePublic {
  answer_key_json: Record<string, unknown>;
  pedagogical_explanation: string;
}

export interface AuditLogOut {
  id: string;
  organization_id: string | null;
  actor_user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  outcome: 'success' | 'denied' | 'error';
  details_json: Record<string, unknown>;
  created_at: string;
}

export interface ClassroomOut {
  id: string;
  organization_id: string;
  curriculum_version_id: string;
  code: string;
  name: string;
  energy_enabled: boolean;
  max_energy: number;
  invite_code?: string | null;
  invite_enabled?: boolean;
  status: string;
}

export interface InvitePreviewOut {
  classroom_id: string;
  classroom_name: string;
  classroom_code: string;
  organization_id: string;
  organization_name: string;
  invite_code: string;
  invite_enabled: boolean;
}

export interface JoinClassroomResponse {
  status: string;
  organization_id: string;
  classroom_id: string;
  classroom_name: string;
}

export interface LessonPlayerContextOut {
  lesson_id: string;
  lesson_title: string;
  lesson_type: LessonType;
  estimated_minutes: number;
  passing_score_pct: number;
  is_safety_critical: boolean;
  course_id: string;
  course_title: string;
}

export interface DocumentExtractResponse {
  filename: string;
  char_count: number;
  extracted_text: string;
}

export interface AdaptiveRemediationResponse {
  job_id: string;
  provider: string;
  title: string;
  remediation_markdown: string;
  action_steps: string[];
}

export interface LiveParticipantOut {
  id: string;
  display_name: string;
  score: number;
  answered_count: number;
  correct_count: number;
}

export interface LiveSessionStateOut {
  id: string;
  room_code: string;
  title: string;
  status: 'waiting' | 'active' | 'finished';
  current_index: number;
  total_challenges: number;
  current_challenge: ChallengePublic | null;
  leaderboard: LiveParticipantOut[];
}

export interface NotificationsSummaryOut {
  due_reviews_count: number;
  current_streak_days: number;
  email_verified: boolean;
  reminders: {
    id: string;
    kind: string;
    title: string;
    body: string;
    action_url: string;
  }[];
}

export interface ClassroomStudentOut {
  user_id: string;
  email: string;
  full_name: string;
  enrollment_status: string;
  enrolled_at: string;
  completed_lessons: number;
  avg_score_pct: number;
}

export interface LessonProgressOut {
  id: string;
  lesson_version_id: string;
  classroom_id: string | null;
  organization_id: string | null;
  status: 'not_started' | 'in_progress' | 'completed';
  best_score_pct: string;
  completed_challenges: number;
  total_challenges: number;
  last_activity_at: string;
}

export interface StudentCompetencyOut {
  competency_id: string;
  organization_id: string | null;
  mastery_score: string;
  evaluated_attempts: number;
  mastery_status: string;
  last_evaluated_at: string;
}
