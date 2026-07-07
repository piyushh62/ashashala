import type { ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Button } from "./index";

/* ---------------------------------------------------------------------------
 * Modal — generic dialog shell built on Radix (focus trap, ESC-to-close,
 * scroll lock, and portal rendering come for free; we only own the visuals).
 * ------------------------------------------------------------------------- */

export function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
  size = "md",
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  size?: "sm" | "md" | "lg";
}) {
  const widths: Record<string, string> = { sm: "max-w-sm", md: "max-w-lg", lg: "max-w-2xl" };
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-slate-900/40 backdrop-blur-[2px] z-40 data-[state=open]:animate-fade-in" />
        <Dialog.Content
          className={`fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[calc(100%-2rem)] ${widths[size]} bg-white dark:bg-slate-900 rounded-2xl shadow-soft border border-slate-200/70 dark:border-slate-800 focus:outline-none data-[state=open]:animate-pop-in max-h-[85vh] flex flex-col`}
        >
          <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800 shrink-0">
            <Dialog.Title className="font-semibold text-slate-800 dark:text-slate-100">{title}</Dialog.Title>
            {description && (
              <Dialog.Description className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{description}</Dialog.Description>
            )}
          </div>
          <div className="p-5 overflow-y-auto">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/* ---------------------------------------------------------------------------
 * ConfirmDialog — the one every destructive action must go through.
 * ------------------------------------------------------------------------- */

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  tone = "danger",
  isPending = false,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "danger" | "primary";
  isPending?: boolean;
  onConfirm: () => void;
}) {
  return (
    <Modal open={open} onOpenChange={onOpenChange} title={title} description={description} size="sm">
      <div className="flex justify-end gap-2.5">
        <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={isPending}>
          {cancelLabel}
        </Button>
        <Button
          variant={tone === "danger" ? "danger" : "primary"}
          onClick={onConfirm}
          disabled={isPending}
        >
          {isPending ? "Working…" : confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}

/**
 * useConfirm — imperative helper so callers don't hand-roll open/pending
 * state for every destructive button. Usage:
 *
 *   const confirm = useConfirm();
 *   <Button onClick={() => confirm.ask({
 *     title: "Delete school?",
 *     description: "This can't be undone.",
 *     onConfirm: () => del.mutateAsync(id),
 *   })} />
 *   {confirm.dialog}
 */
import { useCallback, useState } from "react";

interface ConfirmOptions {
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "danger" | "primary";
  onConfirm: () => Promise<unknown> | void;
}

export function useConfirm() {
  const [opts, setOpts] = useState<ConfirmOptions | null>(null);
  const [isPending, setIsPending] = useState(false);

  const ask = useCallback((o: ConfirmOptions) => setOpts(o), []);
  const close = useCallback(() => {
    if (!isPending) setOpts(null);
  }, [isPending]);

  const handleConfirm = useCallback(async () => {
    if (!opts) return;
    setIsPending(true);
    try {
      await opts.onConfirm();
      setOpts(null);
    } finally {
      setIsPending(false);
    }
  }, [opts]);

  const dialog = opts ? (
    <ConfirmDialog
      open
      onOpenChange={close}
      title={opts.title}
      description={opts.description}
      confirmLabel={opts.confirmLabel}
      cancelLabel={opts.cancelLabel}
      tone={opts.tone}
      isPending={isPending}
      onConfirm={handleConfirm}
    />
  ) : null;

  return { ask, dialog };
}
