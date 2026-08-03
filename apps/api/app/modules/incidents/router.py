from fastapi import APIRouter, Depends

from app.modules.enterprise.router import require_owner
from app.modules.incidents import service
from app.modules.incidents.schemas import IncidentStatus

router = APIRouter(prefix="/incidents", tags=["incidents"])


# Owner-only: this is the platform's OWN operational data (error logs, alert
# state, deploy history), not org-scoped customer data — a regular member,
# or in a real multi-tenant product a random customer, has no business
# seeing another operator's infra internals. require_owner is the closest
# fit that already exists in this codebase; a real many-tenant product would
# need a genuine platform-admin role, separate from any customer's own org
# ownership, which this project doesn't have yet (see analytics' org
# endpoint for the same borrowed pattern).
@router.get("/status", response_model=IncidentStatus)
async def get_status(current_user=Depends(require_owner)):
    recent_errors = await service.get_recent_errors(minutes=60)
    alert_policies = await service.get_alert_policies()
    recent_deployments = await service.get_recent_deployments(limit=5)
    return IncidentStatus(
        recent_errors=recent_errors,
        alert_policies=alert_policies,
        recent_deployments=recent_deployments,
    )
