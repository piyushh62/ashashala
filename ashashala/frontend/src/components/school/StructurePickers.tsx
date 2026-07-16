import { useTranslation } from "react-i18next";
import { Select } from "../ui";
import type { ClassSection, Subject } from "../../types/api";

// Shared pickers for the school structure pages — all populated by name from
// the school's real classes/subjects/users, so nobody has to type a UUID by
// hand. Data comes in via props so both the list and create pages can reuse
// them with their own queries.

export function Row({ children }: { children: React.ReactNode }) {
  return <div className="p-5 grid md:grid-cols-4 gap-3 items-end">{children}</div>;
}

export function ClassPicker({
  classes,
  loading,
  value,
  onChange,
}: {
  classes?: ClassSection[];
  loading: boolean;
  value: string;
  onChange: (v: string) => void;
}) {
  const { t } = useTranslation();
  return (
    <Select value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">{loading ? t("common.loading") : t("school.structure.selectAClass")}</option>
      {classes?.map((c) => (
        <option key={c.id} value={c.id}>{t("school.structure.classGradeOption", { name: c.name, grade: c.grade_level })}</option>
      ))}
    </Select>
  );
}

export function SubjectPicker({
  subjects,
  loading,
  value,
  onChange,
}: {
  subjects?: Subject[];
  loading: boolean;
  value: string;
  onChange: (v: string) => void;
}) {
  const { t } = useTranslation();
  return (
    <Select value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">{loading ? t("common.loading") : t("school.structure.selectASubject")}</option>
      {subjects?.map((s) => (
        <option key={s.id} value={s.id}>{s.name}</option>
      ))}
    </Select>
  );
}

export function UserPicker({
  users,
  loading,
  value,
  onChange,
  placeholder,
  total,
}: {
  users?: { id: string; name: string; email: string }[];
  loading: boolean;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  total?: number;
}) {
  const { t } = useTranslation();
  const truncated = total != null && users != null && users.length < total;
  return (
    <div>
      <Select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{loading ? t("common.loading") : placeholder}</option>
        {users?.map((u) => (
          <option key={u.id} value={u.id}>{t("school.structure.userEmailOption", { name: u.name, email: u.email })}</option>
        ))}
      </Select>
      {truncated && (
        <p className="text-xs text-amber-600 dark:text-amber-500 mt-1">
          {t("school.structure.pickerTruncated", { shown: users!.length, total })}
        </p>
      )}
    </div>
  );
}
