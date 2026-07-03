import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./stores/auth";
import { AppLayout, type NavItem } from "./components/layout/AppLayout";
import { HOME_FOR, RoleGuard } from "./components/layout/RoleGuard";
import type { Role } from "./types/api";
import { Spinner } from "./components/ui";

import Login from "./routes/Login";
import AdminSchools from "./routes/admin/AdminSchools";
import AdminDashboard from "./routes/admin/AdminDashboard";
import SchoolDashboard from "./routes/school/SchoolDashboard";
import SchoolUsers from "./routes/school/SchoolUsers";
import SchoolStructure from "./routes/school/SchoolStructure";
import SchoolAudit from "./routes/school/SchoolAudit";
import TeacherMaterials from "./routes/teacher/TeacherMaterials";
import TeacherTimetable from "./routes/teacher/TeacherTimetable";
import TeacherFlagged from "./routes/teacher/TeacherFlagged";
import StudentDashboard from "./routes/student/StudentDashboard";
import StudentChat from "./routes/student/StudentChat";
import StudentQuiz from "./routes/student/StudentQuiz";
import StudentHistory from "./routes/student/StudentHistory";
import ParentChildren from "./routes/parent/ParentChildren";
import ParentChild from "./routes/parent/ParentChild";

const NAV: Record<Role, NavItem[]> = {
  super_admin: [
    { to: "/admin", label: "Schools", icon: "🏫" },
    { to: "/admin/dashboard", label: "Platform", icon: "📊" },
  ],
  school_admin: [
    { to: "/school", label: "Dashboard", icon: "📊" },
    { to: "/school/users", label: "Users", icon: "👥" },
    { to: "/school/structure", label: "Classes", icon: "🗂️" },
    { to: "/school/audit", label: "Audit", icon: "📜" },
  ],
  teacher: [
    { to: "/teacher", label: "Materials", icon: "📚" },
    { to: "/teacher/timetable", label: "Timetable", icon: "🗓️" },
    { to: "/teacher/flagged", label: "Flagged", icon: "🚩" },
  ],
  student: [
    { to: "/student", label: "Dashboard", icon: "📊" },
    { to: "/student/chat", label: "Tutor", icon: "💬" },
    { to: "/student/quiz", label: "Quiz", icon: "🧠" },
    { to: "/student/history", label: "History", icon: "📜" },
  ],
  parent: [{ to: "/parent", label: "Children", icon: "👨‍👩‍👧" }],
};

function Shell({ role, title, children }: { role: Role; title: string; children: React.ReactNode }) {
  return (
    <RoleGuard allow={[role]}>
      <AppLayout title={title} nav={NAV[role]}>
        {children}
      </AppLayout>
    </RoleGuard>
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

      {/* School Admin */}
      <Route path="/school" element={<Shell role="school_admin" title="School Admin"><SchoolDashboard /></Shell>} />
      <Route path="/school/users" element={<Shell role="school_admin" title="School Admin"><SchoolUsers /></Shell>} />
      <Route path="/school/structure" element={<Shell role="school_admin" title="School Admin"><SchoolStructure /></Shell>} />
      <Route path="/school/audit" element={<Shell role="school_admin" title="School Admin"><SchoolAudit /></Shell>} />

      {/* Teacher */}
      <Route path="/teacher" element={<Shell role="teacher" title="Teacher"><TeacherMaterials /></Shell>} />
      <Route path="/teacher/timetable" element={<Shell role="teacher" title="Teacher"><TeacherTimetable /></Shell>} />
      <Route path="/teacher/flagged" element={<Shell role="teacher" title="Teacher"><TeacherFlagged /></Shell>} />

      {/* Student */}
      <Route path="/student" element={<Shell role="student" title="Student"><StudentDashboard /></Shell>} />
      <Route path="/student/chat" element={<Shell role="student" title="Student"><StudentChat /></Shell>} />
      <Route path="/student/quiz" element={<Shell role="student" title="Student"><StudentQuiz /></Shell>} />
      <Route path="/student/history" element={<Shell role="student" title="Student"><StudentHistory /></Shell>} />

      {/* Parent */}
      <Route path="/parent" element={<Shell role="parent" title="Parent"><ParentChildren /></Shell>} />
      <Route path="/parent/child/:id" element={<Shell role="parent" title="Parent"><ParentChild /></Shell>} />

      <Route path="/" element={<RootRedirect />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
