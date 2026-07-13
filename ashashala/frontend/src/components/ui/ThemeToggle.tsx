import { useTranslation } from "react-i18next";
import { useTheme } from "../../stores/theme";

export function ThemeToggle({ className = "" }: { className?: string }) {
  const { t } = useTranslation();
  const { mode, toggle } = useTheme();
  const isDark = mode === "dark";
  return (
    <button
      onClick={toggle}
      aria-label={isDark ? t("common.switchToLightMode") : t("common.switchToDarkMode")}
      className={`w-9 h-9 grid place-items-center rounded-full text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800 transition ${className}`}
    >
      <span className="text-base">{isDark ? "☀️" : "🌙"}</span>
    </button>
  );
}
