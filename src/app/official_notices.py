"""Official SSC and Railway notices checked on 29 Oct 2026.

Dates come from the notice or the Press Information Bureau.
A missing date stays empty. The same official link is saved once.
"""

from app.vacancy import create_vacancy, delete_vacancy, list_vacancies, update_vacancy


OFFICIAL_NOTICES = (
    {
        "title": "Railway RRB Station Master Recruitment CEN 08/2026",
        "organization": "Railway Recruitment Boards",
        "category": "Railway",
        "description": (
            "Recruitment form is open. Apply at https://www.rrbapply.gov.in/. "
            "Press Information Bureau, 27 Oct 2026, says the window closes on 25 Nov 2026."
        ),
        "eligibility": "Graduate",
        "application_start": "2026-10-27",
        "application_end": "2026-11-25",
        "official_link": (
            "https://rrb.indianrailways.gov.in/-/image/"
            "1793016771817CEN_08_2026_StationMaster.pdf/examsDocuments"
        ),
        "source_name": "Press Information Bureau, 27 Oct 2026",
        "registration_board": "rrb",
    },
    {
        "title": "Railway RRB NTPC Graduate Recruitment CEN 06/2026",
        "organization": "Railway Recruitment Boards",
        "category": "Railway",
        "description": (
            "Recruitment form is open until 6 Nov 2026, 23:59. "
            "The notice names https://rrb.indianrailways.gov.in/ and https://www.rrbapply.gov.in/."
        ),
        "eligibility": "Graduate",
        "application_start": "2026-10-08",
        "application_end": "2026-11-06",
        "official_link": "https://www.rrbapply.gov.in/",
        "source_name": "CEN 06/2026 notice",
        "registration_board": "rrb",
    },
    {
        "title": "SSC Junior Engineer Recruitment 2026",
        "organization": "Staff Selection Commission",
        "category": "SSC",
        "description": (
            "Online form closed on 22 Sep 2026. "
            "Paper-I is 2 Nov 2026 to 6 Nov 2026. Official site: https://ssc.gov.in/"
        ),
        "eligibility": "",
        "application_start": "2026-09-02",
        "application_end": "2026-09-22",
        "exam_date": "2026-11-02",
        "official_link": (
            "https://ssc.gov.in/api/attachment/uploads/masterData/"
            "NoticeBoards/Notice_of_adv_je_2026.pdf"
        ),
        "source_name": "SSC notice, exam dates 1 Oct 2026",
        "registration_board": "ssc",
    },
    {
        "title": "SSC Sub-Inspector Delhi Police and CAPF Recruitment 2026",
        "organization": "Staff Selection Commission",
        "category": "SSC",
        "description": (
            "Online form closed on 30 Sep 2026. "
            "Computer based exam is 20 Nov 2026 to 28 Nov 2026. Official site: https://ssc.gov.in/"
        ),
        "eligibility": "",
        "application_start": "2026-09-10",
        "application_end": "2026-09-30",
        "exam_date": "2026-11-20",
        "official_link": (
            "https://ssc.gov.in/api/attachment/uploads/masterData/"
            "NoticeBoards/Notice_of_adv_capf_2026.pdf"
        ),
        "source_name": "SSC notice, exam dates 1 Oct 2026",
        "registration_board": "ssc",
    },
    {
        "title": "SSC CHSL Recruitment 2026",
        "organization": "Staff Selection Commission",
        "category": "SSC",
        "description": (
            "Online form closed on 7 Oct 2026. "
            "Tier-I is 30 Nov 2026 to 31 Dec 2026. Official site: https://ssc.gov.in/"
        ),
        "eligibility": "",
        "application_start": "2026-09-07",
        "application_end": "2026-10-07",
        "exam_date": "2026-11-30",
        "official_link": (
            "https://ssc.gov.in/api/attachment/uploads/masterData/"
            "NoticeBoards/Notice_of_adv_chsl_2026.pdf"
        ),
        "source_name": "SSC notice, exam dates 1 Oct 2026",
        "registration_board": "ssc",
    },
    {
        "title": "SSC Constable GD 2026 Result | Out : 12/10/2026",
        "organization": "Staff Selection Commission",
        "category": "SSC",
        "description": (
            "Result of the computer based exam was declared on 12 Oct 2026. "
            "The write-up shortlists candidates for PET and PST. Official site: https://ssc.gov.in/"
        ),
        "eligibility": "",
        "official_link": (
            "https://ssc.gov.in/api/attachment/uploads/masterData/"
            "Results/writeup_12102026.pdf"
        ),
        "source_name": "SSC result write-up, 12 Oct 2026",
        "registration_board": "none",
    },
    {
        "title": "SSC CHSL 2025 Final Result | Out : 07/10/2026",
        "organization": "Staff Selection Commission",
        "category": "SSC",
        "description": (
            "Final result of CHSL 2025 was declared on 7 Oct 2026. "
            "Official site: https://ssc.gov.in/"
        ),
        "eligibility": "",
        "official_link": (
            "https://ssc.gov.in/api/attachment/uploads/masterData/"
            "Results/writeup_final_chsl_2025_07102026.pdf"
        ),
        "source_name": "SSC final result write-up, 7 Oct 2026",
        "registration_board": "none",
    },
    {
        "title": "SSC Stenographer Grade C and D 2025 Result | Last Date : 06/11/2026",
        "organization": "Staff Selection Commission",
        "category": "SSC",
        "description": (
            "Final result was declared on 25 Aug 2026. "
            "Marks stay on https://ssc.gov.in/ from 7 Oct 2026 until 6 Nov 2026, 6:00 PM."
        ),
        "eligibility": "",
        "official_link": (
            "https://ssc.gov.in/api/attachment/uploads/masterData/"
            "NoticeBoards/Final_Marks_Writeup_07102026.pdf"
        ),
        "source_name": "SSC marks write-up, 7 Oct 2026",
        "registration_board": "none",
    },
    {
        "title": "SSC Selection Post Phase-XIV 2026 Answer Key | Out : 09/10/2026",
        "organization": "Staff Selection Commission",
        "category": "SSC",
        "description": (
            "Tentative answer key was uploaded on 9 Oct 2026. "
            "The challenge window closed on 12 Oct 2026. Official site: https://ssc.gov.in/"
        ),
        "eligibility": "",
        "official_link": (
            "https://ssc.gov.in/api/attachment/uploads/masterData/"
            "NoticeBoards/writeup_rhq.pdf"
        ),
        "source_name": "SSC answer key write-up, 9 Oct 2026",
        "registration_board": "none",
    },
    {
        "title": "SSC CGL 2026 Tier-I Admit Card | Last Date : 30/10/2026",
        "organization": "Staff Selection Commission",
        "category": "SSC",
        "description": (
            "Tier-I runs until 30 Oct 2026. "
            "The admit card is on https://ssc.gov.in/."
        ),
        "eligibility": "",
        "official_link": (
            "https://ssc.gov.in/api/attachment/uploads/masterData/"
            "NoticeBoards/cgle_2026_city_live_21092026.pdf"
        ),
        "source_name": "SSC city and admit card notice, 21 Sep 2026",
        "registration_board": "none",
    },
    {
        "title": "SSC Junior Engineer 2026 Admit Card | Coming : 02/11/2026",
        "organization": "Staff Selection Commission",
        "category": "SSC",
        "description": (
            "Exam city is live on https://ssc.gov.in/. "
            "The admit card is issued about 2 to 3 days before Paper-I, which starts on 2 Nov 2026."
        ),
        "eligibility": "",
        "official_link": (
            "https://ssc.gov.in/api/attachment/uploads/masterData/"
            "NoticeBoards/JE_2026_City_Live_Notice_23102026.pdf"
        ),
        "source_name": "SSC city and admit card notice, 23 Oct 2026",
        "registration_board": "none",
    },
    {
        "title": "Railway RRB CEN 04/2026 Admit Card | Out : 23/10/2026",
        "organization": "Railway Recruitment Boards",
        "category": "Railway",
        "description": (
            "The e-call letter was listed on 23 Oct 2026. "
            "Official site: https://rrb.indianrailways.gov.in/"
        ),
        "eligibility": "",
        "official_link": "https://rrb.indianrailways.gov.in/chennai",
        "source_name": "RRB Chennai updates, 23 Oct 2026",
        "registration_board": "none",
    },
    {
        "title": "JEE Main 2027 Session 1 Admission | Last Date : 22/11/2026",
        "organization": "National Testing Agency",
        "category": "NTA",
        "description": (
            "Admission form is open from 24 Oct 2026 until 22 Nov 2026. "
            "Apply at https://jeemain.nta.nic.in/"
        ),
        "eligibility": "",
        "official_link": "https://nta.ac.in/Download/Notice/Notice_20261024220013.pdf",
        "source_name": "NTA public notice, 24 Oct 2026",
        "registration_board": "none",
    },
    {
        "title": "NIFTEE 2027 Admission | Last Date : 16/11/2026",
        "organization": "National Testing Agency",
        "category": "NTA",
        "description": (
            "Admission form for NIFT programmes is open until 16 Nov 2026."
        ),
        "eligibility": "",
        "official_link": "https://www.nta.ac.in/Download/Notice/Notice_20261016183525.pdf",
        "source_name": "NTA public notice, 16 Oct 2026",
        "registration_board": "none",
    },
    {
        "title": "Kamareddy AYUSH Outsourcing | Last Date : 31/10/2026",
        "organization": "District Kamareddy, Government of Telangana",
        "category": "Outsourcing",
        "description": (
            "Outsourcing applications are open from 24 Oct 2026 to 31 Oct 2026."
        ),
        "eligibility": "",
        "official_link": "https://kamareddy.telangana.gov.in/notice/nam-outsouring-recruitment/",
        "source_name": "Kamareddy district notice, 24 Oct 2026",
        "registration_board": "none",
    },
    {
        "title": "Yadadri Bhuvanagiri AYUSH Outsourcing | Last Date : 04/11/2026",
        "organization": "Yadadri Bhuvanagiri District, Government of Telangana",
        "category": "Outsourcing",
        "description": (
            "Eight outsourcing posts in the Ayush department. "
            "Applications run from 28 Oct 2026 to 4 Nov 2026."
        ),
        "eligibility": "",
        "official_link": "https://yadadri.telangana.gov.in/notice_category/recruitment/",
        "source_name": "Yadadri Bhuvanagiri district notice, 28 Oct 2026",
        "registration_board": "none",
    },
)


def publish_official_notices():
    """Save each official notice once. The same link keeps one row."""
    grouped = {}
    for item in list_vacancies():
        grouped.setdefault(item.get("official_link"), []).append(item)
    added = []
    for notice in OFFICIAL_NOTICES:
        matches = grouped.get(notice["official_link"], [])
        if not matches:
            added.append(create_vacancy(**notice))
            continue
        current = matches[0]
        same = (
            current.get("title") == notice["title"]
            and (current.get("application_end") or "") == notice.get("application_end", "")
        )
        if not same:
            update_vacancy(current["id"], **notice)
            added.append(current["id"])
        for extra in matches[1:]:
            delete_vacancy(extra["id"])
    return added
