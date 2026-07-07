// Typed endpoint helpers grouped by role. Thin wrappers over `api`.

import { api } from "./client";
import type {
  AtRiskStudentOut,
  AuditRow,
  ChildRow,
  ClassMasteryOut,
  ClassProgressStudent,
  ClassSection,
  DocumentRow,
  EnrollmentJoinRow,
  ExamRow,
  FlaggedAnswer,
  Me,
  Notification,
  NotificationListOut,
  Page,
  ParentLinkJoinRow,
  PlatformDashboard,
  QuizAttemptRow,
  QuizOut,
  QuizSubmitResponse,
  School,
  SchoolDashboardOut,
  StudentDashboard,
  Subject,
  TeacherAssignmentJoinRow,
  TeacherDashboardOut,
  TeacherTimetableRow,
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
  passwordReset: (email: string, newPassword: string) =>
    api.post<{ status: string }>("/api/v1/auth/password-reset", { email, new_password: newPassword }),
};

export const adminApi = {
  listSchools: () => api.get<School[]>("/api/v1/admin/schools"),
  dashboard: (days = 14) => api.get<PlatformDashboard>(`/api/v1/admin/dashboard?days=${days}`),
  schoolDashboard: (schoolId: string) =>
    api.get<SchoolDashboardOut>(`/api/v1/admin/schools/${schoolId}/dashboard`),
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

export interface SchoolDashboard {
  teachers: number;
  students: number;
  classes: number;
  avg_mastery: number;
}

export const schoolApi = {
  dashboard: () => api.get<SchoolDashboard>("/api/v1/school/dashboard"),
  atRisk: (limit = 10) => api.get<AtRiskStudentOut[]>(`/api/v1/school/dashboard/at-risk?limit=${limit}`),
  masteryByClass: () => api.get<ClassMasteryOut[]>("/api/v1/school/dashboard/mastery-by-class"),
  llmUsage: (days = 7) => api.get<LlmUsageSummary>(`/api/v1/school/llm-usage?days=${days}`),
  listUsers: (role?: Role, limit = 50, offset = 0) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (role) params.set("role", role);
    return api.get<Page<UserRow>>(`/api/v1/school/users?${params.toString()}`);
  },
  createUser: (body: {
    name: string;
    email: string;
    role: Role;
    grade?: number;
    interests?: string;
  }) => api.post<{ user: UserRow; temp_password: string | null }>("/api/v1/school/users", body),
  listClasses: () => api.get<ClassSection[]>("/api/v1/school/classes"),
  createClass: (body: { name: string; grade_level: number }) =>
    api.post<ClassSection>("/api/v1/school/classes", body),
  listSubjects: () => api.get<Subject[]>("/api/v1/school/subjects"),
  createSubject: (body: { name: string }) => api.post<Subject>("/api/v1/school/subjects", body),
  assignTeacher: (body: { teacher_id: string; class_id: string; subject_id: string }) =>
    api.post<{ id: string }>("/api/v1/school/teacher-assignments", body),
  listTeacherAssignments: (limit = 50, offset = 0) =>
    api.get<Page<TeacherAssignmentJoinRow>>(`/api/v1/school/teacher-assignments?limit=${limit}&offset=${offset}`),
  unassignTeacher: (id: string) =>
    api.del<{ status: string }>(`/api/v1/school/teacher-assignments/${id}`),
  enroll: (body: { student_id: string; class_id: string }) =>
    api.post<{ id: string }>("/api/v1/school/enrollments", body),
  listEnrollments: (limit = 50, offset = 0) =>
    api.get<Page<EnrollmentJoinRow>>(`/api/v1/school/enrollments?limit=${limit}&offset=${offset}`),
  unenrollStudent: (id: string) => api.del<{ status: string }>(`/api/v1/school/enrollments/${id}`),
  linkParent: (body: { parent_id: string; student_id: string }) =>
    api.post<{ id: string }>("/api/v1/school/parent-links", body),
  listParentLinks: (limit = 50, offset = 0) =>
    api.get<Page<ParentLinkJoinRow>>(`/api/v1/school/parent-links?limit=${limit}&offset=${offset}`),
  unlinkParent: (id: string) => api.del<{ status: string }>(`/api/v1/school/parent-links/${id}`),
  updateUser: (id: string, body: Partial<{ name: string; is_active: boolean; grade: number; interests: string }>) =>
    api.patch<UserRow>(`/api/v1/school/users/${id}`, body),
  resetUserPassword: (id: string) =>
    api.post<{ temp_password: string }>(`/api/v1/school/users/${id}/reset-password`, {}),
  bulkImportUsers: (form: FormData) =>
    api.postForm<{ created: { id: string; email: string; temp_password: string }[]; count: number }>(
      "/api/v1/school/users/bulk",
      form,
    ),
  audit: (action?: string, limit = 50, offset = 0) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (action) params.set("action", action);
    return api.get<Page<AuditRow>>(`/api/v1/school/audit?${params.toString()}`);
  },
};

export interface TeacherAssignmentRow {
  class_id: string;
  class_name: string;
  subject_id: string;
  subject_name: string;
}

export const teacherApi = {
  dashboard: () => api.get<TeacherDashboardOut>("/api/v1/teacher/dashboard"),
  classProgress: (classId: string) =>
    api.get<ClassProgressStudent[]>(`/api/v1/teacher/classes/${classId}/progress`),
  assignments: () => api.get<TeacherAssignmentRow[]>("/api/v1/teacher/assignments"),
  materials: (limit = 50, offset = 0) =>
    api.get<Page<DocumentRow>>(`/api/v1/teacher/materials?limit=${limit}&offset=${offset}`),
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
  listTimetable: () => api.get<TeacherTimetableRow[]>("/api/v1/teacher/timetable"),
  deleteTimetableEntry: (id: string) => api.del<{ status: string }>(`/api/v1/teacher/timetable/${id}`),
  flagged: (limit = 50, offset = 0) =>
    api.get<Page<FlaggedAnswer>>(`/api/v1/teacher/flagged-answers?limit=${limit}&offset=${offset}`),
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
  history: (limit = 50, offset = 0) =>
    api.get<Page<QuizAttemptRow>>(`/api/v1/student/history?limit=${limit}&offset=${offset}`),
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
  childHistory: (id: string, limit = 50, offset = 0) =>
    api.get<Page<QuizAttemptRow>>(`/api/v1/parent/children/${id}/history?limit=${limit}&offset=${offset}`),
  childExamTimetable: (id: string) =>
    api.get<ExamRow[]>(`/api/v1/parent/children/${id}/exam-timetable`),
};

export const notificationsApi = {
  list: (unreadOnly = false) =>
    api.get<NotificationListOut>(`/api/v1/notifications${unreadOnly ? "?unread_only=true" : ""}`),
  markRead: (id: string) => api.post<Notification>(`/api/v1/notifications/${id}/read`, {}),
  markAllRead: () => api.post<{ status: string; count: number }>("/api/v1/notifications/read-all", {}),
};
