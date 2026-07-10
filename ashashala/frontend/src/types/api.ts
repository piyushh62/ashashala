// Shared API types (mirror the FastAPI Pydantic schemas).

export type Role = "super_admin" | "school_admin" | "teacher" | "student" | "parent";

/** Generic pagination envelope — mirrors the backend's `app.schemas.pagination.Page[T]`. */
export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Me {
  id: string;
  name: string;
  email: string;
  role: Role;
  school_id: string | null;
  grade: number | null;
  interests: string | null;
  permissions: string[];
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface School {
  id: string;
  name: string;
  address: string | null;
  is_active: boolean;
  features_json: Record<string, boolean>;
  timezone: string;
}

export interface TokenTrendDay {
  day: string;
  tokens: number;
  calls: number;
}

export interface PlatformDashboard {
  active_schools: number;
  total_users: number;
  tokens_today_by_school: Record<string, number>;
  error_rate: number;
  tokens_by_day: TokenTrendDay[];
}

export interface SchoolDashboardOut {
  school_id: string;
  teachers: number;
  students: number;
  classes: number;
  avg_mastery: number;
}

export interface AtRiskStudentOut {
  student_id: string;
  student_name: string;
  avg_mastery: number;
}

export interface ClassMasteryOut {
  class_id: string;
  class_name: string;
  avg_mastery: number;
  student_count: number;
}

export interface UserRow {
  id: string;
  name: string;
  email: string;
  role: Role;
  school_id: string | null;
  is_active: boolean;
  grade: number | null;
}

export interface ClassSection {
  id: string;
  name: string;
  grade_level: number;
}

export interface Subject {
  id: string;
  name: string;
}

export interface DocumentRow {
  id: string;
  filename: string;
  source_type: "pdf" | "docx" | "txt" | "url" | "youtube" | "image";
  source_ref: string | null;
  storage_url: string | null;
  status: "pending" | "indexed" | "failed";
  class_id: string;
  subject_id: string | null;
}

export interface TimetableRow {
  day_of_week: number;
  period_number: number;
  class_id: string;
  subject_id: string;
  room?: string | null;
}

export interface ExamRow {
  exam_name: string;
  exam_date: string;
  class_id: string;
  subject_id: string;
}

export interface MasteryItem {
  topic: string;
  score: number;
}

export interface StudentDashboard {
  name: string;
  grade: number | null;
  mastery: MasteryItem[];
  recommended_topic: string | null;
}

export interface Citation {
  source_type: string;
  filename: string | null;
  title: string | null;
  page: number | null;
  timestamp: string | null;
  url: string | null;
}

export interface QuizQuestion {
  index: number;
  type: "mcq" | "short";
  question: string;
  difficulty?: string | null;
  xp?: number | null;
  options?: string[] | null;
}

export interface QuizOut {
  id: string;
  topic: string;
  status: string;
  class_id: string;
  subject_id: string | null;
  questions: QuizQuestion[];
}

export interface PerQuestionFeedback {
  index: number;
  type: string;
  score: number;
  xp_awarded: number;
  feedback: string;
  flagged: boolean;
}

export interface QuizSubmitResponse {
  quiz_id: string;
  attempt_id: string;
  attempt_score: number;
  total_xp: number;
  feedback_summary: string;
  per_question: PerQuestionFeedback[];
  mastery_update: { topic: string; old: number; new: number } | null;
}

export interface FlaggedAnswer {
  id: string;
  quiz_attempt_id: string;
  quiz_id: string;
  student_id: string;
  question_text: string;
  student_answer: string;
  expected_answer: string | null;
  ai_score: number | null;
  ai_confidence: number | null;
  flag_reason: string;
  status: string;
  created_at: string;
}

export interface AuditRow {
  id: string;
  ts: string;
  action: string;
  actor_user_id: string | null;
  actor_role: string | null;
  target_type: string | null;
  target_id: string | null;
  status: string;
}

export interface ChildRow {
  id: string;
  name: string;
  grade: number | null;
}

export interface TeacherAssignmentJoinRow {
  id: string;
  teacher_id: string;
  teacher_name: string;
  class_id: string;
  class_name: string;
  subject_id: string;
  subject_name: string;
}

export interface EnrollmentJoinRow {
  id: string;
  student_id: string;
  student_name: string;
  class_id: string;
  class_name: string;
}

export interface ParentLinkJoinRow {
  id: string;
  parent_id: string;
  parent_name: string;
  student_id: string;
  student_name: string;
}

export interface TeacherTimetableRow {
  id: string;
  day_of_week: number;
  period_number: number;
  class_id: string;
  subject_id: string;
  room?: string | null;
}

export interface QuizAttemptRow {
  quiz_id: string;
  score: number;
  attempted_at: string;
}

export interface ClassProgressStudent {
  student_id: string;
  name: string;
  grade: number | null;
  avg_mastery: number;
  topics: { topic: string; score: number }[];
}

export interface TeacherDashboardOut {
  classes: string[];
  subjects: string[];
  materials_uploaded: number;
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string | null;
  link: string | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListOut {
  items: Notification[];
  unread_count: number;
}

export interface PermissionOut {
  id: string;
  resource: string;
  action: string;
}

export interface RoleTemplateOut {
  id: string;
  name: string;
  is_system: boolean;
  description: string | null;
  permissions: string[];
}

export interface RoleOut {
  id: string;
  name: string;
  is_custom: boolean;
  template_id: string | null;
  permissions: string[];
}

export interface CreationRightsOut {
  role_id: string;
  creatable_template_names: string[];
}

export interface AgentActionOut {
  id: string;
  agent_name: string;
  action_type: string;
  payload_json: Record<string, unknown>;
  confidence: number | null;
  status: "pending" | "approved" | "rejected" | "auto_applied";
  reviewed_by_user_id: string | null;
  reviewed_at: string | null;
  created_at: string;
}
