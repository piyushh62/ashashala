import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../../stores/auth";
import { Avatar, Badge } from "../ui";

export interface NavItem {
  to: string;
  label: string;
  icon: string;
}

const ROLE_LABEL: Record<string, string> = {
  super_admin: "Super Admin",
  school_admin: "School Admin",
  teacher: "Teacher",
  student: "Student",
  parent: "Parent",
};

export function AppLayout({ title, nav, children }: { title: string; nav: NavItem[]; children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const doLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 shrink-0 hidden md:flex flex-col sticky top-0 h-screen bg-white/80 backdrop-blur border-r border-slate-200/70">
        <div className="px-5 py-5 flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-brand-500 to-violet-500 text-white grid place-items-center font-bold shadow-pop">
            अ
          </div>
          <div>
            <div className="font-bold text-slate-800 leading-tight">AshaShala</div>
            <div className="text-[11px] text-slate-400">{title}</div>
          </div>
        </div>

        <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
          <div className="px-3 pt-2 pb-1 text-[10px] font-semibold uppercase tracking-widest text-slate-300">
            Menu
          </div>
          {nav.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end
              className={({ isActive }) =>
                `group flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition relative ${
                  isActive
                    ? "bg-brand-50 text-brand-700 font-semibold"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    className={`absolute left-0 top-1/2 -translate-y-1/2 h-6 w-1 rounded-full bg-brand-500 transition-all ${
                      isActive ? "opacity-100" : "opacity-0"
                    }`}
                  />
                  <span className="text-lg w-6 text-center">{n.icon}</span>
                  {n.label}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="m-3 p-3 rounded-2xl bg-slate-50 border border-slate-100">
          <div className="flex items-center gap-3">
            <Avatar name={user?.name || "?"} />
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium text-slate-700 truncate">{user?.name}</div>
              <div className="text-xs text-slate-400 truncate">{user?.email}</div>
            </div>
          </div>
          <button
            onClick={doLogout}
            className="mt-3 w-full text-xs font-medium text-slate-500 hover:text-rose-600 bg-white border border-slate-200 rounded-lg py-1.5 transition"
          >
            Log out
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Mobile top bar */}
        <header className="md:hidden flex items-center justify-between px-4 h-14 bg-white border-b border-slate-200">
          <div className="flex items-center gap-2 font-bold text-brand-600">
            <span className="w-8 h-8 rounded-xl bg-gradient-to-br from-brand-500 to-violet-500 text-white grid place-items-center text-sm">
              अ
            </span>
            AshaShala
          </div>
          <button onClick={doLogout} className="text-xs text-rose-600">
            Log out
          </button>
        </header>

        <div className="hidden md:flex items-center justify-end px-8 h-14 border-b border-slate-200/60">
          <Badge tone="brand">{ROLE_LABEL[user?.role || ""] || "Signed in"}</Badge>
        </div>

        <main className="flex-1 min-w-0 p-5 md:p-8 max-w-6xl w-full mx-auto animate-fade-in">{children}</main>
      </div>
    </div>
  );
}

export function PageTitle({ children, subtitle }: { children: ReactNode; subtitle?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-slate-800 tracking-tight">{children}</h1>
      {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
    </div>
  );
}
