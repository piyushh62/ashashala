import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

type ToastKind = "success" | "error" | "info";
interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

interface ToastCtx {
  push: (message: string, kind?: ToastKind) => void;
}

const Ctx = createContext<ToastCtx>({ push: () => {} });

export function useToast() {
  return useContext(Ctx);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback((message: string, kind: ToastKind = "info") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, kind, message }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000);
  }, []);

  const value = useMemo(() => ({ push }), [push]);

  const meta: Record<ToastKind, { ring: string; icon: string; iconBg: string }> = {
    success: { ring: "border-emerald-200", icon: "✓", iconBg: "bg-emerald-500" },
    error: { ring: "border-rose-200", icon: "!", iconBg: "bg-rose-500" },
    info: { ring: "border-slate-200", icon: "i", iconBg: "bg-slate-700" },
  };

  return (
    <Ctx.Provider value={value}>
      {children}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2.5">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`flex items-center gap-3 bg-white text-slate-700 text-sm pl-3 pr-4 py-2.5 rounded-xl shadow-soft border ${meta[t.kind].ring} max-w-xs animate-slide-up`}
          >
            <span
              className={`w-6 h-6 rounded-full ${meta[t.kind].iconBg} text-white grid place-items-center text-xs font-bold shrink-0`}
            >
              {meta[t.kind].icon}
            </span>
            <span className="min-w-0">{t.message}</span>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
