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
