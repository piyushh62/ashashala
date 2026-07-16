import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./stores/auth";
import { AppLayout, isNavGroup, type NavEntry } from "./components/layout/AppLayout";
import type { SearchSource } from "./components/layout/CommandPalette";
import { HOME_FOR, RoleGuard } from "./components/layout/RoleGuard";
import type { Role, School, UserRow, DocumentRow } from "./types/api";
import { adminApi, schoolApi, teacherApi } from "./api/endpoints";
import { Spinner } from "./components/ui";

import Login from "./routes/Login";
import AdminSchools from "./routes/admin/AdminSchools";
import AdminSchoolCreate from "./routes/admin/AdminSchoolCreate";
import AdminDashboard from "./routes/admin/AdminDashboard";
import SchoolDashboard from "./routes/school/SchoolDashboard";
import SchoolUsers from "./routes/school/SchoolUsers";
import SchoolUserCreate from "./routes/school/SchoolUserCreate";
import SchoolStructure from "./routes/school/SchoolStructure";
import SchoolStructureCreate from "./routes/school/SchoolStructureCreate";
import SchoolAudit from "./routes/school/SchoolAudit";
import SchoolAgentActions from "./routes/school/SchoolAgentActions";
import TeacherDashboard from "./routes/teacher/TeacherDashboard";
import TeacherMaterials from "./routes/teacher/TeacherMaterials";
import TeacherMaterialCreate from "./routes/teacher/TeacherMaterialCreate";
import TeacherTimetable from "./routes/teacher/TeacherTimetable";
import TeacherTimetableCreate from "./routes/teacher/TeacherTimetableCreate";
import TeacherFlagged from "./routes/teacher/TeacherFlagged";
import TeacherStudents from "./routes/teacher/TeacherStudents";
import TeacherAgentActions from "./routes/teacher/TeacherAgentActions";
import TeacherExamTimetable from "./routes/teacher/TeacherExamTimetable";
import TeacherClassProgress from "./routes/teacher/TeacherClassProgress";
import TeacherMessages from "./routes/teacher/TeacherMessages";
import TeacherAssignments from "./routes/teacher/TeacherAssignments";
import TeacherAssignmentCreate from "./routes/teacher/TeacherAssignmentCreate";
import AdminRoles from "./routes/admin/AdminRoles";
import AdminRoleCreate from "./routes/admin/AdminRoleCreate";
import AdminAudit from "./routes/admin/AdminAudit";
import SchoolRoles from "./routes/school/SchoolRoles";
import SchoolRoleCreate from "./routes/school/SchoolRoleCreate";
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
const NAV: Record<Role, NavEntry[]> = {
  super_admin: [
    {
      label: "nav.schools",
      icon: "schools",
      children: [
        { to: "/admin", label: "nav.schoolList", icon: "schools" },
        { to: "/admin/new", label: "nav.addSchool", icon: "add" },
      ],
    },
    { to: "/admin/dashboard", label: "nav.platform", icon: "platform" },
    {
      label: "nav.roles",
      icon: "roles",
      permission: "role:manage",
      children: [
        { to: "/admin/roles", label: "nav.roleList", icon: "roles" },
        { to: "/admin/roles/new", label: "nav.addRole", icon: "add" },
      ],
    },
    { to: "/admin/audit", label: "nav.audit", icon: "audit" },
    { to: "/settings", label: "nav.settings", icon: "settings" },
  ],
  school_admin: [
    { to: "/school", label: "nav.dashboard", icon: "dashboard" },
    {
      label: "nav.users",
      icon: "users",
      children: [
        { to: "/school/users", label: "nav.userList", icon: "users" },
        { to: "/school/users/new", label: "nav.addUser", icon: "add" },
      ],
    },
    {
      label: "nav.classes",
      icon: "structure",
      children: [
        { to: "/school/structure", label: "nav.structureOverview", icon: "structure" },
        { to: "/school/structure/new", label: "nav.structureAdd", icon: "add" },
      ],
    },
    {
      label: "nav.roles",
      icon: "roles",
      permission: "role:manage",
      children: [
        { to: "/school/roles", label: "nav.roleList", icon: "roles" },
        { to: "/school/roles/new", label: "nav.addRole", icon: "add" },
      ],
    },
    { to: "/school/agent-actions", label: "nav.agentQueue", icon: "agentQueue", permission: "agent_action:view" },
    { to: "/school/audit", label: "nav.audit", icon: "audit" },
    { to: "/settings", label: "nav.settings", icon: "settings" },
  ],
  teacher: [
    { to: "/teacher", label: "nav.dashboard", icon: "dashboard" },
    {
      label: "nav.materials",
      icon: "materials",
      children: [
        { to: "/teacher/materials", label: "nav.materialList", icon: "materials" },
        { to: "/teacher/materials/new", label: "nav.addMaterial", icon: "add" },
      ],
    },
    {
      label: "nav.assignments",
      icon: "assignments",
      children: [
        { to: "/teacher/assignments", label: "nav.assignmentList", icon: "assignments" },
        { to: "/teacher/assignments/new", label: "nav.addAssignment", icon: "add" },
      ],
    },
    {
      label: "nav.timetable",
      icon: "timetable",
      children: [
        { to: "/teacher/timetable", label: "nav.timetableView", icon: "timetable" },
        { to: "/teacher/timetable/new", label: "nav.addPeriod", icon: "add" },
      ],
    },
    { to: "/teacher/exam-timetable", label: "nav.exams", icon: "exams" },
    { to: "/teacher/flagged", label: "nav.flagged", icon: "flagged" },
    { to: "/teacher/students", label: "nav.students", icon: "students", permission: "teacher:portal" },
    { to: "/teacher/messages", label: "nav.messages", icon: "messages" },
    { to: "/teacher/agent-actions", label: "nav.agentQueue", icon: "agentQueue", permission: "agent_action:view" },
    { to: "/settings", label: "nav.settings", icon: "settings" },
  ],
  student: [
    { to: "/student", label: "nav.dashboard", icon: "dashboard" },
    { to: "/student/today", label: "nav.today", icon: "today" },
    { to: "/student/chat", label: "nav.tutor", icon: "tutor" },
    { to: "/student/quiz", label: "nav.quiz", icon: "quiz" },
    { to: "/student/history", label: "nav.history", icon: "history" },
    { to: "/student/exams", label: "nav.exams", icon: "exams" },
    { to: "/settings", label: "nav.settings", icon: "settings" },
  ],
  parent: [
    { to: "/parent", label: "nav.children", icon: "children" },
    { to: "/settings", label: "nav.settings", icon: "settings" },
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

function navForUser(role: Role, permissions: string[] | undefined, t: (key: string) => string): NavEntry[] {
  const has = (p?: string) => !p || (permissions ?? []).includes(p);
  return NAV[role]
    .filter((e) => has(e.permission))
    .map((e) =>
      isNavGroup(e)
        ? {
            ...e,
            label: t(e.label),
            children: e.children.filter((c) => has(c.permission)).map((c) => ({ ...c, label: t(c.label) })),
          }
        : { ...e, label: t(e.label) },
    )
    .filter((e) => !isNavGroup(e) || e.children.length > 0);
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
      <Route path="/admin/new" element={<Shell role="super_admin" permissions={["platform:admin"]}><AdminSchoolCreate /></Shell>} />
      <Route path="/admin/dashboard" element={<Shell role="super_admin" permissions={["platform:admin"]}><AdminDashboard /></Shell>} />
      <Route
        path="/admin/roles"
        element={<Shell role="super_admin" permissions={["platform:admin", "role:manage"]}><AdminRoles /></Shell>}
      />
      <Route
        path="/admin/roles/new"
        element={<Shell role="super_admin" permissions={["platform:admin", "role:manage"]}><AdminRoleCreate /></Shell>}
      />
      <Route path="/admin/audit" element={<Shell role="super_admin" permissions={["platform:admin"]}><AdminAudit /></Shell>} />

      {/* School Admin */}
      <Route path="/school" element={<Shell role="school_admin" permissions={["school:admin"]}><SchoolDashboard /></Shell>} />
      <Route path="/school/users" element={<Shell role="school_admin" permissions={["school:admin"]}><SchoolUsers /></Shell>} />
      <Route path="/school/users/new" element={<Shell role="school_admin" permissions={["school:admin"]}><SchoolUserCreate /></Shell>} />
      <Route path="/school/structure" element={<Shell role="school_admin" permissions={["school:admin"]}><SchoolStructure /></Shell>} />
      <Route path="/school/structure/new" element={<Shell role="school_admin" permissions={["school:admin"]}><SchoolStructureCreate /></Shell>} />
      <Route
        path="/school/roles"
        element={<Shell role="school_admin" permissions={["school:admin", "role:manage"]}><SchoolRoles /></Shell>}
      />
      <Route
        path="/school/roles/new"
        element={<Shell role="school_admin" permissions={["school:admin", "role:manage"]}><SchoolRoleCreate /></Shell>}
      />
      <Route
        path="/school/agent-actions"
        element={<Shell role="school_admin" permissions={["school:admin", "agent_action:view"]}><SchoolAgentActions /></Shell>}
      />
      <Route path="/school/audit" element={<Shell role="school_admin" permissions={["school:admin"]}><SchoolAudit /></Shell>} />

      {/* Teacher */}
      <Route path="/teacher" element={<Shell role="teacher" permissions={["teacher:portal"]}><TeacherDashboard /></Shell>} />
      <Route path="/teacher/materials" element={<Shell role="teacher" permissions={["teacher:portal"]}><TeacherMaterials /></Shell>} />
      <Route path="/teacher/materials/new" element={<Shell role="teacher" permissions={["teacher:portal"]}><TeacherMaterialCreate /></Shell>} />
      <Route path="/teacher/assignments" element={<Shell role="teacher" permissions={["teacher:portal"]}><TeacherAssignments /></Shell>} />
      <Route path="/teacher/assignments/new" element={<Shell role="teacher" permissions={["teacher:portal"]}><TeacherAssignmentCreate /></Shell>} />
      <Route path="/teacher/timetable" element={<Shell role="teacher" permissions={["teacher:portal"]}><TeacherTimetable /></Shell>} />
      <Route path="/teacher/timetable/new" element={<Shell role="teacher" permissions={["teacher:portal"]}><TeacherTimetableCreate /></Shell>} />
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
