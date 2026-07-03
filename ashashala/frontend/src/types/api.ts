// Shared API types (mirror the FastAPI Pydantic schemas).

export type Role = "super_admin" | "school_admin" | "teacher" | "student" | "parent";

export interface Me {
  id: string;
  name: string;
  email: string;
  role: Role;
  school_id: string | null;
  grade: number | null;
  interests: string | null;
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

export interface PlatformDashboard {
  active_schools: number;
  total_users: number;
  tokens_today_by_school: Record<string, number>;
  error_rate: number;
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
