"""Compare a vacancy only with explicit structured criteria.

Free-text eligibility is not parsed and is never treated as an official
pass or fail. Missing or unclear criteria stay unknown.
"""


def assess_eligibility(vacancy, verified_profile):
    if not isinstance(vacancy, dict):
        return {
            "status": "unknown",
            "checks": [],
            "reason": "vacancy is missing",
        }

    criteria = vacancy.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        return {
            "status": "unknown",
            "checks": [],
            "reason": (
                "no explicit criteria; free-text eligibility is not a rule"
            ),
        }

    if not isinstance(verified_profile, dict):
        return {
            "status": "unknown",
            "checks": [],
            "reason": "verified profile is missing",
        }

    checks = []
    for rule in criteria:
        if (
            not isinstance(rule, dict)
            or not str(rule.get("field") or "").strip()
            or "equals" not in rule
        ):
            return {
                "status": "unknown",
                "checks": [],
                "reason": "a criterion is not explicit",
            }
        field = str(rule["field"]).strip()
        actual = verified_profile.get(field)
        if actual is None or str(actual).strip() == "":
            checks.append({"field": field, "status": "unknown"})
            continue
        expected = str(rule["equals"]).strip().lower()
        status = (
            "met"
            if str(actual).strip().lower() == expected
            else "not_met"
        )
        checks.append({"field": field, "status": status})

    if any(item["status"] == "unknown" for item in checks):
        overall = "unknown"
    elif any(item["status"] == "not_met" for item in checks):
        overall = "not_met"
    else:
        overall = "met"
    return {
        "status": overall,
        "checks": checks,
        "reason": "compared only with explicit criteria",
    }
