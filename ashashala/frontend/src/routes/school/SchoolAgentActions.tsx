import { useTranslation } from "react-i18next";
import { AgentActionQueue } from "../../components/AgentActionQueue";
import { PageTitle } from "../../components/layout/AppLayout";

export default function SchoolAgentActions() {
  const { t } = useTranslation();
  return (
    <div>
      <PageTitle subtitle={t("agentQueue.subtitle")}>
        {t("agentQueue.title")}
      </PageTitle>
      <AgentActionQueue />
    </div>
  );
}
