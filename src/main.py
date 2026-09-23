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
)

init_vacancy_db()


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
            "error": str(error)
        }), 500


@app.route("/api/vacancies", methods=["GET"])
def list_vacancies_api():
    try:
        return jsonify({
            "success": True,
            "vacancies": list_vacancies()
        })
    except Exception as error:
        return jsonify({
            "success": False,
            "error": str(error)
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
            "error": str(error)
        }), 500


# --------------------------------------------------
# Phase 2 Profile Media
# Photo / Signature use the existing Document Vault.
# --------------------------------------------------

@app.route("/api/profile/<int:profile_id>/media/<media_type>",
           methods=["POST"])
def upload_profile_media(profile_id, media_type):
    from app.profile import profile_exists
    from app.document_vault import STORAGE_DIR, allowed_file
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


from app.document_vault import (
    register_document_vault,
    register_document_vault_ui,
    DB_PATH as DOCUMENTS_DB_PATH,
)
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
        return jsonify({"success": False, "error": str(error)}), 500

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

async function analyzeAndFill() {

    const form = document.getElementById("testForm");

    const html = form.outerHTML;

    document.getElementById("status").innerHTML =
        "🤖 FormBharat analyzing fields...";

    document.getElementById("result").innerHTML =
        "";

    try {

        const response = await fetch("/analyze", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                html: html
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

        document.getElementById("status").innerHTML =
            "✅ Form analyzed and filled successfully";

        document.getElementById("result").innerHTML =
            "<b>Fields detected:</b> " +
            result.fields_detected +
            "<br><br>" +

            "<b>Fields filled:</b> " +
            (result.filled_count || 0) +
            "<br><br>" +

            "<b>Fields skipped:</b> " +
            (result.skipped_count || 0) +
            "<br><br>" +

            "<pre>" +
            JSON.stringify(
                result.filled || [],
                null,
                2
            ) +
            "</pre>";

    }

    catch (error) {

        document.getElementById("status").innerHTML =
            "❌ Error";

        document.getElementById("result").innerHTML =
            "<pre>" +
            error +
            "</pre>";

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
            padding: 13px;
            border: 1px solid #ccc;
            border-radius: 8px;
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

        <h2>Test Form</h2>

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


        <button onclick="analyzeForm()">
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

async function analyzeForm() {

    const profile = {

        name:
            document.getElementById("name").value,

        email:
            document.getElementById("email").value,

        mobile:
            document.getElementById("mobile").value,

        dob:
            document.getElementById("dob").value,

        address:
            document.getElementById("address").value
    };


    document.getElementById("status").innerHTML =
        "AI analyzing form...";


    document.getElementById("result").innerHTML =
        "";


    try {

        const response = await fetch("/analyze", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                profile: profile
            })
        });


        const data = await response.json();


        if (data.success) {

            document.getElementById("status").innerHTML =
                '<span class="success">Analysis successful ✓</span>';


            document.getElementById("result").innerHTML =
                "<pre>" +
                JSON.stringify(data.result, null, 2) +
                "</pre>";

        }

        else {

            document.getElementById("status").innerHTML =
                '<span class="error">Error</span>';


            document.getElementById("result").innerHTML =
                "<pre>" +
                JSON.stringify(data, null, 2) +
                "</pre>";
        }


    }

    catch (error) {

        document.getElementById("status").innerHTML =
            '<span class="error">Server error</span>';


        document.getElementById("result").innerHTML =
            "<pre>" +
            error +
            "</pre>";
    }

}

</script>

</body>

</html>
"""


# --------------------------------------------------
# Home
# --------------------------------------------------

@app.route("/")
def home():

    return render_template_string(PAGE)


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

@app.route("/analyze", methods=["POST"])
def analyze():

    try:

        data = request.get_json(silent=True) or {}

        # Bible boundary:
        # Raw Profile must never be used for form filling.
        # Form filling may use only an explicitly Verified Profile.
        profile_id = data.get("profile_id", 1)

        try:
            profile_id = int(profile_id)
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "error": "profile_id must be an integer between 1 and 5"
            }), 400

        profile = get_verified_profile(profile_id)

        html = data.get("html", "")

        result = {
            "message": "Form received successfully.",
            "profile": profile,
            "verified_profile": profile is not None,
        }

        # --------------------------------------------------
        # FORM AUTOMATION PIPELINE
        # HTML → Reader → Analyzer → Profile Matcher
        # --------------------------------------------------

        if html:

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

        else:

            result["fields_detected"] = 0
            result["fields"] = []
            result["matched_fields"] = []

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

                result["ai_warning"] = str(ai_error)

        return jsonify({
            "success": True,
            "result": result
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "error": str(error)
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

if __name__ == "__main__":

    print("")
    print("================================")
    print(" FormBharat Server")
    print("================================")
    print("Home   : http://127.0.0.1:5000/")
    print("Health : http://127.0.0.1:5000/health")
    print("Analyze: POST /analyze")
    print("================================")
    print("")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )

