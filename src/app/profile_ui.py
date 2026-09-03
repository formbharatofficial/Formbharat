from flask import jsonify, render_template_string, request, redirect, url_for
from app.profile import init_db, save_profile, get_profile

PROFILE_PAGE = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FormBharat - Profile</title>
<style>
body{font-family:Arial,sans-serif;background:#f4f7f6;margin:0;padding:20px}
.container{max-width:700px;margin:auto}
.card{background:white;padding:20px;border-radius:14px;box-shadow:0 2px 8px rgba(0,0,0,.08)}
h1{color:#146c43}
label{display:block;margin-top:14px;margin-bottom:6px;font-weight:bold}
input,select{width:100%;box-sizing:border-box;padding:13px;border:1px solid #ccc;border-radius:8px;font-size:16px}
button{width:100%;margin-top:20px;padding:14px;background:#146c43;color:white;border:0;border-radius:8px;font-size:17px;font-weight:bold}
.success{color:#146c43;font-weight:bold;margin-bottom:12px}
</style>
</head>
<body>
<div class="container">
<div class="card">
<h1>FormBharat 👤</h1>
<p>My Profile</p>

{% if saved %}
<div class="success">✓ Profile saved successfully</div>
{% endif %}

<form method="POST">

<label>Full Name</label>
<input name="name" value="{{ profile.name }}" placeholder="Enter your name">

<label>Email</label>
<input name="email" value="{{ profile.email }}" placeholder="Enter email">

<label>Mobile Number</label>
<input name="mobile" value="{{ profile.mobile }}" placeholder="Enter mobile number">

<label>Date of Birth</label>
<input name="dob" type="date" value="{{ profile.dob }}">

<label>Gender</label>
<input name="gender" value="{{ profile.gender }}" placeholder="Male / Female / Other">

<label>Nationality</label>
<input name="nationality" value="{{ profile.nationality }}" placeholder="Nationality">

<label>Category</label>
<input name="category" value="{{ profile.category }}" placeholder="General / OBC / SC / ST / EWS">

<label>Father Name</label>
<input name="father_name" value="{{ profile.father_name }}" placeholder="Father's name">

<label>Mother Name</label>
<input name="mother_name" value="{{ profile.mother_name }}" placeholder="Mother's name">

<label>Address</label>
<input name="address" value="{{ profile.address }}" placeholder="Full address">

<label>State</label>
<input name="state" value="{{ profile.state }}" placeholder="State">

<label>District</label>
<input name="district" value="{{ profile.district }}" placeholder="District">

<label>Pincode</label>
<input name="pincode" value="{{ profile.pincode }}" placeholder="Pincode">

<label>10th Roll Number</label>
<input name="tenth_roll_number" value="{{ profile.tenth_roll_number }}">

<label>10th Passing Year</label>
<input name="tenth_passing_year" value="{{ profile.tenth_passing_year }}">

<label>10th Marks</label>
<input name="tenth_marks" value="{{ profile.tenth_marks }}">

<label>10th Percentage</label>
<input name="tenth_percentage" value="{{ profile.tenth_percentage }}">

<label>12th Roll Number</label>
<input name="twelfth_roll_number" value="{{ profile.twelfth_roll_number }}">

<label>12th Passing Year</label>
<input name="twelfth_passing_year" value="{{ profile.twelfth_passing_year }}">

<label>12th Marks</label>
<input name="twelfth_marks" value="{{ profile.twelfth_marks }}">

<label>12th Percentage</label>
<input name="twelfth_percentage" value="{{ profile.twelfth_percentage }}">

<label>Graduation Degree</label>
<input name="graduation_degree" value="{{ profile.graduation_degree }}">

<label>Graduation Roll Number</label>
<input name="graduation_roll_number" value="{{ profile.graduation_roll_number }}">

<label>Graduation Passing Year</label>
<input name="graduation_passing_year" value="{{ profile.graduation_passing_year }}">

<label>Graduation Marks</label>
<input name="graduation_marks" value="{{ profile.graduation_marks }}">

<label>Graduation Percentage</label>
<input name="graduation_percentage" value="{{ profile.graduation_percentage }}">

<label>Post Graduation Degree</label>
<input name="post_graduation_degree" value="{{ profile.post_graduation_degree }}">

<label>Post Graduation Roll Number</label>
<input name="post_graduation_roll_number" value="{{ profile.post_graduation_roll_number }}">

<label>Post Graduation Passing Year</label>
<input name="post_graduation_passing_year" value="{{ profile.post_graduation_passing_year }}">

<label>Post Graduation Marks</label>
<input name="post_graduation_marks" value="{{ profile.post_graduation_marks }}">

<label>Post Graduation Percentage</label>
<input name="post_graduation_percentage" value="{{ profile.post_graduation_percentage }}">

<label>Diploma Name</label>
<input name="diploma_name" value="{{ profile.diploma_name }}">

<label>Diploma Roll Number</label>
<input name="diploma_roll_number" value="{{ profile.diploma_roll_number }}">

<label>Diploma Passing Year</label>
<input name="diploma_passing_year" value="{{ profile.diploma_passing_year }}">

<label>Diploma Marks</label>
<input name="diploma_marks" value="{{ profile.diploma_marks }}">

<label>Diploma Percentage</label>
<input name="diploma_percentage" value="{{ profile.diploma_percentage }}">

<label>Other Qualification</label>
<input name="other_qualification" value="{{ profile.other_qualification }}">


<label>Country</label>
<select name="country">
<option value="in" {% if profile.country == "in" %}selected{% endif %}>India</option>
<option value="us" {% if profile.country == "us" %}selected{% endif %}>USA</option>
</select>

<button type="submit">Save Profile</button>
</form>
</div>
</div>
</body>
</html>
"""

def register_profile_ui(app):
    init_db()

    def profile_id_from_path(profile_id):
        try:
            return int(profile_id)
        except (TypeError, ValueError):
            raise ValueError("profile_id must be an integer between 1 and 5")

    @app.route("/profile", methods=["GET", "POST"])
    def profile_page():
        if request.method == "POST":
            save_profile({
                "name": request.form.get("name", ""),
                "email": request.form.get("email", ""),
                "mobile": request.form.get("mobile", ""),
                "dob": request.form.get("dob", ""),
                "address": request.form.get("address", ""),
                "country": request.form.get("country", "in"),
                "father_name": request.form.get("father_name", ""),
                "mother_name": request.form.get("mother_name", ""),
                "gender": request.form.get("gender", ""),
                "nationality": request.form.get("nationality", ""),
                "category": request.form.get("category", ""),
                "state": request.form.get("state", ""),
                "district": request.form.get("district", ""),
                "pincode": request.form.get("pincode", ""),
                "tenth_roll_number": request.form.get("tenth_roll_number", ""),
                "tenth_passing_year": request.form.get("tenth_passing_year", ""),
                "tenth_marks": request.form.get("tenth_marks", ""),
                "tenth_percentage": request.form.get("tenth_percentage", ""),
                "twelfth_roll_number": request.form.get("twelfth_roll_number", ""),
                "twelfth_passing_year": request.form.get("twelfth_passing_year", ""),
                "twelfth_marks": request.form.get("twelfth_marks", ""),
                "twelfth_percentage": request.form.get("twelfth_percentage", ""),
                "graduation_degree": request.form.get("graduation_degree", ""),
                "graduation_roll_number": request.form.get("graduation_roll_number", ""),
                "graduation_passing_year": request.form.get("graduation_passing_year", ""),
                "graduation_marks": request.form.get("graduation_marks", ""),
                "graduation_percentage": request.form.get("graduation_percentage", ""),

                "post_graduation_degree": request.form.get("post_graduation_degree", ""),
                "post_graduation_roll_number": request.form.get("post_graduation_roll_number", ""),
                "post_graduation_passing_year": request.form.get("post_graduation_passing_year", ""),
                "post_graduation_marks": request.form.get("post_graduation_marks", ""),
                "post_graduation_percentage": request.form.get("post_graduation_percentage", ""),
                "diploma_name": request.form.get("diploma_name", ""),
                "diploma_roll_number": request.form.get("diploma_roll_number", ""),
                "diploma_passing_year": request.form.get("diploma_passing_year", ""),
                "diploma_marks": request.form.get("diploma_marks", ""),
                "diploma_percentage": request.form.get("diploma_percentage", ""),
                "other_qualification": request.form.get("other_qualification", ""),
            })
            return redirect(url_for("profile_page", saved=1))

        profile = get_profile()
        return render_template_string(
            PROFILE_PAGE,
            profile=profile,
            saved=request.args.get("saved") == "1"
        )

    @app.route("/api/profile/<profile_id>", methods=["GET"])
    def get_profile_api(profile_id):
        try:
            saved_profile = get_profile(profile_id_from_path(profile_id))
            return jsonify({
                "success": True,
                "profile": saved_profile
            })
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

    @app.route("/api/profile/<profile_id>", methods=["POST"])
    def save_profile_api(profile_id):
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "success": False,
                "error": "Invalid or missing JSON data"
            }), 400

        try:
            parsed_profile_id = profile_id_from_path(profile_id)
            save_profile(data, parsed_profile_id)
            return jsonify({
                "success": True,
                "message": "Profile saved successfully",
                "profile": get_profile(parsed_profile_id)
            })
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
