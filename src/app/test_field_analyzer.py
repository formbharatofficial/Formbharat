from field_analyzer import FieldAnalyzer


def test_name():
    fields = [{"name": "full_name", "label": "Full Name", "type": "text"}]

    result = FieldAnalyzer().analyze(fields)

    assert result[0]["purpose"] == "name"


def test_email():
    fields = [{"name": "email", "label": "Email Address", "type": "email"}]

    result = FieldAnalyzer().analyze(fields)

    assert result[0]["purpose"] == "email"


def test_phone():
    fields = [{"name": "mobile", "label": "Mobile Number", "type": "tel"}]

    result = FieldAnalyzer().analyze(fields)

    assert result[0]["purpose"] == "phone"


def test_age():
    fields = [{"name": "age", "label": "Age", "type": "number"}]

    result = FieldAnalyzer().analyze(fields)

    assert result[0]["purpose"] == "age"


def test_address():
    fields = [{"name": "city", "label": "City", "type": "text"}]

    result = FieldAnalyzer().analyze(fields)

    assert result[0]["purpose"] == "address"


def test_country():
    fields = [{"name": "country", "label": "Country", "type": "select"}]

    result = FieldAnalyzer().analyze(fields)

    assert result[0]["purpose"] == "country"


def test_unknown():
    fields = [{"name": "favorite_color", "label": "Favorite Color", "type": "text"}]

    result = FieldAnalyzer().analyze(fields)

    assert result[0]["purpose"] == "unknown"
