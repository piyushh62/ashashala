import { AgentActionQueue } from "../../components/AgentActionQueue";
import { PageTitle } from "../../components/layout/AppLayout";

export default function TeacherAgentActions() {
  return (
    <div>
      <PageTitle subtitle="Proactive suggestions from AshaShala's agents, awaiting your review.">
        Agent Queue
      </PageTitle>
      <AgentActionQueue />
    </div>
  );
}
