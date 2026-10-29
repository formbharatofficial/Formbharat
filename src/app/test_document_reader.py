from app.document_reader import read_document_text
from app.document_vault import build_extracted_data


AADHAAR = """
Government of India
आधार
नाम
Asha Singh
जन्म तिथि
01/01/1990
Female
1234 5678 9012
"""

PAN = """
INCOME TAX DEPARTMENT
Permanent Account Number
ABCDE1234F
Name
ASHA SINGH
Father's Name
RAM SINGH
Date of Birth
02/02/1991
"""

MARKSHEET = """
10th Marksheet
Name: Asha Singh
Roll No: 1234567
Year of Passing: 2016
"""


def test_aadhaar_lines_are_read_without_guessing_the_header():
    data = read_document_text(AADHAAR)

    assert data["document_kind"] == "aadhaar"
    assert data["name"] == "Asha Singh"
    assert data["dob"] == "01/01/1990"
    assert data["gender"] == "female"
    assert data["aadhaar_number"] == "123456789012"
    assert "Government" not in data["name"]


def test_pan_card_text_is_read():
    data = read_document_text(PAN)

    assert data["document_kind"] == "pan"
    assert data["name"] == "ASHA SINGH"
    assert data["father_name"] == "RAM SINGH"
    assert data["dob"] == "02/02/1991"
    assert data["pan_number"] == "ABCDE1234F"


def test_marksheet_roll_stays_with_the_class_it_names():
    data = read_document_text(MARKSHEET)

    assert data["document_kind"] == "marksheet"
    assert data["name"] == "Asha Singh"
    assert data["roll_number"] == "1234567"
    assert data["tenth_roll_number"] == "1234567"
    assert data["tenth_passing_year"] == "2016"
    assert "twelfth_roll_number" not in data


def test_old_labeled_lines_still_parse():
    data = build_extracted_data("Name: Asha\nFather: Ram\nDOB: 03/03/1992\nClass: 10")

    assert data["name"] == "Asha"
    assert data["father_name"] == "Ram"
    assert data["dob"] == "03/03/1992"
    assert data["class"] == "10"
    assert "Name: Asha" in data["raw_text"]


def test_empty_text_does_not_invent_fields():
    data = read_document_text("")

    assert data["name"] == ""
    assert data["dob"] == ""
    assert data["document_kind"] == "document"
    assert data["raw_text"] == ""
