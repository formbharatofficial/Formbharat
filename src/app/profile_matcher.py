def match_profile_to_fields(fields, profile):
    """
    Form fields ko saved user profile se safely match karta hai.

    Goal:
    - High-confidence fields automatically match hon.
    - Father/mother fields only match their dedicated saved profile values.
    - Other related-name fields never match the user's profile.
    - OTP/CAPTCHA ko kabhi automatically match na kare.
    """

    aliases = {
        "name": [
            "name",
            "fullname",
            "full_name",
            "candidate_name",
            "candidate_full_name",
            "applicant_name",
            "applicant_full_name"
        ],

        "father_name": [
            "father_name",
            "fathername",
        ],

        "mother_name": [
            "mother_name",
            "mothername",
        ],

        "email": [
            "email",
            "email_id", "mail_id",
            "emailid",
            "mail"
        ],

        "mobile": [
            "mobile",
            "mobile_number",
            "phone",
            "phone_number",
            "contact",
            "contact_number"
        ],

        "dob": [
            "dob",
            "date_of_birth",
            "birth_date",
            "datebirth",
            "birthdate"
        ],

        "address": [
            "address",
            "residential_address",
            "postal_address",
            "permanent_address",
            "present_address"
        ],

        "country": [
            "country",
            "nationality"
        ]
    }

    # Fields which must NEVER be automatically matched.
    blocked_terms = [
        "otp",
        "one_time_password",
        "captcha",
        "verification_code",
        "security_code"
    ]

    # Name-like fields which belong to another person.
    related_name_terms = [
        "guardian",
        "guardian_name",
        "guardianname",
        "husband",
        "husband_name",
        "husbandname",
        "spouse",
        "spouse_name",
        "spousename"
    ]

    result = []

    for field in fields:

        item = dict(field)

        raw_id = str(
            item.get("id")
            or item.get("name")
            or ""
        )

        raw_name = str(item.get("name") or "")
        raw_label = str(item.get("label") or "")

        field_id = (
            raw_id
            .lower()
            .strip()
            .replace("-", "_")
            .replace(" ", "_")
        )

        name = (
            raw_name
            .lower()
            .strip()
            .replace("-", "_")
            .replace(" ", "_")
        )

        label = (
            raw_label
            .lower()
            .strip()
            .replace("-", "_")
            .replace(" ", "_")
        )

        combined = " ".join([
            field_id,
            name,
            label
        ])

        # --------------------------------------------------
        # SAFETY BLOCK: OTP / CAPTCHA
        # --------------------------------------------------

        if any(term in combined for term in blocked_terms):

            item["profile_key"] = None
            item["profile_value"] = None
            item["matched"] = False
            item["match_confidence"] = "blocked"

            result.append(item)
            continue
        # SAFETY BLOCK: OTHER RELATED PERSON'S NAME
        #
        # father_name and mother_name are deliberately not included here.
        # They can only match their same-named, explicit profile values via
        # the aliases above; they can never fall back to the user's name.

        # --------------------------------------------------
        # SAFETY BLOCK: OTHER PERSON'S NAME
        # --------------------------------------------------

        if any(term in combined for term in related_name_terms):

            item["profile_key"] = None
            item["profile_value"] = None
            item["matched"] = False
            item["match_confidence"] = "blocked"

            result.append(item)
            continue

        matched_key = None
        match_confidence = "low"

        # --------------------------------------------------
        # EXACT MATCH
        # --------------------------------------------------

        for profile_key, names in aliases.items():

            if (
                field_id in names
                or name in names
                or label in names
            ):
                matched_key = profile_key
                match_confidence = "high"
                break

        # --------------------------------------------------
        # SAFE FALLBACK MATCH
        # --------------------------------------------------

        if matched_key is None:

            normalized_values = {
                "name": [
                    "candidate name",
                    "applicant name",
                    "full name",
                    "candidate full name"
                ],
                "email": [
                    "email address"
                ],
                "mobile": [
                    "mobile number",
                    "phone number",
                    "contact number"
                ],
                "dob": [
                    "date of birth",
                    "birth date"
                ],
                "address": [
                    "permanent address",
                    "residential address",
                    "present address"
                ],
                "country": [
                    "nationality"
                ]
            }

            for profile_key, phrases in normalized_values.items():

                if any(
                    phrase in combined
                    for phrase in phrases
                ):
                    matched_key = profile_key
                    match_confidence = "medium"
                    break

        # --------------------------------------------------
        # APPLY PROFILE VALUE
        # --------------------------------------------------

        if (
            matched_key
            and isinstance(profile, dict)
            and profile.get(matched_key) not in (None, "")
        ):

            item["profile_key"] = matched_key
            item["profile_value"] = profile.get(matched_key)
            item["matched"] = True
            item["match_confidence"] = match_confidence

        else:

            item["profile_key"] = None
            item["profile_value"] = None
            item["matched"] = False
            item["match_confidence"] = "low"

        result.append(item)

    return result
