import { useDropzone, type Accept } from "react-dropzone";
import { Icon } from "./icons";
import { cn } from "../../lib/cn";

/**
 * Drag-and-drop file picker matching the app's field styling. Single-file by
 * default; shows the chosen filename and supports click-to-browse as a
 * fallback. Wraps react-dropzone so screens don't touch it directly.
 */
export function Dropzone({
  onFile,
  file,
  accept,
  disabled = false,
  hint,
  browseLabel = "Drag a file here, or click to browse",
  className = "",
}: {
  onFile: (file: File | null) => void;
  file: File | null;
  accept?: Accept;
  disabled?: boolean;
  hint?: string;
  browseLabel?: string;
  className?: string;
}) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept,
    disabled,
    multiple: false,
    onDrop: (accepted) => {
      if (accepted[0]) onFile(accepted[0]);
    },
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        "flex flex-col items-center justify-center gap-1.5 rounded-xl border-2 border-dashed px-4 py-6 text-center text-sm transition cursor-pointer",
        isDragActive
          ? "border-brand-400 bg-brand-50 dark:bg-brand-500/10"
          : "border-slate-300 hover:border-brand-300 dark:border-slate-700 dark:hover:border-brand-600",
        disabled && "opacity-50 cursor-not-allowed",
        className,
      )}
    >
      <input {...getInputProps()} />
      <Icon name={file ? "check" : "upload"} className="w-5 h-5 text-slate-400" />
      {file ? (
        <span className="font-medium text-slate-700 dark:text-slate-200 truncate max-w-full">{file.name}</span>
      ) : (
        <span className="text-slate-500 dark:text-slate-400">{browseLabel}</span>
      )}
      {hint && <span className="text-xs text-slate-400">{hint}</span>}
    </div>
  );
}
