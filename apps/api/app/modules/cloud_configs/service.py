import io
import uuid

import hcl2
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.modules.cloud_configs.models import CloudConfig

# Terraform (.tf, HCL2) only for v1 — the most common IaC format; CloudFormation
# and Kubernetes manifests have different-enough resource models that
# supporting them would mean a second parser and a second set of checks,
# better scoped as its own future addition than force-fit here.
MAX_CONFIG_SIZE = 2 * 1024 * 1024

SENSITIVE_ATTRIBUTE_KEYWORDS = ("password", "secret", "token", "api_key", "apikey")
BROAD_IAM_ROLES = {"roles/owner", "roles/editor"}
OPEN_CIDR = "0.0.0.0/0"

# Deliberately rough, illustrative-only monthly estimates for common GCP
# resource types — this app never touches real billing data (advisory-only,
# no cloud credentials, per the architecture decision for this phase), so
# this is a flat heuristic lookup, not a real cost calculation. Every tool
# result built from this says so explicitly.
COST_ESTIMATES_USD = {
    "google_compute_instance": 25.0,
    "google_sql_database_instance": 50.0,
    "google_storage_bucket": 1.0,
    "google_cloud_run_service": 5.0,
    "google_container_cluster": 75.0,
    "google_redis_instance": 35.0,
    "google_compute_firewall": 0.0,
    "google_project_iam_member": 0.0,
    "google_sql_user": 0.0,
}
DEFAULT_ESTIMATE_USD = 5.0


def _clean_scalar(raw):
    if isinstance(raw, str) and raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
        return raw[1:-1]
    return raw


def _is_hardcoded_literal(raw) -> bool:
    return isinstance(raw, str) and raw.startswith('"') and raw.endswith('"')


def _parse_terraform(content: bytes) -> list[dict]:
    """Each returned resource carries both raw_attributes (hcl2's original
    values, still quote-wrapped for literals or "${...}" for references) and
    attributes (cleaned, human-readable) — the security checks need the raw
    form to tell a hardcoded literal apart from a variable reference, which
    is lost once both are stripped down to plain strings."""
    try:
        text = content.decode("utf-8")
        parsed = hcl2.load(io.StringIO(text))
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Could not parse Terraform file: {exc}") from exc

    resources = []
    for block in parsed.get("resource", []):
        for raw_type, named in block.items():
            resource_type = _clean_scalar(raw_type)
            for raw_name, raw_attrs in named.items():
                resource_name = _clean_scalar(raw_name)
                raw_attributes = {}
                attributes = {}
                for key, value in raw_attrs.items():
                    if key == "__is_block__":
                        continue
                    if isinstance(value, list) and value and isinstance(value[0], dict):
                        continue  # nested block (e.g. `allow { ... }`) — not needed for these checks
                    raw_attributes[key] = value
                    if isinstance(value, list):
                        attributes[key] = [_clean_scalar(v) for v in value]
                    else:
                        attributes[key] = _clean_scalar(value)
                resources.append(
                    {
                        "type": resource_type,
                        "name": resource_name,
                        "raw_attributes": raw_attributes,
                        "attributes": attributes,
                    }
                )
    return resources


async def create_cloud_config(db: AsyncSession, user_id: uuid.UUID, title: str, content: bytes) -> CloudConfig:
    resources = _parse_terraform(content)
    type_counts: dict[str, int] = {}
    for r in resources:
        type_counts[r["type"]] = type_counts.get(r["type"], 0) + 1
    resource_types = [{"type": t, "count": c} for t, c in type_counts.items()]

    config = CloudConfig(
        user_id=user_id,
        title=title,
        storage_ref="",
        resource_count=len(resources),
        resource_types=resource_types,
    )
    db.add(config)
    await db.flush()  # assigns config.id before it's needed as the storage key

    config.storage_ref = await storage.save(config.id, content, "text/plain", folder="cloud_configs")
    await db.commit()
    await db.refresh(config)
    return config


async def list_cloud_configs(db: AsyncSession, user_id: uuid.UUID) -> list[CloudConfig]:
    result = await db.scalars(
        select(CloudConfig).where(CloudConfig.user_id == user_id).order_by(CloudConfig.created_at.desc())
    )
    return list(result)


async def _get_owned_config(db: AsyncSession, user_id: uuid.UUID, config_id: uuid.UUID) -> CloudConfig | None:
    result = await db.scalars(
        select(CloudConfig).where(CloudConfig.id == config_id, CloudConfig.user_id == user_id)
    )
    return result.first()


async def _load_resources(db: AsyncSession, user_id: uuid.UUID, config_id: uuid.UUID):
    config = await _get_owned_config(db, user_id, config_id)
    if config is None:
        return None, {"error": "Cloud config not found"}
    content = await storage.load(config.storage_ref)
    return _parse_terraform(content), None


async def list_cloud_configs_for_agent(db: AsyncSession, user_id: uuid.UUID) -> dict:
    configs = await list_cloud_configs(db, user_id)
    return {
        "cloud_configs": [
            {
                "id": str(c.id),
                "title": c.title,
                "resource_count": c.resource_count,
                "resource_types": c.resource_types,
            }
            for c in configs
        ]
    }


async def list_resources(db: AsyncSession, user_id: uuid.UUID, config_id: uuid.UUID) -> dict:
    resources, error = await _load_resources(db, user_id, config_id)
    if error:
        return error
    return {
        "resources": [{"type": r["type"], "name": r["name"], "attributes": r["attributes"]} for r in resources]
    }


async def check_security_issues(db: AsyncSession, user_id: uuid.UUID, config_id: uuid.UUID) -> dict:
    resources, error = await _load_resources(db, user_id, config_id)
    if error:
        return error

    findings = []
    for r in resources:
        label = f'{r["type"]}.{r["name"]}'

        for key, raw_value in r["raw_attributes"].items():
            if any(kw in key.lower() for kw in SENSITIVE_ATTRIBUTE_KEYWORDS) and _is_hardcoded_literal(raw_value):
                findings.append(
                    {
                        "severity": "high",
                        "resource": label,
                        "issue": f"Attribute '{key}' looks like a hardcoded secret (a literal value, not a "
                        f"variable reference) — move it to a Terraform variable or a secret manager instead.",
                    }
                )

        for key, value in r["attributes"].items():
            values = value if isinstance(value, list) else [value]
            if ("cidr" in key.lower() or "range" in key.lower()) and OPEN_CIDR in values:
                findings.append(
                    {
                        "severity": "high",
                        "resource": label,
                        "issue": f"Attribute '{key}' allows {OPEN_CIDR} — open to the entire internet.",
                    }
                )

        role = r["attributes"].get("role")
        if role in BROAD_IAM_ROLES:
            findings.append(
                {
                    "severity": "medium",
                    "resource": label,
                    "issue": f"Grants the broad '{role}' role — prefer a narrower, least-privilege role.",
                }
            )

    return {"issue_count": len(findings), "findings": findings}


async def estimate_monthly_cost(db: AsyncSession, user_id: uuid.UUID, config_id: uuid.UUID) -> dict:
    resources, error = await _load_resources(db, user_id, config_id)
    if error:
        return error

    itemized = []
    total = 0.0
    for r in resources:
        estimate = COST_ESTIMATES_USD.get(r["type"], DEFAULT_ESTIMATE_USD)
        total += estimate
        itemized.append({"resource": f'{r["type"]}.{r["name"]}', "estimated_monthly_usd": estimate})

    return {
        "itemized": itemized,
        "total_estimated_monthly_usd": round(total, 2),
        "disclaimer": (
            "Rough, illustrative estimate from a flat per-resource-type lookup table — not real cloud "
            "billing data. This app has no cloud credentials and makes no calls to any billing API."
        ),
    }
