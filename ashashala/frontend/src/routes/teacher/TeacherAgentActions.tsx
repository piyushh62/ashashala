import { Link } from "react-router-dom";
import { AgentActionQueue } from "../../components/AgentActionQueue";
import { PageTitle } from "../../components/layout/AppLayout";

export default function TeacherAgentActions() {
  return (
    <div>
      <PageTitle subtitle="Proactive suggestions from AshaShala's agents, awaiting your review.">
        Agent Queue
      </PageTitle>
      <p className="text-sm text-slate-500 -mt-4 mb-6">
        Looking for AI timetable suggestions? Those are reviewed on the{" "}
        <Link to="/teacher/timetable" className="text-brand-600 hover:underline">
          Timetable page
        </Link>
        .
      </p>
      <AgentActionQueue />
    </div>
  );
}
