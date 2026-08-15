def match_profile_to_fields(fields, profile):
    """
    Form fields ko saved user profile se match karta hai.
    Sirf confidently matched fields ko value deta hai.
    """

    aliases = {
        "name": ["name", "fullname", "full_name", "candidate_name", "applicant_name"],
        "email": ["email", "email_id", "emailid", "mail"],
        "mobile": ["mobile", "mobile_number", "phone", "phone_number", "contact"],
        "dob": ["dob", "date_of_birth", "birth_date", "datebirth"],
        "address": ["address", "residential_address", "postal_address"],
        "country": ["country", "nationality"]
    }

    result = []

    for field in fields:
        item = dict(field)

        field_id = str(
            item.get("id")
            or item.get("name")
            or item.get("label")
            or ""
        ).lower().strip().replace("-", "_").replace(" ", "_")

        label = str(item.get("label") or "").lower().strip()
        name = str(item.get("name") or "").lower().strip()

        matched_key = None

        for profile_key, names in aliases.items():
            if (
                field_id in names
                or name in names
                or label in names
            ):
                matched_key = profile_key
                break

        if matched_key and profile.get(matched_key) not in (None, ""):
            item["profile_key"] = matched_key
            item["profile_value"] = profile.get(matched_key)
            item["matched"] = True
            item["match_confidence"] = "high"
        else:
            item["profile_key"] = None
            item["profile_value"] = None
            item["matched"] = False
            item["match_confidence"] = "low"

        result.append(item)

    return result
