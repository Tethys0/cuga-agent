"""Policy and public projections for manual Evolve retention."""

from __future__ import annotations

from typing import Any

DEFAULT_RETENTION_POLICY: dict[str, Any] = {
    "rules": [
        {
            "name": "unused-guidelines",
            "entity_type": "guideline",
            "max_unused_days": 180,
            "action": "delete",
            "on_missing_access_signal": "skip",
        },
        {
            "name": "stale-guidelines",
            "entity_type": "guideline",
            "max_age_days": 90,
            "action": "flag",
        },
        {
            "name": "old-sessions",
            "entity_type": "trajectory",
            "max_age_days": 365,
            "action": "delete",
            "cascade_derived": True,
        },
    ]
}

_REPORT_FIELDS = {
    "as_of",
    "completed_at",
    "dry_run",
    "run_id",
    "started_at",
}
_REPORT_ITEM_FIELDS = {
    "action",
    "created_at",
    "entity_id",
    "entity_type",
    "outcome",
}


def sanitize_retention_report(report: dict[str, Any]) -> dict[str, Any]:
    """Remove memory content, ownership data, policy internals, and provider details."""
    sanitized = {key: report[key] for key in _REPORT_FIELDS if key in report}
    errors = report.get("errors")
    warnings = report.get("warnings")
    sanitized["error_count"] = len(errors) if isinstance(errors, list) else int(bool(errors))
    sanitized["warning_count"] = len(warnings) if isinstance(warnings, list) else int(bool(warnings))
    for bucket in ("flagged", "deleted", "skipped"):
        sanitized[bucket] = [
            {
                key: value
                for key, value in item.items()
                if key in _REPORT_ITEM_FIELDS and isinstance(value, (str, int, float, bool, type(None)))
            }
            for item in report.get(bucket, [])
            if isinstance(item, dict)
        ]
    return sanitized


def project_retention_report(report: dict[str, Any]) -> dict[str, Any]:
    buckets = {
        bucket: [
            {key: item[key] for key in ("entity_id", "action", "outcome") if key in item}
            for item in report.get(bucket, [])
            if isinstance(item, dict)
        ]
        for bucket in ("flagged", "deleted", "skipped")
    }
    return {
        **{key: report[key] for key in ("run_id", "started_at", "completed_at", "dry_run") if key in report},
        **buckets,
        "summary": (
            f"Retention found {len(buckets['flagged'])} for review, "
            f"{len(buckets['deleted'])} deletion matches, and "
            f"{len(buckets['skipped'])} skipped."
        ),
        "errors": ["One or more memories could not be evaluated."] if report.get("error_count") else [],
        "warnings": ["Some memories were evaluated with incomplete usage data."]
        if report.get("warning_count")
        else [],
    }


def retention_capabilities(*, retention_available: bool) -> dict[str, Any]:
    return {
        "retention_available": retention_available,
        "scheduling_supported": False,
        "schedule": {
            "state": "unavailable",
            "label": "Scheduled retention is unavailable",
        },
        "rules": [
            {
                "name": rule["name"],
                "entity_type": rule["entity_type"],
                "action": rule["action"],
                **(
                    {"max_unused_days": rule["max_unused_days"]}
                    if "max_unused_days" in rule
                    else {"max_age_days": rule["max_age_days"]}
                ),
            }
            for rule in DEFAULT_RETENTION_POLICY["rules"]
        ],
    }


def project_compliance_status(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "healthy": bool(result.get("healthy")),
        "evolve_version": result.get("evolve_version"),
        "backend": result.get("backend"),
        "retention_available": bool(result.get("retention_available")),
        "scheduling_supported": False,
        "plugins": [
            {key: plugin.get(key) for key in ("name", "protection_class", "hooks", "enabled", "healthy")}
            for plugin in result.get("plugins", [])
            if isinstance(plugin, dict)
        ],
    }
