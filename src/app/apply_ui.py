"""Job detail, board account (when the job needs it), profile check, fee, start."""

import os
import tempfile
from urllib.parse import urlparse

from flask import Response, current_app, jsonify, redirect, render_template_string, request, url_for

from app.board_registration import (
    BoardRegistrationError,
    board_config,
    list_records,
    requirement_for_vacancy,
    save_record,
)
from app.document_encryption import DocumentStorageError, read_bytes
from app.document_fit import fit_bounded_copy
from app.document_vault import get_db
from app.media_rules import RRB_SIGNATURE, photo_guidance
from app.fill_fee import (
    FEE_RUPEES,
    FillFeeError,
    confirm_razorpay_payment,
    create_fee,
    fee_settings,
    has_paid_fee,
    latest_fee,
    upi_link,
    upi_request,
)
from app.ownership import SlotAccessError, current_user_id, owned_slot_for_session
from app.profile import get_profile
from app.request_guard import issue_csrf_token
from app.vacancy import get_vacancy


_CHECK_FIELDS = (
    ("name", "Personal Details"),
    ("dob", "Date of birth"),
    ("mobile", "Mobile"),
    ("email", "Email"),
    ("father_name", "Father name"),
    ("address", "Address"),
    ("tenth_roll_number", "10th roll"),
)

JOB_PAGE = """
<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FormBharat Job</title>
</head>
<body>
<div class="container">
<section class="card fb-hero">
<h1>{{ vacancy.title }}</h1>
<p>क्या आप इस फॉर्म को ऑटो-फिल से भरना चाहते हैं?</p>
</section>
<section class="card">
<p>हाँ पर सरकारी साइट नई टैब में खुलेगी। ऐप आपकी सेव प्रोफाइल और दस्तावेज़ से भरेगा। ओटीपी, कैप्चा, पासवर्ड और Submit आप खुद करेंगे।</p>
<a class="fb-go" id="fb-yes" href="{{ yes_url }}">हाँ, ऑटो-फिल से भरो</a>
</section>
{% if vacancy.official_link %}
<section class="card">
<p>नहीं पर सिर्फ सरकारी साइट खुलेगी। ऐप उस पर कुछ नहीं लिखेगा।</p>
<a class="fb-go fb-ghost" href="{{ vacancy.official_link }}" target="_blank" rel="noopener noreferrer">नहीं, मैं खुद भरूँगा</a>
</section>
{% endif %}
{% if open_site %}
<script>
document.getElementById("fb-yes").addEventListener("click", function () {
  window.open({{ open_site | tojson }}, "_blank", "noopener");
});
</script>
{% endif %}
</div>
</body>
</html>
"""

METHOD_PAGE = """
<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FormBharat Fill Method</title>
</head>
<body>
<div class="container">
<section class="card fb-hero">
<h1>फॉर्म भरने की विधि</h1>
<p class="fb-note">AI सहायता प्रोफाइल की सेव फ़ील्ड दिखाती है। मैन्युअल में आधिकारिक साइट आप खुद भरते हो।</p>
</section>
<a class="fb-go" href="{{ pay_url }}">FormBharat से सहायता (AI)</a>
{% if official_link %}
<a class="fb-go fb-ghost" href="{{ official_link }}" target="_blank" rel="noopener noreferrer">मैं स्वयं भरूँगा</a>
{% endif %}
<p class="fb-note">OTP, CAPTCHA, and final Submit stay with you.</p>
</div>
</body>
</html>
"""

CHECK_PAGE = """
<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FormBharat Profile Check</title>
</head>
<body>
<div class="container">
<section class="card fb-hero">
<h1>आवेदन जारी रखें</h1>
<p class="fb-note">प्रोफाइल जाँच। Jo save hai wahi dikhega. Missing field ko hum pura nahi mante.</p>
</section>
<section class="card">
{% for item in checks %}
<div class="fb-line"><span>{{ item.label }}</span>{% if item.ok %}<b class="ok">उपलब्ध</b>{% else %}<b>missing</b>{% endif %}</div>
{% endfor %}
</section>
<a class="fb-go" href="{{ pay_url }}">आगे बढ़ें · ₹{{ fee }}</a>
<p class="fb-note">ऊपर जो missing है वही कमी है। सब उपलब्ध हो तो आगे ₹{{ fee }} है, फिर फॉर्म भरना।</p>
</div>
</body>
</html>
"""

PAY_PAGE = """
<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FormBharat Payment</title>
</head>
<body>
<div class="container">
<section class="card fb-hero">
<h1>भुगतान करें Make Payment</h1>
<p class="fb-kicker">Form Filling Service Fee</p>
<p class="fb-rupee">₹{{ fee }}</p>
<p class="fb-note">per application</p>
</section>
<section class="card">
<p class="fb-note">Ye ₹{{ fee }} FormBharat ki filling service hai. Sarkari form ki alag fee official site par aap doge.</p>
<p class="fb-note">OTP, CAPTCHA, and final Submit stay with you.</p>
{% if error %}<p class="fb-alert">{{ error }}</p>{% endif %}
{% if paid %}
<p class="ok">₹{{ fee }} mil gaya. Ab start-fill khul sakta hai.</p>
<a class="fb-go" href="{{ start_url }}">आगे बढ़ें</a>
{% else %}
<form method="POST">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<label class="fb-choice"><input type="radio" name="method" value="upi" checked> Wallet / UPI / PhonePe</label>
<label class="fb-choice"><input type="radio" name="method" value="card"> Debit/Credit Card</label>
<label class="fb-choice"><input type="radio" name="method" value="netbanking"> Net Banking</label>
<button class="fb-go" type="submit">₹{{ fee }} का भुगतान करें Pay ₹{{ fee }}</button>
</form>
{% if upi %}
<p class="fb-note">UPI ऐप में ₹{{ fee }} खुलेगा। PhonePe यह नहीं बताता कि पैसे आ गए, इसलिए paid खुद नहीं लिखा जाएगा।</p>
<p><a class="fb-go" href="{{ upi }}">UPI से ₹{{ fee }} भेजें</a></p>
{% endif %}
{% if not collectable %}
<p class="fb-note">UPI आईडी या Razorpay चाबी नहीं है। unpaid को paid नहीं लिखा जाएगा।</p>
{% endif %}
<p class="fb-note">Status: {{ status }}। पुराना शुरू पन्ना तभी खुलता है जब Razorpay paid लिखे। सरकारी साइट पर लिखना नीचे वाले बटन से अभी शुरू होता है।</p>
{% endif %}
<form method="POST" action="{{ fill_url }}">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<button class="fb-go" type="submit">सरकारी साइट पर भरो</button>
</form>
<p class="fb-note">Edge खुलेगा। सेव प्रोफाइल और दस्तावेज़ वहाँ लिखे जाएँगे। लाइव फोटो, ओटीपी, कैप्चा, पासवर्ड और Submit आप करेंगे। Submit नहीं होगा।</p>
</section>
</div>
</body>
</html>
"""

FILL_PAGE = """
<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FormBharat Fill</title>
</head>
<body>
<div class="container">
<section class="card fb-hero">
<h1>सरकारी साइट पर लिखा</h1>
<p>{{ filled_count }} खाने भरे। {{ skipped_count }} छोड़े।</p>
<p>Submit नहीं हुआ।</p>
</section>
<section class="card">
{% if not verified %}
<p>सेव प्रोफाइल तैयार नहीं थी, इसलिए खाने खाली रहे। प्रोफाइल सेव करके फिर भरो।</p>
{% endif %}
{% for name in fields %}
<p>{{ name }}</p>
{% endfor %}
{% if attached %}
<p>दस्तावेज़ लगाए: {{ attached }}</p>
{% endif %}
{% if needs_user %}
<p>लाइव फोटो या फाइल चुनना आपके पास रहा: {{ needs_user }}</p>
{% endif %}
<p class="fb-note">लाइव फोटो, ओटीपी, कैप्चा, पासवर्ड और Submit आप करेंगे। paid नहीं लिखा गया।</p>
{% if page_url %}
<p class="fb-note">{{ page_url }}</p>
{% endif %}
<form method="POST" action="{{ again_url }}">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<input type="hidden" name="again" value="yes">
<button class="fb-go" type="submit">खुले पन्ने पर फिर भरो</button>
</form>
<p class="fb-note">लॉगिन या ओटीपी के बाद यही बटन उसी खुले पन्ने के खाने भरेगा। Submit नहीं होगा।</p>
</section>
</div>
</body>
</html>
"""

START_PAGE = """
<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FormBharat Start Fill</title>
</head>
<body>
<div class="container">
<section class="card fb-hero">
<h1>फॉर्म भरना शुरू</h1>
<p class="fb-note">भुगतान रिकॉर्ड हो गया है। आगे प्रोफाइल की सेव फ़ील्ड दिखेंगी। Sarkari website par OTP, CAPTCHA, and final Submit stay with you.</p>
</section>
{% if official_link %}
<a class="fb-go" href="{{ official_link }}" target="_blank" rel="noopener noreferrer">Open the official page</a>
{% endif %}
<a class="fb-go" href="{{ personal_url }}">आगे बढ़ें · व्यक्तिगत विवरण</a>
<p class="fb-note">Photo aur signature official page par aap select karoge.</p>
</div>
</body>
</html>
"""

ACCOUNT_PAGE = """
<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FormBharat Board Account</title>
</head>
<body>
<div class="container">
<section class="card fb-hero">
<p class="fb-kicker">{{ vacancy.title }}</p>
<h1>{{ board.account_name_hi }}</h1>
<p class="fb-note">{{ board.account_name_en }} · {{ board.board_name_hi }}</p>
<p class="fb-note">Yeh kadam isi bharti ke liye hai. Alag se board choose nahi karna.</p>
</section>
{% if error %}<p class="fb-alert">{{ error }}</p>{% endif %}
{% if saved %}
<section class="card">
<p class="ok">Is profile par {{ board.account_name_en }} save hai.</p>
{% if saved.registration_number %}<p>Number: {{ saved.registration_number }}</p>{% endif %}
<p class="fb-note">Saved number is user-confirmed, not independently verified.</p>
<a class="fb-go" href="{{ check_url }}">आगे बढ़ें · प्रोफाइल जाँच</a>
</section>
{% endif %}
{% if step == "need" %}
<section class="card">
<h2>पंजीकरण की आवश्यकता</h2>
<p>इस भर्ती के लिए {{ board.account_name_hi }} आवश्यक है।</p>
<p class="fb-note">This job requires {{ board.account_name_en }}.</p>
<p class="fb-note">Official site: {{ board.portal_home }}</p>
<p class="fb-note">{{ board.edit_warning_hi }}</p>
<a class="fb-go" href="{{ ask_url }}">आगे बढ़ें</a>
</section>
{% elif step == "ask" %}
<section class="card">
<h2>{{ board.account_name_hi }}</h2>
<p>क्या आपके पास {{ board.account_name_hi }} है?</p>
<p>सेव नंबर हो तो ऐप वही भरेगा। आपके पास हो और सेव न हो तो आप नंबर लिखोगे। बिल्कुल न हो तो प्रोफाइल और दस्तावेज़ से नया बनेगा, फिर फॉर्म।</p>
{% if saved %}
<p class="ok">ऐप में सेव नंबर है। आगे वही भरेगा।</p>
<a class="fb-go" href="{{ check_url }}">आगे बढ़ें · प्रोफाइल जाँच</a>
{% else %}
<a class="fb-go" href="{{ existing_url }}">हाँ, मेरे पास है</a>
<a class="fb-go fb-ghost" href="{{ new_url }}">नहीं, प्रोफाइल से नया बनाओ</a>
{% endif %}
<a class="fb-go fb-ghost" href="{{ board.portal_url }}" target="_blank" rel="noopener noreferrer">अकाउंट वाली साइट खोलें</a>
{% if board.board == "rrb" %}
<p>यह SSC One Time Registration नहीं है। साइट rrbapply.gov.in है।</p>
{% endif %}
</section>
{% elif step == "portal" %}
<section class="card">
<h2>आधिकारिक पोर्टल खोलें</h2>
<p>वेबसाइट खोलें। लॉगिन और पासवर्ड आप खुद रखोगे। FormBharat पासवर्ड सेव नहीं करता।</p>
<a class="fb-go" href="{{ board.portal_url }}" target="_blank" rel="noopener noreferrer">वेबसाइट खोलें</a>
<p class="fb-note">{{ board.portal_home }}</p>
<a class="fb-go" href="{{ existing_url }}">आगे बढ़ें · नंबर लिखें</a>
</section>
{% elif step == "existing" %}
<section class="card">
<h2>अकाउंट विवरण दर्ज करें</h2>
<p class="fb-note">नंबर लिखना वैकल्पिक है। बिना सेव भी आवेदन जारी रह सकता है।</p>
<p class="fb-note">Official page par jo number dikha, wahi yahan likho. Password, OTP, CAPTCHA yahan nahi.</p>
<form method="POST">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<input type="hidden" name="account_path" value="existing">
<label for="registration_number">{{ board.account_name_en }} number</label>
<input id="registration_number" name="registration_number" autocomplete="off">
<label class="fb-check"><input type="checkbox" name="consent" value="yes"> Number is profile par save karo. Saved number is user-confirmed, not independently verified. Password, OTP, CAPTCHA, Aadhaar save nahi honge.</label>
<button class="fb-go" type="submit">सेव करें और आगे बढ़ें</button>
</form>
<a class="fb-go" href="{{ check_url }}">बिना नंबर सेव आगे बढ़ें</a>
</section>
{% elif step == "new" %}
<section class="card">
<h2>तैयारी जाँच</h2>
<p>Photograph — {% if photo_ready %}सेव है{% else %}missing{% endif %}</p>
<p>हस्ताक्षर — {% if sign_ready %}सेव है{% else %}missing{% endif %}</p>
<p>FormBharat in saved fields ko {{ board.account_name_hi }} ke liye taiyar karta hai. Khali field yahin se bhar nahi mante.</p>
{% for row in profile_rows %}
<div class="fb-line"><span>{{ row.label }}</span>{% if row.ok %}<b class="ok">{{ row.value }}</b>{% else %}<b>profile me missing</b>{% endif %}</div>
{% endfor %}
<p class="fb-note">आगे OTP और CAPTCHA आप डालोगे।</p>
<a class="fb-go" href="/profile">प्रोफाइल में जो missing है, वहाँ भरो</a>
<a class="fb-go" href="{{ profile_url }}">आगे बढ़ें · प्रोफाइल जानकारी</a>
</section>
{% elif step == "profile" %}
<section class="card">
<h2>प्रोफाइल डेटा की समीक्षा</h2>
<p>Aapki profile se yeh jaankari {{ board.account_name_hi }} ke liye taiyar hai.</p>
{% for row in profile_rows %}
<div class="fb-line"><span>{{ row.label }}</span>{% if row.ok %}<b class="ok">{{ row.value }}</b>{% else %}<b>missing</b>{% endif %}</div>
{% endfor %}
<a class="fb-go" href="{{ progress_url }}">आगे बढ़ें · Auto-Fill स्थिति</a>
</section>
{% elif step == "progress" %}
<section class="card">
<h2>आधिकारिक पोर्टल और सहायता</h2>
<p>{{ ready_count }} / {{ profile_rows|length }} profile fields saved hain. Missing ko bhara hua nahi maante.</p>
{% for row in profile_rows %}
<div class="fb-line"><span>{{ row.label }}</span>{% if row.ok %}<b class="ok">तैयार</b>{% else %}<b>missing</b>{% endif %}</div>
{% endfor %}
<p class="fb-note">OTP aur CAPTCHA is list me nahi hain. Woh aap daloge.</p>
<a class="fb-go" href="{{ handoff_url }}">आगे बढ़ें — OTP और CAPTCHA आप डालोगे</a>
</section>
{% elif step == "handoff" %}
<section class="card">
<h2>OTP और CAPTCHA आपके पास</h2>
<p>Official page par aap hi OTP daloge. Aap hi CAPTCHA daloge. FormBharat OTP nahi bhejta, CAPTCHA solve nahi karta, aur password ya Aadhaar save nahi karta.</p>
<p class="fb-note">Final Submit bhi official page par aap karoge. App yeh nahi kahega ki {{ board.account_name_en }} ban chuka hai jab tak aap number khud na likho.</p>
<ol>
{% for item in board.steps_hi %}
<li>{{ item }}</li>
{% endfor %}
</ol>
{% for item in board.portal_only %}
<p class="fb-note">{{ item.label_hi }}</p>
{% endfor %}
<a class="fb-go" href="{{ board.portal_url }}" target="_blank" rel="noopener noreferrer">आधिकारिक साइट खोलें</a>
<p class="fb-note">{{ board.portal_home }}</p>
<a class="fb-go" href="{{ outcome_url }}">नंबर मिल गया — सेव की अनुमति</a>
</section>
{% elif step == "outcome" %}
<section class="card">
<h2>परिणाम</h2>
<p>क्या आधिकारिक पेज पर {{ board.account_name_hi }} बन गया?</p>
<p class="fb-note">हाँ तभी नंबर सेव होगा। नहीं चुनने पर कुछ सेव नहीं होता।</p>
<a class="fb-go" href="{{ save_url }}">हाँ, नंबर सेव करूँ</a>
<a class="fb-go" href="{{ portal_url }}">नहीं, पोर्टल फिर खोलें</a>
</section>
{% elif step == "save" %}
<section class="card">
<h2>क्या नंबर सेव करें?</h2>
<p>{{ board.account_name_hi }} banane ke baad FormBharat save karne ki anumati mangta hai. Na kahe to kuchh save nahi hoga.</p>
<form method="POST">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<input type="hidden" name="account_path" value="new">
<label for="registration_number">{{ board.account_name_en }} number</label>
<input id="registration_number" name="registration_number" autocomplete="off">
<label class="fb-check"><input type="checkbox" name="consent" value="yes"> Haan, is profile par number save karo. Saved number is user-confirmed, not independently verified.</label>
<button class="fb-go" type="submit">हाँ, सेव करें</button>
</form>
<a class="fb-go" href="{{ check_url }}">नहीं, सेव मत करो</a>
</section>
{% elif step == "saved" %}
<section class="card">
<h2>सेव किए गए खाते</h2>
{% if saved_records %}
{% for item in saved_records %}
<p><strong>{{ item.board }}</strong> — {% if item.registration_number %}{{ item.registration_number }}{% else %}number hidden{% endif %}</p>
<p class="fb-note">user-confirmed, not independently verified.</p>
{% endfor %}
{% else %}
<p>Is profile par abhi koi number save nahi hai.</p>
{% endif %}
<a class="fb-go" href="{{ check_url }}">आगे बढ़ें · प्रोफाइल जाँच</a>
</section>
{% endif %}
<p class="fb-note">Edge me jo khana bhar sakta hai, app likhega. OTP, CAPTCHA, password, live photo aur Submit aap karenge. Official home: {{ board.portal_home }}</p>
{% if board.board == "rrb" %}
<p class="fb-note">This is not an SSC One Time Registration. Use rrbapply.gov.in.</p>
{% endif %}
</div>
</body>
</html>
"""

WALK_PAGE = """
<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FormBharat {{ title }}</title>
</head>
<body>
<div class="container">
<section class="card fb-hero">
<h1>{{ title }}</h1>
<p class="fb-note">Yeh aapki saved profile hai. Sarkari site par yahi fields aapke saamne aati hain. Khali field ko bhara hua nahi maante.</p>
</section>
<section class="card">
{% for line in lines %}
<div class="fb-line"><span>{{ line }}</span></div>
{% endfor %}
</section>
<a class="fb-go" href="{{ prev_url }}">पिछला</a>
{% if extra_url %}
<a class="fb-go" href="{{ extra_url }}">{{ extra_label }}</a>
{% endif %}
<a class="fb-go" href="{{ next_url }}">{{ next_label }}</a>
</div>
</body>
</html>
"""

DONE_PAGE = """
<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FormBharat Application</title>
</head>
<body>
<div class="container">
<section class="card fb-hero">
<p class="fb-rupee">✓</p>
<h1>आवेदन</h1>
<p>{{ message }}</p>
</section>
<form method="POST">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<button class="fb-go" type="submit">मेरे आवेदन में सेव करें</button>
</form>
{% if official_link %}
<a class="fb-go" href="{{ official_link }}" target="_blank" rel="noopener noreferrer">आधिकारिक साइट खोलें</a>
{% endif %}
<a class="fb-go" href="/applications">मेरे आवेदन</a>
</div>
</body>
</html>
"""


def _require_login():
    if current_user_id() is None:
        return redirect(url_for("account_page"))
    return None


def _slot():
    try:
        return owned_slot_for_session()
    except SlotAccessError:
        return None


def _board_for_vacancy(vacancy):
    requirement = requirement_for_vacancy(vacancy)
    if requirement.get("state") != "required":
        return None
    return board_config(requirement["board"])


def _http_url(value):
    text = str(value or "").strip()
    if text.startswith("https://") or text.startswith("http://"):
        return text
    return ""


def _form_page_url(vacancy):
    """Use the form page. A notice PDF is not a form, so the board portal is used."""
    link = _http_url((vacancy or {}).get("official_link"))
    if link and ".pdf" not in urlparse(link).path.lower():
        return link
    board = _board_for_vacancy(vacancy)
    if board:
        return _http_url(board.get("portal_url"))
    return ""


def _site_fill(slot, url, again=False):
    from app.browser import BrowserSession
    from app.rendered_assist import run_local_assist

    try:
        return run_local_assist(
            {
                "profile_id": slot,
                "url": url,
                "action": "reread" if again else "open",
            },
            current_app.extensions.setdefault("local_browser_sessions", {}),
            BrowserSession,
        )
    except Exception as error:
        if isinstance(error, SlotAccessError):
            raise
        if isinstance(error, ValueError):
            raise
        if "playwright" in type(error).__module__:
            raise ValueError("यह पन्ना नहीं खुला") from error
        raise


def _fill_page(result, page_url, again_url):
    review = result.get("review") if isinstance(result, dict) else {}
    proposed = review.get("proposed") if isinstance(review, dict) else []
    names = []
    for item in proposed or []:
        if isinstance(item, dict):
            names.append(str(item.get("profile_key") or item.get("field") or ""))
    attachments = result.get("attachments") if isinstance(result, dict) else []
    attached = 0
    needs_user = 0
    for item in attachments or []:
        if not isinstance(item, dict):
            continue
        if item.get("status") == "attached":
            attached += 1
        elif item.get("status") == "needs_user":
            needs_user += 1
    return render_template_string(
        FILL_PAGE,
        filled_count=int(result.get("filled_count") or 0),
        skipped_count=int(result.get("skipped_count") or 0),
        verified=bool(result.get("verified_profile")),
        fields=[name for name in names if name],
        attached=attached,
        needs_user=needs_user,
        page_url=page_url,
        again_url=again_url,
        csrf_token=issue_csrf_token(),
    )


def _next_after_job(vacancy_id, vacancy):
    if _board_for_vacancy(vacancy) is None:
        return url_for("apply_check", vacancy_id=vacancy_id)
    return url_for("apply_account", vacancy_id=vacancy_id, path="ask")


def _saved_board_record(profile_id, board):
    if profile_id is None:
        return None
    try:
        records = list_records(profile_id)
    except BoardRegistrationError:
        return None
    for record in records:
        if record.get("board") == board:
            return record
    return None


def _profile_rows(profile, board):
    rows = []
    for field in board.get("fields") or []:
        value = str(profile.get(field["key"]) or "").strip()
        rows.append({
            "label": field["label_hi"],
            "value": value,
            "ok": bool(value),
        })
    return rows


def _signature_bytes(profile_id):
    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT storage_path FROM documents
            WHERE profile_id = ? AND lower(doc_type) IN ('signature', 'sign')
            ORDER BY id DESC LIMIT 1
            """,
            (profile_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None or not row["storage_path"]:
        return None
    try:
        return read_bytes(row["storage_path"])
    except (OSError, DocumentStorageError):
        return b""


def _documents(profile_id):
    types = set()
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT doc_type FROM documents WHERE profile_id = ?",
            (profile_id,),
        ).fetchall()
    finally:
        conn.close()
    for row in rows:
        types.add(str(row[0] or "").strip().lower())
    return types


def _checks(profile, docs):
    items = []
    for key, label in _CHECK_FIELDS:
        items.append({"label": label, "ok": bool(str(profile.get(key) or "").strip())})
    items.append({"label": "Photograph", "ok": any("photo" in item or "photograph" in item for item in docs)})
    items.append({"label": "Signature", "ok": any("sign" in item for item in docs)})
    items.append({
        "label": "Aadhaar / Other ID",
        "ok": any("aadhaar" in item or "aadhar" in item or "id" in item for item in docs),
    })
    return items


def register_apply_routes(app):
    other_forms = {
        "pan": ("PAN card", "https://www.incometax.gov.in/iec/foportal"),
        "ration": ("Ration card", "https://nfsa.gov.in/portal/state_portals"),
        "voter": ("Voter card", "https://voters.eci.gov.in/"),
        "licence": ("Driving licence", "https://sarathi.parivahan.gov.in/sarathiservice/stateSelection.do"),
        "passport": ("Passport", "https://www.passportindia.gov.in/psp/Apply"),
        "shram": ("Shram card", "https://www.eshram.gov.in/"),
        "ayushman": ("Ayushman card", "https://nha.gov.in/Ayushman-Card"),
        "kisan": ("Kisan Samman Nidhi", "https://www.pmkisan.gov.in/"),
    }

    def _other_form(form_key):
        item = other_forms.get(form_key)
        if item is None:
            return None
        return {"key": form_key, "title": item[0], "url": item[1]}

    @app.route("/other-fill/<form_key>")
    def other_fill_ask(form_key):
        form = _other_form(form_key)
        if form is None:
            return redirect(url_for("other_forms_page"))
        return render_template_string(
            """
<!DOCTYPE html>
<html lang="hi">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>FormBharat</title></head>
<body>
<div class="container">
<h1>{{ form.title }}</h1>
<p>क्या आप इस फॉर्म को ऑटो-फिल से भरना चाहते हैं?</p>
<section class="card">
<p>हाँ पर सरकारी साइट नई टैब में खुलेगी। ऐप आपकी सेव प्रोफाइल और दस्तावेज़ से भरेगा। ओटीपी, कैप्चा, पासवर्ड और Submit आप खुद करेंगे।</p>
<a class="fb-go" id="fb-yes" href="{{ yes_url }}">हाँ, ऑटो-फिल से भरो</a>
</section>
<section class="card">
<p>नहीं पर सिर्फ सरकारी साइट खुलेगी। ऐप उस पर कुछ नहीं लिखेगा।</p>
<a class="fb-go fb-ghost" href="{{ form.url }}" target="_blank" rel="noopener noreferrer">नहीं, मैं खुद भरूँगा</a>
</section>
{% if open_site %}
<script>
document.getElementById("fb-yes").addEventListener("click", function () {
  window.open({{ open_site | tojson }}, "_blank", "noopener");
});
</script>
{% endif %}
</div>
</body>
</html>
            """,
            form=form,
            yes_url=url_for("other_fill_check", form_key=form_key),
            open_site=_http_url(form["url"]),
        )

    @app.route("/other-fill/<form_key>/check")
    def other_fill_check(form_key):
        form = _other_form(form_key)
        if form is None:
            return redirect(url_for("other_forms_page"))
        gate = _require_login()
        if gate is not None:
            return gate
        slot = _slot()
        if slot is None:
            return redirect(url_for("profile_page"))
        return render_template_string(
            CHECK_PAGE,
            checks=_checks(get_profile(slot), _documents(slot)),
            pay_url=url_for("other_fill_pay", form_key=form_key),
            fee=FEE_RUPEES,
        )

    @app.route("/other-fill/<form_key>/pay")
    def other_fill_pay(form_key):
        form = _other_form(form_key)
        if form is None:
            return redirect(url_for("other_forms_page"))
        gate = _require_login()
        if gate is not None:
            return gate
        return render_template_string(
            """
<!DOCTYPE html>
<html lang="hi">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>FormBharat</title></head>
<body>
<div class="container">
<h1>₹{{ fee }}</h1>
<p>{{ form.title }} की जाँच हो चुकी है। यह FormBharat का शुल्क है। UPI ऐप में ₹{{ fee }} खुलेगा। ऐप यह नहीं देख सकता कि पैसे आ गए, इसलिए paid खुद नहीं लिखा जाएगा।</p>
{% if upi %}
<p><a class="fb-go" href="{{ upi }}">UPI से ₹{{ fee }} भेजें</a></p>
{% endif %}
<form method="POST" action="{{ fill_url }}">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<button class="fb-go" type="submit">सरकारी साइट पर भरो</button>
</form>
<p>Edge खुलेगा। सेव प्रोफाइल और दस्तावेज़ वहाँ लिखे जाएँगे। लाइव फोटो, ओटीपी, कैप्चा, पासवर्ड और Submit आप करेंगे। Submit नहीं होगा।</p>
<p><a href="{{ form.url }}" target="_blank" rel="noopener noreferrer">{{ form.url }}</a></p>
</div>
</body>
</html>
            """,
            form=form,
            fee=FEE_RUPEES,
            upi=upi_request(form["title"]),
            fill_url=url_for("other_fill_site", form_key=form_key),
            csrf_token=issue_csrf_token(),
        )

    @app.route("/rrb-flow")
    def rrb_flow_sheet():
        from pathlib import Path
        sheet = Path(__file__).resolve().parents[2] / "FormBharat_UI_References" / "RRB_screen_flow.html"
        return sheet.read_text(encoding="utf-8")

    @app.route("/job/<int:vacancy_id>")
    def job_page(vacancy_id):
        vacancy = get_vacancy(vacancy_id)
        if vacancy is None:
            return render_template_string(
                "<p>Vacancy not found.</p><p><a href='/vacancies'>Jobs</a></p>"
            ), 404
        return render_template_string(
            JOB_PAGE,
            vacancy=vacancy,
            yes_url=_next_after_job(vacancy_id, vacancy),
            open_site=_http_url(vacancy.get("official_link")),
            fee=FEE_RUPEES,
        )

    @app.route("/apply/<int:vacancy_id>/account", methods=["GET", "POST"])
    def apply_account(vacancy_id):
        vacancy = get_vacancy(vacancy_id)
        if vacancy is None:
            return redirect(url_for("vacancies_page"))
        board = _board_for_vacancy(vacancy)
        if board is None:
            return redirect(url_for("apply_check", vacancy_id=vacancy_id))
        gate = _require_login()
        if gate is not None:
            return gate
        slot = _slot()
        if slot is None:
            return redirect(url_for("profile_page"))
        error = ""
        if request.method == "POST":
            path = str(request.form.get("account_path") or "").strip().lower()
            if path not in {"existing", "new"}:
                error = "account_path is not supported"
            elif request.form.get("consent") != "yes":
                error = "Number tabhi save hoga jab aap haan karo."
            else:
                try:
                    save_record(slot, {
                        "board": board["board"],
                        "account_path": path,
                        "registration_number": request.form.get("registration_number"),
                        "consent": True,
                        "consent_language": "hi",
                        "replace": True,
                    })
                    return redirect(url_for("apply_account", vacancy_id=vacancy_id, path="saved"))
                except BoardRegistrationError as exc:
                    error = str(exc)
            step = "save" if path == "new" else "existing"
        else:
            step = str(request.args.get("path") or "ask").strip().lower()
            if step not in {"need", "ask", "portal", "existing", "new", "profile", "progress", "handoff", "outcome", "save", "saved"}:
                step = "ask"
        docs = _documents(slot)
        rows = _profile_rows(get_profile(slot), board)
        records = []
        try:
            records = [
                item for item in list_records(slot)
                if item.get("board") == board["board"]
            ]
        except BoardRegistrationError:
            records = []
        return render_template_string(
            ACCOUNT_PAGE,
            vacancy=vacancy,
            board=board,
            step=step,
            error=error,
            saved=_saved_board_record(slot, board["board"]),
            saved_records=records,
            profile_rows=rows,
            ready_count=sum(1 for row in rows if row["ok"]),
            photo_ready=any("photo" in item for item in docs),
            sign_ready=any("sign" in item for item in docs),
            csrf_token=issue_csrf_token(),
            check_url=url_for("apply_check", vacancy_id=vacancy_id),
            ask_url=url_for("apply_account", vacancy_id=vacancy_id, path="ask"),
            portal_url=url_for("apply_account", vacancy_id=vacancy_id, path="portal"),
            existing_url=url_for("apply_account", vacancy_id=vacancy_id, path="existing"),
            new_url=url_for("apply_account", vacancy_id=vacancy_id, path="new"),
            outcome_url=url_for("apply_account", vacancy_id=vacancy_id, path="outcome"),
            profile_url=url_for("apply_account", vacancy_id=vacancy_id, path="profile"),
            progress_url=url_for("apply_account", vacancy_id=vacancy_id, path="progress"),
            handoff_url=url_for("apply_account", vacancy_id=vacancy_id, path="handoff"),
            save_url=url_for("apply_account", vacancy_id=vacancy_id, path="save"),
        )

    @app.route("/apply/<int:vacancy_id>/check")
    def apply_check(vacancy_id):
        gate = _require_login()
        if gate is not None:
            return gate
        vacancy = get_vacancy(vacancy_id)
        if vacancy is None:
            return redirect(url_for("vacancies_page"))
        slot = _slot()
        if slot is None:
            return redirect(url_for("profile_page"))
        profile = get_profile(slot)
        return render_template_string(
            CHECK_PAGE,
            vacancy=vacancy,
            checks=_checks(profile, _documents(slot)),
            method_url=url_for("apply_method", vacancy_id=vacancy_id),
            pay_url=url_for("apply_pay", vacancy_id=vacancy_id),
            fee=FEE_RUPEES,
        )

    @app.route("/apply/<int:vacancy_id>/method")
    def apply_method(vacancy_id):
        gate = _require_login()
        if gate is not None:
            return gate
        vacancy = get_vacancy(vacancy_id)
        if vacancy is None:
            return redirect(url_for("vacancies_page"))
        if _slot() is None:
            return redirect(url_for("profile_page"))
        return render_template_string(
            METHOD_PAGE,
            official_link=vacancy.get("official_link") or "",
            pay_url=url_for("apply_pay", vacancy_id=vacancy_id),
        )

    @app.route("/apply/<int:vacancy_id>/pay", methods=["GET", "POST"])
    def apply_pay(vacancy_id):
        gate = _require_login()
        if gate is not None:
            return gate
        vacancy = get_vacancy(vacancy_id)
        if vacancy is None:
            return redirect(url_for("vacancies_page"))
        slot = _slot()
        if slot is None:
            return redirect(url_for("profile_page"))
        error = ""
        fee = latest_fee(vacancy_id, slot)
        if request.method == "POST":
            try:
                fee = create_fee(vacancy_id, slot, request.form.get("method"))
            except FillFeeError as exc:
                error = str(exc)
        settings = fee_settings()
        return render_template_string(
            PAY_PAGE,
            vacancy=vacancy,
            fee=FEE_RUPEES,
            csrf_token=issue_csrf_token(),
            paid=has_paid_fee(vacancy_id, slot),
            collectable=settings["collectable"],
            upi=upi_link(fee) if fee else upi_request(f"FormBharat vacancy {vacancy_id}"),
            status=(fee or {}).get("status", "unpaid"),
            start_url=url_for("apply_start", vacancy_id=vacancy_id),
            fill_url=url_for("apply_fill", vacancy_id=vacancy_id),
            error=error,
        )

    @app.route("/apply/<int:vacancy_id>/fill", methods=["POST"])
    def apply_fill(vacancy_id):
        gate = _require_login()
        if gate is not None:
            return gate
        vacancy = get_vacancy(vacancy_id)
        if vacancy is None:
            return redirect(url_for("vacancies_page"))
        slot = _slot()
        if slot is None:
            return redirect(url_for("profile_page"))
        if latest_fee(vacancy_id, slot) is None:
            try:
                create_fee(vacancy_id, slot, "upi")
            except FillFeeError:
                pass
        page_url = _form_page_url(vacancy)
        if not page_url:
            return render_template_string(
                "<p>इस नोटिस पर फॉर्म का पन्ना नहीं है।</p>"
            ), 400
        try:
            result = _site_fill(slot, page_url, again=request.form.get("again") == "yes")
        except SlotAccessError as error:
            return render_template_string("<p>{{ message }}</p>", message=str(error)), 403
        except ValueError as error:
            return render_template_string(
                "<p>{{ message }}</p><p>Submit नहीं हुआ।</p>",
                message=str(error),
            ), 400
        return _fill_page(result, page_url, url_for("apply_fill", vacancy_id=vacancy_id))

    @app.route("/other-fill/<form_key>/fill", methods=["POST"])
    def other_fill_site(form_key):
        form = _other_form(form_key)
        if form is None:
            return redirect(url_for("other_forms_page"))
        gate = _require_login()
        if gate is not None:
            return gate
        slot = _slot()
        if slot is None:
            return redirect(url_for("profile_page"))
        try:
            result = _site_fill(slot, form["url"], again=request.form.get("again") == "yes")
        except SlotAccessError as error:
            return render_template_string("<p>{{ message }}</p>", message=str(error)), 403
        except ValueError as error:
            return render_template_string(
                "<p>{{ message }}</p><p>Submit नहीं हुआ।</p>",
                message=str(error),
            ), 400
        return _fill_page(result, form["url"], url_for("other_fill_site", form_key=form_key))

    @app.route("/apply/<int:vacancy_id>/start")
    def apply_start(vacancy_id):
        gate = _require_login()
        if gate is not None:
            return gate
        vacancy = get_vacancy(vacancy_id)
        if vacancy is None:
            return redirect(url_for("vacancies_page"))
        slot = _slot()
        if slot is None:
            return redirect(url_for("profile_page"))
        if not has_paid_fee(vacancy_id, slot):
            return redirect(url_for("apply_pay", vacancy_id=vacancy_id))
        return render_template_string(
            START_PAGE,
            vacancy=vacancy,
            official_link=vacancy.get("official_link") or "",
            personal_url=url_for("apply_personal", vacancy_id=vacancy_id),
        )

    def _walk(vacancy_id):
        gate = _require_login()
        if gate is not None:
            return gate, None, None
        vacancy = get_vacancy(vacancy_id)
        if vacancy is None:
            return redirect(url_for("vacancies_page")), None, None
        slot = _slot()
        if slot is None:
            return redirect(url_for("profile_page")), None, None
        if not has_paid_fee(vacancy_id, slot):
            return redirect(url_for("apply_pay", vacancy_id=vacancy_id)), None, None
        return None, vacancy, slot

    def _show_walk(vacancy, title, lines, prev_url, next_url, next_label, extra_url="", extra_label=""):
        return render_template_string(
            WALK_PAGE,
            title=title,
            lines=lines,
            prev_url=prev_url,
            next_url=next_url,
            next_label=next_label,
            extra_url=extra_url,
            extra_label=extra_label,
        )

    @app.route("/apply/<int:vacancy_id>/personal")
    def apply_personal(vacancy_id):
        stopped, vacancy, slot = _walk(vacancy_id)
        if stopped is not None:
            return stopped
        profile = get_profile(slot)
        lines = []
        for key, label in (
            ("name", "नाम"),
            ("father_name", "पिता का नाम"),
            ("mother_name", "माता का नाम"),
            ("dob", "जन्म तिथि"),
            ("gender", "लिंग"),
            ("address", "पता"),
        ):
            value = str(profile.get(key) or "").strip()
            lines.append(label + " — " + (value or "missing"))
        return _show_walk(
            vacancy,
            "व्यक्तिगत विवरण",
            lines,
            url_for("apply_start", vacancy_id=vacancy_id),
            url_for("apply_education", vacancy_id=vacancy_id),
            "आगे बढ़ें · शिक्षा",
        )

    @app.route("/apply/<int:vacancy_id>/education")
    def apply_education(vacancy_id):
        stopped, vacancy, slot = _walk(vacancy_id)
        if stopped is not None:
            return stopped
        profile = get_profile(slot)
        lines = []
        for key, label in (
            ("tenth_roll_number", "10वीं रोल"),
            ("tenth_passing_year", "10वीं वर्ष"),
            ("twelfth_roll_number", "12वीं रोल"),
            ("twelfth_passing_year", "12वीं वर्ष"),
            ("graduation_degree", "स्नातक"),
            ("graduation_passing_year", "स्नातक वर्ष"),
        ):
            value = str(profile.get(key) or "").strip()
            lines.append(label + " — " + (value or "missing"))
        return _show_walk(
            vacancy,
            "शैक्षणिक योग्यता",
            lines,
            url_for("apply_personal", vacancy_id=vacancy_id),
            url_for("apply_photo", vacancy_id=vacancy_id),
            "आगे बढ़ें · फोटो और हस्ताक्षर",
        )

    @app.route("/apply/<int:vacancy_id>/photo")
    def apply_photo(vacancy_id):
        stopped, vacancy, slot = _walk(vacancy_id)
        if stopped is not None:
            return stopped
        saved = _signature_bytes(slot)
        lines, ready = photo_guidance(vacancy.get("registration_board"), saved)
        extra_url = ""
        extra_label = ""
        if ready:
            extra_url = url_for("apply_signature_copy", vacancy_id=vacancy_id)
            extra_label = "दस्तखत की कॉपी डाउनलोड करो"
        return _show_walk(
            vacancy,
            "फोटो और हस्ताक्षर",
            lines,
            url_for("apply_education", vacancy_id=vacancy_id),
            url_for("apply_verify", vacancy_id=vacancy_id),
            "आगे बढ़ें · OTP और CAPTCHA",
            extra_url,
            extra_label,
        )

    @app.route("/apply/<int:vacancy_id>/signature-copy")
    def apply_signature_copy(vacancy_id):
        stopped, vacancy, slot = _walk(vacancy_id)
        if stopped is not None:
            return stopped
        if str(vacancy.get("registration_board") or "").strip().lower() != "rrb":
            return redirect(url_for("apply_photo", vacancy_id=vacancy_id))
        saved = _signature_bytes(slot)
        if not saved:
            return redirect(url_for("apply_photo", vacancy_id=vacancy_id))
        handle = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        handle.close()
        try:
            checked = fit_bounded_copy(saved, handle.name, **RRB_SIGNATURE)
            if not checked.get("ok"):
                return redirect(url_for("apply_photo", vacancy_id=vacancy_id))
            payload = open(handle.name, "rb").read()
        finally:
            if os.path.exists(handle.name):
                os.remove(handle.name)
        return Response(
            payload,
            mimetype="image/jpeg",
            headers={"Content-Disposition": "attachment; filename=rrb-signature.jpg"},
        )

    @app.route("/apply/<int:vacancy_id>/verify")
    def apply_verify(vacancy_id):
        stopped, vacancy, slot = _walk(vacancy_id)
        if stopped is not None:
            return stopped
        lines = [
            "OTP aap official page par daloge.",
            "CAPTCHA aap official page par daloge.",
            "FormBharat OTP nahi bhejta aur CAPTCHA solve nahi karta.",
            "Final Submit bhi aap karoge.",
        ]
        return _show_walk(
            vacancy,
            "OTP और CAPTCHA",
            lines,
            url_for("apply_photo", vacancy_id=vacancy_id),
            url_for("apply_review", vacancy_id=vacancy_id),
            "आगे बढ़ें · अंतिम समीक्षा",
        )

    @app.route("/apply/<int:vacancy_id>/review")
    def apply_review(vacancy_id):
        stopped, vacancy, slot = _walk(vacancy_id)
        if stopped is not None:
            return stopped
        profile = get_profile(slot)
        docs = _documents(slot)
        lines = []
        for key, label in (("name", "Personal"), ("dob", "Date of birth"), ("tenth_roll_number", "Education")):
            lines.append(label + " — " + ("saved" if str(profile.get(key) or "").strip() else "missing"))
        lines.append("Photo — " + ("saved" if any("photo" in item for item in docs) else "missing"))
        lines.append("Signature — " + ("saved" if any("sign" in item for item in docs) else "missing"))
        lines.append("Sarkari site par Submit abhi nahi hua.")
        return _show_walk(
            vacancy,
            "अंतिम समीक्षा",
            lines,
            url_for("apply_verify", vacancy_id=vacancy_id),
            url_for("apply_done", vacancy_id=vacancy_id),
            "आगे बढ़ें · आवेदन सेव",
        )

    @app.route("/apply/<int:vacancy_id>/done", methods=["GET", "POST"])
    def apply_done(vacancy_id):
        stopped, vacancy, slot = _walk(vacancy_id)
        if stopped is not None:
            return stopped
        from app.application_tracker import (
            create_application,
            init_application_tracker_db,
            list_applications,
        )

        init_application_tracker_db()
        message = "Yeh sarkari site par submit nahi hua. Local list me draft tab banega jab aap save karo."
        if request.method == "POST":
            already = any(
                item.get("vacancy_id") == vacancy_id
                for item in list_applications(slot)
            )
            if not already:
                create_application(
                    slot,
                    vacancy.get("title") or "Application",
                    vacancy.get("organization") or "",
                    vacancy_id,
                    "draft",
                    "Prepared in FormBharat. Government submit stays with the user.",
                )
            message = "FormBharat me draft save ho gaya. Sarkari site par Submit aap karoge."
        return render_template_string(
            DONE_PAGE,
            message=message,
            csrf_token=issue_csrf_token(),
            official_link=vacancy.get("official_link") or "",
        )

    @app.post("/api/fill-fee/razorpay")
    def fill_fee_razorpay():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"success": False, "error": "Invalid or missing JSON data"}), 400
        try:
            fee = confirm_razorpay_payment(
                data.get("razorpay_order_id"),
                data.get("razorpay_payment_id"),
                data.get("razorpay_signature"),
            )
        except FillFeeError as exc:
            return jsonify({"success": False, "error": str(exc)}), 400
        return jsonify({"success": True, "fee": fee})
