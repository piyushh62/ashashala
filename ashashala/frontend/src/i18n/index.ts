import i18next from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import hi from "./locales/hi.json";
import gu from "./locales/gu.json";

export const SUPPORTED_LOCALES = ["en", "hi", "gu"] as const;
export type Locale = (typeof SUPPORTED_LOCALES)[number];

const STORAGE_KEY = "ashashala_locale";

function loadInitialLocale(): Locale {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && (SUPPORTED_LOCALES as readonly string[]).includes(stored)) return stored as Locale;
  return "en";
}

i18next.use(initReactI18next).init({
  resources: { en: { translation: en }, hi: { translation: hi }, gu: { translation: gu } },
  lng: loadInitialLocale(),
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export { STORAGE_KEY as LOCALE_STORAGE_KEY };
export default i18next;
