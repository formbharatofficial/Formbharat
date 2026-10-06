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
        alert = create_vacancy_alert(profile_id, vacancy_id)
        return jsonify({"success": True, "alert": alert}), 201
    except (TypeError, ValueError) as error:
        return jsonify({"success": False, "error": str(error)}), 400


@app.route("/api/vacancy-alerts/<int:profile_id>", methods=["GET"])
def list_vacancy_alerts_api(profile_id):
    try:
        if not 1 <= profile_id <= 5:
            raise ValueError("profile_id must be an integer between 1 and 5")
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


def _vacancy_id_for_application(data):
    if data.get("vacancy_id") in (None, ""):
        return None
    vacancy_id = data.get("vacancy_id")
    if isinstance(vacancy_id, bool) or not isinstance(vacancy_id, int) or vacancy_id < 1:
        raise ValueError("vacancy_id must be a positive integer")
    if get_vacancy(vacancy_id) is None:
        raise LookupError("Vacancy not found")
    return vacancy_id


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
        vacancy_id = _vacancy_id_for_application(data)
        application = create_application(
            profile_id,
            str(data.get("title", "")).strip(),
            organization=str(data.get("organization", "")).strip(),
            vacancy_id=vacancy_id,
            status=data.get("status") or "draft",
            note=str(data.get("note", "")).strip(),
        )
        return jsonify({"success": True, "application": application}), 201
    except LookupError as error:
        return jsonify({"success": False, "error": str(error)}), 404
    except (TypeError, ValueError) as error:
        return jsonify({"success": False, "error": str(error)}), 400


@app.route("/api/applications/<int:profile_id>", methods=["GET"])
def list_applications_api(profile_id):
    try:
        _require_saved_profile(profile_id)
        status = request.args.get("status")
        if status == "":
            status = None
        return jsonify({
            "success": True,
            "applications": list_applications(profile_id, status=status),
        })
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400


@app.route(
    "/api/applications/<int:profile_id>/<int:application_id>",
    methods=["GET"],
)
def get_application_api(profile_id, application_id):
    try:
        application = _application_for_profile(profile_id, application_id)
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    if application is None:
        return jsonify({
            "success": False,
            "error": "Application not found"
        }), 404
    return jsonify({"success": True, "application": application})


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
        return jsonify({"success": True, "application": application})
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400


@app.route(
    "/api/applications/<int:profile_id>/<int:application_id>/history",
    methods=["GET"],
)
def application_history_api(profile_id, application_id):
    try:
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

    with open(storage_path, "wb") as f:
        f.write(data)

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



# --------------------------------------------------
# Verified Profile
# --------------------------------------------------

@app.route("/api/profile/<int:profile_id>/verified", methods=["GET", "POST"])
def verified_profile_api(profile_id):
    try:
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

<h1>FormBharat 🇮🇳</h1>

<div class="card">

<h2>AI Form Filling Test</h2>

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

        showStatus("✅ Form analyzed and filled successfully");

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

    </style>

</head>


<body>

<div class="container">

    <h1>FormBharat 🇮🇳</h1>

    <div class="subtitle">
        AI Assisted Form Filling
    </div>

    <div class="card">
        <h2>Dashboard</h2>
        <div class="actions">
            <a href="/profile">Profile</a>
            <a href="/documents">Documents</a>
            <a href="/vacancies">Vacancies</a>
            <a href="/applications">Applications</a>
            <a href="/test-form">Form Filling</a>
        </div>
    </div>


    <div class="card">

        <h2>Test Form</h2>

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


    <div class="card">

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

            showRootResult(
                JSON.stringify(data.result, null, 2)
            );

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
}

_MOBILE_NAV = """
<nav class="fb-nav" aria-label="FormBharat">
<a href="/profile">Profile</a>
<a href="/documents">Documents</a>
<a href="/vacancies">Vacancies</a>
<a href="/applications">Applications</a>
<a href="/">Form</a>
</nav>
<style>
.fb-nav{display:flex;flex-wrap:wrap;gap:8px;margin:0 auto 16px;max-width:700px}
.fb-nav a{flex:1 1 30%;min-width:6.5rem;box-sizing:border-box;text-align:center;padding:12px 8px;background:#146c43;color:#fff;text-decoration:none;border-radius:8px;font-weight:bold;font-size:16px}
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

    return render_template_string(PAGE)


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
<h1>Vacancies</h1>
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
<h1>Applications</h1>
<label for="profile_id">Profile ID</label>
<input id="profile_id" type="number" min="1" max="5" inputmode="numeric">
<button type="button" id="load">Show applications</button>
<p id="application-message">Enter a profile ID to view applications.</p>
<div id="application-list"></div>
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
    addLine(card, "Status:", item.status);
    addLine(card, "Vacancy:", item.vacancy_id);
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
    return APPLICATIONS_PAGE


# --------------------------------------------------
# Health check
# --------------------------------------------------

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
        TEST_FORM_HTML
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

