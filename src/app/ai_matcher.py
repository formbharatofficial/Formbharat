class AIMatcher:
    """
    Safe local AI-style field matcher.

    Purpose:
    - Form field label/name ko samajhna
    - Profile field ka purpose identify karna
    - OTP/CAPTCHA ko block karna
    - Related-person fields ko user's own name se match na karna

    This module NEVER:
    - handles OTP
    - solves CAPTCHA
    - submits forms
    """

    BLOCKED_TERMS = (
        "otp",
        "one time password",
        "one_time_password",
        "captcha",
        "verification code",
        "verification_code",
        "security code",
        "security_code",
    )

    RELATED_PERSON_TERMS = (
        "father",
        "father name",
        "father_name",
        "mother",
        "mother name",
        "mother_name",
        "guardian",
        "guardian name",
        "guardian_name",
        "husband",
        "husband name",
        "husband_name",
        "wife",
        "wife name",
        "wife_name",
        "spouse",
        "spouse name",
        "spouse_name",
    )

    FIELD_PATTERNS = {
        "name": (
            "candidate name",
            "candidate_name",
            "applicant name",
            "applicant_name",
            "full name",
            "full_name",
            "candidate fullname",
            "applicant fullname",
        ),
        "email": (
            "email",
            "e-mail",
            "email id",
            "email_id",
            "mail id",
            "mail_id",
        ),
        "mobile": (
            "mobile",
            "mobile number",
            "mobile_number",
            "phone",
            "phone number",
            "phone_number",
            "contact number",
            "contact_number",
        ),
        "dob": (
            "date of birth",
            "date_of_birth",
            "dob",
            "birth date",
            "birth_date",
            "birthdate",
        ),
        "address": (
            "address",
            "residential address",
            "permanent address",
            "present address",
            "postal address",
        ),
        "country": (
            "country",
            "nationality",
            "nation",
        ),
    }

    def _normalize(self, text):
        return (
            str(text or "")
            .lower()
            .strip()
            .replace("-", " ")
            .replace("_", " ")
        )

    def match(self, label):
        """
        Returns a safe classification for a form field.

        Example:
            match("Candidate Name")
            -> {
                "purpose": "name",
                "confidence": "high",
                "blocked": False
            }
        """

        text = self._normalize(label)

        if not text:
            return {
                "purpose": "unknown",
                "confidence": "low",
                "blocked": False,
            }

        # OTP / CAPTCHA must always be blocked.
        for term in self.BLOCKED_TERMS:
            if self._normalize(term) in text:
                return {
                    "purpose": "blocked",
                    "confidence": "high",
                    "blocked": True,
                    "reason": "otp_or_captcha",
                }

        # Fields belonging to another person must not use
        # the user's own profile name.
        for term in self.RELATED_PERSON_TERMS:
            if self._normalize(term) in text:
                return {
                    "purpose": "blocked",
                    "confidence": "high",
                    "blocked": True,
                    "reason": "related_person",
                }

        # Exact / phrase based classification.
        for purpose, patterns in self.FIELD_PATTERNS.items():
            for pattern in patterns:
                if self._normalize(pattern) in text:
                    return {
                        "purpose": purpose,
                        "confidence": "high",
                        "blocked": False,
                    }

        return {
            "purpose": "unknown",
            "confidence": "low",
            "blocked": False,
        }
