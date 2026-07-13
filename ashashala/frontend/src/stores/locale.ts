import { create } from "zustand";
import i18n, { LOCALE_STORAGE_KEY, type Locale } from "../i18n";

interface LocaleState {
  locale: Locale;
  setLocale: (locale: Locale) => void;
}

export const useLocale = create<LocaleState>((set) => ({
  locale: i18n.language as Locale,
  setLocale: (locale) => {
    localStorage.setItem(LOCALE_STORAGE_KEY, locale);
    i18n.changeLanguage(locale);
    set({ locale });
  },
}));
