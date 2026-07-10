import { useEffect } from "react";
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
import TeacherDashboard from "./routes/teacher/TeacherDashboard";
import TeacherMaterials from "./routes/teacher/TeacherMaterials";
import TeacherTimetable from "./routes/teacher/TeacherTimetable";
import TeacherFlagged from "./routes/teacher/TeacherFlagged";
import TeacherStudents from "./routes/teacher/TeacherStudents";
import TeacherAgentActions from "./routes/teacher/TeacherAgentActions";
import AdminRoles from "./routes/admin/AdminRoles";
import SchoolRoles from "./routes/school/SchoolRoles";
import StudentDashboard from "./routes/student/StudentDashboard";
import StudentChat from "./routes/student/StudentChat";
import StudentQuiz from "./routes/student/StudentQuiz";
import StudentHistory from "./routes/student/StudentHistory";
import ParentChildren from "./routes/parent/ParentChildren";
import ParentChild from "./routes/parent/ParentChild";
import Settings from "./routes/Settings";

const ALL_ROLES: Role[] = ["super_admin", "school_admin", "teacher", "student", "parent"];

const ROLE_TITLE: Record<Role, string> = {
  super_admin: "Super Admin",
  school_admin: "School Admin",
  teacher: "Teacher",
  student: "Student",
  parent: "Parent",
};

const NAV: Record<Role, NavItem[]> = {
  super_admin: [
    { to: "/admin", label: "Schools", icon: "🏫" },
    { to: "/admin/dashboard", label: "Platform", icon: "📊" },
    { to: "/admin/roles", label: "Roles", icon: "🛡️", permission: "role:manage" },
    { to: "/settings", label: "Settings", icon: "⚙️" },
  ],
  school_admin: [
    { to: "/school", label: "Dashboard", icon: "📊" },
    { to: "/school/users", label: "Users", icon: "👥" },
    { to: "/school/structure", label: "Classes", icon: "🗂️" },
    { to: "/school/roles", label: "Roles", icon: "🛡️", permission: "role:manage" },
    { to: "/school/audit", label: "Audit", icon: "📜" },
    { to: "/settings", label: "Settings", icon: "⚙️" },
  ],
  teacher: [
    { to: "/teacher", label: "Dashboard", icon: "📊" },
    { to: "/teacher/materials", label: "Materials", icon: "📚" },
    { to: "/teacher/timetable", label: "Timetable", icon: "🗓️" },
    { to: "/teacher/flagged", label: "Flagged", icon: "🚩" },
    { to: "/teacher/students", label: "Students", icon: "🧑‍🎓", permission: "teacher:portal" },
    { to: "/teacher/agent-actions", label: "Agent Queue", icon: "🤖", permission: "agent_action:view" },
    { to: "/settings", label: "Settings", icon: "⚙️" },
  ],
  student: [
    { to: "/student", label: "Dashboard", icon: "📊" },
    { to: "/student/chat", label: "Tutor", icon: "💬" },
    { to: "/student/quiz", label: "Quiz", icon: "🧠" },
    { to: "/student/history", label: "History", icon: "📜" },
    { to: "/settings", label: "Settings", icon: "⚙️" },
  ],
  parent: [
    { to: "/parent", label: "Children", icon: "👨‍👩‍👧" },
    { to: "/settings", label: "Settings", icon: "⚙️" },
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

function navForUser(role: Role, permissions: string[] | undefined): NavItem[] {
  return NAV[role].filter((n) => !n.permission || (permissions ?? []).includes(n.permission));
}

function Shell({
  role,
  title,
  requirePermission,
  children,
}: {
  role: Role;
  title: string;
  requirePermission?: string;
  children: React.ReactNode;
}) {
  const user = useAuth((s) => s.user);
  return (
    <RoleGuard allow={[role]} requirePermission={requirePermission}>
      <AppLayout title={title} nav={navForUser(role, user?.permissions)} searchSource={SEARCH_SOURCES[role]}>
        {children}
      </AppLayout>
    </RoleGuard>
  );
}

function SettingsRoute() {
  return (
    <RoleGuard allow={ALL_ROLES}>
      <SettingsShell />
    </RoleGuard>
  );
}

function SettingsShell() {
  const user = useAuth((s) => s.user)!;
  return (
    <AppLayout title={ROLE_TITLE[user.role]} nav={navForUser(user.role, user.permissions)}>
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
      <Route path="/admin" element={<Shell role="super_admin" title="Super Admin"><AdminSchools /></Shell>} />
      <Route path="/admin/dashboard" element={<Shell role="super_admin" title="Super Admin"><AdminDashboard /></Shell>} />
      <Route
        path="/admin/roles"
        element={<Shell role="super_admin" title="Super Admin" requirePermission="role:manage"><AdminRoles /></Shell>}
      />

      {/* School Admin */}
      <Route path="/school" element={<Shell role="school_admin" title="School Admin"><SchoolDashboard /></Shell>} />
      <Route path="/school/users" element={<Shell role="school_admin" title="School Admin"><SchoolUsers /></Shell>} />
      <Route path="/school/structure" element={<Shell role="school_admin" title="School Admin"><SchoolStructure /></Shell>} />
      <Route
        path="/school/roles"
        element={<Shell role="school_admin" title="School Admin" requirePermission="role:manage"><SchoolRoles /></Shell>}
      />
      <Route path="/school/audit" element={<Shell role="school_admin" title="School Admin"><SchoolAudit /></Shell>} />

      {/* Teacher */}
      <Route path="/teacher" element={<Shell role="teacher" title="Teacher"><TeacherDashboard /></Shell>} />
      <Route path="/teacher/materials" element={<Shell role="teacher" title="Teacher"><TeacherMaterials /></Shell>} />
      <Route path="/teacher/timetable" element={<Shell role="teacher" title="Teacher"><TeacherTimetable /></Shell>} />
      <Route path="/teacher/flagged" element={<Shell role="teacher" title="Teacher"><TeacherFlagged /></Shell>} />
      <Route path="/teacher/students" element={<Shell role="teacher" title="Teacher"><TeacherStudents /></Shell>} />
      <Route
        path="/teacher/agent-actions"
        element={<Shell role="teacher" title="Teacher" requirePermission="agent_action:view"><TeacherAgentActions /></Shell>}
      />

      {/* Student */}
      <Route path="/student" element={<Shell role="student" title="Student"><StudentDashboard /></Shell>} />
      <Route path="/student/chat" element={<Shell role="student" title="Student"><StudentChat /></Shell>} />
      <Route path="/student/quiz" element={<Shell role="student" title="Student"><StudentQuiz /></Shell>} />
      <Route path="/student/history" element={<Shell role="student" title="Student"><StudentHistory /></Shell>} />

      {/* Parent */}
      <Route path="/parent" element={<Shell role="parent" title="Parent"><ParentChildren /></Shell>} />
      <Route path="/parent/child/:id" element={<Shell role="parent" title="Parent"><ParentChild /></Shell>} />

      {/* Shared */}
      <Route path="/settings" element={<SettingsRoute />} />

      <Route path="/" element={<RootRedirect />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
