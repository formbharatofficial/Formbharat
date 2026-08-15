from flask import render_template_string, request, redirect, url_for
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

<label>Address</label>
<input name="address" value="{{ profile.address }}" placeholder="Enter address">

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

    @app.route("/profile", methods=["GET", "POST"])
    def profile_page():
        if request.method == "POST":
            save_profile({
                "name": request.form.get("name", ""),
                "email": request.form.get("email", ""),
                "mobile": request.form.get("mobile", ""),
                "dob": request.form.get("dob", ""),
                "address": request.form.get("address", ""),
                "country": request.form.get("country", "in")
            })
            return redirect(url_for("profile_page", saved=1))

        profile = get_profile()
        return render_template_string(
            PROFILE_PAGE,
            profile=profile,
            saved=request.args.get("saved") == "1"
        )
