class FormBharatAI:

    def about(self):
        print("Welcome to FormBharat AI")
        print("AI will help fill forms")
        print("OTP user dalega")
        print("CAPTCHA user dalega")
        print("Final Submit user karega")

    def analyze(self, fields):
        print("AI analyzing fields")
        return fields

    def match_fields(self, fields, profile):
        """
        Match analyzed form fields with user's saved profile.

        This function only prepares the mapping.
        It does NOT submit the form, handle OTP, or solve CAPTCHA.
        """

        if fields is None:
            return []

        if profile is None:
            profile = {}

        matched = []

        for field in fields:

            if not isinstance(field, dict):
                continue

            item = dict(field)

            purpose = str(
                item.get("purpose", "")
            ).lower()

            mapping = {
                "name": "name",
                "email": "email",
                "phone": "phone",
                "age": "dob",
                "address": "address",
                "country": "country",
            }

            profile_key = mapping.get(purpose)

            item["profile_key"] = profile_key

            if profile_key and profile_key in profile:
                item["profile_value"] = profile[profile_key]
                item["matched"] = True
                item["confidence"] = "high"
            else:
                item["profile_value"] = None
                item["matched"] = False
                item["confidence"] = "low"

            matched.append(item)

        return matched


ai = FormBharatAI()
ai.about()
