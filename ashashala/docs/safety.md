# AshaShala — Safety

Layered defense so a student always gets a safe, on-topic, cited answer.

## 1. Gemini built-in safety (first line, zero extra cost)
Every Gemini call carries `SAFETY_SETTINGS` (see `app/services/gemini_client.py`):
hate speech, harassment, sexually-explicit and dangerous-content categories are
set to `BLOCK_ONLY_HIGH`. Gemini blocks high-severity harmful content before it
ever reaches the student — no extra request, no extra latency.

> **Live check (needs a real GEMINI_API_KEY):** send an inappropriate message
> to `POST /api/v1/student/chat` and confirm the answer is blocked/empty rather
> than harmful. This can't run in CI (no network), so it's a manual pre-launch step.

## 2. Topic guard (deterministic + LLM)
`app/agents/safety.py::safety_wrapper` runs before the Tutor:
- a **keyword fast-path** rejects clearly off-topic / unsafe terms with zero LLM cost, and
- a cheap `fast_chat` classification confirms the question relates to the student's subject.

Off-topic questions raise `ForbiddenError` (403) with a redirect-to-teacher
message — the tutor never answers outside the class context.

## 3. Grounding (no hallucination)
The tutor prompt (`build_tutor_prompt`, Section 6) forbids answering from general
knowledge: every claim must cite retrieved material, and if the answer isn't in
the material the tutor says so and points to the teacher.

## 4. Rate limiting (quota protection)
`slowapi` limits the expensive endpoints per IP (configurable in `config.py`):
- `POST /api/v1/student/chat` → `CHAT_RATE_LIMIT` (default **30/minute**)
- `POST /api/v1/student/quiz/start` → `QUIZ_RATE_LIMIT` (default **20/minute**)

Exceeding a limit returns **429**. This protects the free Gemini/NVIDIA quotas
from a single runaway client. The limiter degrades gracefully to a no-op if
`slowapi` isn't installed, so the app never fails to boot because of it.

## 5. Audit
Every chat message is audit-logged (`CHAT_MESSAGE`, hashed content + retrieved
chunk ids). Grading overrides and flags are logged too — a full trail for review.

## Deferred (post-Phase 6)
The NVIDIA `nemoguard-jailbreak-detect` classifier is real defense-in-depth but
consumes a pre-computed embedding per message. It's registered in
`model_registry.yaml` (`safety_jailbreak`) and wired in once its free-tier cost
per message is measured.
