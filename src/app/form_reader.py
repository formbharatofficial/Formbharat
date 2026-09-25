from bs4 import BeautifulSoup


def _user_controls(form):
    """Collect submit, button, and reset controls without treating them as data."""
    controls = []
    for tag in form.find_all(["input", "button"]):
        control_type = str(tag.get("type") or "").lower()
        if tag.name == "button":
            control_type = control_type or "submit"
        elif control_type not in {"submit", "button", "reset", "image"}:
            continue
        label = tag.get("value") or tag.get_text(strip=True)
        controls.append({
            "tag": tag.name,
            "type": control_type,
            "name": tag.get("name") or "",
            "id": tag.get("id") or "",
            "label": label,
            "control": "user",
        })
    return controls


class FormReader:

    def __init__(self):
        print("Form Reader Ready")

    def read(self, html):
        print("Reading HTML Form...")

        soup = BeautifulSoup(html, "html.parser")

        fields = []

        for tag in soup.find_all(["input", "textarea", "select"]):
            if str(tag.get("type") or "").lower() in {
                "submit", "button", "reset", "image"
            }:
                continue

            field = {
    "name": tag.get("name", ""),
    "id": tag.get("id", ""),
    "type": tag.get("type", ""),
    "placeholder": tag.get("placeholder", ""),
    "value": tag.get("value", ""),
"checked": tag.has_attr("checked"),
"disabled": tag.has_attr("disabled"),
"label": "",
"options": []
}

            if tag.name == "select":
                for option in tag.find_all("option"):
                    field["options"].append({
    "value": option.get("value", ""),
    "label": option.get_text(strip=True),
    "selected": option.has_attr("selected")
})

            if field["id"]:
                lbl = soup.find("label", attrs={"for": field["id"]})
                if lbl:
                    field["label"] = lbl.get_text(strip=True)

            if not field["label"]:
                field["label"] = field["name"]

            fieldset = tag.find_parent("fieldset")
            legend = ""
            if fieldset is not None:
                legend_tag = fieldset.find("legend")
                if legend_tag is not None:
                    legend = legend_tag.get_text(strip=True)
            field["legend"] = legend

            parent_form = tag.find_parent("form")
            forms = soup.find_all("form")
            if parent_form is None:
                field["form_index"] = None
                field["form_action"] = ""
                field["form_method"] = ""
            else:
                field["form_index"] = forms.index(parent_form)
                field["form_action"] = parent_form.get("action") or ""
                field["form_method"] = (
                    parent_form.get("method") or "get"
                ).lower()
            field["required"] = tag.has_attr("required")

            fields.append(field)

        return fields

    def read_structure(self, html):
        """Detect each form and the fields that belong to it.

        Submit controls stay outside the field list. Final submit is
        user-controlled and is not treated as data to understand or fill.
        """
        fields = self.read(html)
        soup = BeautifulSoup(html, "html.parser")
        forms = []

        for index, form in enumerate(soup.find_all("form")):
            forms.append({
                "form_index": index,
                "action": form.get("action") or "",
                "method": (form.get("method") or "get").lower(),
                "submit_control": "user",
                "user_controls": _user_controls(form),
                "fields": [
                    field for field in fields
                    if field.get("form_index") == index
                ],
            })

        return {
            "forms": forms,
            "unattached_fields": [
                field for field in fields
                if field.get("form_index") is None
            ],
        }
