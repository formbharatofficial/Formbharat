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
        "guardian_name": [
            "guardian_name",
            "guardianname",
        ],

        "country": [
            "country"
        ],

        "nationality": [
            "nationality"
        ],

        "category": [
            "category",
            "caste"
        ],

        "pincode": [
            "pincode",
            "pin_code",
            "zip",
            "zipcode",
            "zip_code",
            "पिनकोड",
            "पिन_कोड",
        ],
        "name": [
            "name",
            "fullname",
            "full_name",
            "candidate_name",
            "candidate_full_name",
            "applicant_name",
            "applicant_full_name",
            "नाम",
            "पूरा_नाम",
            "आवेदक_का_नाम",
        ],
        "father_name": [
            "father_name",
            "fathername",
            "पिता",
            "पिता_का_नाम",
        ],
        "mother_name": [
            "mother_name",
            "mothername",
            "माता",
            "माता_का_नाम",
        ],
        "dob": [
            "dob",
            "date_of_birth",
            "birth_date",
            "datebirth",
            "birthdate",
            "जन्म_तिथि",
            "जन्म_की_तारीख",
        ],
        "mobile": [
            "mobile",
            "mobile_number",
            "phone",
            "phone_number",
            "contact",
            "contact_number",
            "मोबाइल",
            "मोबाइल_नंबर",
        ],
        "address": [
            "address",
            "residential_address",
            "postal_address",
            "permanent_address",
            "present_address",
            "पता",
        ],
        "email": [
            "email",
            "email_id",
            "mail_id",
            "emailid",
            "mail",
            "ईमेल",
        ],
        "gender": [
            "gender",
            "sex",
            "लिंग",
        ],
        "state": [
            "state",
            "राज्य",
        ],
        "district": [
            "district",
            "जिला",
        ],
        "tenth_roll_number": ["tenth_roll_number", "10th_roll_number", "10th_roll_no", "matric_roll_number"],
        "tenth_passing_year": ["tenth_passing_year", "10th_passing_year", "matric_year"],
        "tenth_marks": ["tenth_marks", "10th_marks"],
        "tenth_percentage": ["tenth_percentage", "10th_percentage"],
        "twelfth_roll_number": ["twelfth_roll_number", "12th_roll_number", "12th_roll_no"],
        "twelfth_passing_year": ["twelfth_passing_year", "12th_passing_year"],
        "twelfth_marks": ["twelfth_marks", "12th_marks"],
        "twelfth_percentage": ["twelfth_percentage", "12th_percentage"],
        "graduation_degree": ["graduation_degree", "graduation"],
        "graduation_roll_number": ["graduation_roll_number"],
        "graduation_passing_year": ["graduation_passing_year", "graduation_year"],
        "graduation_marks": ["graduation_marks"],
        "graduation_percentage": ["graduation_percentage"],
        "post_graduation_degree": ["post_graduation_degree"],
        "post_graduation_roll_number": ["post_graduation_roll_number"],
        "post_graduation_passing_year": ["post_graduation_passing_year"],
        "post_graduation_marks": ["post_graduation_marks"],
        "post_graduation_percentage": ["post_graduation_percentage"],
        "diploma_name": ["diploma_name"],
        "diploma_roll_number": ["diploma_roll_number"],
        "diploma_passing_year": ["diploma_passing_year"],
        "diploma_marks": ["diploma_marks"],
        "diploma_percentage": ["diploma_percentage"],
        "other_qualification": ["other_qualification"],
        "pan_number": [
            "pan",
            "pan_number",
            "pan_no",
            "pannumber",
            "permanent_account_number",
            "पैन",
            "पैन_नंबर",
            "पैन_नम्बर",
        ],
        "aadhaar_number": [
            "aadhaar",
            "aadhaar_number",
            "aadhaar_no",
            "aadhar",
            "aadhar_number",
            "aadhar_no",
            "आधार",
            "आधार_नंबर",
            "आधार_नम्बर",
        ],

        # age is intentionally absent so it cannot receive dob.
        # A generic education or qualification label is intentionally absent.
        # Tenth, twelfth, graduation, diploma, and other_qualification match
        # only their own saved value.
    }

    # Fields which must NEVER be automatically matched.
    blocked_terms = [
        "otp",
        "one_time_password",
        "captcha",
        "verification_code",
        "security_code",
        "password",
        "passwd",
    ]

    # Name-like fields which belong to another person.
    related_name_terms = [
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

        field_type = str(item.get("type") or "").lower()
        if field_type in {"password", "submit", "button", "reset", "image"} or any(
            term in combined for term in blocked_terms
        ):

            item["profile_key"] = None
            item["profile_value"] = None
            item["matched"] = False
            item["match_confidence"] = "blocked"

            result.append(item)
            continue
        # SAFETY BLOCK: OTHER RELATED PERSON'S NAME
        #
        # father_name, mother_name, and guardian_name are deliberately not
        # included here. Each matches only its own explicit profile value.
        # An empty guardian, or one equal to the applicant name, is not used.

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
                ]
            }

            for profile_key, phrases in normalized_values.items():

                if any(
                    phrase.replace(" ", "_") in combined
                    for phrase in phrases
                ):
                    matched_key = profile_key
                    match_confidence = "medium"
                    break

        # --------------------------------------------------
        # APPLY PROFILE VALUE
        # --------------------------------------------------

        if matched_key == "guardian_name" and isinstance(profile, dict):
            guardian_value = str(profile.get("guardian_name") or "").strip()
            applicant_name = str(profile.get("name") or "").strip()
            same_person = (
                guardian_value
                and applicant_name
                and guardian_value.casefold() == applicant_name.casefold()
            )
            if not guardian_value or same_person:
                item["profile_key"] = "guardian_name"
                item["profile_value"] = None
                item["matched"] = False
                item["match_confidence"] = (
                    "blocked" if same_person else "low"
                )
                result.append(item)
                continue

        if (
            matched_key
            and match_confidence == "high"
            and isinstance(profile, dict)
            and profile.get(matched_key) not in (None, "")
        ):

            item["profile_key"] = matched_key
            item["profile_value"] = profile.get(matched_key)
            item["matched"] = True
            item["match_confidence"] = match_confidence

        elif matched_key and match_confidence != "high":
            # Phrase-level understanding is kept, but medium or uncertain
            # confidence must not supply a value for silent auto-fill.
            item["profile_key"] = matched_key
            item["profile_value"] = None
            item["matched"] = False
            item["match_confidence"] = match_confidence

        else:

            item["profile_key"] = None
            item["profile_value"] = None
            item["matched"] = False
            item["match_confidence"] = "low"

        result.append(item)

    return result
