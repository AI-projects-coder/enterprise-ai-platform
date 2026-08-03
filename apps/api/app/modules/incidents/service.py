import asyncio
import os
from datetime import datetime, timedelta, timezone

import google.auth
from google.cloud import logging as gcloud_logging
from google.cloud import monitoring_v3
from google.cloud import run_v2

# This app has always deployed to one region across all 3 environments
# (see phase 6) — not worth detecting dynamically for a value that's never
# actually varied.
REGION = "asia-south1"
SERVICES = ("api", "web")

_project_id: str | None = None

NOT_DEPLOYED_ERROR = {
    "error": "This tool reads real Cloud Logging/Monitoring/Run data from this app's own "
    "deployed environment and only works in sandbox/stage/production, not local dev "
    "(there's no real GCP project behind docker-compose)."
}


def _is_deployed() -> bool:
    # K_SERVICE is set by Cloud Run itself on every running instance,
    # guaranteed present there and guaranteed absent everywhere else — same
    # check apps/web/src/lib/api.ts already uses for the identical question.
    return bool(os.environ.get("K_SERVICE"))


def _get_project_id() -> str:
    # google.auth.default() resolves ADC the same way every google-cloud-*
    # client already does implicitly (see storage.py) — on Cloud Run this
    # returns the project THIS specific instance's service account belongs
    # to, so sandbox/stage/prod each naturally see only their own project,
    # with no project id hardcoded or configured anywhere.
    global _project_id
    if _project_id is None:
        _, _project_id = google.auth.default()
    return _project_id


def _get_recent_errors_sync(minutes: int) -> dict:
    project_id = _get_project_id()
    client = gcloud_logging.Client(project=project_id)
    since = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    filter_str = f'resource.type="cloud_run_revision" severity>=ERROR timestamp>="{since}"'
    entries = client.list_entries(
        resource_names=[f"projects/{project_id}"],
        filter_=filter_str,
        order_by=gcloud_logging.DESCENDING,
        max_results=20,
    )
    errors = []
    for e in entries:
        message = e.payload.get("message") if isinstance(e.payload, dict) else str(e.payload)
        errors.append(
            {
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "severity": e.severity,
                "service": e.resource.labels.get("service_name"),
                "message": message,
            }
        )
    return {"minutes": minutes, "error_count": len(errors), "errors": errors}


def _get_alert_policies_sync() -> dict:
    project_id = _get_project_id()
    client = monitoring_v3.AlertPolicyServiceClient()
    policies = client.list_alert_policies(name=f"projects/{project_id}")
    return {"policies": [{"name": p.display_name, "enabled": p.enabled} for p in policies]}


def _get_recent_deployments_sync(limit: int) -> dict:
    project_id = _get_project_id()
    client = run_v2.RevisionsClient()
    deployments = []
    for service in SERVICES:
        parent = f"projects/{project_id}/locations/{REGION}/services/{service}"
        for r in client.list_revisions(parent=parent):
            healthy = any(
                c.type_ == "Ready" and c.state == run_v2.Condition.State.CONDITION_SUCCEEDED
                for c in r.conditions
            )
            deployments.append(
                {
                    "service": service,
                    "revision": r.name.split("/")[-1],
                    "created_at": r.create_time.isoformat() if r.create_time else None,
                    "healthy": healthy,
                }
            )
    # list_revisions' ordering isn't documented as guaranteed, so sort
    # explicitly rather than trust it — same reasoning as never trusting an
    # unverified API shape.
    deployments.sort(key=lambda d: d["created_at"] or "", reverse=True)
    return {"deployments": deployments[:limit]}


async def get_recent_errors(minutes: int = 15) -> dict:
    if not _is_deployed():
        return NOT_DEPLOYED_ERROR
    # Every client above is synchronous (blocking) — same reasoning as
    # storage.py: run it off the event loop so it doesn't stall other
    # concurrent requests on this worker.
    return await asyncio.to_thread(_get_recent_errors_sync, minutes)


async def get_alert_policies() -> dict:
    if not _is_deployed():
        return NOT_DEPLOYED_ERROR
    return await asyncio.to_thread(_get_alert_policies_sync)


async def get_recent_deployments(limit: int = 5) -> dict:
    if not _is_deployed():
        return NOT_DEPLOYED_ERROR
    return await asyncio.to_thread(_get_recent_deployments_sync, limit)
