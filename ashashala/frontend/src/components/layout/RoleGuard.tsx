import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../../stores/auth";
import type { Role } from "../../types/api";
import { Spinner } from "../ui";

export const HOME_FOR: Record<Role, string> = {
  super_admin: "/admin",
  school_admin: "/school",
  teacher: "/teacher",
  student: "/student",
  parent: "/parent",
};

export function RoleGuard({
  permissions = [],
  children,
}: {
  permissions?: string[];
  children: ReactNode;
}) {
  const { user, status } = useAuth();

  if (status === "loading") {
    return (
      <div className="h-screen grid place-items-center">
        <Spinner label="Loading…" />
      </div>
    );
  }
  if (status === "anon" || !user) return <Navigate to="/login" replace />;
  if (permissions.some((p) => !user.permissions.includes(p))) {
    return <Navigate to={HOME_FOR[user.role]} replace />;
  }
  return <>{children}</>;
}
