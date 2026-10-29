from app.official_notices import OFFICIAL_NOTICES, publish_official_notices
from app import vacancy


def test_official_notices_save_once(monkeypatch, tmp_path):
    monkeypatch.setattr(vacancy, "DB_PATH", tmp_path / "notices.db")
    vacancy.init_vacancy_db()

    first = publish_official_notices()
    second = publish_official_notices()
    saved = vacancy.list_vacancies()

    assert len(first) == len(OFFICIAL_NOTICES)
    assert second == []
    assert len(saved) == len(OFFICIAL_NOTICES)
    links = {item["official_link"] for item in saved}
    assert "https://www.rrbapply.gov.in/" in links
    assert "https://ssc.gov.in/" not in links
    open_titles = {item["title"] for item in saved if item["status"] == "open"}
    assert any("CEN 08/2026" in title for title in open_titles)
    assert any("CEN 06/2026" in title for title in open_titles)
    assert all(item["registration_board"] in {"ssc", "rrb", "none"} for item in saved)
    result_titles = {item["title"] for item in saved if "Result" in item["title"]}
    assert any("Constable GD 2026" in title for title in result_titles)
    assert any("CHSL 2025" in title for title in result_titles)
    assert any("Stenographer" in title for title in result_titles)
    assert "https://ssc.gov.in/api/attachment/uploads/masterData/Results/writeup_12102026.pdf" in links
    assert any("Answer Key" in item["title"] for item in saved)
    assert any("Admit Card" in item["title"] for item in saved)
    assert any("Admission" in item["title"] for item in saved)
    assert "https://nta.ac.in/Download/Notice/Notice_20261024220013.pdf" in links
    assert any("Outsourcing" in item["title"] for item in saved)

    vacancy.create_vacancy(
        "RRB NTPC 2026",
        "Railway",
        official_link="https://www.rrbapply.gov.in/",
        registration_board="rrb",
    )
    publish_official_notices()
    refreshed = [
        item for item in vacancy.list_vacancies()
        if item["official_link"] == "https://www.rrbapply.gov.in/"
    ]
    assert len(refreshed) == 1
    assert refreshed[0]["application_end"] == "2026-11-06"
    assert "CEN 06/2026" in refreshed[0]["title"]
