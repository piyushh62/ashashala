"""Scheduling Agent prompt — proposes timetable slot options constrained to a
supplied free-slot list. Produces strict JSON so the agent can defensively
re-validate every slot before anything is persisted (hallucination guard).
"""

from __future__ import annotations

_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def build_scheduling_prompt(
    *,
    free_slots: list[tuple[int, int]],
    teacher_load: dict[int, int],
    class_subject_days: dict[int, int],
    periods_per_week: int,
    lang: str = "en",
) -> str:
    slots_lines = "\n".join(
        f"  - day={d} ({_DAY_NAMES[d]}), period={p}" for d, p in free_slots
    )
    load_lines = "\n".join(
        f"  - {_DAY_NAMES[d]}: {count} period(s) already assigned"
        for d, count in sorted(teacher_load.items())
    ) or "  - (no existing periods this week)"
    cluster_lines = "\n".join(
        f"  - {_DAY_NAMES[d]}: {count} period(s) of this subject already in this class"
        for d, count in sorted(class_subject_days.items())
    ) or "  - (no existing periods of this subject in this class)"

    return f"""You are a school timetable planning assistant. Propose {periods_per_week} weekly
period slot(s) for one teacher teaching one subject to one class.

You MUST choose slots ONLY from this list of currently free (day_of_week, period_number)
pairs — day_of_week is 0=Monday .. 5=Saturday:
{slots_lines}

The teacher's existing weekly workload by day:
{load_lines}

This class's existing weekly period distribution for this subject:
{cluster_lines}

Propose 2 to 4 DIFFERENT options, each choosing exactly {periods_per_week} slot(s) from the
free-slot list above. Each option should follow a distinct, named strategy — for example
"workload-balanced" (spread across the teacher's lighter days), "subject-clustered" (group
near existing periods of this subject), or "early-week" (front-load the week). Give a short
rationale for each option grounded in the workload/distribution data above.

Return STRICT JSON (no markdown, no prose) with exactly this shape:
{{
  "options": [
    {{
      "strategy": "workload-balanced",
      "rationale": "one sentence explaining why, referencing the data above",
      "slots": [{{"day_of_week": 0, "period_number": 1, "room": null}}]
    }}
  ]
}}

Every slot's (day_of_week, period_number) pair MUST appear verbatim in the free-slot list
above — never invent a pair that isn't listed. "room" may be null if no room is suggested."""
