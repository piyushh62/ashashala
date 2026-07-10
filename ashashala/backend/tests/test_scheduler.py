"""APScheduler wrapper — the test/mocked-settings guard in `start_scheduler`.

`tests/conftest.py` sets ENVIRONMENT=test and MOCK_EXTERNAL_SERVICES=true, so
this guard is what keeps a real background job from spinning up during the
test suite (on top of the fact that the ASGI test client never runs
`lifespan()` at all — see app/core/scheduler.py's docstring).
"""

import pytest

from app.core.scheduler import start_scheduler, stop_scheduler


def test_start_scheduler_noops_under_test_settings():
    scheduler = start_scheduler()
    assert scheduler is None
    stop_scheduler()  # no-op, must not raise when nothing was started


@pytest.mark.asyncio
async def test_dispatch_job_runs_against_a_real_session(db):
    """`_run_dispatch_job` isn't directly reachable without a live scheduler,
    but `dispatch_pending_notifications` — the function it wraps every
    interval — is exercised end-to-end in test_notification_dispatch.py."""
    from app.services.notification_dispatch import dispatch_pending_notifications

    count = await dispatch_pending_notifications(db)
    assert count == 0
