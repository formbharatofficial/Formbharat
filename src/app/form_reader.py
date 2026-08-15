from bs4 import BeautifulSoup

class FormReader:

    def __init__(self):
        print("Form Reader Ready")

    def read(self, html):
        print("Reading HTML Form...")

        soup = BeautifulSoup(html, "html.parser")

        fields = []

        for tag in soup.find_all(["input", "textarea", "select"]):
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

            fields.append(field)

        return fields
