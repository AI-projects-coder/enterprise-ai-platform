from pydantic import BaseModel


class IncidentStatus(BaseModel):
    recent_errors: dict
    alert_policies: dict
    recent_deployments: dict
