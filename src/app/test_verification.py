from app.verification import verify_fields


def test_matching_fields_are_verified():
    result = verify_fields(
        {
            "name": "Sunil Kumar",
            "father_name": "Ajit Kumar",
            "dob": "20-06-1991",
        },
        {
            "name": "Sunil Kumar",
            "father_name": "Ajit Kumar",
            "dob": "20-06-1991",
        },
    )

    assert result["name"]["status"] == "verified"
    assert result["father_name"]["status"] == "verified"
    assert result["dob"]["status"] == "verified"
    assert result["name"]["source"] == "document"


def test_mismatched_field_needs_review():
    result = verify_fields(
        {"name": "Sunil Kumar"},
        {"name": "Sunil Singh"},
    )

    assert result["name"]["status"] == "needs_review"


def test_missing_document_field_is_unavailable():
    result = verify_fields(
        {"name": "Sunil Kumar"},
        {},
    )

    assert result["name"]["status"] == "unavailable"


def test_invalid_input_is_rejected():
    try:
        verify_fields([], {})
        assert False
    except ValueError:
        pass


def test_profile_documents_are_verified_only_for_selected_profile(monkeypatch, tmp_path):
    from app import profile, verification

    db = tmp_path / "formbharat.db"
    monkeypatch.setattr(profile, "DB_PATH", db)
    monkeypatch.setattr(verification, "DB_PATH", db)

    profile.save_profile({"name": "Sunil Kumar"}, profile_id=1)

    import sqlite3
    import json

    conn = sqlite3.connect(db)
    conn.execute(
        """
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER,
            doc_type TEXT NOT NULL,
            document_reference TEXT NOT NULL,
            extracted_data TEXT,
            verified INTEGER DEFAULT 0
        )
        """
    )
    conn.execute(
        "INSERT INTO documents "
        "(profile_id, doc_type, document_reference, extracted_data, verified) "
        "VALUES (?, ?, ?, ?, ?)",
        (1, "Aadhaar", "DOC-1", json.dumps({"name": "Sunil Kumar"}), 1),
    )
    conn.execute(
        "INSERT INTO documents "
        "(profile_id, doc_type, document_reference, extracted_data, verified) "
        "VALUES (?, ?, ?, ?, ?)",
        (2, "Aadhaar", "DOC-2", json.dumps({"name": "Wrong Profile"}), 1),
    )
    conn.commit()
    conn.close()

    result = verification.verify_profile_documents(
        profile.get_profile(1),
        profile_id=1,
        db_path=db,
    )

    assert result["profile_id"] == 1
    assert result["document_count"] == 1
    assert result["documents"][0]["fields"]["name"]["status"] == "verified"


def test_only_verified_fields_are_selected_for_promotion():
    from app.verification import verified_data_from_results

    results = {
        "name": {
            "profile_value": "Sunil Kumar",
            "document_value": "Sunil Kumar",
            "source": "document",
            "status": "verified",
        },
        "father_name": {
            "profile_value": "Ajit Kumar",
            "document_value": "Wrong Name",
            "source": "document",
            "status": "needs_review",
        },
        "dob": {
            "profile_value": "20-06-1991",
            "document_value": "",
            "source": "document",
            "status": "unavailable",
        },
    }

    verified = verified_data_from_results(results)

    assert verified == {"name": "Sunil Kumar"}
    assert "father_name" not in verified
    assert "dob" not in verified


def test_promotion_requires_no_unresolved_document_mismatch():
    from app.verification import can_promote_verified_profile

    verified_results = {
        "name": {"status": "verified"},
        "father_name": {"status": "unavailable"},
    }

    review_results = {
        "name": {"status": "verified"},
        "father_name": {"status": "needs_review"},
    }

    assert can_promote_verified_profile(verified_results) is True
    assert can_promote_verified_profile(review_results) is False


def test_promotion_requires_at_least_one_verified_field():
    from app.verification import can_promote_verified_profile

    unavailable_results = {
        "name": {"status": "unavailable"},
        "father_name": {"status": "unavailable"},
    }

    assert can_promote_verified_profile(unavailable_results) is False


def test_combined_field_results_block_on_any_document_mismatch():
    from app.verification import combined_field_results, can_promote_verified_profile

    combined = combined_field_results([
        {
            "fields": {
                "name": {
                    "status": "verified",
                    "document_value": "Sunil Kumar",
                },
            },
        },
        {
            "fields": {
                "name": {
                    "status": "needs_review",
                    "document_value": "Sunil Singh",
                },
            },
        },
    ])

    assert combined["name"]["status"] == "needs_review"
    assert can_promote_verified_profile(combined) is False


def test_combined_field_results_reject_unverified_documents():
    from app.verification import combined_field_results, can_promote_verified_profile

    unverified = combined_field_results([
        {
            "document_verified": False,
            "fields": {
                "name": {
                    "status": "verified",
                    "document_value": "Sunil Kumar",
                },
            },
        },
    ])

    assert "name" not in unverified
    assert can_promote_verified_profile(unverified) is False

    verified = combined_field_results([
        {
            "document_verified": True,
            "fields": {
                "name": {
                    "status": "verified",
                    "document_value": "Sunil Kumar",
                },
            },
        },
    ])

    assert verified["name"]["status"] == "verified"
    assert can_promote_verified_profile(verified) is True


def test_failed_processing_cannot_promote_even_when_document_is_marked_verified():
    from app.verification import combined_field_results, can_promote_verified_profile

    combined = combined_field_results([
        {
            "document_verified": True,
            "processing_status": "failed",
            "fields": {
                "name": {
                    "status": "verified",
                    "document_value": "Sunil Kumar",
                },
            },
        },
    ])

    assert "name" not in combined
    assert can_promote_verified_profile(combined) is False
