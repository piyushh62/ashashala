import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { adminApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, Input, Label } from "../../components/ui";
import { useToast } from "../../components/ui/Toast";

export default function AdminSchoolCreate() {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");

  const create = useMutation({
    mutationFn: () => adminApi.createSchool({ name, address: address || undefined }),
    onSuccess: () => {
      toast.push(t("admin.schools.schoolCreated"), "success");
      qc.invalidateQueries({ queryKey: ["admin", "schools"] });
      navigate("/admin");
    },
    onError: () => toast.push(t("admin.schools.createSchoolFailed"), "error"),
  });

  return (
    <div>
      <PageTitle subtitle={t("admin.schools.subtitle")}>{t("admin.schools.onboardASchool")}</PageTitle>

      <Card>
        <CardHeader title={t("admin.schools.onboardASchool")} />
        <form
          className="p-5 flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div className="flex-1 min-w-[180px]">
            <Label>{t("admin.schools.name")}</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="flex-1 min-w-[180px]">
            <Label>{t("admin.schools.address")}</Label>
            <Input value={address} onChange={(e) => setAddress(e.target.value)} />
          </div>
          <Button type="submit" disabled={create.isPending}>
            {create.isPending ? t("admin.schools.creating") : t("admin.schools.create")}
          </Button>
        </form>
      </Card>
    </div>
  );
}
