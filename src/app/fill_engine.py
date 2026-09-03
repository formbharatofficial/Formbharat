from bs4 import BeautifulSoup


def fill_form(html, matched_fields):
    """
    Matched profile values ko HTML form fields me fill karta hai.

    OTP, CAPTCHA aur final submit ko touch nahi karta.
    """

    if not isinstance(html, str):
        raise ValueError("html must be a string")

    if not isinstance(matched_fields, list):
        raise ValueError("matched_fields must be a list")

    soup = BeautifulSoup(html, "html.parser")

    filled = []
    skipped = []

    for field in matched_fields:

        if not isinstance(field, dict):
            continue

        if field.get("matched") is not True:
            skipped.append({
                "field": field.get("name") or field.get("id"),
                "reason": "not matched"
            })
            continue

        field_name = str(field.get("name") or "").strip()
        field_id = str(field.get("id") or "").strip()
        value = field.get("profile_value")

        if value is None:
            skipped.append({
                "field": field_name or field_id,
                "reason": "empty profile value"
            })
            continue

        tag = None

        if field_id:
            tag = soup.find(id=field_id)

        if tag is None and field_name:
            tag = soup.find(
                ["input", "textarea", "select"],
                attrs={"name": field_name}
            )

        if tag is None:
            skipped.append({
                "field": field_name or field_id,
                "reason": "HTML field not found"
            })
            continue

        tag_name = tag.name.lower()

        # ------------------------------------------
        # SELECT
        # ------------------------------------------

        if tag_name == "select":

            for option in tag.find_all("option"):
                option_value = option.get("value", "")

                if str(option_value) == str(value):
                    option["selected"] = True
                else:
                    option.attrs.pop("selected", None)

        # ------------------------------------------
        # CHECKBOX / RADIO
        # ------------------------------------------

        elif tag_name == "input" and tag.get("type", "").lower() in (
            "checkbox",
            "radio"
        ):

            if str(value).lower() in (
                "true",
                "1",
                "yes",
                "on"
            ):
                tag["checked"] = True
            else:
                tag.attrs.pop("checked", None)

        # ------------------------------------------
        # NORMAL INPUT / TEXTAREA
        # ------------------------------------------

        else:
            tag["value"] = str(value)

            if tag_name == "textarea":
                tag.clear()
                tag.append(str(value))

        filled.append({
            "field": field_name or field_id,
            "profile_key": field.get("profile_key"),
            "value": value
        })

    return {
        "html": str(soup),
        "filled": filled,
        "skipped": skipped,
        "filled_count": len(filled),
        "skipped_count": len(skipped)
    }
