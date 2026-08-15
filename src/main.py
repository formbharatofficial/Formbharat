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
    from app.ai_engine import FormBharatAI
except Exception:
    FormBharatAI = None


app = Flask(__name__)


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
<form>
    <label for="name">Full Name</label>
    <input
        id="name"
        name="name"
        type="text"
        placeholder="Enter your name"
    >

    <label for="email">Email</label>
    <input
        id="email"
        name="email"
        type="email"
        placeholder="Enter email"
    >

    <label for="mobile">Mobile Number</label>
    <input
        id="mobile"
        name="mobile"
        type="tel"
        placeholder="Enter mobile number"
    >

    <label for="dob">Date of Birth</label>
    <input
        id="dob"
        name="dob"
        type="date"
    >

    <label for="address">Address</label>
    <input
        id="address"
        name="address"
        type="text"
        placeholder="Enter address"
    >

    <label for="country">Country</label>
    <select id="country" name="country">
        <option value="in">India</option>
        <option value="us">USA</option>
    </select>
</form>
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

        profile = data.get("profile", {})


        if not isinstance(profile, dict):

            return jsonify({
                "success": False,
                "error": "Invalid profile data"
            }), 400


        # ------------------------------------------
        # Basic profile information
        # ------------------------------------------

        result = {

            "message":
                "Form received successfully.",

            "profile":
                profile,

            "fields_detected": [
                "name",
                "email",
                "mobile",
                "dob",
                "address"
            ],

            "next_step":
                "Profile matching engine can now process these fields."
        }


        # ------------------------------------------
        # Try AI engine if available
        # ------------------------------------------

        if FormBharatAI:

            try:

                ai = FormBharatAI()

                ai_result = None


                # Try common method names safely

                if hasattr(ai, "analyze_profile"):

                    ai_result = ai.analyze_profile(profile)

                elif hasattr(ai, "analyze"):

                    ai_result = ai.analyze(profile)

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

