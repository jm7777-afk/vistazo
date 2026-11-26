export type UIProfile = 'kids' | 'youth' | 'pro';

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
  is_minor: boolean;
  preferred_ui_profile: UIProfile;
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
  is_safety_critical: boolean;
  active_lesson_version_id: string | null;
  active_version_number: number | null;
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

export interface ClassroomOut {
  id: string;
  organization_id: string;
  curriculum_version_id: string;
  code: string;
  name: string;
  energy_enabled: boolean;
  max_energy: number;
  status: string;
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
