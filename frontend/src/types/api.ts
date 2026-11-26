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
