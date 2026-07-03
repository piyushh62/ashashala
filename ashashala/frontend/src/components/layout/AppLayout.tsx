import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../../stores/auth";

export interface NavItem {
  to: string;
  label: string;
  icon: string;
}

export function AppLayout({ title, nav, children }: { title: string; nav: NavItem[]; children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const doLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 shrink-0 bg-white border-r border-slate-200 flex flex-col">
        <div className="px-5 py-4 border-b border-slate-100">
          <div className="font-bold text-brand-600 text-lg">AshaShala</div>
          <div className="text-xs text-slate-400">{title}</div>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {nav.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${
                  isActive ? "bg-brand-50 text-brand-700 font-medium" : "text-slate-600 hover:bg-slate-50"
                }`
              }
            >
              <span>{n.icon}</span>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-slate-100">
          <div className="text-sm text-slate-700 truncate">{user?.name}</div>
          <div className="text-xs text-slate-400 truncate">{user?.email}</div>
          <button onClick={doLogout} className="mt-2 text-xs text-rose-600 hover:underline">
            Log out
          </button>
        </div>
      </aside>
      <main className="flex-1 min-w-0 p-6 max-w-6xl">{children}</main>
    </div>
  );
}

export function PageTitle({ children, subtitle }: { children: ReactNode; subtitle?: string }) {
  return (
    <div className="mb-5">
      <h1 className="text-xl font-bold text-slate-800">{children}</h1>
      {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
    </div>
  );
}
