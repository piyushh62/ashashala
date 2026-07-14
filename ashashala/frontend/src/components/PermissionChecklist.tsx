import { CheckboxRow } from "./ui/Checkbox";
import { Skeleton } from "./ui";

interface PermissionLike {
  id: string;
  resource: string;
  action: string;
}

/** Checkbox list for granting resource:action permissions to a role template. */
export function PermissionChecklist({
  permissions,
  loading,
  selected,
  onToggle,
  idPrefix,
}: {
  permissions: PermissionLike[];
  loading?: boolean;
  selected: string[];
  onToggle: (key: string, checked: boolean) => void;
  idPrefix: string;
}) {
  if (loading) return <Skeleton className="h-16" />;

  return (
    <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-1 border border-slate-100 dark:border-slate-800 rounded-xl p-2 max-h-64 overflow-y-auto">
      {permissions.map((p) => {
        const key = `${p.resource}:${p.action}`;
        return (
          <CheckboxRow
            key={p.id}
            id={`${idPrefix}-${p.id}`}
            label={key}
            checked={selected.includes(key)}
            onCheckedChange={(checked) => onToggle(key, checked)}
          />
        );
      })}
    </div>
  );
}
