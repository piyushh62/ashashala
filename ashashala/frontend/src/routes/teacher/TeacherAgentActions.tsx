import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AgentActionQueue } from "../../components/AgentActionQueue";
import { PageTitle } from "../../components/layout/AppLayout";

export default function TeacherAgentActions() {
  const { t } = useTranslation();
  return (
    <div>
      <PageTitle subtitle={t("agentQueue.subtitle")}>{t("agentQueue.title")}</PageTitle>
      <p className="text-sm text-slate-500 -mt-4 mb-6">
        {t("agentQueue.timetableHintPrefix")}{" "}
        <Link to="/teacher/timetable" className="text-brand-600 hover:underline">
          {t("agentQueue.timetablePage")}
        </Link>
        .
      </p>
      <AgentActionQueue />
    </div>
  );
}
