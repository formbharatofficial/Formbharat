"""Mobile page for SSC OTR and RRB Candidate Account assistance."""

PAGE = r"""<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FormBharat Board Account</title>
<style>
body{font-family:"Segoe UI",system-ui,sans-serif;background:#f4f7f6;margin:0;padding:16px}
.container{max-width:430px;margin:auto}
.card{background:#fff;border:1px solid #e6edf5;border-radius:22px;padding:16px;margin-bottom:12px}
h1{color:#17345c;font-size:1.35rem;margin:8px 0}
h2{color:#17345c;font-size:1.05rem;margin:0 0 8px}
p{line-height:1.45}
.choice{display:block;width:100%;box-sizing:border-box;margin-top:10px;min-height:52px;border-radius:16px;border:1px solid #d9e3ee;background:#fff;color:#17345c;font-weight:800;font-size:1rem}
.warn{background:#fff4e0;border-radius:16px;padding:12px}
.missing{color:#9a3412;font-weight:700}
.ok{color:#12833a;font-weight:700}
small{display:block;color:#5d7088}
</style>
</head>
<body>
<div class="container">
<section class="card">
<button type="button" id="lang-hi" class="choice">हिन्दी</button>
<button type="button" id="lang-en" class="choice">English</button>
<h1 id="heading"></h1>
<p id="lead"></p>
<p class="warn" id="live-note"></p>
</section>
<p id="flow-status" class="ok"></p>
<section class="card" id="panel-skip" hidden>
<h2 id="skip-title"></h2>
<p id="skip-copy"></p>
</section>
<section class="card" id="panel-ask" hidden>
<h2 id="ask-title"></h2>
<p id="ask-copy"></p>
<button type="button" id="pick-ssc" class="choice"></button>
<button type="button" id="pick-rrb" class="choice"></button>
<button type="button" id="pick-none" class="choice"></button>
</section>
<section class="card" id="panel-account" hidden>
<h2 id="account-title"></h2>
<p id="account-question"></p>
<button type="button" id="path-existing" class="choice"></button>
<button type="button" id="path-new" class="choice"></button>
</section>
<section class="card" id="panel-prepare" hidden>
<h2 id="prepare-title"></h2>
<p id="prepare-why"></p>
<ol id="steps"></ol>
<p class="warn" id="edit-warning"></p>
<p id="profile-state"></p>
<div id="copy-list"></div>
<div id="missing-list"></div>
<div id="conflict-list"></div>
<div id="portal-only"></div>
<p id="documents"></p>
<a id="portal-link" class="fb-go" target="_blank" rel="noopener noreferrer"></a>
<p id="manual-note"></p>
<button type="button" id="continue-result" class="choice"></button>
</section>
<section class="card" id="panel-result" hidden>
<h2 id="result-title"></h2>
<p id="result-copy"></p>
<p id="confirm-label"></p>
<label id="number-label" for="registration-number"></label>
<input id="registration-number" autocomplete="off" inputmode="text">
<button type="button" id="have-number" class="choice"></button>
<button type="button" id="mark-waiting" class="choice"></button>
<button type="button" id="mark-interrupted" class="choice"></button>
<button type="button" id="mark-failed" class="choice"></button>
<p id="outcome"></p>
</section>
<section class="card" id="panel-consent" hidden>
<h2 id="consent-title"></h2>
<p id="consent-copy"></p>
<p id="consent-preview"></p>
<button type="button" id="consent-yes" class="choice"></button>
<button type="button" id="consent-no" class="choice"></button>
<button type="button" id="consent-replace" class="choice" hidden></button>
</section>
<section class="card" id="panel-saved">
<h2 id="saved-title"></h2>
<div id="saved-list"></div>
</section>
<p id="message"></p>
<input id="profile_id" type="hidden" data-slot="__PROFILE_SLOT__">
</div>
<script>
const STRINGS = {
    hi: {
        heading: "बोर्ड खाता सहायता",
        lead: "SSC का OTR और RRB का उम्मीदवार खाता अलग हैं। FormBharat आधिकारिक साइट पर OTP, CAPTCHA या Submit नहीं करता।",
        live: "लाइव पोर्टल भरना उपलब्ध नहीं है। लोकल अभ्यास फॉर्म ssc.gov.in या rrbapply.gov.in नहीं है।",
        skipTitle: "इस नोटिस में यह कदम नहीं है",
        skipCopy: "इस भर्ती के लिए SSC OTR या RRB उम्मीदवार खाता जरूरी नहीं रखा गया है।",
        askTitle: "कौन सा खाता चाहिए?",
        askCopy: "नोटिस में बोर्ड साफ नहीं है। नाम से अनुमान नहीं लगाया जाएगा।",
        pickSsc: "SSC — वन टाइम रजिस्ट्रेशन (OTR)",
        pickRrb: "RRB — उम्मीदवार खाता",
        pickNone: "इनमें से कोई खाता नहीं चाहिए",
        accountTitle: "खाते की स्थिति",
        accountQuestion: "क्या इस भर्ती बोर्ड में आपका अकाउंट पहले से बना है?",
        pathExisting: "हाँ, मेरा अकाउंट पहले से है",
        pathNew: "नहीं, नया अकाउंट बनाना है",
        prepareExisting: "पुराना खाता",
        prepareNew: "नया खाता",
        whyExisting: "लॉगिन आधिकारिक पेज पर खुद करें। FormBharat लॉगिन की जाँच नहीं करता और पासवर्ड नहीं माँगता।",
        whyNewSsc: "इस भर्ती के लिए SSC OTR चाहिए। नीचे वही जानकारी है जो आपकी जाँची हुई प्रोफाइल में है।",
        whyNewRrb: "इस भर्ती के लिए RRB उम्मीदवार खाता चाहिए। यह SSC OTR नहीं है।",
        profileReady: "जाँची हुई प्रोफाइल तैयार है। फिर भी आधिकारिक पेज पर मिला लें।",
        profileIncomplete: "कुछ जानकारी अधूरी है या दो जगह अलग है। FormBharat खुद मान नहीं भरेगा।",
        profileUnverified: "प्रोफाइल जाँची नहीं है। कॉपी करने लायक जानकारी नहीं दिखाई जाएगी।",
        copyTitle: "कॉपी करने लायक जानकारी",
        missingTitle: "प्रोफाइल में नहीं है",
        conflictTitle: "दो जगह अलग है — FormBharat एक को नहीं चुनेगा",
        portalOnlyTitle: "केवल आधिकारिक पेज पर",
        documents: "फोटो और हस्ताक्षर का आकार आधिकारिक पेज तय करता है। FormBharat आकार नहीं गढ़ता।",
        openPortal: "आधिकारिक पेज खोलें",
        manual: "फॉर्म आप खुद भरेंगे। OTP, CAPTCHA और अंतिम Submit आपके पास रहेंगे।",
        continueResult: "आधिकारिक पेज पर काम के बाद आगे बढ़ें",
        resultTitle: "परिणाम",
        resultCopy: "नंबर लिखने से रजिस्ट्रेशन सफल नहीं माना जाएगा। FormBharat आधिकारिक पेज खुद नहीं पढ़ता।",
        confirmLabel: "यह नंबर आपके लिखने पर आधारित है। स्वतंत्र रूप से जाँचा नहीं गया।",
        numberLabel: "आधिकारिक पेज पर दिखा रजिस्ट्रेशन नंबर",
        haveNumber: "मैंने आधिकारिक पेज पर नंबर देखा",
        waiting: "आधिकारिक पेज पर मेरा काम बाकी है",
        interrupted: "बीच में रुक गया",
        failed: "पोर्टल नहीं खुला या काम नहीं बना",
        outcomeWaiting: "स्थिति: आपके काम की प्रतीक्षा। कुछ सेव नहीं हुआ।",
        outcomeInterrupted: "स्थिति: बीच में रुका। आधिकारिक पेज पर बाद में जारी रखें। कुछ सेव नहीं हुआ।",
        outcomeFailed: "स्थिति: असफल या पोर्टल उपलब्ध नहीं। FormBharat रजिस्ट्रेशन पूरा नहीं करता।",
        outcomeNumber: "स्थिति: आपने नंबर की पुष्टि की। यह स्वतंत्र रूप से जाँचा नहीं गया।",
        consentTitle: "क्या यह रिकॉर्ड सेव करूँ?",
        consentYes: "हाँ, मेरी प्रोफाइल पर सेव करें",
        consentNo: "नहीं, सेव न करें",
        consentReplace: "पुराने नंबर की जगह यह नंबर सेव करें",
        savedTitle: "सेव किए गए बोर्ड रिकॉर्ड",
        savedEmpty: "अभी कोई बोर्ड रिकॉर्ड सेव नहीं है।",
        savedUser: "user-confirmed, independently verified नहीं",
        remove: "यह रिकॉर्ड मिटाएँ",
        notSaved: "रिकॉर्ड सेव नहीं हुआ।",
        savedOk: "रिकॉर्ड सेव हो गया। यह सफल रजिस्ट्रेशन का प्रमाण नहीं है।",
        duplicate: "इस बोर्ड का रिकॉर्ड पहले से है। बदलना हो तो नीचे वाली अनुमति दें।",
        badNumber: "नंबर खाली है या पहचान के रूप में नहीं है। आधिकारिक पेज वाला नंबर लिखें।",
        slot: "यह प्रोफाइल इस खाते पर नहीं खुलती। खाता पेज से साइन इन करें।",
        network: "अभी जानकारी नहीं खुली। फिर कोशिश करें।",
        statusNotStarted: "स्थिति: शुरू नहीं हुआ",
        statusInProgress: "स्थिति: चल रहा है",
        photo: "फोटो",
        signature: "हस्ताक्षर"
    },
    en: {
        heading: "Board account assistance",
        lead: "An SSC One Time Registration and an RRB Candidate Account are different. FormBharat does not enter OTP, CAPTCHA, or Submit on the official site.",
        live: "Live portal fill is unavailable. A local practice form is not ssc.gov.in or rrbapply.gov.in.",
        skipTitle: "This notice does not need this step",
        skipCopy: "SSC OTR or an RRB Candidate Account is not required for this recruitment.",
        askTitle: "Which account is needed?",
        askCopy: "The notice does not name a board. The job title will not be used as a guess.",
        pickSsc: "SSC — One Time Registration (OTR)",
        pickRrb: "RRB — Candidate Account",
        pickNone: "Neither account is needed",
        accountTitle: "Account status",
        accountQuestion: "Do you already have an account on this recruitment board?",
        pathExisting: "Yes, I already have an account",
        pathNew: "No, I need to create one",
        prepareExisting: "Existing account",
        prepareNew: "New account",
        whyExisting: "Sign in on the official page yourself. FormBharat does not check the login and does not ask for the password.",
        whyNewSsc: "This recruitment needs an SSC One Time Registration. The details below come from your verified profile.",
        whyNewRrb: "This recruitment needs an RRB Candidate Account. This is not an SSC One Time Registration.",
        profileReady: "The verified profile has the mapped details. Still compare them on the official page.",
        profileIncomplete: "Some details are missing or do not match. FormBharat will not invent a value.",
        profileUnverified: "The profile is not verified. Copy-ready details are hidden.",
        copyTitle: "Copy-ready details",
        missingTitle: "Not in the verified profile",
        conflictTitle: "The values differ — FormBharat will not choose one",
        portalOnlyTitle: "Official page only",
        documents: "The official page decides photo and signature size. FormBharat does not invent a size.",
        openPortal: "Open the official page",
        manual: "You fill the form. OTP, CAPTCHA, and final Submit stay with you.",
        continueResult: "Continue after working on the official page",
        resultTitle: "Result",
        resultCopy: "Typing a number does not make the registration successful. FormBharat does not read the official success page.",
        confirmLabel: "This number is user-confirmed, not independently verified.",
        numberLabel: "Registration number shown on the official page",
        haveNumber: "I saw the number on the official page",
        waiting: "I still have work on the official page",
        interrupted: "It was interrupted",
        failed: "The portal did not open or the work failed",
        outcomeWaiting: "Status: waiting for you. Nothing was saved.",
        outcomeInterrupted: "Status: interrupted. Continue later on the official page. Nothing was saved.",
        outcomeFailed: "Status: failed or the portal is unavailable. FormBharat does not finish the registration.",
        outcomeNumber: "Status: you confirmed a number. It is not independently verified.",
        consentTitle: "May this record be saved?",
        consentYes: "Yes, save it on my profile",
        consentNo: "No, do not save it",
        consentReplace: "Save this number in place of the old one",
        savedTitle: "Saved board records",
        savedEmpty: "No board record is saved yet.",
        savedUser: "user-confirmed, not independently verified",
        remove: "Delete this record",
        notSaved: "The record was not saved.",
        savedOk: "The record was saved. This is not proof of a successful registration.",
        duplicate: "A record for this board is already saved. Allow the replacement below if you want to change it.",
        badNumber: "The number is empty or not an identifier. Type the number from the official page.",
        slot: "This profile is not open for this account. Sign in from the account page.",
        network: "The details could not be loaded. Try again.",
        statusNotStarted: "Status: not started",
        statusInProgress: "Status: in progress",
        photo: "Photo",
        signature: "Signature"
    }
};

const state = {
    lang: "hi",
    board: "",
    path: "",
    review: null,
    flow: "not_started"
};

function t(key) {
    return STRINGS[state.lang][key] || "";
}

function slot() {
    const field = document.getElementById("profile_id");
    const saved = field.getAttribute("data-slot") || "";
    if (/^[1-5]$/.test(saved)) {
        field.value = saved;
        return saved;
    }
    field.value = "";
    return "";
}

function applyStatic() {
    document.documentElement.lang = state.lang;
    const map = {
        heading: "heading",
        lead: "lead",
        "live-note": "live",
        "skip-title": "skipTitle",
        "skip-copy": "skipCopy",
        "ask-title": "askTitle",
        "ask-copy": "askCopy",
        "pick-ssc": "pickSsc",
        "pick-rrb": "pickRrb",
        "pick-none": "pickNone",
        "account-title": "accountTitle",
        "account-question": "accountQuestion",
        "path-existing": "pathExisting",
        "path-new": "pathNew",
        "result-title": "resultTitle",
        "result-copy": "resultCopy",
        "confirm-label": "confirmLabel",
        "number-label": "numberLabel",
        "have-number": "haveNumber",
        "mark-waiting": "waiting",
        "mark-interrupted": "interrupted",
        "mark-failed": "failed",
        "consent-title": "consentTitle",
        "consent-yes": "consentYes",
        "consent-no": "consentNo",
        "consent-replace": "consentReplace",
        "saved-title": "savedTitle",
        "continue-result": "continueResult",
        "portal-link": "openPortal",
        "manual-note": "manual"
    };
    Object.keys(map).forEach(function(id) {
        document.getElementById(id).textContent = t(map[id]);
    });
    paintFlow();
    if (state.review) {
        renderReview(state.review);
    }
}

function docWord(value) {
    const words = {
        hi: {missing: "नहीं है", saved: "सेव है, जाँचा नहीं", verified: "जाँचा हुआ"},
        en: {missing: "missing", saved: "saved, not verified", verified: "verified"}
    };
    return (words[state.lang] && words[state.lang][value]) || value;
}

function paintFlow() {
    const names = {
        not_started: "statusNotStarted",
        in_progress: "statusInProgress",
        waiting_for_user: "outcomeWaiting",
        user_confirmed: "outcomeNumber",
        failed: "outcomeFailed",
        interrupted: "outcomeInterrupted"
    };
    document.getElementById("flow-status").textContent = t(names[state.flow] || "statusNotStarted");
    if (names[state.flow] && state.flow !== "not_started" && state.flow !== "in_progress") {
        document.getElementById("outcome").textContent = t(names[state.flow]);
    }
}

function show(id, visible) {
    document.getElementById(id).hidden = !visible;
}

function setMessage(text) {
    document.getElementById("message").textContent = text || "";
}

function addBlock(parent, title, lines) {
    parent.replaceChildren();
    if (!lines.length) {
        return;
    }
    const heading = document.createElement("h2");
    heading.textContent = title;
    parent.appendChild(heading);
    lines.forEach(function(line) {
        const paragraph = document.createElement("p");
        paragraph.textContent = line;
        parent.appendChild(paragraph);
    });
}

function labelFor(item) {
    return state.lang === "hi" ? item.label_hi : item.label_en;
}

function renderReview(review) {
    state.review = review;
    const steps = document.getElementById("steps");
    steps.replaceChildren();
    const stepLines = state.lang === "hi" ? review.steps_hi : review.steps_en;
    stepLines.forEach(function(line) {
        const item = document.createElement("li");
        item.textContent = line;
        steps.appendChild(item);
    });
    document.getElementById("edit-warning").textContent = state.lang === "hi"
        ? review.edit_warning_hi
        : review.edit_warning_en;
    document.getElementById("prepare-title").textContent = state.path === "existing"
        ? t("prepareExisting")
        : t("prepareNew");
    if (state.path === "existing") {
        document.getElementById("prepare-why").textContent = t("whyExisting");
    } else if (review.board === "rrb") {
        document.getElementById("prepare-why").textContent = t("whyNewRrb");
    } else {
        document.getElementById("prepare-why").textContent = t("whyNewSsc");
    }
    const stateKey = {
        ready: "profileReady",
        incomplete: "profileIncomplete",
        unverified: "profileUnverified"
    }[review.profile_state] || "profileIncomplete";
    document.getElementById("profile-state").textContent = t(stateKey);
    addBlock(
        document.getElementById("copy-list"),
        t("copyTitle"),
        (review.copy_fields || []).map(function(item) {
            return labelFor(item) + ": " + item.value;
        })
    );
    addBlock(
        document.getElementById("missing-list"),
        t("missingTitle"),
        (review.missing || []).map(labelFor)
    );
    addBlock(
        document.getElementById("conflict-list"),
        t("conflictTitle"),
        (review.conflicts || []).map(function(item) {
            return labelFor(item) + ": " + item.verified_value + " / " + item.profile_value;
        })
    );
    addBlock(
        document.getElementById("portal-only"),
        t("portalOnlyTitle"),
        (review.portal_only || []).map(labelFor)
    );
    const docs = review.documents || {};
    document.getElementById("documents").textContent = t("documents")
        + " " + t("photo") + ": " + docWord(docs.photo || "missing")
        + ". " + t("signature") + ": " + docWord(docs.signature || "missing") + ".";
    const link = document.getElementById("portal-link");
    link.href = review.portal_url;
    link.textContent = t("openPortal");
    document.getElementById("consent-copy").textContent = state.lang === "hi"
        ? review.consent_text_hi
        : review.consent_text_en;
}

async function readJson(response) {
    try {
        return await response.json();
    } catch (error) {
        return {success: false, code: "network"};
    }
}

async function loadReview() {
    const profileId = slot();
    if (!profileId || !state.board) {
        setMessage(t("slot"));
        return;
    }
    setMessage("");
    const response = await fetch(
        "/api/board-registration/review?profile_id=" + profileId + "&board=" + state.board
    );
    const data = await readJson(response);
    if (!data.success) {
        setMessage(data.code === "forbidden_slot" ? t("slot") : t("network"));
        return;
    }
    renderReview(data);
    show("panel-prepare", true);
    state.flow = "in_progress";
    paintFlow();
}

function chooseBoard(board) {
    state.board = board;
    state.flow = "in_progress";
    show("panel-ask", false);
    show("panel-skip", false);
    show("panel-account", true);
    paintFlow();
}

function choosePath(path) {
    state.path = path;
    state.flow = "waiting_for_user";
    show("panel-account", false);
    show("panel-result", false);
    show("panel-consent", false);
    loadReview();
}

function showSkip() {
    show("panel-skip", true);
    show("panel-ask", false);
    show("panel-account", false);
    show("panel-prepare", false);
    show("panel-result", false);
    show("panel-consent", false);
    state.flow = "not_started";
    paintFlow();
}

async function loadRequirement() {
    const params = new URLSearchParams(window.location.search);
    const requested = params.get("lang");
    if (requested === "hi" || requested === "en") {
        state.lang = requested;
    } else {
        const stored = sessionStorage.getItem("fb-board-lang");
        if (stored === "hi" || stored === "en") {
            state.lang = stored;
        }
    }
    applyStatic();
    const vacancyId = params.get("vacancy_id") || "";
    if (!vacancyId) {
        show("panel-ask", true);
        return;
    }
    const response = await fetch("/api/board-registration/requirement?vacancy_id=" + encodeURIComponent(vacancyId));
    const data = await readJson(response);
    if (!data.success) {
        show("panel-ask", true);
        setMessage(t("network"));
        return;
    }
    const requirement = data.requirement || {};
    if (requirement.state === "skip") {
        showSkip();
        return;
    }
    if (requirement.state === "required" && (requirement.board === "ssc" || requirement.board === "rrb")) {
        chooseBoard(requirement.board);
        return;
    }
    show("panel-ask", true);
}

function openResult() {
    show("panel-result", true);
    state.flow = "waiting_for_user";
    paintFlow();
    document.getElementById("outcome").textContent = t("outcomeWaiting");
}

async function saveConsent(replace) {
    const profileId = slot();
    if (!profileId) {
        setMessage(t("slot"));
        return;
    }
    const number = document.getElementById("registration-number").value.trim();
    const response = await fetch("/api/board-registration/records/" + profileId, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            board: state.board,
            account_path: state.path,
            registration_number: number,
            consent: true,
            consent_language: state.lang,
            replace: replace
        })
    });
    const data = await readJson(response);
    if (response.status === 409 || data.code === "duplicate") {
        document.getElementById("consent-replace").hidden = false;
        setMessage(t("duplicate"));
        return;
    }
    if (data.code === "number") {
        setMessage(t("badNumber"));
        return;
    }
    if (!data.success || !data.saved) {
        setMessage(t("network"));
        return;
    }
    document.getElementById("consent-replace").hidden = true;
    setMessage(t("savedOk"));
    loadSaved();
}

async function declineConsent() {
    const profileId = slot();
    if (!profileId) {
        setMessage(t("slot"));
        return;
    }
    const response = await fetch("/api/board-registration/records/" + profileId, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            board: state.board,
            consent: false
        })
    });
    const data = await readJson(response);
    if (!data.success || data.saved) {
        setMessage(t("network"));
        return;
    }
    setMessage(t("notSaved"));
}

function renderSaved(records) {
    const list = document.getElementById("saved-list");
    list.replaceChildren();
    if (!records.length) {
        const empty = document.createElement("p");
        empty.textContent = t("savedEmpty");
        list.appendChild(empty);
        return;
    }
    records.forEach(function(record) {
        const card = document.createElement("article");
        const title = document.createElement("h2");
        title.textContent = record.board === "rrb" ? t("pickRrb") : t("pickSsc");
        card.appendChild(title);
        const number = document.createElement("p");
        number.textContent = record.registration_number || "";
        card.appendChild(number);
        const note = document.createElement("p");
        note.textContent = t("savedUser");
        card.appendChild(note);
        const button = document.createElement("button");
        button.type = "button";
        button.className = "delete";
        button.textContent = t("remove");
        button.onclick = function() {
            removeRecord(record.id);
        };
        card.appendChild(button);
        list.appendChild(card);
    });
}

async function loadSaved() {
    const profileId = slot();
    if (!profileId) {
        renderSaved([]);
        return;
    }
    const response = await fetch("/api/board-registration/records/" + profileId);
    const data = await readJson(response);
    if (!data.success) {
        setMessage(data.code === "forbidden_slot" ? t("slot") : t("network"));
        return;
    }
    renderSaved(data.records || []);
}

async function removeRecord(recordId) {
    const profileId = slot();
    const response = await fetch(
        "/api/board-registration/records/" + profileId + "/" + recordId,
        {method: "DELETE"}
    );
    const data = await readJson(response);
    if (!data.success) {
        setMessage(t("network"));
        return;
    }
    loadSaved();
}

document.getElementById("lang-hi").onclick = function() {
    state.lang = "hi";
    sessionStorage.setItem("fb-board-lang", "hi");
    applyStatic();
    loadSaved();
};
document.getElementById("lang-en").onclick = function() {
    state.lang = "en";
    sessionStorage.setItem("fb-board-lang", "en");
    applyStatic();
    loadSaved();
};
document.getElementById("pick-ssc").onclick = function() { chooseBoard("ssc"); };
document.getElementById("pick-rrb").onclick = function() { chooseBoard("rrb"); };
document.getElementById("pick-none").onclick = showSkip;
document.getElementById("path-existing").onclick = function() { choosePath("existing"); };
document.getElementById("path-new").onclick = function() { choosePath("new"); };
document.getElementById("continue-result").onclick = openResult;
document.getElementById("have-number").onclick = function() {
    state.flow = "user_confirmed";
    paintFlow();
    document.getElementById("outcome").textContent = t("outcomeNumber");
    const typed = document.getElementById("registration-number").value.trim();
    document.getElementById("consent-preview").textContent = typed;
    show("panel-consent", true);
};
document.getElementById("mark-waiting").onclick = function() {
    state.flow = "waiting_for_user";
    paintFlow();
    document.getElementById("outcome").textContent = t("outcomeWaiting");
    show("panel-consent", false);
};
document.getElementById("mark-interrupted").onclick = function() {
    state.flow = "interrupted";
    paintFlow();
    document.getElementById("outcome").textContent = t("outcomeInterrupted");
    show("panel-consent", false);
};
document.getElementById("mark-failed").onclick = function() {
    state.flow = "failed";
    paintFlow();
    document.getElementById("outcome").textContent = t("outcomeFailed");
    show("panel-consent", false);
};
document.getElementById("consent-yes").onclick = function() { saveConsent(false); };
document.getElementById("consent-no").onclick = declineConsent;
document.getElementById("consent-replace").onclick = function() { saveConsent(true); };

loadRequirement();
loadSaved();
</script>
</body>
</html>
"""
