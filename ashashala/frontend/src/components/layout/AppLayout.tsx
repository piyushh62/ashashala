import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import * as Dialog from "@radix-ui/react-dialog";
import { ChevronDown, Menu, Search, X } from "lucide-react";
import { useAuth } from "../../stores/auth";
import { Avatar, Icon, type IconName } from "../ui";
import { Dropdown, DropdownItem, DropdownLabel, DropdownSeparator } from "../ui/Dropdown";
import { NotificationBell } from "./NotificationBell";
import { CommandPalette, type SearchSource } from "./CommandPalette";
import { ThemeToggle } from "../ui/ThemeToggle";
import { ConnectivityBanner } from "./ConnectivityBanner";

export interface NavItem {
  to: string;
  label: string;
  icon: IconName;
  permission?: string;
}

export interface NavGroup {
  label: string;
  icon: IconName;
  permission?: string;
  children: NavItem[];
}

export type NavEntry = NavItem | NavGroup;

export const isNavGroup = (e: NavEntry): e is NavGroup => "children" in e;

export const flattenNav = (nav: NavEntry[]): NavItem[] =>
  nav.flatMap((e) => (isNavGroup(e) ? e.children : [e]));

const ROLE_LABEL_KEY: Record<string, string> = {
  super_admin: "roleTitle.superAdmin",
  school_admin: "roleTitle.schoolAdmin",
  teacher: "roleTitle.teacher",
  student: "roleTitle.student",
  parent: "roleTitle.parent",
};

function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div
      className={`rounded-2xl bg-gradient-to-br from-brand-500 to-violet-500 text-white grid place-items-center font-bold shadow-pop shrink-0 ${
        compact ? "w-8 h-8 text-sm" : "w-10 h-10"
      }`}
    >
      अ
    </div>
  );
}

function NavLeafLink({
  item,
  indent = false,
  onNavigate,
}: {
  item: NavItem;
  indent?: boolean;
  onNavigate?: () => void;
}) {
  return (
    <NavLink
      to={item.to}
      end
      onClick={onNavigate}
      className={({ isActive }) =>
        `group flex items-center gap-3 ${indent ? "pl-9 pr-3" : "px-3"} py-2.5 rounded-xl text-sm transition relative ${
          isActive
            ? "bg-brand-50 text-brand-700 font-semibold dark:bg-brand-500/10 dark:text-brand-300"
            : "text-slate-600 hover:bg-slate-50 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
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
          {!indent && (
            <span className="w-6 grid place-items-center">
              <Icon name={item.icon} className="w-[18px] h-[18px]" />
            </span>
          )}
          {indent && (
            <span className="w-5 grid place-items-center">
              <Icon name={item.icon} className="w-4 h-4" />
            </span>
          )}
          {item.label}
        </>
      )}
    </NavLink>
  );
}

function NavGroupRow({ group, onNavigate }: { group: NavGroup; onNavigate?: () => void }) {
  const location = useLocation();
  const childActive = group.children.some(
    (c) => location.pathname === c.to || location.pathname.startsWith(c.to + "/"),
  );
  const [open, setOpen] = useState(childActive);
  // Auto-open when navigating into a child route; never auto-close.
  useEffect(() => {
    if (childActive) setOpen(true);
  }, [childActive]);
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition ${
          childActive
            ? "text-brand-700 font-semibold dark:text-brand-300"
            : "text-slate-600 hover:bg-slate-50 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
        }`}
      >
        <span className="w-6 grid place-items-center">
          <Icon name={group.icon} className="w-[18px] h-[18px]" />
        </span>
        <span className="flex-1 text-left">{group.label}</span>
        <ChevronDown className={`w-4 h-4 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="space-y-1 mt-1">
          {group.children.map((c) => (
            <NavLeafLink key={c.to} item={c} indent onNavigate={onNavigate} />
          ))}
        </div>
      )}
    </div>
  );
}

function NavLinks({ nav, onNavigate }: { nav: NavEntry[]; onNavigate?: () => void }) {
  const { t } = useTranslation();
  return (
    <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
      <div className="px-3 pt-2 pb-1 text-[10px] font-semibold uppercase tracking-widest text-slate-300 dark:text-slate-600">{t("layout.menu")}</div>
      {nav.map((e) =>
        isNavGroup(e) ? (
          <NavGroupRow key={e.label} group={e} onNavigate={onNavigate} />
        ) : (
          <NavLeafLink key={e.to} item={e} onNavigate={onNavigate} />
        ),
      )}
    </nav>
  );
}

function BrandHeader() {
  return (
    <div className="px-5 py-5 flex items-center gap-3">
      <Logo />
      <div>
        <div className="font-bold text-slate-800 dark:text-slate-100 leading-tight">AshaShala</div>
      </div>
    </div>
  );
}

function SidebarUserCard({ onLogout }: { onLogout: () => void }) {
  const { t } = useTranslation();
  const user = useAuth((s) => s.user);
  return (
    <div className="m-3 p-3 rounded-2xl bg-slate-50 border border-slate-100 dark:bg-slate-800/60 dark:border-slate-700">
      <div className="flex items-center gap-3">
        <Avatar name={user?.name || "?"} />
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium text-slate-700 dark:text-slate-200 truncate">{user?.name}</div>
          <div className="text-xs text-slate-400 truncate">{user?.email}</div>
        </div>
      </div>
      <button
        onClick={onLogout}
        className="mt-3 w-full text-xs font-medium text-slate-500 hover:text-rose-600 bg-white border border-slate-200 rounded-lg py-1.5 transition dark:bg-slate-900 dark:border-slate-700 dark:text-slate-400"
      >
        {t("layout.logout")}
      </button>
    </div>
  );
}

function UserMenu({ onLogout }: { onLogout: () => void }) {
  const { t } = useTranslation();
  const user = useAuth((s) => s.user);
  const navigate = useNavigate();
  return (
    <Dropdown
      trigger={
        <button className="flex items-center gap-2.5 rounded-full pl-1 pr-3 py-1 hover:bg-slate-100 dark:hover:bg-slate-800 transition">
          <Avatar name={user?.name || "?"} size={30} />
          <span className="hidden sm:block text-sm font-medium text-slate-700 dark:text-slate-200 truncate max-w-[10rem]">
            {user?.name}
          </span>
        </button>
      }
    >
      <DropdownLabel>{user?.role ? t(ROLE_LABEL_KEY[user.role]) : t("layout.account")}</DropdownLabel>
      <div className="px-3 pb-2 text-xs text-slate-400 truncate">{user?.email}</div>
      <DropdownSeparator />
      <DropdownItem onSelect={() => navigate("/settings")}>
        <Icon name="settings" className="w-4 h-4" /> {t("nav.settings")}
      </DropdownItem>
      <DropdownItem danger onSelect={onLogout}>
        {t("layout.logout")}
      </DropdownItem>
    </Dropdown>
  );
}

export function AppLayout({
  title,
  nav,
  searchSource,
  children,
}: {
  title: string;
  nav: NavEntry[];
  searchSource?: SearchSource<any>;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  const doLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const flatNav = useMemo(() => flattenNav(nav), [nav]);

  const currentSection = useMemo(() => {
    const matches = flatNav.filter((n) => location.pathname.startsWith(n.to));
    matches.sort((a, b) => b.to.length - a.to.length);
    return matches[0]?.label;
  }, [flatNav, location.pathname]);

  useEffect(() => {
    document.title = currentSection ? `${currentSection} · AshaShala` : `${title} · AshaShala`;
  }, [currentSection, title]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((open) => !open);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <div className="min-h-screen flex">
      {/* Desktop sidebar */}
      <aside className="w-64 shrink-0 hidden md:flex flex-col sticky top-0 h-screen bg-white/80 dark:bg-slate-900/80 backdrop-blur border-r border-slate-200/70 dark:border-slate-800">
        <BrandHeader />
        <NavLinks nav={nav} />
        <SidebarUserCard onLogout={doLogout} />
      </aside>

      {/* Mobile drawer */}
      <Dialog.Root open={drawerOpen} onOpenChange={setDrawerOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-slate-900/40 backdrop-blur-[2px] z-40 md:hidden data-[state=open]:animate-fade-in" />
          <Dialog.Content className="fixed inset-y-0 left-0 z-50 w-72 max-w-[85%] bg-white dark:bg-slate-900 border-r border-slate-200/70 dark:border-slate-800 flex flex-col md:hidden focus:outline-none data-[state=open]:animate-slide-up">
            <Dialog.Title className="sr-only">{t("layout.navigation")}</Dialog.Title>
            <div className="flex items-center justify-between px-5 py-5">
              <div className="flex items-center gap-3">
                <Logo />
                <div className="font-bold text-slate-800 dark:text-slate-100 leading-tight">AshaShala</div>
              </div>
              <Dialog.Close className="w-8 h-8 grid place-items-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300">
                <X className="w-5 h-5" />
              </Dialog.Close>
            </div>
            <NavLinks nav={nav} onNavigate={() => setDrawerOpen(false)} />
            <SidebarUserCard onLogout={doLogout} />
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* Main */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Mobile top bar */}
        <header className="md:hidden flex items-center justify-between px-4 h-14 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
          <button
            onClick={() => setDrawerOpen(true)}
            aria-label={t("layout.openNav")}
            className="w-9 h-9 grid place-items-center rounded-lg text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2 font-bold text-brand-600">
            <Logo compact />
          </div>
          <div className="flex items-center gap-1">
            <ThemeToggle />
            <NotificationBell />
            <UserMenu onLogout={doLogout} />
          </div>
        </header>

        {/* Desktop top bar */}
        <div className="hidden md:flex items-center justify-between px-8 h-14 border-b border-slate-200/60 dark:border-slate-800">
          <div className="text-sm text-slate-400">
            <span className="text-slate-500 dark:text-slate-400 font-medium">{title}</span>
            {currentSection && (
              <>
                <span className="mx-2 text-slate-300 dark:text-slate-700">/</span>
                <span className="text-slate-700 dark:text-slate-200 font-medium">{currentSection}</span>
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPaletteOpen(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full text-sm text-slate-400 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-400 transition"
            >
              <Search className="w-4 h-4" />
              <span>{t("layout.search")}</span>
              <kbd className="text-[10px] font-medium text-slate-400 border border-slate-300 dark:border-slate-600 rounded px-1">
                ⌘K
              </kbd>
            </button>
            <ThemeToggle />
            <NotificationBell />
            <UserMenu onLogout={doLogout} />
          </div>
        </div>

        <main className="flex-1 min-w-0 p-5 md:p-8 max-w-6xl w-full mx-auto animate-fade-in">{children}</main>
      </div>

      <CommandPalette nav={flatNav} searchSource={searchSource} open={paletteOpen} onOpenChange={setPaletteOpen} />
      <ConnectivityBanner />
    </div>
  );
}

export function PageTitle({ children, subtitle }: { children: ReactNode; subtitle?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 tracking-tight">{children}</h1>
      {subtitle && <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{subtitle}</p>}
    </div>
  );
}
