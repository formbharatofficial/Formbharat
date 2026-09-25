from form_reader import FormReader

def test_input_value():
    reader = FormReader()

    html = """
    <form>
        <label for="username">Username</label>
        <input id="username" name="username" type="text"
               value="bharat" placeholder="Enter username">
    </form>
    """

    result = reader.read(html)

    assert len(result) == 1
    assert result[0]["name"] == "username"
    assert result[0]["id"] == "username"
    assert result[0]["type"] == "text"
    assert result[0]["placeholder"] == "Enter username"
    assert result[0]["value"] == "bharat"
    assert result[0]["label"] == "Username"

def test_select_options():
    reader = FormReader()

    html = """
    <form>
        <label for="country">Country</label>
        <select id="country" name="country">
            <option value="in">India</option>
            <option value="us">USA</option>
        </select>
    </form>
    """

    result = reader.read(html)

    assert len(result) == 1
    assert result[0]["name"] == "country"
    assert result[0]["id"] == "country"
    assert result[0]["label"] == "Country"

def test_select_option_values():
    reader = FormReader()

    html = """
    <form>
        <label for="country">Country</label>
        <select id="country" name="country">
            <option value="in">India</option>
            <option value="us">USA</option>
        </select>
    </form>
    """

    result = reader.read(html)

    assert result[0]["options"] == [
    {"value": "in", "label": "India", "selected": False},
    {"value": "us", "label": "USA", "selected": False},
]

def test_checkbox_and_radio():
    reader = FormReader()

    html = """
    <form>
        <label for="agree">I Agree</label>
        <input id="agree" name="agree" type="checkbox">

        <label for="gender">Male</label>
        <input id="gender" name="gender" type="radio" value="male">
    </form>
    """

    result = reader.read(html)

    assert len(result) == 2

    assert result[0]["name"] == "agree"
    assert result[0]["id"] == "agree"
    assert result[0]["type"] == "checkbox"
    assert result[0]["label"] == "I Agree"

    assert result[1]["name"] == "gender"
    assert result[1]["id"] == "gender"
    assert result[1]["type"] == "radio"
    assert result[1]["label"] == "Male"

def test_checked_and_selected():
    reader = FormReader()

    html = """
    <form>
        <input name="agree" type="checkbox" checked>
        
        <select name="country">
            <option value="in" selected>India</option>
            <option value="us">USA</option>
        </select>
    </form>
    """

    result = reader.read(html)

    assert result[0]["checked"] is True

    assert result[1]["options"][0]["selected"] is True
    assert result[1]["options"][1]["selected"] is False

def test_disabled():
    reader = FormReader()

    html = """
    <form>
        <input name="username" type="text" disabled>
        <select name="country" disabled>
            <option value="in">India</option>
        </select>
    </form>
    """

    result = reader.read(html)

    assert result[0]["disabled"] is True
    assert result[1]["disabled"] is True


def test_form_structure_keeps_fields_with_their_form():
    reader = FormReader()

    html = """
    <form id="basic" action="/basic" method="post">
        <label for="full_name">Full Name</label>
        <input id="full_name" name="full_name" type="text" required>
        <button type="submit">Submit</button>
    </form>
    <form id="contact" action="/contact" method="get">
        <label for="email">Email</label>
        <input id="email" name="email" type="email">
    </form>
    <input id="loose" name="loose" type="text">
    """

    structure = reader.read_structure(html)

    assert len(structure["forms"]) == 2
    assert structure["forms"][0]["action"] == "/basic"
    assert structure["forms"][0]["method"] == "post"
    assert structure["forms"][0]["submit_control"] == "user"
    assert structure["forms"][0]["user_controls"][0]["type"] == "submit"
    assert structure["forms"][0]["user_controls"][0]["control"] == "user"
    assert structure["forms"][0]["user_controls"][0]["label"] == "Submit"
    assert [field["name"] for field in structure["forms"][0]["fields"]] == ["full_name"]
    assert structure["forms"][0]["fields"][0]["required"] is True
    assert [field["name"] for field in structure["forms"][1]["fields"]] == ["email"]
    assert structure["forms"][1]["fields"][0]["required"] is False
    assert [field["name"] for field in structure["unattached_fields"]] == ["loose"]
    assert all(
        field["type"] != "submit"
        for form in structure["forms"]
        for field in form["fields"]
    )


def test_fieldset_legend_is_kept_without_changing_the_field():
    reader = FormReader()

    html = """
    <form>
        <fieldset>
            <legend>Father Details</legend>
            <label for="person_name">Name</label>
            <input id="person_name" name="person_name" type="text">
        </fieldset>
        <input type="reset" value="Reset">
        <input type="file" id="marksheet" name="marksheet">
    </form>
    """

    result = reader.read(html)

    assert result[0]["legend"] == "Father Details"
    assert result[0]["name"] == "person_name"
    assert result[1]["type"] == "file"
    structure = reader.read_structure(html)
    assert structure["forms"][0]["user_controls"][0]["type"] == "reset"
    assert structure["forms"][0]["user_controls"][0]["control"] == "user"
