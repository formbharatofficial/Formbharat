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

from app.document_vault import register_document_vault
register_document_vault(app)


# --------------------------------------------------
# Profile UI
# --------------------------------------------------

if register_profile_ui:
    try:
        register_profile_ui(app)
    except Exception as e:
        print("Profile UI warning:", e)


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

        profile = data.get("profile")

        if profile is None:
            from app.profile import get_profile
            profile = get_profile()

        if not isinstance(profile, dict):
            return jsonify({
                "success": False,
                "error": "Invalid profile data"
            }), 400

        html = data.get("html", "")

        result = {
            "message": "Form received successfully.",
            "profile": profile
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

