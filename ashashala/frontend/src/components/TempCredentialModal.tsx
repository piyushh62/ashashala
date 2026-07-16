import { useTranslation } from "react-i18next";
import { Button } from "./ui";
import { Modal } from "./ui/Modal";

export interface TempCredential {
  email: string;
  password: string;
}

/**
 * Shared "temporary password" modal shown after creating a user (or resetting
 * a password). The credential is only ever displayed once, so callers must not
 * navigate away until the user closes this modal — pass that navigation in
 * `onClose` instead.
 */
export function TempCredentialModal({
  credential,
  onClose,
}: {
  credential: TempCredential | null;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  return (
    <Modal
      open={!!credential}
      onOpenChange={(open) => !open && onClose()}
      title={t("common.tempPasswordTitle")}
      description={t("common.tempPasswordDesc")}
      size="sm"
    >
      {credential && (
        <div className="space-y-3">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{t("common.email")}</div>
            <div className="text-sm font-medium text-slate-700">{credential.email}</div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{t("common.tempPasswordLabel")}</div>
            <div className="flex items-center gap-2 mt-1">
              <code className="flex-1 px-3 py-2 rounded-lg bg-slate-50 border border-slate-200 text-sm font-mono text-slate-700">
                {credential.password}
              </code>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => navigator.clipboard.writeText(credential.password)}
              >
                {t("common.copy")}
              </Button>
            </div>
          </div>
          <Button type="button" className="w-full" onClick={onClose}>
            {t("common.done")}
          </Button>
        </div>
      )}
    </Modal>
  );
}
