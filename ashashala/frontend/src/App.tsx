import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./stores/auth";
import { AppLayout, type NavItem } from "./components/layout/AppLayout";
import type { SearchSource } from "./components/layout/CommandPalette";
import { HOME_FOR, RoleGuard } from "./components/layout/RoleGuard";
import type { Role, School, UserRow, DocumentRow } from "./types/api";
import { adminApi, schoolApi, teacherApi } from "./api/endpoints";
import { Spinner } from "./components/ui";

import Login from "./routes/Login";
import AdminSchools from "./routes/admin/AdminSchools";
import AdminDashboard from "./routes/admin/AdminDashboard";
import SchoolDashboard from "./routes/school/SchoolDashboard";
import SchoolUsers from "./routes/school/SchoolUsers";
import SchoolStructure from "./routes/school/SchoolStructure";
import SchoolAudit from "./routes/school/SchoolAudit";
import SchoolAgentActions from "./routes/school/SchoolAgentActions";
import TeacherDashboard from "./routes/teacher/TeacherDashboard";
import TeacherMaterials from "./routes/teacher/TeacherMaterials";
import TeacherTimetable from "./routes/teacher/TeacherTimetable";
import TeacherFlagged from "./routes/teacher/TeacherFlagged";
import TeacherStudents from "./routes/teacher/TeacherStudents";
import TeacherAgentActions from "./routes/teacher/TeacherAgentActions";
import TeacherExamTimetable from "./routes/teacher/TeacherExamTimetable";
import TeacherClassProgress from "./routes/teacher/TeacherClassProgress";
import TeacherMessages from "./routes/teacher/TeacherMessages";
import TeacherAssignments from "./routes/teacher/TeacherAssignments";
import AdminRoles from "./routes/admin/AdminRoles";
import AdminAudit from "./routes/admin/AdminAudit";
import SchoolRoles from "./routes/school/SchoolRoles";
import StudentDashboard from "./routes/student/StudentDashboard";
import StudentToday from "./routes/student/StudentToday";
import StudentChat from "./routes/student/StudentChat";
import StudentQuiz from "./routes/student/StudentQuiz";
import StudentHistory from "./routes/student/StudentHistory";
import StudentExams from "./routes/student/StudentExams";
import ParentChildren from "./routes/parent/ParentChildren";
import ParentChild from "./routes/parent/ParentChild";
import ParentReports from "./routes/parent/ParentReports";
import ParentMessages from "./routes/parent/ParentMessages";
import Settings from "./routes/Settings";

const ROLE_TITLE_KEY: Record<Role, string> = {
  super_admin: "roleTitle.superAdmin",
  school_admin: "roleTitle.schoolAdmin",
  teacher: "roleTitle.teacher",
  student: "roleTitle.student",
  parent: "roleTitle.parent",
};

// NavItem.label holds an i18next translation key here (resolved in navForUser),
// not display text — keeps this table language-agnostic.
const NAV: Record<Role, NavItem[]> = {
  super_admin: [
    { to: "/admin", label: "nav.schools", icon: "🏫" },
    { to: "/admin/dashboard", label: "nav.platform", icon: "📊" },
    { to: "/admin/roles", label: "nav.roles", icon: "🛡️", permission: "role:manage" },
    { to: "/admin/audit", label: "nav.audit", icon: "📜" },
    { to: "/settings", label: "nav.settings", icon: "⚙️" },
  ],
  school_admin: [
    { to: "/school", label: "nav.dashboard", icon: "📊" },
    { to: "/school/users", label: "nav.users", icon: "👥" },
    { to: "/school/structure", label: "nav.classes", icon: "🗂️" },
    { to: "/school/roles", label: "nav.roles", icon: "🛡️", permission: "role:manage" },
    { to: "/school/agent-actions", label: "nav.agentQueue", icon: "🤖", permission: "agent_action:view" },
    { to: "/school/audit", label: "nav.audit", icon: "📜" },
    { to: "/settings", label: "nav.settings", icon: "⚙️" },
  ],
  teacher: [
    { to: "/teacher", label: "nav.dashboard", icon: "📊" },
    { to: "/teacher/materials", label: "nav.materials", icon: "📚" },
    { to: "/teacher/assignments", label: "nav.assignments", icon: "📋" },
    { to: "/teacher/timetable", label: "nav.timetable", icon: "🗓️" },
    { to: "/teacher/exam-timetable", label: "nav.exams", icon: "📝" },
    { to: "/teacher/flagged", label: "nav.flagged", icon: "🚩" },
    { to: "/teacher/students", label: "nav.students", icon: "🧑‍🎓", permission: "teacher:portal" },
    { to: "/teacher/messages", label: "nav.messages", icon: "💬" },
    { to: "/teacher/agent-actions", label: "nav.agentQueue", icon: "🤖", permission: "agent_action:view" },
    { to: "/settings", label: "nav.settings", icon: "⚙️" },
  ],
  student: [
    { to: "/student", label: "nav.dashboard", icon: "📊" },
    { to: "/student/today", label: "nav.today", icon: "📖" },
    { to: "/student/chat", label: "nav.tutor", icon: "💬" },
    { to: "/student/quiz", label: "nav.quiz", icon: "🧠" },
    { to: "/student/history", label: "nav.history", icon: "📜" },
    { to: "/student/exams", label: "nav.exams", icon: "📝" },
    { to: "/settings", label: "nav.settings", icon: "⚙️" },
  ],
  parent: [
    { to: "/parent", label: "nav.children", icon: "👨‍👩‍👧" },
    { to: "/settings", label: "nav.settings", icon: "⚙️" },
  ],
};

const SEARCH_SOURCES: Partial<Record<Role, SearchSource<any>>> = {
  super_admin: {
    label: "Schools",
    queryKey: ["admin", "schools"],
    queryFn: () => adminApi.listSchools(),
    toItem: (s: School) => ({ id: s.id, label: s.name, sublabel: s.address ?? undefined, to: "/admin" }),
  },
  school_admin: {
    label: "Users",
    queryKey: ["school", "users"],
    queryFn: () => schoolApi.listUsers(undefined, 200).then((p) => p.items),
    toItem: (u: UserRow) => ({ id: u.id, label: u.name, sublabel: u.email, to: "/school/users" }),
  },
  teacher: {
    label: "Materials",
    queryKey: ["teacher", "materials"],
    queryFn: () => teacherApi.materials(200).then((p) => p.items),
    toItem: (d: DocumentRow) => ({ id: d.id, label: d.filename, sublabel: d.source_type, to: "/teacher/materials" }),
  },
};

function navForUser(role: Role, permissions: string[] | undefined, t: (key: string) => string): NavItem[] {
  return NAV[role]
    .filter((n) => !n.permission || (permissions ?? []).includes(n.permission))
    .map((n) => ({ ...n, label: t(n.label) }));
}

function Shell({
  role,
  permissions,
  children,
}: {
  role: Role;
  permissions: string[];
  children: React.ReactNode;
}) {
  const { t } = useTranslation();
  const user = useAuth((s) => s.user);
  return (
    <RoleGuard permissions={permissions}>
      <AppLayout title={t(ROLE_TITLE_KEY[role])} nav={navForUser(role, user?.permissions, t)} searchSource={SEARCH_SOURCES[role]}>
        {children}
      </AppLayout>
    </RoleGuard>
  );
}

function SettingsRoute() {
  return (
    <RoleGuard permissions={[]}>
      <SettingsShell />
    </RoleGuard>
  );
}

function SettingsShell() {
  const { t } = useTranslation();
  const user = useAuth((s) => s.user)!;
  return (
    <AppLayout title={t(ROLE_TITLE_KEY[user.role])} nav={navForUser(user.role, user.permissions, t)}>
      <Settings />
    </AppLayout>
  );
}

function RootRedirect() {
  const { user, status } = useAuth();
  if (status === "loading")
    return (
      <div className="h-screen grid place-items-center">
        <Spinner label="Loading…" />
      </div>
    );
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={HOME_FOR[user.role]} replace />;
}

export default function App() {
  const bootstrap = useAuth((s) => s.bootstrap);
  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      {/* Super Admin */}
      <Route path="/admin" element={<Shell role="super_admin" permissions={["platform:admin"]}><AdminSchools /></Shell>} />
      <Route path="/admin/dashboard" element={<Shell role="super_admin" permissions={["platform:admin"]}><AdminDashboard /></Shell>} />
      <Route
        path="/admin/roles"
        element={<Shell role="super_admin" permissions={["platform:admin", "role:manage"]}><AdminRoles /></Shell>}
      />
      <Route path="/admin/audit" element={<Shell role="super_admin" permissions={["platform:admin"]}><AdminAudit /></Shell>} />

      {/* School Admin */}
      <Route path="/school" element={<Shell role="school_admin" permissions={["school:admin"]}><SchoolDashboard /></Shell>} />
      <Route path="/school/users" element={<Shell role="school_admin" permissions={["school:admin"]}><SchoolUsers /></Shell>} />
      <Route path="/school/structure" element={<Shell role="school_admin" permissions={["school:admin"]}><SchoolStructure /></Shell>} />
      <Route
        path="/school/roles"
        element={<Shell role="school_admin" permissions={["school:admin", "role:manage"]}><SchoolRoles /></Shell>}
      />
      <Route
        path="/school/agent-actions"
        element={<Shell role="school_admin" permissions={["school:admin", "agent_action:view"]}><SchoolAgentActions /></Shell>}
      />
      <Route path="/school/audit" element={<Shell role="school_admin" permissions={["school:admin"]}><SchoolAudit /></Shell>} />

      {/* Teacher */}
      <Route path="/teacher" element={<Shell role="teacher" permissions={["teacher:portal"]}><TeacherDashboard /></Shell>} />
      <Route path="/teacher/materials" element={<Shell role="teacher" permissions={["teacher:portal"]}><TeacherMaterials /></Shell>} />
      <Route path="/teacher/assignments" element={<Shell role="teacher" permissions={["teacher:portal"]}><TeacherAssignments /></Shell>} />
      <Route path="/teacher/timetable" element={<Shell role="teacher" permissions={["teacher:portal"]}><TeacherTimetable /></Shell>} />
      <Route path="/teacher/exam-timetable" element={<Shell role="teacher" permissions={["teacher:portal"]}><TeacherExamTimetable /></Shell>} />
      <Route path="/teacher/flagged" element={<Shell role="teacher" permissions={["teacher:portal"]}><TeacherFlagged /></Shell>} />
      <Route path="/teacher/students" element={<Shell role="teacher" permissions={["teacher:portal"]}><TeacherStudents /></Shell>} />
      <Route path="/teacher/messages" element={<Shell role="teacher" permissions={["teacher:portal"]}><TeacherMessages /></Shell>} />
      <Route path="/teacher/class-progress/:classId" element={<Shell role="teacher" permissions={["teacher:portal"]}><TeacherClassProgress /></Shell>} />
      <Route
        path="/teacher/agent-actions"
        element={<Shell role="teacher" permissions={["teacher:portal", "agent_action:view"]}><TeacherAgentActions /></Shell>}
      />

      {/* Student */}
      <Route path="/student" element={<Shell role="student" permissions={["student:portal"]}><StudentDashboard /></Shell>} />
      <Route path="/student/today" element={<Shell role="student" permissions={["student:portal"]}><StudentToday /></Shell>} />
      <Route path="/student/chat" element={<Shell role="student" permissions={["student:portal"]}><StudentChat /></Shell>} />
      <Route path="/student/quiz" element={<Shell role="student" permissions={["student:portal"]}><StudentQuiz /></Shell>} />
      <Route path="/student/history" element={<Shell role="student" permissions={["student:portal"]}><StudentHistory /></Shell>} />
      <Route path="/student/exams" element={<Shell role="student" permissions={["student:portal"]}><StudentExams /></Shell>} />

      {/* Parent */}
      <Route path="/parent" element={<Shell role="parent" permissions={["parent:portal"]}><ParentChildren /></Shell>} />
      <Route path="/parent/child/:id" element={<Shell role="parent" permissions={["parent:portal"]}><ParentChild /></Shell>} />
      <Route path="/parent/child/:id/reports" element={<Shell role="parent" permissions={["parent:portal"]}><ParentReports /></Shell>} />
      <Route path="/parent/child/:id/messages" element={<Shell role="parent" permissions={["parent:portal"]}><ParentMessages /></Shell>} />

      {/* Shared */}
      <Route path="/settings" element={<SettingsRoute />} />

      <Route path="/" element={<RootRedirect />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
