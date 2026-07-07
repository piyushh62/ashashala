import { create } from "zustand";

export type ThemeMode = "light" | "dark";

const STORAGE_KEY = "ashashala_theme";

function applyMode(mode: ThemeMode) {
  document.documentElement.classList.toggle("dark", mode === "dark");
}

function loadInitialMode(): ThemeMode {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

interface ThemeState {
  mode: ThemeMode;
  toggle: () => void;
  set: (mode: ThemeMode) => void;
}

const initialMode = loadInitialMode();
applyMode(initialMode);

export const useTheme = create<ThemeState>((set, get) => ({
  mode: initialMode,

  toggle: () => {
    const next: ThemeMode = get().mode === "dark" ? "light" : "dark";
    localStorage.setItem(STORAGE_KEY, next);
    applyMode(next);
    set({ mode: next });
  },

  set: (mode: ThemeMode) => {
    localStorage.setItem(STORAGE_KEY, mode);
    applyMode(mode);
    set({ mode });
  },
}));
