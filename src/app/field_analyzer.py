class FieldAnalyzer:

    def analyze(self, fields=None):
        print("Field Analyzer Loaded")

        if fields is None:
            return None

        analyzed = []

        for field in fields:
            if not isinstance(field, dict):
                continue

            item = dict(field)

            name = str(item.get("name", "")).lower()
            label = str(item.get("label", "")).lower()
            field_type = str(item.get("type", "")).lower()
            placeholder = str(item.get("placeholder", "")).lower()

            text = " ".join(
                [name, label, field_type, placeholder]
            )

            if any(
                word in text
                for word in ["name", "fullname", "full_name"]
            ):
                item["purpose"] = "name"

            elif any(
                word in text
                for word in ["email", "e-mail"]
            ):
                item["purpose"] = "email"

            elif any(
                word in text
                for word in ["mobile", "phone", "contact"]
            ):
                item["purpose"] = "phone"

            elif any(
                word in text
                for word in ["age", "dob", "birth"]
            ):
                item["purpose"] = "age"

            elif any(
                word in text
                for word in [
                    "address",
                    "city",
                    "state",
                    "pincode",
                    "zip"
                ]
            ):
                item["purpose"] = "address"

            elif any(
                word in text
                for word in ["country", "nation"]
            ):
                item["purpose"] = "country"

            else:
                item["purpose"] = "unknown"

            analyzed.append(item)

        return analyzed
