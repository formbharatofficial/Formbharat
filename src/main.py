from flask import Flask, request, render_template_string, jsonify

# Optional FormBharat modules
try:
    from app.profile_ui import register_profile_ui
except Exception:
    register_profile_ui = None

try:
    from app.form_reader import FormReader
except Exception:
    FormReader = None

try:
    from app.field_analyzer import FieldAnalyzer
except Exception:
    FieldAnalyzer = None

try:
    from app.profile_matcher import match_profile_to_fields
except Exception:
    match_profile_to_fields = None

try:
    from app.fill_engine import fill_form
except Exception:
    fill_form = None

try:
    from app.form_reader import FormReader
except Exception:
    FormReader = None

try:
    from app.field_analyzer import FieldAnalyzer
except Exception:
    FieldAnalyzer = None

try:
    from app.ai_matcher import AIMatcher
except Exception:
    AIMatcher = None

try:
    from app.ai_engine import FormBharatAI
except Exception:
    FormBharatAI = None


app = Flask(__name__)

# --------------------------------------------------
# Phase 4 Vacancy
# Vacancy Data Foundation APIs
# --------------------------------------------------

from app.vacancy import (
    init_vacancy_db,
    create_vacancy,
    get_vacancy,
    list_vacancies,
    update_vacancy,
    delete_vacancy,
    create_vacancy_alert,
    list_vacancy_alerts,
)

init_vacancy_db()

from app.application_tracker import (
    init_application_tracker_db,
    create_application,
    get_application,
    list_applications,
    update_application_status,
    list_application_history,
)
from app.profile import profile_exists

init_application_tracker_db()


@app.route("/api/vacancies", methods=["POST"])
def create_vacancy_api():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "Invalid or missing JSON data"
        }), 400

    try:
        vacancy_id = create_vacancy(
            title=str(data.get("title", "")).strip(),
            organization=str(data.get("organization", "")).strip(),
            category=str(data.get("category", "")).strip(),
            description=str(data.get("description", "")).strip(),
            eligibility=str(data.get("eligibility", "")).strip(),
            application_start=str(data.get("application_start", "")).strip(),
            application_end=str(data.get("application_end", "")).strip(),
            exam_date=str(data.get("exam_date", "")).strip(),
            official_link=str(data.get("official_link", "")).strip(),
            source_name=str(data.get("source_name", "")).strip(),
        )

        return jsonify({
            "success": True,
            "vacancy": get_vacancy(vacancy_id)
        }), 201

    except ValueError as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 400

    except Exception as error:
        return jsonify({
            "success": False,
            "error": "Request could not be completed"
        }), 500


@app.route("/api/vacancies", methods=["GET"])
def list_vacancies_api():
    try:
        return jsonify({
            "success": True,
            "vacancies": list_vacancies(
                category=request.args.get("category"),
                status=request.args.get("status"),
            )
        })
    except Exception as error:
        return jsonify({
            "success": False,
            "error": "Request could not be completed"
        }), 500


@app.route("/api/vacancies/<int:vacancy_id>", methods=["GET"])
def get_vacancy_api(vacancy_id):
    try:
        vacancy = get_vacancy(vacancy_id)

        if vacancy is None:
            return jsonify({
                "success": False,
                "error": "Vacancy not found"
            }), 404

        return jsonify({
            "success": True,
            "vacancy": vacancy
        })
    except Exception as error:
        return jsonify({
            "success": False,
            "error": "Request could not be completed"
        }), 500


@app.route("/api/vacancies/<int:vacancy_id>/eligibility", methods=["GET"])
def vacancy_eligibility_api(vacancy_id):
    """Report explicit criteria only. Free text stays unknown."""
    from app.eligibility import assess_eligibility

    vacancy = get_vacancy(vacancy_id)
    if vacancy is None:
        return jsonify({
            "success": False,
            "error": "Vacancy not found",
        }), 404
    profile_id = request.args.get("profile_id", default=1, type=int)
    try:
        denied = _deny_slot(profile_id)
        if denied is not None:
            return denied
        profile = get_verified_profile(profile_id)
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    result = assess_eligibility(vacancy, profile)
    result["success"] = True
    result["authenticated_account"] = _access_flags()["authenticated_account"]
    return jsonify(result)


@app.route("/api/vacancies/<int:vacancy_id>", methods=["PUT"])
def update_vacancy_api(vacancy_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "Invalid or missing JSON data"
        }), 400
    try:
        vacancy = update_vacancy(vacancy_id, **data)
        if vacancy is None:
            return jsonify({
                "success": False,
                "error": "Vacancy not found"
            }), 404
        return jsonify({"success": True, "vacancy": vacancy})
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400


@app.route("/api/vacancies/<int:vacancy_id>", methods=["DELETE"])
def delete_vacancy_api(vacancy_id):
    if not delete_vacancy(vacancy_id):
        return jsonify({
            "success": False,
            "error": "Vacancy not found"
        }), 404
    return jsonify({"success": True, "deleted": True})


@app.route("/api/vacancies/<int:vacancy_id>/alerts", methods=["POST"])
def create_vacancy_alert_api(vacancy_id):
    from app.profile import profile_exists

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "Invalid or missing JSON data"
        }), 400
    if get_vacancy(vacancy_id) is None:
        return jsonify({
            "success": False,
            "error": "Vacancy not found"
        }), 404
    try:
        profile_id = data.get("profile_id")
        if not profile_exists(profile_id):
            raise ValueError("profile_id must refer to an existing profile")
        denied = _deny_slot(profile_id)
        if denied is not None:
            return denied
        alert = create_vacancy_alert(profile_id, vacancy_id)
        return jsonify({"success": True, "alert": alert}), 201
    except (TypeError, ValueError) as error:
        return jsonify({"success": False, "error": str(error)}), 400


@app.route("/api/vacancy-alerts/<int:profile_id>", methods=["GET"])
def list_vacancy_alerts_api(profile_id):
    try:
        if not 1 <= profile_id <= 5:
            raise ValueError("profile_id must be an integer between 1 and 5")
        denied = _deny_slot(profile_id)
        if denied is not None:
            return denied
        return jsonify({
            "success": True,
            "alerts": list_vacancy_alerts(profile_id)
        })
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400


# --------------------------------------------------
# Phase 7 Application Tracker
# --------------------------------------------------

def _require_saved_profile(profile_id):
    if not profile_exists(profile_id):
        raise ValueError("profile_id must refer to an existing profile")


def _deny_slot(profile_id):
    from app.ownership import guard_response
    return guard_response(profile_id)


def _viewer_slot():
    from app.ownership import SlotAccessError, current_user_id, owned_slot_for_session

    if current_user_id() is None:
        return 1
    try:
        return owned_slot_for_session()
    except SlotAccessError:
        return ""


def _access_flags():
    from app.ownership import current_user_id
    logged_in = current_user_id() is not None
    return {
        "authenticated_account": logged_in,
        "access": "account" if logged_in else "profile_slot",
    }


def _vacancy_id_for_application(data):
    if data.get("vacancy_id") in (None, ""):
        return None
    vacancy_id = data.get("vacancy_id")
    if isinstance(vacancy_id, bool) or not isinstance(vacancy_id, int) or vacancy_id < 1:
        raise ValueError("vacancy_id must be a positive integer")
    if get_vacancy(vacancy_id) is None:
        raise LookupError("Vacancy not found")
    return vacancy_id


def _attach_vacancy_reference(application):
    if not isinstance(application, dict) or not application.get("vacancy_id"):
        return application
    vacancy = get_vacancy(application["vacancy_id"])
    if not vacancy:
        return application
    linked = dict(application)
    linked["official_link"] = vacancy.get("official_link") or ""
    linked["deadline"] = vacancy.get("application_end") or ""
    return linked


def _application_for_profile(profile_id, application_id):
    _require_saved_profile(profile_id)
    item = get_application(application_id)
    if item is None or item["profile_id"] != profile_id:
        return None
    return item


@app.route("/api/applications", methods=["POST"])
def create_application_api():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "Invalid or missing JSON data"
        }), 400
    try:
        profile_id = data.get("profile_id")
        _require_saved_profile(profile_id)
        denied = _deny_slot(profile_id)
        if denied is not None:
            return denied
        vacancy_id = _vacancy_id_for_application(data)
        application = create_application(
            profile_id,
            str(data.get("title", "")).strip(),
            organization=str(data.get("organization", "")).strip(),
            vacancy_id=vacancy_id,
            status=data.get("status") or "draft",
            note=str(data.get("note", "")).strip(),
        )
        return jsonify({
            "success": True,
            "application": _attach_vacancy_reference(application),
        }), 201
    except LookupError as error:
        return jsonify({"success": False, "error": str(error)}), 404
    except (TypeError, ValueError) as error:
        return jsonify({"success": False, "error": str(error)}), 400


@app.route("/api/applications/<int:profile_id>", methods=["GET"])
def list_applications_api(profile_id):
    try:
        _require_saved_profile(profile_id)
        denied = _deny_slot(profile_id)
        if denied is not None:
            return denied
        status = request.args.get("status")
        if status == "":
            status = None
        return jsonify({
            "success": True,
            **_access_flags(),
            "applications": [
                _attach_vacancy_reference(item)
                for item in list_applications(profile_id, status=status)
            ],
        })
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400


@app.route(
    "/api/applications/<int:profile_id>/<int:application_id>",
    methods=["GET"],
)
def get_application_api(profile_id, application_id):
    try:
        denied = _deny_slot(profile_id)
        if denied is not None:
            return denied
        application = _application_for_profile(profile_id, application_id)
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    if application is None:
        return jsonify({
            "success": False,
            "error": "Application not found"
        }), 404
    return jsonify({
        "success": True,
        "application": _attach_vacancy_reference(application),
    })


@app.route(
    "/api/applications/<int:profile_id>/<int:application_id>",
    methods=["PUT"],
)
def update_application_status_api(profile_id, application_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "Invalid or missing JSON data"
        }), 400
    try:
        denied = _deny_slot(profile_id)
        if denied is not None:
            return denied
        if _application_for_profile(profile_id, application_id) is None:
            return jsonify({
                "success": False,
                "error": "Application not found"
            }), 404
        application = update_application_status(
            application_id,
            data.get("status"),
            note=str(data.get("note", "")).strip(),
        )
        if application is None:
            return jsonify({
                "success": False,
                "error": "Application not found"
            }), 404
        return jsonify({
            "success": True,
            "application": _attach_vacancy_reference(application),
        })
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400


@app.route(
    "/api/applications/<int:profile_id>/<int:application_id>/history",
    methods=["GET"],
)
def application_history_api(profile_id, application_id):
    try:
        denied = _deny_slot(profile_id)
        if denied is not None:
            return denied
        if _application_for_profile(profile_id, application_id) is None:
            return jsonify({
                "success": False,
                "error": "Application not found"
            }), 404
        return jsonify({
            "success": True,
            "history": list_application_history(application_id),
        })
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400


# --------------------------------------------------
# Phase 2 Profile Media
# Photo / Signature use the existing Document Vault.
# --------------------------------------------------

@app.route("/api/profile/<int:profile_id>/media/<media_type>",
           methods=["POST"])
def upload_profile_media(profile_id, media_type):
    from app.profile import profile_exists
    from app.document_vault import STORAGE_DIR, allowed_file, file_contents_match
    from werkzeug.utils import secure_filename
    import hashlib
    import os

    if not profile_exists(profile_id):
        return jsonify({
            "success": False,
            "error": "profile_id must refer to an existing valid profile"
        }), 400
    denied = _deny_slot(profile_id)
    if denied is not None:
        return denied

    media_type = str(media_type).strip().lower()
    if media_type not in ("photo", "signature"):
        return jsonify({
            "success": False,
            "error": "media_type must be photo or signature"
        }), 400

    if "file" not in request.files:
        return jsonify({
            "success": False,
            "error": "file is required"
        }), 400

    uploaded = request.files["file"]
    filename = secure_filename(uploaded.filename or "")

    if not filename or not allowed_file(filename):
        return jsonify({
            "success": False,
            "error": "Only PDF, JPG, JPEG and PNG are allowed"
        }), 400

    data = uploaded.read()
    if len(data) > 10 * 1024 * 1024:
        return jsonify({
            "success": False,
            "error": "Maximum file size is 10 MB"
        }), 400

    if not file_contents_match(filename, data):
        return jsonify({
            "success": False,
            "error": "File contents do not match a PDF, JPEG, or PNG"
        }), 400

    digest = hashlib.sha256(data).hexdigest()
    ext = filename.rsplit(".", 1)[1].lower()

    media_dir = os.path.join(STORAGE_DIR, str(profile_id))
    os.makedirs(media_dir, exist_ok=True)

    storage_path = os.path.join(
        media_dir, f"{media_type}_{digest}.{ext}"
    )

    from app.document_encryption import DocumentStorageError, store_bytes
    try:
        stored_bytes = store_bytes(data)
    except DocumentStorageError as error:
        return jsonify({"success": False, "error": str(error)}), 400

    with open(storage_path, "wb") as handle:
        handle.write(stored_bytes)

    from app.document_vault import get_db, _generate_document_reference
    from datetime import datetime

    conn = get_db()
    try:
        now = datetime.utcnow().isoformat()

        previous = conn.execute("""
            SELECT id, document_version
            FROM documents
            WHERE profile_id = ? AND doc_type = ?
            ORDER BY document_version DESC
            LIMIT 1
        """, (profile_id, media_type)).fetchone()

        version = (previous["document_version"] if previous else 0) + 1
        reference = _generate_document_reference(conn)

        cur = conn.execute("""
            INSERT INTO documents
            (
                profile_id, doc_type, original_filename,
                storage_path, mime_type, file_hash,
                extracted_text, extracted_data, verified,
                created_at, updated_at, document_version,
                document_reference
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile_id,
            media_type,
            filename,
            storage_path,
            uploaded.mimetype or "",
            digest,
            "",
            "{}",
            0,
            now,
            now,
            version,
            reference,
        ))

        conn.commit()

        return jsonify({
            "success": True,
            "message": f"{media_type.capitalize()} uploaded successfully",
            "profile_id": profile_id,
            "media_type": media_type,
            "document_id": cur.lastrowid,
            "document_version": version,
            "document_reference": reference
        })
    finally:
        conn.close()


import app.document_vault as document_vault
from app.runtime_config import apply_document_vault_paths

apply_document_vault_paths(document_vault)
register_document_vault = document_vault.register_document_vault
register_document_vault_ui = document_vault.register_document_vault_ui
DOCUMENTS_DB_PATH = document_vault.DB_PATH
register_document_vault(app)
register_document_vault_ui(app)

from app.verified_profile import (
    init_verified_profile_db,
    save_verified_profile,
    get_verified_profile,
)
from app.profile import get_profile
from app.verification import (
    verify_profile_documents,
    combined_field_results,
    can_promote_verified_profile,
    verified_data_from_results,
)
init_verified_profile_db()


# --------------------------------------------------
# Profile UI
# --------------------------------------------------

if register_profile_ui:
    try:
        register_profile_ui(app)
    except Exception as e:
        print("Profile UI warning:", e)

try:
    from app.accounts import register_account_routes
    register_account_routes(app)
except Exception as e:
    print("Account warning:", e)



# --------------------------------------------------
# Verified Profile
# --------------------------------------------------

@app.route("/api/profile/<int:profile_id>/verified", methods=["GET", "POST"])
def verified_profile_api(profile_id):
    try:
        denied = _deny_slot(profile_id)
        if denied is not None:
            return denied
        if request.method == "POST":
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                return jsonify({
                    "success": False,
                    "error": "Invalid or missing JSON data"
                }), 400

            # verified=true in the request is never enough to promote.
            confirmed = data.get("confirmed") is True

            report = verify_profile_documents(
                get_profile(profile_id),
                profile_id,
                DOCUMENTS_DB_PATH,
            )
            field_results = combined_field_results(report["documents"])
            promotable = can_promote_verified_profile(field_results)

            if not promotable:
                return jsonify({
                    "success": False,
                    "verified": False,
                    "profile": None,
                    "error": "Profile cannot be marked verified until matching document data is confirmed",
                    "verification": report,
                }), 400

            if not confirmed:
                return jsonify({
                    "success": False,
                    "verified": False,
                    "profile": None,
                    "error": "User confirmation is required before promoting a verified profile",
                    "verification": report,
                }), 400

            save_verified_profile(
                verified_data_from_results(field_results),
                profile_id=profile_id,
                verified=True,
            )

        verified = get_verified_profile(profile_id)

        return jsonify({
            "success": True,
            "verified": verified is not None,
            "profile": verified,
        })
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except Exception as error:
        return jsonify({
            "success": False,
            "error": "Request could not be completed",
        }), 500

# --------------------------------------------------
# Test form
# --------------------------------------------------

TEST_FORM_HTML = """
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>FormBharat Test Form</title>

<style>

body {
    font-family: Arial, sans-serif;
    background: #f4f7f6;
    padding: 20px;
}

.container {
    max-width: 700px;
    margin: auto;
}

.card {
    background: white;
    padding: 20px;
    margin-bottom: 20px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

h1 {
    color: #146c43;
}

label {
    display: block;
    margin-top: 14px;
    margin-bottom: 6px;
    font-weight: bold;
}

input,
textarea,
select {
    width: 100%;
    padding: 12px;
    box-sizing: border-box;
    border: 1px solid #ccc;
    border-radius: 8px;
    font-size: 16px;
}

textarea {
    min-height: 80px;
}

button {
    width: 100%;
    padding: 14px;
    margin-top: 20px;
    border: none;
    border-radius: 8px;
    background: #146c43;
    color: white;
    font-size: 17px;
    font-weight: bold;
}

.status {
    margin-top: 15px;
    font-weight: bold;
}

.result {
    margin-top: 15px;
    background: #eef8f2;
    padding: 15px;
    border-radius: 8px;
    overflow-x: auto;
}

pre {
    white-space: pre-wrap;
    word-break: break-word;
}

</style>

</head>

<body>

<div class="container">

<h1>Auto Fill Form</h1>
<p>Pehle My Profile me apni jaankari bharo. Phir yahan dekho kaun se fields bhar sakte hain. OTP, CAPTCHA, payment aur final Submit aap khud karenge.</p>

<div class="card">

<h2>Local form par check karein</h2>

<input
    id="profile_id"
    name="profile_id"
    type="hidden"
    value="{{ profile_slot }}"
>

<form id="testForm">

<label for="full_name">
Full Name
</label>

<input
    id="full_name"
    name="full_name"
    type="text"
>

<label for="email">
Email
</label>

<input
    id="email"
    name="email"
    type="email"
>

<label for="mobile_number">
Mobile Number
</label>

<input
    id="mobile_number"
    name="mobile_number"
    type="tel"
>

<label for="dob">
Date of Birth
</label>

<input
    id="dob"
    name="dob"
    type="date"
>

<label for="address">
Address
</label>

<textarea
    id="address"
    name="address"
></textarea>

<label for="country">
Country
</label>

<select
    id="country"
    name="country"
>

<option value="in">
India
</option>

<option value="us">
USA
</option>

</select>

<button
    type="button"
    onclick="analyzeAndFill()"
>
    🤖 Analyze & Fill Form
</button>

</form>

<div
    id="status"
    class="status"
>
Ready.
</div>

<div
    id="result"
    class="result"
>
FormBharat ready to analyze this form.
</div>

</div>

</div>

<script>

function showStatus(text) {

    document.getElementById("status").textContent = text;

}

function showResultText(text) {

    const result = document.getElementById("result");

    result.replaceChildren();

    const pre = document.createElement("pre");

    pre.textContent = text;

    result.appendChild(pre);

}

function showAnalysisResult(resultData) {

    const result = document.getElementById("result");

    result.replaceChildren();

    function addLine(label, value) {

        const strong = document.createElement("strong");

        strong.textContent = label;

        result.appendChild(strong);

        result.appendChild(
            document.createTextNode(" " + value)
        );

        result.appendChild(document.createElement("br"));

        result.appendChild(document.createElement("br"));

    }

    addLine(
        "Fields detected:",
        String(resultData.fields_detected)
    );

    addLine(
        "Fields filled:",
        String(resultData.filled_count || 0)
    );

    addLine(
        "Fields skipped:",
        String(resultData.skipped_count || 0)
    );

    const pre = document.createElement("pre");

    pre.textContent = JSON.stringify(
        resultData.filled || [],
        null,
        2
    );

    result.appendChild(pre);

    addLine(
        "Review before you submit:",
        "Final submit stays with you"
    );

    const reviewData = resultData.review || {};

    (reviewData.proposed || []).forEach(function(item) {

        addLine(
            "Proposed:",
            (item.field || "") + " = " + (item.value || "")
        );

    });

    (reviewData.withheld || []).forEach(function(item) {

        addLine(
            "Withheld:",
            (item.field || "") + " (" + (item.reason || "") + ")"
        );

    });

    const review = document.createElement("pre");

    review.textContent = JSON.stringify(
        resultData.review || {},
        null,
        2
    );

    result.appendChild(review);

}

async function analyzeAndFill() {

    const form = document.getElementById("testForm");

    const html = form.outerHTML;

    const profileId = document.getElementById("profile_id").value.trim();

    if (!/^[1-5]$/.test(profileId)) {

        showStatus("❌ Error");

        showResultText(
            "profile_id must be an integer between 1 and 5"
        );

        return;

    }

    showStatus("🤖 FormBharat analyzing fields...");

    document.getElementById("result").replaceChildren();

    try {

        const response = await fetch("/analyze", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                html: html,
                profile_id: Number(profileId)
            })

        });

        const data = await response.json();

        if (!data.success) {

            throw new Error(
                data.error || "Analysis failed"
            );

        }

        const result = data.result;

        // --------------------------------------------------
        // APPLY FILLED VALUES TO ACTUAL BROWSER FORM
        // --------------------------------------------------

        const filledFields = result.filled || [];

        for (const item of filledFields) {

            const fieldName = item.field;
            const value = item.value;

            if (!fieldName) {
                continue;
            }

            const element =
                form.querySelector(
                    '[name="' + CSS.escape(fieldName) + '"]'
                ) ||
                document.getElementById(fieldName);

            if (!element) {
                continue;
            }

            const tag = element.tagName.toLowerCase();

            if (tag === "select") {

                element.value = String(value);

            } else if (
                element.type === "checkbox" ||
                element.type === "radio"
            ) {

                element.checked =
                    ["true", "1", "yes", "on"]
                    .includes(String(value).toLowerCase());

            } else {

                element.value = String(value);
            }

            // Let the page know that the value changed.
            element.dispatchEvent(
                new Event("input", { bubbles: true })
            );

            element.dispatchEvent(
                new Event("change", { bubbles: true })
            );
        }

        if ((result.filled_count || 0) > 0) {
            showStatus("Profile ki details form me bhar di gayi hain. Submit aap karenge.");
        } else {
            showStatus("Pehle My Profile me naam aur details save karo. Khali profile se form nahi bharta.");
        }

        showAnalysisResult(result);

    }

    catch (error) {

        showStatus("❌ Error");

        showResultText(String(error));

    }

}

</script>

</body>

</html>
"""




# --------------------------------------------------
# Main page
# --------------------------------------------------

PAGE = """
<!DOCTYPE html>
<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>FormBharat</title>

    <style>

        * {
            box-sizing: border-box;
        }

        body {
            font-family: Arial, sans-serif;
            background: #f4f7f6;
            margin: 0;
            padding: 20px;
        }

        .container {
            max-width: 700px;
            margin: auto;
        }

        h1 {
            color: #146c43;
            margin-bottom: 5px;
        }

        h2 {
            margin-top: 0;
        }

        .subtitle {
            color: #555;
            margin-bottom: 20px;
        }

        .card {
            background: white;
            padding: 20px;
            margin-bottom: 18px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        label {
            display: block;
            margin-top: 14px;
            margin-bottom: 6px;
            font-weight: bold;
        }

        input,
        select {
            width: 100%;
            max-width: 100%;
            box-sizing: border-box;
            padding: 13px;
            border: 1px solid #ccc;
            border-radius: 8px;
            font-size: 16px;
        }

        .actions {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .actions a {
            flex: 1 1 30%;
            min-width: 6.5rem;
            box-sizing: border-box;
            text-align: center;
            padding: 12px 8px;
            background: #146c43;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: bold;
            font-size: 16px;
        }

        button {
            width: 100%;
            margin-top: 20px;
            padding: 14px;
            background: #146c43;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 17px;
            font-weight: bold;
            cursor: pointer;
        }

        button:hover {
            background: #0f5132;
        }

        .result {
            background: #eef8f2;
            padding: 12px;
            margin-top: 10px;
            border-radius: 8px;
            overflow-x: auto;
        }

        .success {
            color: #146c43;
            font-weight: bold;
        }

        .error {
            color: #b02a37;
            font-weight: bold;
        }

        pre {
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        .fb-splash{position:fixed;inset:0;z-index:80;background:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:24px}
        .fb-splash.is-done{opacity:0;transition:opacity .45s ease;pointer-events:none}
        .fb-splash .fb-mark{width:120px;height:104px}
        .fb-splash .fb-word{margin:8px 0 0;font-size:2.05rem;font-weight:800;letter-spacing:-.04em;line-height:1}
        .fb-splash .fb-word span:first-child{color:#12833a}
        .fb-splash .fb-word span:last-child{color:#ef8b14}
        .fb-splash .fb-tagline{margin:8px 0 0;color:#1d4e89;font-weight:700;line-height:1.35}
        .fb-splash .fb-bar{width:128px;height:7px;margin-top:22px;border-radius:99px;background:linear-gradient(90deg,#ff9933 0 34%,#f4f7fb 34% 66%,#138a3a 66%);overflow:hidden;position:relative}
        .fb-splash .fb-bar i{position:absolute;inset:0 auto 0 0;width:0;background:rgba(255,255,255,.55);animation:fbload 2.6s ease forwards}
        .fb-splash .fb-next{margin:14px 0 0;color:#1d4e89;font-weight:700}
        .fb-kept{position:absolute;left:-10000px;width:1px;height:1px;overflow:hidden}
        .fb-wave-top,.fb-wave-bottom{position:absolute;left:0;width:100%;pointer-events:none}
        .fb-wave-top{top:0;height:170px}
        .fb-wave-bottom{bottom:0;height:150px}
        @keyframes fbload{to{width:100%}}

    </style>

</head>


<body data-signed-in="{{ '1' if signed_in else '0' }}">

<div class="fb-splash" id="fb-splash">
<svg class="fb-wave-top" viewBox="0 0 400 170" preserveAspectRatio="none" aria-hidden="true"><path d="M0 0h230C180 50 150 90 210 140 120 50 60 20 0 90Z" fill="#ff9a1f"/><path d="M0 0h150C140 60 90 90 70 150 40 80 10 40 0 100Z" fill="#ffb24d"/></svg>
<svg class="fb-wave-bottom" viewBox="0 0 400 150" preserveAspectRatio="none" aria-hidden="true"><path d="M0 36c80-28 150 12 220 18 80 6 120-16 180-22v118H0Z" fill="#ff9933"/><path d="M0 68c80-24 150 10 220 14 70 4 120-12 180-16v84H0Z" fill="#fff"/><path d="M0 102c70-20 150 8 220 10 70 2 120-8 180-12v50H0Z" fill="#138808"/></svg>
<svg class="fb-mark" viewBox="0 0 140 120" aria-hidden="true"><rect x="40" y="14" width="44" height="56" rx="5" fill="none" stroke="#1b4f9c" stroke-width="4.5"/><path d="M50 30h24M50 39h24M50 48h15" stroke="#1b4f9c" stroke-width="3" stroke-linecap="round"/><path d="M16 84c24-36 52-38 84-8" fill="none" stroke="#f58220" stroke-width="9" stroke-linecap="round"/><path d="M22 100c24-28 54-24 78 8" fill="none" stroke="#14913d" stroke-width="9" stroke-linecap="round"/><g transform="translate(98,44)"><circle r="16" fill="#fff" stroke="#0a3d91" stroke-width="2"/><circle r="3.2" fill="#0a3d91"/><circle r="11.5" fill="none" stroke="#0a3d91" stroke-width="1.3" stroke-dasharray="1.5 2.3"/></g></svg>
<p class="fb-word"><span>Form</span><span>Bharat</span></p>
<p class="fb-tagline">Government Forms,<br>Ab aur bhi Aasaan</p>
<div class="fb-bar" aria-hidden="true"><i></i></div>
<p class="fb-next" id="fb-next"></p>
</div>
<script>
(function () {
    var splash = document.getElementById("fb-splash");
    if (!splash) return;
    var signedIn = document.body.getAttribute("data-signed-in") === "1";
    var next = document.getElementById("fb-next");
    if (next) {
        next.textContent = signedIn ? "Home khul raha hai" : "Agle pal login khulega";
    }
    var seen = false;
    try {
        seen = sessionStorage.getItem("fb-opened") === "1";
    } catch (error) {}
    function go() {
        try { sessionStorage.setItem("fb-opened", "1"); } catch (error) {}
        if (!signedIn) {
            window.location.replace("/account");
            return;
        }
        splash.classList.add("is-done");
        setTimeout(function () { splash.remove(); }, 500);
    }
    if (seen) {
        go();
        return;
    }
    setTimeout(go, 2800);
})();
</script>

<div class="container">

    <section class="card fb-hero">
        <svg class="fb-logo" viewBox="0 0 88 88" aria-hidden="true">
            <rect x="24" y="20" width="30" height="40" rx="4" fill="#1d4e89"/>
            <path d="M30 32h16M30 38h16M30 44h10" stroke="#fff" stroke-width="2"/>
            <path d="M18 56c14-18 34-18 52-2" fill="none" stroke="#ff9933" stroke-width="5" stroke-linecap="round"/>
            <path d="M20 64c14-14 34-12 50 4" fill="none" stroke="#138a3a" stroke-width="5" stroke-linecap="round"/>
            <circle cx="60" cy="36" r="11" fill="#fff" stroke="#0a3d91" stroke-width="2"/>
            <circle cx="60" cy="36" r="3" fill="#0a3d91"/>
        </svg>
        <p class="fb-kicker">Dashboard · Ek Profile · Sabhi Forms · Kam Samay</p>
        <h1>Government Forms,<br>Ab aur bhi Aasaan</h1>
        <p class="fb-note">OTP, CAPTCHA, and final Submit stay with you.</p>
        <p class="fb-note">Sign in from Account. Khali slot My Profile par milta hai. Purani profile Account se khud jod sakte hain.</p>
    </section>
    <div class="fb-tiles">
        <a class="fb-tile fb-mint" href="/profile"><i class="fb-ico">P</i><div><strong>My Profile</strong><span>Apni personal information manage karein</span></div></a>
        <a class="fb-tile fb-sky" href="/test-form"><i class="fb-ico">A</i><div><strong>Auto Fill Form</strong><span>Pehle profile, phir form. OTP aur Submit aap karenge</span></div></a>
    </div>
    <div class="fb-row">
        <a href="/documents">Documents Manage</a>
        <a href="/vacancies">Find Vacancies</a>
        <a href="/applications">My Applications</a>
    </div>
    <section class="fb-rule">
        <strong>Rules &amp; Regulations</strong>
        <p class="fb-note">Form filling yahin rukta hai jahan site password, OTP, CAPTCHA, payment ya final Submit maange.</p>
    </section>


    <div class="card fb-kept">

        <h2>Local form check</h2>
        <p class="fb-note">Yahin saved profile se fields match hote hain. Site khud submit nahi hoti.</p>

        <label for="profile_id">
            Profile ID
        </label>

        <input
            id="profile_id"
            name="profile_id"
            type="number"
            min="1"
            max="5"
            inputmode="numeric"
        >

        <form id="rootForm">

        <label for="name">
            Full Name
        </label>

        <input
            id="name"
            placeholder="Enter your name"
        >


        <label for="email">
            Email
        </label>

        <input
            id="email"
            type="email"
            placeholder="Enter email"
        >


        <label for="mobile">
            Mobile Number
        </label>

        <input
            id="mobile"
            placeholder="Enter mobile number"
        >


        <label for="dob">
            Date of Birth
        </label>

        <input
            id="dob"
            type="date"
        >


        <label for="address">
            Address
        </label>

        <input
            id="address"
            placeholder="Enter address"
        >

        </form>

        <button type="button" onclick="analyzeForm()">
            Analyze Form
        </button>

    </div>


    <div class="card fb-kept">

        <h2>AI Result</h2>

        <div id="status">
            FormBharat ready.
        </div>

        <div id="result" class="result"></div>

    </div>

</div>


<script>

function showRootStatus(className, text) {

    const status = document.getElementById("status");

    status.replaceChildren();

    if (!className) {

        status.textContent = text;

        return;

    }

    const span = document.createElement("span");

    span.className = className;

    span.textContent = text;

    status.appendChild(span);

}

function showRootResult(text) {

    const result = document.getElementById("result");

    result.replaceChildren();

    const pre = document.createElement("pre");

    pre.textContent = text;

    result.appendChild(pre);

}

async function analyzeForm() {

    const profileId = document.getElementById("profile_id").value.trim();

    if (!/^[1-5]$/.test(profileId)) {

        showRootStatus("error", "Error");

        showRootResult(
            "profile_id must be an integer between 1 and 5"
        );

        return;

    }

    const html = document.getElementById("rootForm").outerHTML;

    showRootStatus("", "AI analyzing form...");

    document.getElementById("result").replaceChildren();

    try {

        const response = await fetch("/analyze", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                html: html,
                profile_id: Number(profileId)
            })
        });


        const data = await response.json();


        if (data.success) {

            showRootStatus(
                "success",
                "Analysis successful ✓"
            );

            const review = (data.result && data.result.review) || {};
            const lines = [
                "Review before you submit. Final submit stays with you."
            ];
            (review.proposed || []).forEach(function(item) {
                lines.push(
                    "Proposed: " + (item.field || "") + " = " + (item.value || "")
                );
            });
            (review.withheld || []).forEach(function(item) {
                lines.push(
                    "Withheld: " + (item.field || "") + " (" + (item.reason || "") + ")"
                );
            });
            lines.push("Submitted: false");
            lines.push(JSON.stringify(data.result, null, 2));
            showRootResult(lines.join("\n"));

        }

        else {

            showRootStatus("error", "Error");

            showRootResult(
                JSON.stringify(data, null, 2)
            );
        }


    }

    catch (error) {

        showRootStatus("error", "Server error");

        showRootResult(String(error));
    }

}

</script>

</body>

</html>
"""


# --------------------------------------------------
# Mobile navigation
# Shared by the existing pages and the read-only Vacancy and Application pages.
# --------------------------------------------------

_MOBILE_NAV_PATHS = {
    "/",
    "/test-form",
    "/profile",
    "/documents",
    "/vacancies",
    "/applications",
    "/account",
}

_MOBILE_NAV = """
<header class="fb-header">
<a class="fb-brand" href="/"><span>Form</span><span>Bharat</span></a>
<a class="fb-account" href="/account">खाता</a>
<i class="fb-ribbon"></i>
</header>
<nav class="fb-nav" aria-label="FormBharat">
<a href="/"><span>Home</span><small>होम</small></a>
<a href="/profile"><span>Profile</span><small>प्रोफ़ाइल</small></a>
<a href="/documents"><span>Documents</span><small>दस्तावेज़</small></a>
<a href="/vacancies"><span>Vacancies</span><small>नौकरी</small></a>
<a href="/applications"><span>Applications</span><small>आवेदन</small></a>
</nav>
<svg class="fb-flag-wave" viewBox="0 0 400 150" preserveAspectRatio="none" aria-hidden="true"><path d="M0 36c80-28 150 12 220 18 80 6 120-16 180-22v118H0Z" fill="#ff9933"/><path d="M0 68c80-24 150 10 220 14 70 4 120-12 180-16v84H0Z" fill="#fff"/><path d="M0 102c70-20 150 8 220 10 70 2 120-8 180-12v50H0Z" fill="#138808"/></svg>
<style>
:root{--fb-ink:#16324f;--fb-green:#12833a;--fb-saffron:#ef8b14;--fb-line:#e6edf5}
body{font-family:"Segoe UI",system-ui,sans-serif;color:var(--fb-ink);margin:0;padding:14px 14px 128px;background:
radial-gradient(280px 140px at -10% -20px,#ffb04a 0%,rgba(255,153,51,0) 72%),
radial-gradient(320px 160px at 110% -30px,#ffd19a 0%,rgba(255,153,51,0) 70%),
linear-gradient(#fff,#fff)}
.container,.fb-header{max-width:430px;margin-left:auto;margin-right:auto}
h1,h2{color:#17345c;letter-spacing:0}
.fb-header{position:relative;margin-bottom:14px;padding:6px 2px 12px;background:transparent;border:0}
.fb-brand{font-size:1.7rem;font-weight:800;letter-spacing:-.04em;line-height:1;text-decoration:none}
.fb-brand span:first-child{color:var(--fb-green)}
.fb-brand span:last-child{color:var(--fb-saffron)}
.fb-account{position:absolute;right:0;top:8px;color:var(--fb-green);font-weight:800;text-decoration:none}
.fb-ribbon{display:block;height:6px;margin-top:12px;border-radius:99px;border:1px solid #eadfce;background:linear-gradient(90deg,#ff9933 0 33%,#fff 33% 67%,#138808 67%)}
.fb-flag-wave{position:fixed;left:0;right:0;bottom:0;z-index:4;width:100%;height:118px;pointer-events:none}/* tiranga */
.fb-nav{position:fixed;left:0;right:0;bottom:0;z-index:6;display:flex;gap:4px;margin:0;padding:8px 8px calc(8px + env(safe-area-inset-bottom));background:transparent;border-top:0;box-shadow:none}
.fb-nav a{flex:1 1 0;min-width:0;box-sizing:border-box;text-align:center;padding:8px 2px;background:#fff;color:var(--fb-green);text-decoration:none;border-radius:14px;font-weight:800;font-size:11px;line-height:1.15}
.fb-nav small{display:block;color:#6b7c90;font-size:10px;font-weight:700}
body .card{background:#fff;border:1px solid #edf2f7;border-radius:22px;box-shadow:0 10px 28px rgba(22,50,79,.06);padding:18px 16px;margin-bottom:14px}
.fb-hero{text-align:center;background:linear-gradient(180deg,#fff,#f5fbff)}
.fb-hero h1{margin:8px 0 6px;font-size:1.45rem;line-height:1.25}
.fb-kicker{margin:0;color:#5d7088;font-weight:700}
.fb-logo{width:92px;height:92px;margin:4px auto 8px;border-radius:50%;background:#fff;box-shadow:0 8px 20px rgba(22,50,79,.08)}
.fb-tiles{display:grid;gap:12px;margin:14px 0}
.fb-tile{display:flex;gap:12px;align-items:center;padding:16px;border-radius:22px;text-decoration:none;color:var(--fb-ink);box-shadow:0 8px 20px rgba(22,50,79,.05)}
.fb-tile strong{display:block;font-size:1.05rem}
.fb-tile span{display:block;color:#5d7088;font-size:.9rem;font-weight:600}
.fb-tile::after{content:"›";margin-left:auto;color:#8aa0b8;font-size:1.4rem;font-weight:700}
.fb-mint{background:#e7f8ee}
.fb-sky{background:#e7f1ff}
.fb-ico{width:46px;height:46px;border-radius:50%;display:grid;place-items:center;color:#fff;font-style:normal;font-weight:800;flex:0 0 46px}
.fb-mint .fb-ico{background:#12833a}
.fb-sky .fb-ico{background:#2563eb}
.fb-row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin:0 0 14px}
.fb-row a{display:flex;min-height:92px;padding:12px;border-radius:18px;text-decoration:none;font-weight:800;color:#17345c;align-items:flex-start;line-height:1.25;font-size:.92rem}
.fb-row a:nth-child(1){background:#ffe8ec}
.fb-row a:nth-child(2){background:#fff3df}
.fb-row a:nth-child(3){background:#f3e8ff}
.fb-rule{background:#e7f8ee;border-radius:22px;padding:14px 16px;margin-bottom:14px}
body label{color:#24507a;font-weight:700}
body input,body select,body textarea{width:100%;box-sizing:border-box;border:1px solid #d9e3ee;border-radius:14px;background:#f8fbfe;color:var(--fb-ink);padding:14px;font-size:16px}
body button:not(.delete),body .fb-go{display:block;width:100%;box-sizing:border-box;background:var(--fb-green);color:#fff;border:0;border-radius:16px;min-height:52px;margin-top:14px;font-weight:800;font-size:1.05rem;text-align:center;text-decoration:none;scroll-margin-bottom:120px}
body button:not(.delete):hover{background:#0f6d2e}
body button.delete{background:#b3261e;color:#fff;border:0;border-radius:14px}
.fb-note{margin:8px 0 0;color:#5d7088}
.fb-status{display:inline-block;margin:0 0 8px;padding:4px 10px;border-radius:999px;background:#e8f8ee;color:var(--fb-green);font-weight:800}
h2.fb-section{margin:18px 0 8px;padding:12px 14px;border-radius:16px;font-size:1rem}
h2.fb-sec-personal{background:#e7f1ff;color:#1d4e89}
h2.fb-sec-family{background:#ffe8ee;color:#9d174d}
h2.fb-sec-address{background:#e7f8ee;color:#138a3a}
h2.fb-sec-education{background:#fff4e0;color:#b45309}
h2.fb-sec-category{background:#f3e8ff;color:#6d28d9}
.fb-meter i{display:block;height:8px;margin-top:8px;border-radius:99px;background:#e5eef6;position:relative;overflow:hidden}
.fb-meter i::after{content:"";position:absolute;inset:0 auto 0 0;width:var(--fb-fill,0%);background:linear-gradient(90deg,#138a3a,#8ed35a)}
.fb-split{display:grid;grid-template-columns:1fr auto 1fr;gap:8px;align-items:center;color:#8aa;margin:8px 0}
.fb-split::before,.fb-split::after{content:"";height:1px;background:#e1e8f0}
a{color:var(--fb-green)}
.fb-auth{text-align:left}
.fb-auth h1,.fb-auth .fb-lead{text-align:center}
@media(min-width:900px){
body{padding:28px 24px 128px}
.fb-nav,.fb-flag-wave{left:50%;right:auto;width:min(430px,100%);transform:translateX(-50%)}
}
</style>
"""


def _inject_mobile_nav(html):
    if 'class="fb-nav"' in html:
        return html
    start = html.lower().find("<body")
    if start < 0:
        return html
    end = html.find(">", start)
    if end < 0:
        return html
    return html[:end + 1] + _MOBILE_NAV + html[end + 1:]


@app.after_request
def add_mobile_nav(response):
    if request.path not in _MOBILE_NAV_PATHS or response.status_code != 200:
        return response
    if response.mimetype != "text/html":
        return response
    response.set_data(_inject_mobile_nav(response.get_data(as_text=True)))
    return response


# --------------------------------------------------
# Home
# --------------------------------------------------

@app.route("/")
def home():
    from app.ownership import current_user_id

    return render_template_string(
        PAGE,
        signed_in=current_user_id() is not None,
    )


VACANCIES_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FormBharat Vacancies</title>
<style>
body{font-family:Arial,sans-serif;background:#f4f7f6;margin:0;padding:20px}
.container{max-width:700px;margin:auto}
h1{color:#146c43}
.card{background:#fff;padding:16px;margin-bottom:12px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.08);overflow-wrap:anywhere}
button{width:100%;padding:14px;background:#146c43;color:#fff;border:0;border-radius:8px;font-size:16px;font-weight:bold}
a{color:#146c43}
</style>
</head>
<body>
<div class="container">
<section class="card fb-hero">
<h1>Find Vacancies</h1>
<p class="fb-note">These are local profile slots, not signed-in accounts. Official links stay read-only.</p>
</section>
<button type="button" id="refresh">Refresh</button>
<p id="vacancy-message">Loading vacancies...</p>
<div id="vacancy-list"></div>
</div>
<script>
function addLine(parent, label, value) {
    if (value === null || value === undefined || String(value).trim() === "") {
        return;
    }
    const line = document.createElement("p");
    const strong = document.createElement("strong");
    strong.textContent = label;
    line.appendChild(strong);
    line.appendChild(document.createTextNode(" " + value));
    parent.appendChild(line);
}

function renderVacancy(item) {
    const card = document.createElement("article");
    card.className = "card";
    const title = document.createElement("h2");
    title.textContent = item.title || "Vacancy";
    card.appendChild(title);
    addLine(card, "Organization:", item.organization);
    addLine(card, "Category:", item.category);
    addLine(card, "Eligibility:", item.eligibility);
    const eligibilityNote = document.createElement("p");
    eligibilityNote.textContent = "Eligibility text is not an automatic decision.";
    card.appendChild(eligibilityNote);
    addLine(card, "Details:", item.description);
    addLine(card, "Opens:", item.application_start);
    addLine(card, "Deadline:", item.application_end);
    addLine(card, "Exam date:", item.exam_date);
    addLine(card, "Status:", item.status);
    addLine(card, "Source:", item.source_name);
    const link = String(item.official_link || "");
    if (link.startsWith("https://") || link.startsWith("http://")) {
        const anchor = document.createElement("a");
        anchor.href = link;
        anchor.textContent = "Official link";
        card.appendChild(anchor);
    }
    return card;
}

async function loadVacancies() {
    const message = document.getElementById("vacancy-message");
    const list = document.getElementById("vacancy-list");
    list.replaceChildren();
    message.textContent = "Loading vacancies...";
    try {
        const response = await fetch("/api/vacancies");
        const data = await response.json();
        if (!data.success) {
            message.textContent = data.error || "Could not load vacancies.";
            return;
        }
        const vacancies = data.vacancies || [];
        if (!vacancies.length) {
            message.textContent = "No vacancies saved yet.";
            return;
        }
        message.textContent = "";
        vacancies.forEach(function(item) {
            list.appendChild(renderVacancy(item));
        });
    } catch (error) {
        message.textContent = "Could not load vacancies.";
    }
}

document.getElementById("refresh").onclick = loadVacancies;
loadVacancies();
</script>
</body>
</html>
"""


APPLICATIONS_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FormBharat Applications</title>
<style>
body{font-family:Arial,sans-serif;background:#f4f7f6;margin:0;padding:20px}
.container{max-width:700px;margin:auto}
h1{color:#146c43}
label{display:block;margin-top:14px;margin-bottom:6px;font-weight:bold}
input,button{width:100%;max-width:100%;box-sizing:border-box;padding:13px;border-radius:8px;font-size:16px}
input{border:1px solid #ccc}
button{margin-top:12px;background:#146c43;color:#fff;border:0;font-weight:bold}
.card{background:#fff;padding:16px;margin-top:12px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.08);overflow-wrap:anywhere}
</style>
</head>
<body>
<div class="container">
<section class="card fb-hero">
<h1>My Applications</h1>
<p class="fb-note">These are local profile slots, not signed-in accounts. Saving a status here does not submit a government form.</p>
</section>
<input id="profile_id" type="hidden" data-slot="{{ profile_slot }}">
<button type="button" id="load">Show applications</button>
<p id="application-message">Aapki applications yahin dikhengi.</p>
<div id="application-list"></div>
</div>
<script>
const savedSlot = document.getElementById("profile_id").getAttribute("data-slot");
if (savedSlot) {
    document.getElementById("profile_id").value = savedSlot;
}
function addLine(parent, label, value) {
    if (value === null || value === undefined || String(value).trim() === "") {
        return;
    }
    const line = document.createElement("p");
    const strong = document.createElement("strong");
    strong.textContent = label;
    line.appendChild(strong);
    line.appendChild(document.createTextNode(" " + value));
    parent.appendChild(line);
}

function renderHistory(history) {
    const block = document.createElement("div");
    const heading = document.createElement("h3");
    heading.textContent = "History";
    block.appendChild(heading);
    if (!history.length) {
        const empty = document.createElement("p");
        empty.textContent = "No status history.";
        block.appendChild(empty);
        return block;
    }
    history.forEach(function(entry) {
        const line = document.createElement("p");
        let text = entry.status || "";
        if (entry.note) {
            text += " — " + entry.note;
        }
        if (entry.created_at) {
            text += " (" + entry.created_at + ")";
        }
        line.textContent = text;
        block.appendChild(line);
    });
    return block;
}

function renderApplication(item, history) {
    const card = document.createElement("article");
    card.className = "card";
    const title = document.createElement("h2");
    title.textContent = item.title || "Application";
    card.appendChild(title);
    addLine(card, "Organization:", item.organization);
    const status = document.createElement("p");
    status.className = "fb-status";
    status.textContent = item.status || "";
    card.appendChild(status);
    addLine(card, "Vacancy:", item.vacancy_id);
    addLine(card, "Deadline:", item.deadline);
    addLine(card, "Official link:", item.official_link);
    addLine(card, "Updated:", item.updated_at);
    card.appendChild(renderHistory(history));
    return card;
}

async function loadApplications() {
    const message = document.getElementById("application-message");
    const list = document.getElementById("application-list");
    const profileId = document.getElementById("profile_id").value.trim();
    list.replaceChildren();
    if (!/^[1-5]$/.test(profileId)) {
        message.textContent = "profile_id must be an integer between 1 and 5";
        return;
    }
    message.textContent = "Loading applications...";
    try {
        const response = await fetch("/api/applications/" + profileId);
        const data = await response.json();
        if (!data.success) {
            message.textContent = data.error || "Could not load applications.";
            return;
        }
        const applications = data.applications || [];
        if (!applications.length) {
            message.textContent = "No applications saved yet.";
            return;
        }
        message.textContent = "";
        for (const item of applications) {
            let history = [];
            const historyResponse = await fetch(
                "/api/applications/" + profileId + "/" + item.id + "/history"
            );
            const historyData = await historyResponse.json();
            if (historyData.success) {
                history = historyData.history || [];
            }
            list.appendChild(renderApplication(item, history));
        }
    } catch (error) {
        message.textContent = "Could not load applications.";
    }
}

document.getElementById("load").onclick = loadApplications;
</script>
</body>
</html>
"""


@app.route("/vacancies")
def vacancies_page():
    return VACANCIES_PAGE


@app.route("/applications")
def applications_page():
    return render_template_string(
        APPLICATIONS_PAGE,
        profile_slot=_viewer_slot(),
    )


# --------------------------------------------------
# Health check
# --------------------------------------------------

@app.route("/api/access")
def access_api():
    from app.access_boundary import slot_access
    from app.document_encryption import encryption_status

    payload = slot_access()
    payload.update(_access_flags())
    if payload["authenticated_account"]:
        payload["account_note"] = (
            "This session is an account. It can use only slots it owns."
        )
    return jsonify({
        "success": True,
        **payload,
        "legacy_claim": "explicit_empty_slot_only",
        "documents": encryption_status(),
    })


@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "service": "FormBharat",
        "version": "1.0"
    })


# --------------------------------------------------
# Analyze
# --------------------------------------------------

MAX_ANALYZE_HTML_BYTES = 1_000_000


@app.route("/api/local-assist", methods=["POST"])
def local_assist_api():
    """Read a local file page for one verified profile slot.

    The request cannot supply profile values. Reread returns the DOM
    of the page already open in that slot. Nothing is submitted.
    """
    from app.browser import BrowserSession
    from app.rendered_assist import run_local_assist

    data = request.get_json(silent=True)
    if isinstance(data, dict) and data.get("profile_id") is not None:
        try:
            denied = _deny_slot(data.get("profile_id"))
        except (TypeError, ValueError):
            denied = None
        if denied is not None:
            return denied
    try:
        result = run_local_assist(
            data,
            app.extensions.setdefault("local_browser_sessions", {}),
            BrowserSession,
        )
    except ValueError as error:
        return jsonify({
            "success": False,
            "error": str(error),
            "submitted": False,
        }), 400
    except Exception as error:
        from app.ownership import SlotAccessError
        if isinstance(error, SlotAccessError):
            return jsonify({
                "success": False,
                "error": str(error),
                "submitted": False,
            }), 403
        raise
    return jsonify(result)


@app.route("/analyze", methods=["POST"])
def analyze():

    try:

        data = request.get_json(silent=True) or {}

        html = data.get("html")
        if not isinstance(html, str) or not html.strip():
            return jsonify({
                "success": False,
                "error": "html must be a non-empty string"
            }), 400

        if len(html.encode("utf-8")) > MAX_ANALYZE_HTML_BYTES:
            return jsonify({
                "success": False,
                "error": "html exceeds the maximum size"
            }), 400

        # Bible boundary:
        # Raw Profile must never be used for form filling.
        # Form filling may use only an explicitly Verified Profile.
        profile_id = data.get("profile_id", 1)
        if isinstance(profile_id, str) and profile_id.strip().isdigit():
            profile_id = int(profile_id.strip())
        if (
            isinstance(profile_id, bool)
            or not isinstance(profile_id, int)
            or not 1 <= profile_id <= 5
        ):
            return jsonify({
                "success": False,
                "error": "profile_id must be an integer between 1 and 5"
            }), 400

        denied = _deny_slot(profile_id)
        if denied is not None:
            return denied

        profile = get_verified_profile(profile_id)

        result = {
            "message": "Form received successfully.",
            "profile": profile,
            "verified_profile": profile is not None,
        }

        # --------------------------------------------------
        # FORM AUTOMATION PIPELINE
        # HTML → Reader → Analyzer → Profile Matcher
        # --------------------------------------------------

        if FormReader is None:
            raise RuntimeError("FormReader unavailable")

        if FieldAnalyzer is None:
            raise RuntimeError("FieldAnalyzer unavailable")

        if match_profile_to_fields is None:
            raise RuntimeError("Profile Matcher unavailable")

        reader = FormReader()
        analyzer = FieldAnalyzer()

        fields = reader.read(html)

        analyzed_fields = analyzer.analyze(fields)

        # --------------------------------------------------
        # AI MATCHER
        # Field meaning + safety classification
        # --------------------------------------------------

        if AIMatcher is None:
            raise RuntimeError("AI Matcher unavailable")

        ai_matcher = AIMatcher()

        for field in analyzed_fields:

            if not isinstance(field, dict):
                continue

            ai_text = " ".join([
                str(field.get("label") or ""),
                str(field.get("name") or ""),
                str(field.get("id") or ""),
                str(field.get("placeholder") or "")
            ]).strip()

            ai_result = ai_matcher.match(ai_text)

            field["ai_purpose"] = ai_result.get("purpose")
            field["ai_confidence"] = ai_result.get("confidence")
            field["ai_blocked"] = ai_result.get("blocked", False)

            if ai_result.get("reason"):
                field["ai_block_reason"] = ai_result["reason"]

        matched_fields = match_profile_to_fields(
            analyzed_fields,
            profile
        )

        from app.rendered_assist import apply_fill_boundaries, build_review

        withheld = apply_fill_boundaries(matched_fields)

        result["fields_detected"] = len(fields)
        result["fields"] = analyzed_fields
        result["matched_fields"] = matched_fields

        # --------------------------------------------------
        # FILL ENGINE
        # Matched profile values → HTML form
        # --------------------------------------------------

        if fill_form is None:
            raise RuntimeError("Fill Engine unavailable")

        fill_result = fill_form(
            html,
            matched_fields
        )

        result["filled_html"] = fill_result["html"]
        result["filled"] = fill_result["filled"]
        result["skipped"] = fill_result["skipped"]
        result["filled_count"] = fill_result["filled_count"]
        result["skipped_count"] = fill_result["skipped_count"]
        result["review"] = build_review(fill_result["filled"], withheld)
        result["submitted"] = False

        # --------------------------------------------------
        # Existing AI engine
        # --------------------------------------------------

        if FormBharatAI:

            try:

                ai = FormBharatAI()
                ai_result = None

                if hasattr(ai, "analyze_profile"):
                    ai_result = ai.analyze_profile(profile)

                elif hasattr(ai, "analyze"):
                    ai_result = ai.analyze(
                        result.get("fields", [])
                    )

                elif hasattr(ai, "process"):
                    ai_result = ai.process(profile)

                if ai_result is not None:
                    result["ai_result"] = ai_result

            except Exception as ai_error:

                result["ai_warning"] = "AI analysis was skipped"

        return jsonify({
            "success": True,
            "result": result
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "error": "Request could not be completed"
        }), 500


# --------------------------------------------------
# Test form API
# --------------------------------------------------

@app.route("/test-form")
def test_form():

    return render_template_string(
        TEST_FORM_HTML,
        profile_slot=_viewer_slot(),
    )


# --------------------------------------------------
# Application start
# --------------------------------------------------

def serve():
    from app.runtime_config import load_settings

    settings = load_settings()
    if settings["production"]:
        app.config["DEBUG"] = False
        app.config["PROPAGATE_EXCEPTIONS"] = False
        from waitress import serve as waitress_serve

        waitress_serve(app, host=settings["host"], port=settings["port"])
        return

    app.run(
        host=settings["host"],
        port=settings["port"],
        debug=True,
    )


if __name__ == "__main__":
    from app.runtime_config import load_settings

    settings = load_settings()
    print("")
    print("================================")
    print(" FormBharat Server")
    print("================================")
    print(f"Mode   : {settings['environment']}")
    print(f"Home   : http://127.0.0.1:{settings['port']}/")
    print(f"Health : http://127.0.0.1:{settings['port']}/health")
    print("Analyze: POST /analyze")
    print("================================")
    print("")

    serve()

