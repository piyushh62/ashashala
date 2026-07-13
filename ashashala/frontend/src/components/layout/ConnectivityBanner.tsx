import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

export function ConnectivityBanner() {
  const { t } = useTranslation();
  const [online, setOnline] = useState(navigator.onLine);

  useEffect(() => {
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  if (online) return null;

  return (
    <div className="fixed bottom-0 inset-x-0 z-50 bg-amber-500 text-white text-sm text-center py-2 px-4 shadow-soft">
      {t("layout.offlineBanner")}
    </div>
  );
}
