import {
  AlertTriangle,
  BarChart3,
  Bell,
  Bot,
  BookOpen,
  Brain,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ClipboardList,
  Copy,
  FileText,
  Flag,
  FolderTree,
  GraduationCap,
  History,
  Info,
  LayoutDashboard,
  Leaf,
  Library,
  LogOut,
  MessageSquare,
  Moon,
  Pencil,
  Play,
  Presentation,
  ScrollText,
  Search,
  Send,
  Settings as SettingsIcon,
  Shield,
  Siren,
  Sparkles,
  Sun,
  Target,
  Trash2,
  TrendingUp,
  Users,
  UsersRound,
  X,
  XCircle,
  Zap,
  type LucideIcon,
} from "lucide-react";

/**
 * Central icon registry. Everything in the app references icons by a semantic
 * name (e.g. "schools", "flagged") instead of importing lucide icons ad-hoc or
 * pasting emoji. This keeps the icon set consistent, themeable, and swappable
 * from one place.
 */
export const ICONS = {
  // navigation / domains
  schools: Presentation,
  platform: BarChart3,
  dashboard: LayoutDashboard,
  users: Users,
  students: GraduationCap,
  student: GraduationCap,
  teacher: Presentation,
  parents: UsersRound,
  children: UsersRound,
  classes: FolderTree,
  structure: FolderTree,
  roles: Shield,
  audit: ScrollText,
  history: History,
  settings: SettingsIcon,
  agentQueue: Bot,
  materials: Library,
  assignments: ClipboardList,
  timetable: CalendarDays,
  exams: FileText,
  flagged: Flag,
  messages: MessageSquare,
  chat: MessageSquare,
  tutor: MessageSquare,
  quiz: Brain,
  today: BookOpen,
  reading: BookOpen,
  reports: FileText,

  // dashboard / status glyphs
  target: Target,
  trend: TrendingUp,
  activity: Zap,
  alert: AlertTriangle,
  critical: Siren,
  wellbeing: Leaf,
  mastery: Brain,
  bell: Bell,

  // ui affordances
  search: Search,
  sortAsc: ChevronUp,
  sortDesc: ChevronDown,
  success: CheckCircle2,
  error: XCircle,
  info: Info,
  check: Check,
  close: X,
  copy: Copy,
  edit: Pencil,
  delete: Trash2,
  logout: LogOut,
  sun: Sun,
  moon: Moon,
  sparkles: Sparkles,
  play: Play,
  file: FileText,
  send: Send,
} satisfies Record<string, LucideIcon>;

export type IconName = keyof typeof ICONS;

/**
 * Render a registry icon by name at a consistent default size (1.25rem).
 * Pass `className` to override size/color via Tailwind utilities.
 */
export function Icon({
  name,
  className = "w-5 h-5",
  strokeWidth = 2,
}: {
  name: IconName;
  className?: string;
  strokeWidth?: number;
}) {
  const Cmp = ICONS[name];
  return <Cmp className={className} strokeWidth={strokeWidth} aria-hidden />;
}
