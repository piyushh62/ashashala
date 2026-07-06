// Typed endpoint helpers grouped by role. Thin wrappers over `api`.

import { api } from "./client";
import type {
  AuditRow,
  ChildRow,
  ClassSection,
  DocumentRow,
  ExamRow,
  FlaggedAnswer,
  Me,
  PlatformDashboard,
  QuizOut,
  QuizSubmitResponse,
  School,
  StudentDashboard,
  Subject,
  TimetableRow,
  TokenResponse,
  UserRow,
  Role,
  MasteryItem,
} from "../types/api";

export const authApi = {
  login: (email: string, password: string) =>
    api.post<TokenResponse>("/api/v1/auth/login", { email, password }),
  me: () => api.get<Me>("/api/v1/auth/me"),
};

export const adminApi = {
  dashboard: () => api.get<PlatformDashboard>("/api/v1/admin/dashboard"),
  createSchool: (body: { name: string; address?: string }) =>
    api.post<School>("/api/v1/admin/schools", body),
  updateSchool: (id: string, body: Partial<{ is_active: boolean; name: string }>) =>
    api.patch<School>(`/api/v1/admin/schools/${id}`, body),
  deleteSchool: (id: string) => api.del<{ status: string }>(`/api/v1/admin/schools/${id}`),
  createSchoolAdmin: (schoolId: string, body: { name: string; email: string }) =>
    api.post<{ user_id: string; email: string; temp_password: string }>(
      `/api/v1/admin/schools/${schoolId}/admins`,
      body,
    ),
};

export interface LlmUsageSummary {
  days: number;
  by_day: { day: string; provider: string; tokens: number; calls: number }[];
  today_tokens: number;
  today_calls: number;
  today_error_rate: number;
  daily_token_limit: number;
  over_quota: boolean;
}

export const schoolApi = {
  dashboard: () => api.get<Record<string, number>>("/api/v1/school/dashboard"),
  llmUsage: (days = 7) => api.get<LlmUsageSummary>(`/api/v1/school/llm-usage?days=${days}`),
  listUsers: (role?: Role) =>
    api.get<UserRow[]>(`/api/v1/school/users${role ? `?role=${role}` : ""}`),
  createUser: (body: {
    name: string;
    email: string;
    role: Role;
    grade?: number;
    interests?: string;
  }) => api.post<{ user: UserRow; temp_password: string | null }>("/api/v1/school/users", body),
  createClass: (body: { name: string; grade_level: number }) =>
    api.post<ClassSection>("/api/v1/school/classes", body),
  createSubject: (body: { name: string }) => api.post<Subject>("/api/v1/school/subjects", body),
  assignTeacher: (body: { teacher_id: string; class_id: string; subject_id: string }) =>
    api.post<{ id: string }>("/api/v1/school/teacher-assignments", body),
  enroll: (body: { student_id: string; class_id: string }) =>
    api.post<{ id: string }>("/api/v1/school/enrollments", body),
  linkParent: (body: { parent_id: string; student_id: string }) =>
    api.post<{ id: string }>("/api/v1/school/parent-links", body),
  audit: (action?: string) =>
    api.get<AuditRow[]>(`/api/v1/school/audit${action ? `?action=${action}` : ""}`),
};

export const teacherApi = {
  dashboard: () => api.get<Record<string, unknown>>("/api/v1/teacher/dashboard"),
  materials: () => api.get<DocumentRow[]>("/api/v1/teacher/materials"),
  uploadFile: (form: FormData) => api.postForm<DocumentRow>("/api/v1/teacher/materials/file", form),
  uploadUrl: (body: { class_id: string; subject_id?: string; url: string }) =>
    api.post<DocumentRow>("/api/v1/teacher/materials/url", body),
  uploadYoutube: (body: { class_id: string; subject_id?: string; url: string }) =>
    api.post<DocumentRow>("/api/v1/teacher/materials/youtube", body),
  createTimetable: (body: {
    class_id: string;
    subject_id: string;
    day_of_week: number;
    period_number: number;
    room?: string;
  }) => api.post<TimetableRow>("/api/v1/teacher/timetable", body),
  flagged: () => api.get<FlaggedAnswer[]>("/api/v1/teacher/flagged-answers"),
  override: (id: string, body: { score: number; feedback?: string }) =>
    api.post<{ status: string }>(`/api/v1/teacher/flagged-answers/${id}/override`, body),
  approveQuiz: (id: string, approved: boolean) =>
    api.post<{ status: string }>(`/api/v1/teacher/quizzes/${id}/approve`, { approved }),
};

export const studentApi = {
  dashboard: () => api.get<StudentDashboard>("/api/v1/student/dashboard"),
  progress: () => api.get<MasteryItem[]>("/api/v1/student/progress"),
  classes: () => api.get<{ class_ids: string[] }>("/api/v1/student/classes"),
  timetable: () => api.get<TimetableRow[]>("/api/v1/student/timetable"),
  exams: () => api.get<ExamRow[]>("/api/v1/student/exam-timetable"),
  history: () => api.get<{ quiz_attempts: { quiz_id: string; score: number }[] }>(
    "/api/v1/student/history",
  ),
  startQuiz: (body: { class_id: string; subject_id?: string }) =>
    api.post<QuizOut>("/api/v1/student/quiz/start", body),
  submitQuiz: (id: string, answers: unknown[]) =>
    api.post<QuizSubmitResponse>(`/api/v1/student/quiz/${id}/submit`, { answers }),
  ttsUrl: (text: string, language: string) =>
    `${import.meta.env.VITE_API_URL || ""}/api/v1/student/voice/tts?text=${encodeURIComponent(
      text,
    )}&language=${language}`,
};

export const parentApi = {
  children: () => api.get<ChildRow[]>("/api/v1/parent/children"),
  childDashboard: (id: string) =>
    api.get<{ student: ChildRow; mastery: MasteryItem[] }>(
      `/api/v1/parent/children/${id}/dashboard`,
    ),
  childTimetable: (id: string) =>
    api.get<TimetableRow[]>(`/api/v1/parent/children/${id}/timetable`),
  childHistory: (id: string) =>
    api.get<{ quiz_attempts: { quiz_id: string; score: number }[] }>(
      `/api/v1/parent/children/${id}/history`,
    ),
};
